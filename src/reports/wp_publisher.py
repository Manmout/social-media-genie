"""
WordPress publisher — renders trend reports into WP-optimized HTML
and publishes to hemle.blog via REST API.

Supports two modes:
  1. "draft" — generates WP-ready HTML + saves locally (for manual paste)
  2. "publish" — auto-publishes via WordPress REST API
"""

from __future__ import annotations

import html as html_mod
from pathlib import Path
from datetime import datetime

from src.reports.trend_report import (
    TrendReport,
    PestalEntry,
    JobToBeDone,
    Competitor,
    MarketPlayer,
    TimelineEvent,
)
from src.apis.wordpress import WordPressClient
from src.utils.logger import get_logger
from config import settings

log = get_logger("wp-publisher")

WP_TEMPLATE_PATH = Path(__file__).resolve().parent.parent.parent / "templates" / "wp_trend_post.html"
HOME_TEMPLATE_PATH = Path(__file__).resolve().parent.parent.parent / "templates" / "wp_pages" / "home_forest.html"
REPORTS_DIR = settings.OUTPUT_DIR / "reports"

# WordPress.com v1.1 page ID for the homepage (hemle.blog/)
HOME_PAGE_ID = 13

# ── Trend Signal nav & footer — injected into every published post ──
# WordPress.com Personal has no functions.php, so we wrap post content
# with inline HTML. Forest green palette (#1A1F1A / #2D3A2D / #EDE8E2).

TS_NAV = """
<nav style="background:#1A1F1A;display:flex;align-items:center;
justify-content:space-between;padding:0 2.5rem;height:56px;
font-family:system-ui,-apple-system,sans-serif;
position:sticky;top:0;z-index:100;">
  <a href="https://hemle.blog/" style="color:#EDE8E2;font-size:13px;
     letter-spacing:0.14em;text-decoration:none;text-transform:uppercase;
     font-weight:500;">Trend Signal</a>
  <ul style="display:flex;gap:2rem;list-style:none;margin:0;padding:0;">
    <li><a href="https://hemle.blog/blog/" style="color:#8BA886;
       font-size:13px;text-decoration:none;">Rapports</a></li>
    <li><a href="https://hemle.blog/a-propos/" style="color:#8BA886;
       font-size:13px;text-decoration:none;">\u00c0 propos</a></li>
  </ul>
  <a href="https://hemle.blog/sabonner/" style="background:#2D3A2D;
     color:#EDE8E2;padding:0.45rem 1.1rem;border-radius:6px;font-size:12px;
     font-weight:600;text-decoration:none;">S\u2019abonner</a>
</nav>
"""

TS_FOOTER = """
<footer style="background:#1A1F1A;padding:2rem 2.5rem;
display:flex;justify-content:space-between;align-items:center;
border-top:1px solid rgba(45,58,45,0.18);margin-top:4rem;
font-family:system-ui,-apple-system,sans-serif;">
  <span style="font-size:11px;letter-spacing:0.1em;
     text-transform:uppercase;color:#EDE8E2;">Trend Signal par Hemle</span>
  <div style="display:flex;gap:1.5rem;">
    <a href="https://hemle.blog/blog/" style="font-size:11px;
       color:#8BA886;text-decoration:none;">Rapports</a>
    <a href="https://hemle.blog/a-propos/" style="font-size:11px;
       color:#8BA886;text-decoration:none;">\u00c0 propos</a>
    <a href="https://hemle.blog/sabonner/" style="font-size:11px;
       color:#8BA886;text-decoration:none;">S\u2019abonner</a>
  </div>
  <span style="font-size:10px;color:#8BA886;">\u00a9 2026 Hemle</span>
</footer>
"""


