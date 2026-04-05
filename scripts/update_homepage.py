"""
Auto-update hemle.blog homepage with latest reports.
Reads published posts via MCP-compatible WordPress API, rebuilds the
hero section + 3 latest report cards, and pushes to page ID 13 via MCP CLI.

Usage:
    py -3.13 scripts/update_homepage.py
    py -3.13 scripts/update_homepage.py --dry-run   # preview without publishing
"""
import sys
import json
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── Configuration ──────────────────────────────────────────────
HOMEPAGE_MCP_ID = 13
MAX_CARDS = 3
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Collect latest reports from local data files ───────────────
def get_latest_reports():
    """Read all trend data JSONs and return sorted by recency."""
    reports_dir = PROJECT_ROOT / "output" / "reports"
    reports = []

    for f in sorted(reports_dir.glob("*-trend-data.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            reports.append({
                "name": d.get("trend_name", f.stem),
                "category": d.get("category", "AI & Technology"),
                "status": d.get("status", "surging"),
                "trigger": d.get("trigger", "")[:120],
                "search_volume": d.get("search_volume", "N/A")[:30],
                "slug": f.stem.replace("-trend-data", ""),
                "file": str(f),
            })
        except Exception as e:
            print(f"  Skip {f.name}: {e}")

    return reports


# ── URL mapping (slug → live URL) ─────────────────────────────
URL_MAP = {
    "agentic-ai": "https://hemle.blog/2026/03/29/trend-agentic-ai/",
    "suno-ai": "https://hemle.blog/2026/03/29/trend-suno-ai/",
    "claude-code": "https://hemle.blog/2026/03/29/trend-claude-code/",
    "agentic-music-composition": "https://hemle.blog/2026/04/05/trend-agentic-music-composition/",
    "open-source-ai-agents-smb": "https://hemle.blog/2026/04/05/trend-open-source-ai-agents-pme/",
    "vibe-coding": "https://hemle.blog/2026/04/05/trend-vibe-coding/",
    "ai-video-creative-direction": "https://hemle.blog/2026/04/05/trend-ai-video-creative-direction/",
}


def slug_to_url(slug):
    if slug in URL_MAP:
        return URL_MAP[slug]
    # Fallback: guess URL from slug
    return f"https://hemle.blog/trend-{slug}/"


# ── Build homepage HTML ────────────────────────────────────────
def build_homepage(reports):
    total = len(reports)
    hero = reports[0]
    cards = reports[:MAX_CARDS]

    hero_url = slug_to_url(hero["slug"])
    hero_excerpt = hero["trigger"][:150]

    # Cards HTML
    cards_html = ""
    for i, r in enumerate(cards):
        border = 'border-left:2px solid #2D3A2D;' if i == 0 else ''
        url = slug_to_url(r["slug"])
        cards_html += f"""<div class="card" style="background-color:#ffffff;padding:2rem;transition:all 0.2s;{border}">
<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:3rem;">
<span style="font-family:'Space Grotesk',monospace;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;color:#7a757d;">IA &amp; Technologie</span>
<span style="font-family:'Space Grotesk',monospace;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;color:#0a5c42;">En hausse</span>
</div>
<h3 class="card-title" style="font-family:'Newsreader',serif;font-size:1.875rem;margin:0 0 1.5rem 0;">{r['name']}</h3>
<p style="font-family:'Inter',sans-serif;font-size:0.875rem;color:#49454c;line-height:1.625;margin:0 0 2rem 0;">{r['trigger'][:120]}</p>
<a class="card-link" href="{url}" style="font-family:'Space Grotesk',monospace;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;display:flex;align-items:center;text-decoration:none;color:#2D3A2D;">Analyse compl&egrave;te<svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" style="display:inline-block;vertical-align:middle;margin-left:4px;"><path d="M2 10L10 2M10 2H4M10 2V8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></a>
</div>
"""

    return f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,300;0,400;0,700;1,300&family=Inter:wght@400;700&family=Space+Grotesk:wght@300;400;700&display=swap');
