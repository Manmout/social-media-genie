# Trend Intelligence Pipeline — Skill Reference

## What This Does
End-to-end pipeline: scan trends → deep analysis → NotebookLM enrichment → infographic generation → WordPress publishing. Produces premium trend intelligence reports for hemle.blog.

## Architecture

```
Keywords Everywhere (8K+ trends)
       ↓ scan + filter
/trends analyze "X" --full
       ↓ structured data
JSON trend data file
       ↓ render
HTML infographic (dark standalone + WP light theme)
       ↓ enrich (optional)
NotebookLM deep research
       ↓ publish
WordPress.com API v1.1 → hemle.blog
       ↓ distribute (optional)
Social Media Genie → Instagram Reels
```

## Data Flow

### 1. Trend Scanning
```bash
/trends list --status=surging --category=technology --subcategory=AI
/trends analyze "Topic Name" --full
```
Produces: status, search volume, growth metrics, PESTAL, JTBD, market position, consumer canvas, companies, takeaways.

### 2. Save as JSON
All trend data goes into a structured JSON file at `output/reports/<slug>-trend-data.json`.

Required fields:
```json
{
  "trend_name": "string",
  "status": "surging|steady|peaked",
  "search_volume": "string",
  "category": "string",
  "growth_5y": "string",
  "growth_1y": "string",
  "growth_3m": "string",
  "trigger": "string",
  "timeline": [{"date": "string", "event": "string"}],
  "pestal": [{"factor": "Political|Economic|Social|Technological|Environmental|Legal", "impact": "string"}],
  "jobs": [{"job": "string", "solution": "string"}],
  "market": [{"name": "string", "share": "string", "loved": "string", "segment": "string"}],
  "competitors": [{"name": "string", "detail": "string"}],
  "canvas": {"who": "", "where": "", "why_now": "", "behavior": "", "unmet": ""},
  "takeaways": ["string"]
}
```

### 3. Generate Report
```bash
# Standalone dark-theme infographic (opens in browser)
py -3.13 cli.py report --data output/reports/data.json --open

# With NotebookLM enrichment
py -3.13 cli.py report --data data.json --notebook NOTEBOOK_ID --open
```

### 4. Publish to WordPress
```bash
# Draft (review first)
py -3.13 cli.py publish --data output/reports/data.json --tier pro --status draft

# Publish directly
py -3.13 cli.py publish --data output/reports/data.json --tier pro --status publish

# Free-tier version (truncated + paywall CTA + blurred takeaways)
py -3.13 cli.py publish --data output/reports/data.json --tier free --status publish
```

### 5. Distribute via Social Media Genie
```bash
# Create Instagram Reel from trend analysis
py -3.13 cli.py reel \
  --script "Did you know Claude Code now powers 4% of all GitHub commits?" \
  --caption "Claude Code is surging. Full analysis at hemle.blog #trends #AI" \
  --provider remotion \
  --composition KineticText \
  --props '{"hook":"Claude Code","facts":["41% market share","46% most loved","$2.5B ARR"],"cta":"Full report at hemle.blog","palette":"dark"}'
```

## Templates

| Template | File | Use |
|---|---|---|
| Dark infographic | `templates/trend_infographic.html` | Standalone report (browser/PDF) |
| WP blog post | `templates/wp_trend_post.html` | WordPress Custom HTML block |
| Home page | `templates/wp_pages/home.html` | hemle.blog landing page |
| About page | `templates/wp_pages/about.html` | Pipeline + methodology |
| Subscribe page | `templates/wp_pages/subscribe.html` | Pricing tiers |

## Report Sections

Every trend report includes:
1. **Status badge** — surging (green), steady (yellow), peaked (red) with pulse animation
2. **Growth metric cards** — 5Y, 1Y, 3M growth + search volume
3. **SVG sparkline** — Interest-over-time chart (auto-generated from timeline)
4. **Timeline** — Key growth inflection events
5. **PESTAL table** — Color-coded factor badges (Political, Economic, Social, Technological, Environmental, Legal)
6. **Jobs-to-be-Done grid** — Job + Solution cards
7. **Consumer Trend Canvas** — Who, Where, Why Now, Emerging Behavior, Unmet Need
8. **Market position bars** — Share % + "most loved" % per player
9. **Companies to Watch** — Name + detail cards
10. **NotebookLM insights** — Deep research panel (purple gradient, optional)
11. **Actionable takeaways** — Numbered action items for creators, builders, investors, developers

## Free vs Pro Tier

| Feature | Free | Pro |
|---|---|---|
| Growth metrics | Yes | Yes |
| Timeline | Yes | Yes |
| PESTAL | No | Yes |
| JTBD | No | Yes |
| Market position | No | Yes |
| NotebookLM insights | No | Yes |
| Takeaways | First 2 only, rest blurred | All |
| Paywall CTA | Shown | Hidden |

## WordPress.com API

- **Endpoint**: `https://public-api.wordpress.com/rest/v1.1/sites/225453060/`
- **Auth**: OAuth2 bearer token (stored in `.wpcom_token`)
- **Plan**: Personal (€3.25/mo) — API works on all plans
- **Categories auto-created**: Trend Intelligence, AI & Technology, Surging Trends
- **Tags auto-created**: trend slug, status, trend-analysis, market-intelligence

## MCP Server

The `wordpress-com` MCP server exposes 9 tools for direct WordPress management from Claude Code:
- `wp_create_post`, `wp_update_post`, `wp_delete_post`, `wp_get_post`, `wp_list_posts`
- `wp_create_page`, `wp_get_site_info`, `wp_manage_categories`, `wp_site_settings`
- `wp_publish_trend_report` (one-shot: HTML file → published post)

## Weekly Workflow

```
Monday    → /trends list --status=surging (scan)
Tuesday   → Pick 3 → /trends analyze --full (research)
Wednesday → Save JSON + NotebookLM enrichment
Thursday  → py -3.13 cli.py publish --data ... --status draft (generate + draft)
Friday    → Review drafts → publish + distribute Reels
```
