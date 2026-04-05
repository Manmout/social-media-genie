# Social Media Genie

## What This Is
Content automation pipeline — Claude Code orchestrates 12 APIs to research trends, generate infographic reports, publish to WordPress, and produce Instagram Reels.

Two main workflows:
1. **Trend Intelligence** — scan → analyze → infographic → publish to hemle.blog
2. **Social Media** — script → voiceover → video → subtitles → publish to Instagram

## Stack
- **Language**: Python 3.13 (async/await throughout)
- **HTTP client**: httpx (async)
- **Config**: python-dotenv → `config/settings.py`
- **Video assembly**: FFmpeg (must be in PATH)
- **MCP server**: Node.js (WordPress.com API v1.1)
- **Blog**: hemle.blog (WordPress.com Personal plan)

## Project Structure
```
config/              — settings.py (loads .env), __init__.py
src/
  apis/              — One client per service (12 integrations)
    elevenlabs.py    — Text → MP3 voiceover
    remotion.py      — Composition + props → MP4 video (free)
    runway.py        — Text/image → cinematic video (paid)
    stability.py     — Text → image (PNG)
    openai_image.py  — DALL-E 3 image generation
    gemini_image.py  — Gemini Flash images
    heygen.py        — Script → avatar video
    instagram.py     — Publish reels/images, comments, DMs
    ayrshare.py      — Multi-platform scheduling
    whisper.py       — Audio → SRT subtitles
    keywords_everywhere.py — Keyword + competitor research
    wordpress.py     — WordPress.com API v1.1 (hemle.blog)
  orchestrator/
    pipeline.py      — Chains APIs into workflows
  reports/
    trend_report.py  — TrendReport dataclass (all analysis fields)
    generator.py     — HTML infographic renderer + NotebookLM integration
    wp_publisher.py  — WordPress-optimized renderer (free/pro tiers)
  content/
    niche_inspirer.py — Niche discovery + content calendar
  utils/
    cost_tracker.py  — API spend tracking
    brand_extractor.py — URL → brand kit JSON
    ffmpeg.py        — Video merge, subtitles, concat
    probe.py         — Media metadata
    logger.py        — Structured logging
templates/
  trend_infographic.html — Dark-theme standalone report (SVG sparkline)
  wp_trend_post.html     — Light-theme WordPress post template
  wp_pages/              — Home, About, Subscribe page templates
skills/                  — Skill docs (7 files)
mcp-wordpress/           — WordPress.com MCP server (Node.js)
  server.js              — 9 MCP tools for WP management
  get-token.js           — OAuth2 token helper
  package.json
output/
  reports/               — Generated HTML reports + JSON data files
  videos/   audio/   images/   subtitles/   avatars/   niches/   brands/
```

## Skills (in ./skills/)

### Remotion Video
1. **remotion-agent-setup.md** — Architecture, installation, MCP tools, troubleshooting
2. **remotion-reel-templates.md** — 4 compositions (KineticText, QuoteCard, Listicle, BeforeAfter)
3. **remotion-promo-video.md** — Full promo pipeline: analyze → scenes → voiceover → render
4. **remotion-iterate-and-chain.md** — Iterative editing + multi-video chaining
5. **remotion-cinematic-patterns.md** — Springs, typography, backgrounds, particles, effects

### Trend Intelligence
6. **trend-intelligence-pipeline.md** — End-to-end: scan → analyze → infographic → publish
7. **wordpress-mcp-publishing.md** — WordPress.com API v1.1 setup, MCP tools, troubleshooting
8. **hemle-blog-deployment.md** — Complete hemle.blog deployment: page registry, Gutenberg wrapping, Kadence override, wpautop fixes, design system, nav/footer injection, archive generation, troubleshooting
9. **trend-report-full-pipeline.md** — Complete report framework: research → NotebookLM verify → gen_clean_report.py → Gemini illustration → WP media upload → MCP publish → update homepage/archive. Includes MCP vs v1.1 API namespace discovery, ts-report CSS reference, category/tag/page ID registry, and new report checklist

