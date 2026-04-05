# Trend Report Full Pipeline — Skill Reference

## What This Does
Complete end-to-end pipeline: research trend data → verify sources via NotebookLM → generate clean HTML report → create hand-drawn illustration via Gemini → publish to hemle.blog via MCP → update homepage + archive pages.

Produces publication-ready trend intelligence reports with verified sources, lifestyle illustrations, and consistent `ts-report` template design.

## Architecture

```
Trend Topic (user input or /trends scan)
       ↓ research (WebSearch + NotebookLM deep)
JSON trend data file (output/reports/<slug>-trend-data.json)
       ↓ generate report
Clean HTML (scripts/gen_clean_report.py)
       ↓ inject sources + CTA
Final HTML with citations + subscribe block
       ↓ generate illustration
Gemini Flash → hand-drawn lifestyle JPEG (scripts/gen_report_illustrations.py)
       ↓ upload image
WordPress.com Media API → CDN URL
       ↓ inject image into report HTML
       ↓ publish via MCP
hemle.blog live post (mcp__wordpress-com__wp_create_post + wp_update_post)
       ↓ update pages
Homepage hero + Rapports archive + Blog badges
```

## Critical Discovery: MCP vs v1.1 API

**WordPress.com MCP server and REST API v1.1 operate on SEPARATE namespaces.**

| Channel | Creates live posts? | Can see MCP posts? | Can see API posts? |
|---------|-------------------|--------------------|--------------------|
| MCP (`mcp__wordpress-com__*`) | YES | YES | NO |
| REST API v1.1 (`public-api.wordpress.com/rest/v1.1`) | NO (404 on live site) | NO | YES |

**Rule: ALL publishing MUST go through MCP tools.** The v1.1 API is only useful for media uploads and site settings.

## Step-by-Step Pipeline

### Step 1: Research Trend Data

Option A — Agent research:
```
Launch a general-purpose agent with WebSearch to gather:
- Market size + growth (5Y, 1Y, 3M)
- Timeline (6 milestones)
- PESTAL (6 factors)
- Jobs to Be Done (5 use cases)
- Market players (top 5 with share %)
- Competitors (top 5 with detail)
- Consumer Trend Canvas (who, where, why_now, behavior, unmet)
- Takeaways (4 actionable recommendations)
```

Option B — NotebookLM deep research:
```bash
PYTHONIOENCODING=utf-8 py -3.13 -m notebooklm create "Trend — <Topic>" --json
PYTHONIOENCODING=utf-8 py -3.13 -m notebooklm source add-research "<topic> market size growth 2026" --mode deep
PYTHONIOENCODING=utf-8 py -3.13 -m notebooklm ask "What is the exact market size? Key players? Growth rates?" --json
```

Output: `output/reports/<slug>-trend-data.json` matching the schema in trend-intelligence-pipeline.md.

### Step 2: Verify Sources

For every data claim (market size, growth %, ARR figures), find a verifiable URL:
- Fortune Business Insights, Gartner, BCG, McKinsey for market sizing
- TechCrunch, CNBC for funding/ARR
- Company blogs for product claims
- Academic/government for regulatory

Use NotebookLM to cross-check:
```bash
PYTHONIOENCODING=utf-8 py -3.13 -m notebooklm source add "<URL>"
PYTHONIOENCODING=utf-8 py -3.13 -m notebooklm ask "What exact figure does this source give for X?"
```

Build a sources block (6 citations per report):
```html
<div class="ts-sources"><h3>Sources</h3><ol>
<li>Publisher — <a href="URL">Claim summary</a></li>
...
</ol></div>
```

Flag any claim that cannot be sourced. Replace or remove — never publish unverifiable numbers.

### Step 3: Generate Report HTML

```bash
py -3.13 scripts/gen_clean_report.py output/reports/<slug>-trend-data.json output/reports/mcp_clean_<slug>.html
```