class WPPublisher:
    """Renders trend reports for WordPress and optionally publishes them."""

    def __init__(self):
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        self.wp = WordPressClient()

    async def publish(
        self,
        report: TrendReport,
        *,
        status: str = "draft",
        tier: str = "pro",
        images: dict | None = None,
    ) -> dict:
        """
        Render and publish a trend report to hemle.blog.

        Args:
            report: TrendReport data
            status: "draft" or "publish"
            tier: "free" (truncated + CTA) or "pro" (full report)
            images: dict from ImagePipeline {"hero": Path, "og_image": Path, ...}

        Returns:
            dict with 'id', 'link', 'status', 'local_file'
        """
        # Render WordPress-optimized HTML
        content = self._render(report, tier=tier, hero_image=images.get("hero") if images else None)

        # Save local copy
        slug = report.trend_name.lower().replace(" ", "-").replace("/", "-")
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        local_path = REPORTS_DIR / f"wp_{slug}_{stamp}.html"
        local_path.write_text(content, encoding="utf-8")
        log.info(f"WP content saved locally: {local_path}")

        # Build SEO excerpt
        excerpt = self._build_excerpt(report)

        # Determine categories and tags (comma-separated for WP.com API v1.1)
        cats = ["Trend Intelligence"]
        if "AI" in report.category or "ai" in report.category.lower():
            cats.append("AI & Technology")
        if report.status == "surging":
            cats.append("Surging Trends")
        categories_csv = ",".join(cats)

        raw_tags = [slug, report.status, "trend-analysis", "market-intelligence"]
        try:
            from src.content.tag_optimizer import TagOptimizer
            optimizer = TagOptimizer()
            tag_result = await optimizer.optimize(
                seed_tags=raw_tags,
                category=report.category,
                trend_name=report.trend_name,
            )
            tags_csv = ",".join(tag_result.tags)
        except Exception as e:
            log.warning(f"Tag optimization failed: {e}. Using raw tags.")
            tags_csv = ",".join(raw_tags)

        # Publish via API
        try:
            result = await self.wp.create_post(
                title=f"{report.trend_name} — Trend Intelligence Report",
                content=content,
                excerpt=excerpt,
                categories=categories_csv,
                tags=tags_csv,
                status=status,
                slug=f"trend-{slug}",
            )
            result["local_file"] = str(local_path)

            # Update homepage hero with latest report
            try:
                await self.update_home_hero(report)
            except Exception as e:
                log.warning(f"Homepage hero update failed: {e}")

            # Upload OG image as featured media
            og_path = images.get("og_image") if images else None
            if og_path and og_path.exists() and result.get("id"):
                try:
                    media_id = await self.wp.upload_media(str(og_path))
                    if media_id:
                        await self.wp.update_post(result["id"], featured_image=str(media_id))
                        result["featured_image"] = media_id
                        log.info(f"Featured image set: media_id={media_id}")
                except Exception as e:
                    log.warning(f"Featured image upload failed: {e}")

            return result
        except Exception as e:
            log.warning(f"API publish failed ({e}). Content saved locally at {local_path}")
            return {
                "id": None,
                "link": None,
                "status": "local_only",
                "local_file": str(local_path),
                "error": str(e),
            }

    async def update_home_hero(self, report: TrendReport) -> dict:
        """
        Update the homepage hero section with the latest published report.

        Reads home_forest.html template, replaces the three hero placeholders
        with data from the report, extracts the <body> content, and pushes
        it to the homepage (page ID 13) via WordPress.com API v1.1.
        """
        if not HOME_TEMPLATE_PATH.exists():
            raise FileNotFoundError(f"Home template not found: {HOME_TEMPLATE_PATH}")

        html = HOME_TEMPLATE_PATH.read_text(encoding="utf-8")

        # Build dynamic values
        title = html_mod.escape(f"{report.trend_name} — Trend Intelligence Report")
        excerpt = html_mod.escape(self._build_excerpt(report))
        slug = report.trend_name.lower().replace(" ", "-").replace("/", "-")
        url = f"https://hemle.blog/trend-{slug}/"

        # Replace placeholders
        html = html.replace("{{LATEST_REPORT_TITLE}}", title)
        html = html.replace("{{LATEST_REPORT_EXCERPT}}", excerpt)
        html = html.replace("{{LATEST_REPORT_URL}}", url)

        # Extract content between <body> and </body> (strip HTML envelope)
        import re
        style_match = re.search(r"<style>(.*?)</style>", html, re.DOTALL)
        style_block = f"<style>{style_match.group(1)}</style>" if style_match else ""
        body_match = re.search(r"<body[^>]*>(.*)</body>", html, re.DOTALL)
        body_content = body_match.group(1).strip() if body_match else html

        wp_content = f"{style_block}\n{body_content}"

        # Push to WordPress
        result = await self.wp.update_post(HOME_PAGE_ID, content=wp_content)
        log.info(f"Homepage hero updated with: {report.trend_name}")
        return result

    def _render(self, r: TrendReport, tier: str = "pro", hero_image: "Path | None" = None) -> str:
        """Render the WP template with report data."""
        template = WP_TEMPLATE_PATH.read_text(encoding="utf-8")

        # Insert hero image at top if provided
        if hero_image and hero_image.exists():
            import base64
            b64 = base64.b64encode(hero_image.read_bytes()).decode()
            hero_html = (
                f'<div style="margin:0 0 24px;text-align:center;">'
                f'<img src="data:image/png;base64,{b64}" alt="{_esc(r.trend_name)}" '
                f'style="width:100%;max-width:700px;border-radius:8px;"/>'
                f'</div>'
            )
            # Inject after opening div
            template = template.replace(
                '<!-- HERO -->',
                f'{hero_html}\n<!-- HERO -->',
            )

        # Badge background
        badge_bg_map = {
            "surging": "#dcfce7",
            "steady": "#fef9c3",
            "peaked": "#fee2e2",
        }

        replacements = {
            "TREND_NAME": _esc(r.trend_name),
            "STATUS_UPPER": r.status.upper(),
            "STATUS_COLOR": r.status_color(),
            "BADGE_BG": badge_bg_map.get(r.status, "#f3f4f6"),
            "CATEGORY": _esc(r.category),
            "SEARCH_VOLUME": _esc(r.search_volume),
            "GENERATED_AT": _esc(r.generated_at),
            "GROWTH_5Y": _esc(r.growth.five_year),
            "GROWTH_1Y": _esc(r.growth.one_year),
            "GROWTH_3M": _esc(r.growth.three_month),
            "TIMELINE_ITEMS": self._render_timeline(r.timeline),
            "PESTAL_ROWS": self._render_pestal(r.pestal),
            "JTBD_CARDS": self._render_jtbd(r.jobs_to_be_done),
            "CANVAS_WHO": _esc(r.canvas_who),
            "CANVAS_WHERE": _esc(r.canvas_where),
            "CANVAS_WHY_NOW": _esc(r.canvas_why_now),
            "CANVAS_BEHAVIOR": _esc(r.canvas_behavior),
            "CANVAS_UNMET": _esc(r.canvas_unmet),
            "MARKET_BARS": self._render_market_bars(r.market_players),
            "COMPANIES_CARDS": self._render_companies(r.competitors),
            "NOTEBOOK_SECTION": self._render_notebook(r.notebook_insights) if r.notebook_insights else "",
            "CTA_SECTION": self._render_cta() if tier == "free" else "",
            "TAKEAWAY_ITEMS": self._render_takeaways(r.takeaways, tier=tier),
        }

        rendered = template
        for key, value in replacements.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", value)

        # Append subscribe CTA at end of every report
        rendered += self._render_subscribe_cta()

        # Wrap with Trend Signal nav + footer
        rendered = TS_NAV + rendered + TS_FOOTER

        return rendered

    def _build_excerpt(self, r: TrendReport) -> str:
        """Plain-text excerpt for WordPress (max ~150 words, no HTML)."""
        import re as _re
        # Build from trigger + first takeaways (most descriptive fields)
        parts: list[str] = []
        if r.trigger:
            parts.append(r.trigger.strip())
        for t in r.takeaways[:2]:
            parts.append(t.strip())
        raw = " ".join(parts) if parts else f"{r.trend_name} trend analysis."
        # Strip any residual HTML tags
        clean = _re.sub(r"<[^>]+>", "", raw)
        # Trim to ~150 words
        words = clean.split()
        if len(words) > 150:
            clean = " ".join(words[:147]) + "..."
        return clean

    # ── Section renderers (using CSS classes from template) ──────

    def _render_timeline(self, events: list[TimelineEvent]) -> str:
        if not events:
            return ''
        return "\n".join(
            f'<div class="ts-tl-item">'
            f'<div class="ts-tl-left"><span class="ts-tl-date">{_esc(ev.date)}</span></div>'
            f'<div class="ts-tl-line"><div class="ts-tl-dot"></div></div>'
            f'<div class="ts-tl-right">{_esc(ev.event)}</div>'
            f'</div>'
            for ev in events
        )

    def _render_pestal(self, entries: list[PestalEntry]) -> str:
        if not entries:
            return '<tr><td colspan="2" style="text-align:center;color:#9b7fd4;padding:12px;">—</td></tr>'
        css_map = {"Political": "pol", "Economic": "eco", "Social": "soc",
                   "Technological": "tec", "Environmental": "env", "Legal": "leg"}
        return "\n".join(
            f'<tr>'
            f'<td><span class="ts-badge-factor {css_map.get(e.factor, "soc")}">{_esc(e.factor)}</span></td>'
            f'<td>{_esc(e.impact)}</td>'
            f'</tr>'
            for e in entries
        )

    def _render_jtbd(self, jobs: list[JobToBeDone]) -> str:
        if not jobs:
            return ''
        return "\n".join(
            f'<div class="ts-job">'
            f'<div class="ts-job-title">{_esc(j.job)}</div>'
            f'<div class="ts-job-desc">{_esc(j.solution)}</div>'
            f'</div>'
            for j in jobs
        )

    def _render_market_bars(self, players: list[MarketPlayer]) -> str:
        if not players:
            return ''
        colors = ["#7b4fd4", "#0e7a5a", "#3b82f6", "#f59e0b"]
        parts = []
        for i, p in enumerate(players):
            num = "".join(c for c in p.share if c.isdigit() or c == ".")
            width = min(float(num) if num else 10, 100)
            parts.append(
                f'<div class="ts-market-row">'
                f'<div class="ts-market-name">{_esc(p.name)}</div>'
                f'<div class="ts-market-bar-wrap">'
                f'<div class="ts-market-bar" style="width:{width}%;background:{colors[i % 4]}">{_esc(p.share)}</div>'
                f'</div>'
                f'<div class="ts-market-pct">{_esc(p.loved)}</div>'
                f'</div>'
            )
        return "\n".join(parts)

    def _render_companies(self, companies: list[Competitor]) -> str:
        if not companies:
            return ''
        return "\n".join(
            f'<div class="ts-company">'
            f'<div class="ts-company-name">{_esc(c.name)}</div>'
            f'<div class="ts-company-desc">{_esc(c.detail)}</div>'
            f'</div>'
            for c in companies
        )

    def _render_notebook(self, insights: str) -> str:
        if not insights:
            return ""
        return (
            f'<div class="ts-nb">'
            f'<h3>&#x1F4D3; NotebookLM Research Insights</h3>'
            f'<div class="nb-body">{_esc(insights)}</div>'
            f'</div>'
        )

    def _render_cta(self) -> str:
        return (
            '<div class="ts-cta-box">'
            '<h3>Débloquez le rapport complet</h3>'
            '<p>Analyse PESTAL, positionnement marché, insights NotebookLM et recommandations — chaque semaine.</p>'
            '<a href="https://hemle.blog/sabonner/" class="ts-cta-btn">S\'abonner Pro — 19€/mois</a>'
            '</div>'
        )

    def _render_subscribe_cta(self) -> str:
        """End-of-article subscribe CTA — always rendered for all tiers."""
        return (
            '<div class="ts-end-cta">'
            '<h3>Ne manquez aucun signal.</h3>'
            '<p>2 rapports Trend Signal par mois en acc\u00e8s libre. '
            'Passez Pro pour un acc\u00e8s illimit\u00e9 et les donn\u00e9es brutes.</p>'
            '<a href="https://hemle.blog/sabonner/">S\u2019abonner gratuitement</a>'
            '</div>'
        )

    # CSS for the subscribe CTA — inject into <style> block of template
    SUBSCRIBE_CTA_CSS = (
        '.ts-end-cta{background:#2D3A2D;padding:40px 24px;text-align:center;'
        'margin-top:40px;border-radius:10px}'
        '.ts-end-cta h3{font-size:22px;font-weight:700;color:#EDE8E2;margin:0 0 10px}'
        '.ts-end-cta p{color:#8BA886;font-size:15px;margin:0 0 20px;'
        'max-width:480px;margin-left:auto;margin-right:auto}'
        '.ts-end-cta a{display:inline-block;background:#EDE8E2;color:#1A1F1A;'
        'padding:12px 28px;font-weight:700;text-decoration:none;border-radius:8px;font-size:14px}'
        '.ts-end-cta a:hover{background:#fff}'
    )

    def _render_takeaways(self, takeaways: list[str], tier: str = "pro") -> str:
        if not takeaways:
            return ''
        items = takeaways if tier == "pro" else takeaways[:2]
        parts = []
        for i, t in enumerate(items, 1):
            parts.append(
                f'<div class="ts-rec">'
                f'<div class="ts-rec-num">{i}</div>'
                f'<div class="ts-rec-text">{_esc(t)}</div>'
                f'</div>'
            )
        if tier == "free" and len(takeaways) > 2:
            parts.append(
                f'<div class="ts-rec" style="opacity:0.4;filter:blur(3px)">'
                f'<div class="ts-rec-num">3</div>'
                f'<div class="ts-rec-text">{_esc(takeaways[2])}</div>'
                f'</div>'
            )
            parts.append(
                '<div class="ts-cta-box">'
                '<a href="https://hemle.blog/sabonner/" style="color:#7b4fd4;font-weight:600;text-decoration:none;font-size:13px;">'
                f'+ {len(takeaways) - 2} recommandations — S\'abonner pour débloquer →</a>'
                '</div>'
            )
        return "\n".join(parts)


def _esc(text: str) -> str:
    return html_mod.escape(str(text)) if text else ""