## CLI Commands

```bash
# --- Trend Intelligence ---
py -3.13 cli.py report --data data.json [--notebook ID] [--open]
py -3.13 cli.py publish --data data.json [--tier pro|free] [--status draft|publish]

# --- Social Media ---
py -3.13 cli.py reel --script "..." --caption "..." --provider remotion --composition KineticText --props '{...}'
py -3.13 cli.py batch-reel --sequences seq.json --caption "..."
py -3.13 cli.py image-reel --slides slides.json --caption "..." --image-provider openai
py -3.13 cli.py image --prompt "..." --caption "..."
py -3.13 cli.py avatar --script "..."
py -3.13 cli.py schedule --text "..." --platforms instagram --date ISO

# --- Research ---
py -3.13 cli.py spy --domain competitor.com
py -3.13 cli.py keywords --kw "term1" "term2"
py -3.13 cli.py niche --seed "topic" --mode full
py -3.13 cli.py brand-extract --url https://example.com

# --- Utility ---
py -3.13 cli.py check-keys
py -3.13 cli.py costs --last 20
py -3.13 setup_blog.py home|about|subscribe
```

## WordPress.com Integration

- **Site**: hemle.blog (ID: 225453060)
- **API**: WordPress.com REST API v1.1 (`public-api.wordpress.com`)
- **Plan**: Personal (€3.25/mo) — API works on all plans
- **Auth**: OAuth2 token in `.wpcom_token` file
- **MCP**: `wordpress-com` server with 9 tools (create/update/delete posts, pages, categories, settings)
- **Categories**: Trend Intelligence, AI & Technology, Surging Trends, Music & Audio, Business & SaaS, Creator Economy, Steady Trends, Market Briefs

### Token notes
OAuth tokens contain special characters (`@$^!`) that bash mangles. Always store in `.wpcom_token` file (not shell vars). Both Python client and MCP server read from this file as fallback.

## Trend Report Data Format

JSON files in `output/reports/` with these fields:
```
trend_name, status (surging|steady|peaked), search_volume, category,
growth_5y, growth_1y, growth_3m, trigger,
timeline[{date, event}], pestal[{factor, impact}],
jobs[{job, solution}], market[{name, share, loved, segment}],
competitors[{name, detail}], canvas{who, where, why_now, behavior, unmet},
takeaways[string]
```

## Key Constraints
- WordPress.com Personal plan: no plugins, no wp-json/wp/v2 — use public-api v1.1
- Meta Graph API requires app review for DM permissions
- All API clients use async httpx — always `await`
- FFmpeg merge: `-map 0:v:0 -map 1:a:0` (Remotion embeds silent audio)
- FFmpeg subtitle filter needs escaped colons on Windows
- Remotion project at `C:\Users\njeng\OneDrive\Bureau\REMOTION`
- Large HTML content to WordPress: use `urlencode()` not raw `data=` in httpx

## Replicating for a New Blog

### Quick start (30 minutes)
1. Create WordPress.com site (Free or Personal plan)
2. Create OAuth app at `developer.wordpress.com/apps/new/` (redirect: `http://localhost:3891/callback`)
3. Run `node mcp-wordpress/get-token.js --browser --client-id ID --client-secret SECRET`
4. Update `WPCOM_SITE_ID` in `.mcp.json` + `config/settings.py`
5. Run `py -3.13 setup_blog.py home` → paste in WP editor (repeat for about, subscribe)
6. Create categories via CLI or MCP
7. Generate + publish: `py -3.13 cli.py publish --data trend-data.json --status draft`

### Template customization
- Edit `templates/wp_trend_post.html` for blog post styling
- Edit `templates/wp_pages/*.html` for page content
- Colors: change `STATUS_COLOR` and `BADGE_BG` CSS vars
- Branding: update footer, CTA links, subscribe URLs
