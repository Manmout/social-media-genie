---
description: Generate + send a trend newsletter via Brevo
allowed-tools: Bash, Read, Grep, Glob, WebFetch
---

# Send Trend Newsletter

Generate and send a trend intelligence newsletter via Brevo (email).

## Input
The user provides:
- A trend data JSON file path
- Optionally: the hemle.blog post URL, language, recipient

## Steps

1. Generate a draft first to preview:
   ```bash
   PYTHONIOENCODING=utf-8 py -3.13 cli.py newsletter --data <JSON_FILE> --mode draft --lang fr --open
   ```
2. Show the user the draft opened in browser
3. If approved, send as transactional email or create a Brevo campaign:
   ```bash
   # Transactional (single recipient)
   PYTHONIOENCODING=utf-8 py -3.13 cli.py newsletter --data <JSON_FILE> --mode send --to <EMAIL> --url <BLOG_URL>

   # Campaign (list-based)
   PYTHONIOENCODING=utf-8 py -3.13 cli.py newsletter --data <JSON_FILE> --mode campaign --list-id <ID>
   ```

## Options
- `--lang fr|en` — newsletter language (default: fr)
- `--with-image` — generate + inject hero thumbnail
- `--url` — full report URL on hemle.blog (auto-generated if omitted)
- `--send-now` — send campaign immediately (default: save as draft in Brevo)

## Safety
- Always generate `--mode draft` first for user review
- Never `--send-now` without explicit user confirmation
