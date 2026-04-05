"""
Tumblr publisher — creates NPF (Neue Post Format) posts on hemle.tumblr.com.

Uses structured content blocks instead of raw HTML for native Tumblr rendering.
Supports optional tumblr_header image injection via --with-image.
"""

from __future__ import annotations

from pathlib import Path

from src.reports.trend_report import TrendReport, TimelineEvent
from src.reports.newsletter_publisher import NewsletterPublisher
from src.apis.tumblr import TumblrClient
from src.utils.logger import get_logger

log = get_logger("tumblr-publisher")

_MONTH_EN_FR = {
    "Jan ": "Jan. ", "Feb ": "Fév. ", "Mar ": "Mars ", "Apr ": "Avr. ",
    "May ": "Mai ", "Jun ": "Juin ", "Jul ": "Juil. ", "Aug ": "Août ",
    "Sep ": "Sept. ", "Oct ": "Oct. ", "Nov ": "Nov. ", "Dec ": "Déc. ",
    "Early ": "Début ", "Mid ": "Mi-", "Late ": "Fin ",
}


_LABELS = {
    "fr": {
        "timeline": "CHRONOLOGIE",
        "takeaways": "POINTS ACTIONNABLES",
        "cta": "Lire le rapport complet →",
        "footer": "Trend Signal par Hemle · Intelligence marché alimentée par l'IA",
    },
    "en": {
        "timeline": "TIMELINE",
        "takeaways": "ACTIONABLE TAKEAWAYS",
        "cta": "Read the full report →",
        "footer": "Trend Signal by Hemle · AI-powered market intelligence",
    },
}


