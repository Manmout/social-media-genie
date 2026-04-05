# WP Report Prompt — Skill Reference

## What This Is
Prompt template for generating trend intelligence reports in the Trend Signal design system. Use this when manually creating a report via Claude.ai or when the automated pipeline isn't available.

## When to Use
- Manual report creation outside the pipeline
- Testing new report designs
- One-off analyses for topics not in the JSON data files

## Template Location
`templates/wp_trend_post.html` — the CSS + HTML structure

## Design System Reference

### Colors
- Badge border: `{{STATUS_COLOR}}` (green `#0e7a5a` for surging)
- Purple accent: `#7b4fd4`
- Light purple: `#9b7fd4`
- Background: `#f7f5ff`
- Grid gaps: `#e8e2f8`
- Text: `#1a0a2e` (headings), `#444` (body)

### PESTAL Factor Colors
- Political: `.pol` — blue `#1e40af` on `#dbeafe`
- Economic: `.eco` — green `#065f46` on `#d1fae5`
- Social: `.soc` — purple `#5b21b6` on `#ede9fe`
- Technological: `.tec` — amber `#92400e` on `#fef3c7`
- Environmental: `.env` — green `#065f46` on `#d1fae5`
- Legal: `.leg` — red `#991b1b` on `#fee2e2`

### Market Bar Colors (rotate)
1. `#7b4fd4` (purple)
2. `#0e7a5a` (green)
3. `#3b82f6` (blue)
4. `#f59e0b` (amber)

### Badge Statuses
- `SURGING` — green border `#0e7a5a`
- `RISING` — blue border `#3b82f6`
- `ESTABLISHED` — purple border `#7b4fd4`
- `DECLINING` — red border `#dc2626`

### Typography
- Body: Georgia, 'Times New Roman', serif
- UI labels: -apple-system, 'Segoe UI', sans-serif
- Section labels: 9-10px, letter-spacing 2-4px, uppercase, `#9b7fd4`

### Editorial Rules
1. Each PESTAL cell = 1-2 phrases max, dense in data
2. Cite real numbers (ARR, CAGR, %, users)
3. Labels in French, analytical content in English
4. Always 4 recommendation profiles
5. Timeline: 5-8 milestones
6. Market bars: width = actual percentage
7. Neutral tone — no bias toward the subject

## Automated Pipeline (preferred)
```bash
py -3.13 cli.py publish --data output/reports/data.json --status publish --with-image
```
This generates the report automatically using the same template + renderers.
