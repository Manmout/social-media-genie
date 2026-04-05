---
description: Generate + publish a trend report to hemle.blog
allowed-tools: Bash, Read, Grep, Glob, WebFetch
---

# Publish Trend Report

Publish a trend intelligence report to hemle.blog via WordPress.com API v1.1.

## Input
The user provides either:
- A trend data JSON file path (e.g. `output/reports/agentic-ai-trend-data.json`)
- A topic name — in that case, first run `/trends analyze "TOPIC" --full` to generate the JSON

## Steps

1. Verify the JSON data file exists and contains required fields (trend_name, status, category, timeline, pestal, jobs, market)
2. Run syntax check on wp_publisher.py:
   ```bash
   PYTHONIOENCODING=utf-8 py -3.13 -c "import ast; ast.parse(open('src/reports/wp_publisher.py', encoding='utf-8').read()); print('OK')"
   ```
3. Publish as draft first for review:
   ```bash
   PYTHONIOENCODING=utf-8 py -3.13 cli.py publish --data <JSON_FILE> --tier pro --status draft --no-copy
   ```
4. Report the draft URL to the user
5. If the user confirms, re-publish with `--status publish`

## Options
- `--tier free|pro` — free truncates at PESTAL + adds CTA paywall (default: pro)
- `--with-image` — generate AI hero/thumbnail/og images before publishing
- `--notebook ID` — enrich via NotebookLM before rendering

## Post-publish checklist
- Verify the post appears at hemle.blog/blog/
- Check nav/footer colors match forest green palette
- Confirm categories assigned correctly