class TumblrPublisher:
    """Publishes trend reports to Tumblr using NPF content blocks."""

    def __init__(self, blog: str = "hemle"):
        self.tumblr = TumblrClient(blog=blog)

    async def publish(
        self,
        report: TrendReport,
        *,
        state: str = "published",
        report_url: str = "",
        blog: str | None = None,
        images: dict | None = None,
        lang: str = "fr",
    ) -> dict:
        """Build NPF payload and publish to Tumblr."""
        if not report_url:
            slug = report.trend_name.lower().replace(" ", "-").replace("/", "-")
            report_url = f"https://hemle.blog/trend-{slug}/"

        editorial = self._build_editorial(report, report_url, lang)
        content = self._build_npf_content(report, editorial, images, lang)

        # Optimize tags via Keywords Everywhere (lang-aware)
        raw_tags = self._build_tags(report, lang)
        try:
            from src.content.tag_optimizer import TagOptimizer
            optimizer = TagOptimizer()
            tag_result = await optimizer.optimize(
                seed_tags=raw_tags,
                category=report.category,
                trend_name=report.trend_name,
                country="fr" if lang == "fr" else "us",
            )
            tags = tag_result.tags
        except Exception as e:
            log.warning(f"Tag optimization failed: {e}. Using raw tags.")
            tags = raw_tags

        # Build media_sources if we have a tumblr_header image
        media_sources = None
        tumblr_img = images.get("tumblr_header") if images else None
        if tumblr_img and Path(tumblr_img).exists():
            media_sources = {"tumblr_header": str(tumblr_img)}

        result = await self.tumblr.create_npf_post(
            content=content,
            tags=tags,
            state=state,
            blog=blog,
            media_sources=media_sources,
        )
        return result

    # ── NPF content builder ──────────────────────────────────

    def _build_npf_content(self, report: TrendReport, editorial: dict, images: dict | None = None, lang: str = "fr") -> list:
        content = []

        # Tumblr header image — NPF identifier block (uploaded via multipart)
        tumblr_img = images.get("tumblr_header") if images else None
        if tumblr_img and Path(tumblr_img).exists():
            content.append({
                "type": "image",
                "media": [{"type": "image/png", "identifier": "tumblr_header"}],
            })

        # Header — translate category if FR
        cat_display = self._translate_category(report.category, lang)
        content.append({
            "type": "text",
            "text": f"TREND SIGNAL · {cat_display.upper()}",
            "subtype": "heading2",
        })

        content.append({
            "type": "text",
            "text": report.trend_name,
            "subtype": "heading1",
        })

        # Status + metrics
        status_label = self._status_label(report.status, lang)
        metric_labels = {"fr": ("1 an", "3 mois"), "en": ("1 year", "3 months")}
        y_label, m_label = metric_labels.get(lang, metric_labels["fr"])
        content.append({
            "type": "text",
            "text": f"● {status_label}   ·   {y_label} {report.growth.one_year}   ·   {m_label} {report.growth.three_month}",
        })

        # Hook (italic)
        hook = editorial["hook"]
        content.append({
            "type": "text",
            "text": hook,
            "formatting": [{"start": 0, "end": len(hook), "type": "italic"}],
        })

        # Timeline + takeaways: translate if FR, keep English if EN
        if lang == "fr":
            translator = NewsletterPublisher()
            timeline = translator._translate_timeline(report.timeline)
            takeaways = translator._translate_takeaways(report.takeaways)
            warnings = translator._validate_translation(timeline, takeaways)
            for w in warnings:
                log.warning(f"Mixed language in Tumblr post: {w}")
        else:
            timeline = report.timeline
            takeaways = report.takeaways

        # Section labels
        L = _LABELS[lang]

        # Timeline
        if timeline:
            content.append({"type": "text", "text": f"— {L['timeline']} —", "subtype": "heading2"})
            for ev in timeline:
                date = self._translate_date(ev.date) if lang == "fr" else ev.date
                line = f"{date}  {ev.event}"
                content.append({
                    "type": "text",
                    "text": line,
                    "formatting": [{"start": 0, "end": len(date), "type": "bold"}],
                })

        # Takeaways
        if takeaways:
            content.append({"type": "text", "text": f"— {L['takeaways']} —", "subtype": "heading2"})
            for i, takeaway in enumerate(takeaways, 1):
                num = f"{i}."
                text = f"{num}  {takeaway}"
                content.append({
                    "type": "text",
                    "text": text,
                    "formatting": [{"start": 0, "end": len(num), "type": "bold"}],
                })

        # Body intro
        body = editorial.get("body_intro", "")
        if body:
            content.append({"type": "text", "text": body})

        # CTA link
        cta_text = editorial.get("cta_text", L["cta"])
        content.append({
            "type": "text",
            "text": cta_text,
            "formatting": [{
                "start": 0,
                "end": len(cta_text),
                "type": "link",
                "url": editorial.get("report_url", "https://hemle.blog"),
            }],
        })

        # Footer
        footer = L["footer"]
        content.append({
            "type": "text",
            "text": footer,
            "formatting": [{"start": 0, "end": 12, "type": "bold"}],
        })

        return content

    # ── Editorial layer ──────────────────────────────────────

    def _build_editorial(self, r: TrendReport, report_url: str, lang: str = "fr") -> dict:
        L = _LABELS[lang]
        if lang == "fr":
            verb = {"surging": "explose", "steady": "se maintient", "peaked": "ralentit"}.get(r.status, "évolue")
            hook = f"{r.trend_name} {verb}. Volume de recherche : {r.search_volume}. Croissance sur 1 an : {r.growth.one_year}."
            body_intro = f"{r.trend_name} affiche une croissance de {r.growth.one_year} sur un an et {r.growth.three_month} sur les 3 derniers mois."
        else:
            verb = {"surging": "is exploding", "steady": "holds steady", "peaked": "is cooling down"}.get(r.status, "is trending")
            hook = f"{r.trend_name} {verb}. Search volume: {r.search_volume}. 1-year growth: {r.growth.one_year}."
            body_intro = f"{r.trend_name} shows {r.growth.one_year} year-over-year growth and {r.growth.three_month} over the last 3 months."
        return {
            "hook": hook,
            "body_intro": body_intro,
            "cta_text": L["cta"],
            "report_url": report_url,
        }

    # ── Helpers ──────────────────────────────────────────────

    def _status_label(self, status: str, lang: str = "fr") -> str:
        labels = {
            "fr": {"surging": "En explosion", "steady": "Stable", "peaked": "En recul"},
            "en": {"surging": "Surging", "steady": "Steady", "peaked": "Peaked"},
        }
        return labels.get(lang, labels["fr"]).get(status.lower(), status.capitalize())

    _CAT_EN_FR = {
        "technology": "Technologie",
        "ai": "IA",
        "agentic coding": "Coding Agentique",
        "music generation": "Génération Musicale",
        "enterprise automation": "Automatisation Entreprise",
        "business": "Business",
        "health": "Santé",
        "entertainment": "Divertissement",
        "saas": "SaaS",
        "creator economy": "Économie des Créateurs",
    }

    def _translate_category(self, category: str, lang: str) -> str:
        if lang != "fr":
            return category
        parts = category.split(">")
        translated = []
        for part in parts:
            clean = part.strip()
            fr = self._CAT_EN_FR.get(clean.lower(), clean)
            translated.append(f" {fr} ")
        return ">".join(translated).strip()

    def _translate_date(self, date: str) -> str:
        result = date
        for en, fr in _MONTH_EN_FR.items():
            result = result.replace(en, fr)
        return result

    def _build_tags(self, report: TrendReport, lang: str = "fr") -> list[str]:
        slug = report.trend_name.lower().replace(" ", "-").replace("/", "-")
        tags = ["trend-signal", slug]

        if lang == "fr":
            status_tags = {"surging": "en-explosion", "steady": "stable", "peaked": "en-recul"}
            tags.append(status_tags.get(report.status, report.status))
            # French category translations
            cat_fr = {
                "technology": "technologie", "ai": "intelligence-artificielle",
                "agentic coding": "coding-agentique", "music generation": "génération-musicale",
                "enterprise automation": "automatisation-entreprise",
                "business": "business", "health": "santé", "entertainment": "divertissement",
            }
            for part in report.category.lower().split(">"):
                t = part.strip()
                fr = cat_fr.get(t, t.replace(" ", "-"))
                if fr:
                    tags.append(fr)
            tags.extend(["analyse-tendance", "intelligence-marché"])
        else:
            tags.append(report.status)
            for part in report.category.lower().split(">"):
                t = part.strip().replace(" ", "-")
                if t:
                    tags.append(t)
            tags.extend(["trend-analysis", "market-intelligence"])

        return tags[:20]
