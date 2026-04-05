---
description: Generate a trend infographic report (local HTML only)
allowed-tools: Bash, Read, Grep, Glob
---

# Generate Trend Report

Generate a standalone HTML trend intelligence infographic without publishing.

## Input
The user provides a trend data JSON file path (e.g. `output/reports/topic-trend-data.json`).

## Steps

1. Verify the JSON data file exists and is valid
2. Generate the report:
   ```bash
   PYTHONIOENCODING=utf-8 py -3.13 cli.py report --data <JSON_FILE> --open
   ```
3. The `--open` flag opens the HTML in the default browser for immediate preview
4. Report the output file path to the user

## Output
- Dark-theme standalone HTML infographic at `output/reports/trend_<slug>_<timestamp>.html`
- Includes: timeline, growth metrics, PESTAL table, JTBD, market map, consumer canvas, takeaways
- Self-contained (inline CSS, SVG sparklines) — can be shared as a single file

## Optional enrichment
If the user wants NotebookLM-powered deep research added:
```bash
PYTHONIOENCODING=utf-8 py -3.13 cli.py report --data <JSON_FILE> --notebook <ID> --open
```