body.page-id-13 .content-area, body.page-id-13 .entry-content-wrap, body.page-id-13 .site-main {{ margin:0!important;padding:0!important;max-width:none!important; }}
body.page-id-13 .entry-content {{ max-width:none!important;padding:0!important; }}
* {{ box-sizing:border-box; }}
::selection {{ background:#2D3A2D;color:white; }}
.three-col > p, .three-col > p:empty {{ display:none!important; }}
.card:hover {{ box-shadow:0 20px 40px rgba(26,31,26,0.08); }}
.card:hover .card-title {{ color:#2D3A2D!important; }}
.archive-link:hover {{ text-decoration:underline; }}
.card-link svg {{ transition:transform 0.15s; }}
.card-link:hover svg {{ transform:translate(2px,-2px); }}
@media(max-width:767px) {{ .three-col {{ grid-template-columns:1fr!important; }} .hero-h1 {{ font-size:2.5rem!important; }} }}
</style>

<section style="background:#1A1F1A;padding:64px 40px 56px;text-align:center">
<p style="font-family:'Space Grotesk',monospace;font-size:10px;letter-spacing:4px;color:#4A6741;text-transform:uppercase;margin:0 0 16px">Intelligence de march&eacute; &middot; Trend Signal</p>
<div style="display:inline-flex;align-items:center;gap:7px;border:1px solid #52b788;border-radius:100px;padding:5px 16px;margin-bottom:24px">
<span style="width:6px;height:6px;border-radius:50%;background:#52b788;display:inline-block"></span>
<span style="font-family:'Space Grotesk',monospace;font-size:10px;font-weight:600;letter-spacing:2px;color:#52b788;text-transform:uppercase">{total} rapports publi&eacute;s</span>
</div>
<h1 class="hero-h1" style="font-family:'Newsreader',serif;font-size:clamp(2.2rem,5vw,3.5rem);font-weight:400;color:#ffffff;line-height:1.15;margin:0 0 20px;max-width:720px;margin-left:auto;margin-right:auto">{hero['name']}</h1>
<p style="font-family:'Newsreader',serif;font-size:1.1rem;color:#4A6741;max-width:560px;margin:0 auto 36px;line-height:1.7;font-style:italic">{hero_excerpt}</p>
<a href="{hero_url}" style="display:inline-block;background:#2D3A2D;color:#ffffff;padding:14px 36px;font-family:'Space Grotesk',monospace;font-size:13px;letter-spacing:1px;text-decoration:none;text-transform:uppercase">Lire le rapport &rarr;</a>
</section>

<section style="background-color:#E5DFD8;padding:6rem 2rem;">
<div style="max-width:80rem;margin:0 auto;">
<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4rem;">
<h2 style="font-family:'Newsreader',serif;font-size:3rem;margin:0;">Derni&egrave;res analyses</h2>
<a class="archive-link" href="https://hemle.blog/rapports/" style="font-family:'Space Grotesk',monospace;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.1em;color:#2D3A2D;text-decoration:none;">Voir les archives</a>
</div>
<div class="three-col" style="display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background-color:rgba(45,58,45,0.15);">
{cards_html}
</div>
</div>
</section>

<section style="background-color:#EDE8E2;padding:8rem 2rem;">
<div style="max-width:80rem;margin:0 auto;">
<h2 style="font-family:'Space Grotesk',monospace;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.2em;margin:0 0 5rem 0;text-align:center;color:#7a757d;">M&eacute;thodologie</h2>
<div class="three-col" style="display:grid;grid-template-columns:repeat(3,1fr);gap:4rem;">
<div><span style="font-family:'Space Grotesk',monospace;font-size:2.25rem;font-weight:300;color:rgba(45,58,45,0.3);display:block;margin-bottom:1.5rem;">01</span><h3 style="font-family:'Space Grotesk',monospace;font-size:1.25rem;text-transform:uppercase;font-weight:700;margin:0 0 1.5rem;">Veille</h3><p style="font-family:'Inter',sans-serif;color:#49454c;line-height:1.625;margin:0;">Plus de 100 sources mondiales surveill&eacute;es en temps r&eacute;el.</p></div>
<div><span style="font-family:'Space Grotesk',monospace;font-size:2.25rem;font-weight:300;color:rgba(45,58,45,0.3);display:block;margin-bottom:1.5rem;">02</span><h3 style="font-family:'Space Grotesk',monospace;font-size:1.25rem;text-transform:uppercase;font-weight:700;margin:0 0 1.5rem;">Analyse</h3><p style="font-family:'Inter',sans-serif;color:#49454c;line-height:1.625;margin:0;">Cadres PESTAL, JTBD et positionnement concurrentiel.</p></div>
<div><span style="font-family:'Space Grotesk',monospace;font-size:2.25rem;font-weight:300;color:rgba(45,58,45,0.3);display:block;margin-bottom:1.5rem;">03</span><h3 style="font-family:'Space Grotesk',monospace;font-size:1.25rem;text-transform:uppercase;font-weight:700;margin:0 0 1.5rem;">Livraison</h3><p style="font-family:'Inter',sans-serif;color:#49454c;line-height:1.625;margin:0;">Rapports haute densit&eacute; pour la prise de d&eacute;cision.</p></div>
</div>
</div>
</section>

<section style="background:#1A1F1A;padding:64px 40px;text-align:center">
<p style="font-family:'Space Grotesk',monospace;font-size:10px;letter-spacing:3px;color:#8BA886;text-transform:uppercase;margin:0 0 16px">Newsletter</p>
<h2 style="font-family:'Newsreader',serif;font-size:clamp(1.8rem,4vw,2.8rem);font-weight:400;color:#ffffff;margin:0 0 16px;line-height:1.2">Restez en avance sur le march&eacute;.</h2>
<p style="font-family:'Newsreader',serif;font-size:1.05rem;color:#8BA886;max-width:480px;margin:0 auto 32px;line-height:1.7;font-style:italic">2 rapports Trend Signal par mois en acc&egrave;s libre.</p>
<a href="https://hemle.blog/sabonner/" style="display:inline-block;background:#2D3A2D;color:#ffffff;padding:14px 36px;text-decoration:none;font-family:'Space Grotesk',monospace;font-size:13px;letter-spacing:1px;text-transform:uppercase">S'abonner gratuitement &rarr;</a>
</section>"""


def main():
    dry_run = "--dry-run" in sys.argv

    print("Collecting reports...")
    reports = get_latest_reports()
    print(f"Found {len(reports)} reports:")
    for r in reports:
        print(f"  - {r['name']} ({r['slug']})")

    print("\nBuilding homepage HTML...")
    html = build_homepage(reports)
    print(f"Generated: {len(html)} chars")

    # Save locally
    out = PROJECT_ROOT / "output" / "reports" / "homepage_latest.html"
    out.write_text(html, encoding="utf-8")
    print(f"Saved: {out}")

    if dry_run:
        print("\n[DRY RUN] Skipping MCP publish.")
        return

    # The actual MCP push must be done from Claude Code (MCP tools)
    # This script prepares the content; Claude Code pushes it
    print(f"\nHomepage content ready for MCP push to page ID {HOMEPAGE_MCP_ID}.")
    print("Run in Claude Code:")
    print(f'  mcp__wordpress-com__wp_update_post(post_id={HOMEPAGE_MCP_ID}, type="pages", content=<content>)')


if __name__ == "__main__":
    main()