Then inject sources + CTA:
```python
from pathlib import Path

SOURCES = '<div class="ts-sources">...</div>'  # from Step 2
CTA = '<div class="ts-end-cta"><h3>Ne manquez aucun signal.</h3><p>2 rapports par mois en accès libre.</p><a href="https://hemle.blog/sabonner/">S\'abonner gratuitement</a></div>'

content = Path('output/reports/mcp_clean_<slug>.html').read_text(encoding='utf-8')
last_div = content.rfind('</div>')
content = content[:last_div] + SOURCES + CTA + '</div>'
```

### Step 4: Generate Illustration

Style directive (MUST be consistent across all reports):
```
Hand-drawn ink illustration on off-white textured paper.
Minimalist line art with subtle watercolor washes in muted earth tones
(sage green, warm beige, terracotta, soft charcoal).
Lifestyle editorial aesthetic — like a New Yorker magazine spot illustration.
NO photorealism. NO 3D renders. NO gradients. NO digital look.
Loose confident pen strokes, intentional imperfections, breathing white space.
Aspect ratio 16:9, landscape orientation. No text, no labels, no UI elements.
```

Each report needs a unique scene prompt that metaphorically represents the trend — NOT a literal tech illustration. Examples:
- AI agents → person with laptop + small friendly robot helpers + cat
- Music AI → headphones + coffee + musical notes floating upward
- Coding tools → workspace from above + rubber duck + code thought bubbles
- Open source PME → storefront "OPEN" + geometric shapes collaborating

Generate:
```bash
py -3.13 scripts/gen_report_illustrations.py
```

Compress to JPEG:
```python
from PIL import Image
img = Image.open('hero.png').convert('RGB')
img = img.resize((1200, int(h * 1200 / w)), Image.LANCZOS)
img.save('hero.jpg', 'JPEG', quality=82, optimize=True)
```

### Step 5: Upload Image to WordPress

```python
from config.settings import WPCOM_TOKEN, WPCOM_SITE_ID
import httpx

files = {'media[]': ('hero.jpg', img_bytes, 'image/jpeg')}
r = httpx.post(
    f'https://public-api.wordpress.com/rest/v1.1/sites/{WPCOM_SITE_ID}/media/new',
    headers={'Authorization': f'Bearer {WPCOM_TOKEN}'},
    files=files
)
image_url = r.json()['media'][0]['URL']
# Returns: https://hemleblog.wordpress.com/wp-content/uploads/YYYY/MM/filename.jpg
```

**Note:** Media upload works via v1.1 API even though post creation doesn't.

### Step 6: Inject Image + Publish via MCP

Insert the image `<div>` after the hero and before the metrics grid:
```html
<div style="text-align:center;margin:0 0 24px">
  <img src="<CDN_URL>" alt="Illustration <Trend Name>"
       style="width:100%;max-width:780px;border-radius:12px;" />
</div>
```

Publish or update via MCP:
```
mcp__wordpress-com__wp_create_post:
  title: "<Trend Name> — Rapport Trend Intelligence"
  content: <full HTML with image + sources + CTA>
  slug: "trend-<slug>"
  status: "publish"
  categories: [4, 2, 3]  # Trend Intelligence, AI & Technology, Surging Trends
  excerpt: "<SEO description ~150 words>"

mcp__wordpress-com__wp_update_post:
  post_id: <ID returned by create>
  tags: [5, 7, 8, ...]  # market-intelligence, surging, trend-analysis, + topic-specific
```

### Step 7: Update Site Pages

**Homepage (MCP page ID 13):**
- Hero → latest report title + excerpt + link
- Badge → update report count ("X rapports publiés")
- Cards → 3 most recent reports

**Rapports archive (MCP page ID 94):**
- Add new card with title, excerpt, link, date

**Blog (MCP page ID 97):**
- Automatic (WP lists all posts)
- CSS badges distinguish RAPPORT vs ARTICLE via category links

## Template Reference: ts-report

All reports use the `.ts-report` CSS class system:

| Class | Purpose |
|-------|---------|
| `.ts-report` | Root container, max-width 780px |
| `.ts-badge` | SURGING/STEADY/PEAKED pill |
| `.ts-hero` | Centered title + subtitle |
| `.ts-grid` / `.ts-card` | Metrics cards (5Y, 1Y, 3M growth) |
| `.ts-section h2` | Section headers with bottom border |
| `.ts-tl` / `.ts-tl-item` | Timeline with gradient left line |
| `.ts-table` | PESTAL table with rounded corners |
| `.ts-job` | Jobs to Be Done cards |
| `.ts-canvas` / `.ts-canvas-item` | Consumer Trend Canvas 2x2 grid |
| `.ts-rec` / `.ts-rec-num` | Numbered recommendations |
| `.ts-company` | Company profile cards |
| `.ts-sources` | Citations block |
| `.ts-end-cta` | Forest green subscribe CTA |

Status colors: surging = `#00E676` (green), steady = `#FFC107` (amber), peaked = `#FF5252` (red).

## Category & Tag IDs (MCP)

**Categories:**
| ID | Name |
|----|------|
| 2 | AI & Technology |
| 3 | Surging Trends |
| 4 | Trend Intelligence |
| 12 | Blog |
| 15 | Music & Audio |
| 16 | Business & SaaS |
| 17 | Creator Economy |
| 18 | Market Briefs |
| 19 | Steady Trends |

**Tags:**
| ID | Name |
|----|------|
| 5 | market-intelligence |
| 7 | surging |
| 8 | trend-analysis |
| 10 | agentic-ai |
| 9 | claude-code |
| 6 | suno-ai |
| 20 | ai-music |
| 21 | open-source |
| 22 | pme |

## Page IDs (MCP namespace)

| ID | Page |
|----|------|
| 13 | Accueil (homepage) |
| 94 | Rapports (archive) |
| 97 | Blog |
| 12 | S'abonner |
| 15 | À propos |

## Key Files

| File | Purpose |
|------|---------|
| `scripts/gen_clean_report.py` | JSON → clean HTML report |
| `scripts/gen_report_illustrations.py` | Gemini → hand-drawn illustrations |
| `src/reports/wp_publisher.py` | Legacy publisher (v1.1 API — do NOT use for publishing) |
| `src/apis/gemini_image.py` | Gemini image generation client |
| `output/reports/*-trend-data.json` | Source data for each report |
| `output/reports/mcp_clean_*.html` | Generated report HTML |
| `output/reports/mcp_final_*.html` | Report HTML with image injected |
| `output/images/reports/web/*.jpg` | Compressed illustrations |

## Auto-Update Homepage

After every report publication, run:
```bash
py -3.13 scripts/update_homepage.py
```

This script:
1. Reads all `*-trend-data.json` files in `output/reports/`
2. Sorts by file modification date (newest first)
3. Builds homepage HTML: hero = latest report, 3 cards = 3 most recent
4. Updates report counter ("X rapports publiés")
5. Saves to `output/reports/homepage_latest.html`

Then push via MCP:
```
mcp__wordpress-com__wp_update_post(post_id=13, type="pages", content=<homepage_latest.html>)
```

**URL mapping**: The script uses a `URL_MAP` dict in `update_homepage.py`. When adding a new report, add its slug → URL mapping to the dict. Otherwise it falls back to `https://hemle.blog/trend-<slug>/`.

## Checklist for New Report

- [ ] Research trend data (agent + NotebookLM)
- [ ] Save as `output/reports/<slug>-trend-data.json`
- [ ] Verify all claims — find 6 source URLs
- [ ] Generate HTML: `py -3.13 scripts/gen_clean_report.py`
- [ ] Inject sources + CTA
- [ ] Generate illustration via Gemini
- [ ] Compress to JPEG (1200px, quality 82)
- [ ] Upload image via v1.1 media API
- [ ] Inject image URL into report HTML
- [ ] Create post via `mcp__wordpress-com__wp_create_post`
- [ ] Add tags via `mcp__wordpress-com__wp_update_post`
- [ ] **Run `py -3.13 scripts/update_homepage.py` + push via MCP** ← NEW
- [ ] Add card to Rapports page (MCP page 94)
- [ ] Verify live on hemle.blog
