# hemle.blog Deployment — Complete Skill Reference

## What This Does
Full deployment pipeline for hemle.blog (WordPress.com Personal plan): page publishing, post wrapping, archive generation, Kadence theme override, wpautop prevention, and design system enforcement. Zero PHP, zero plugins — everything through API + inline HTML + Additional CSS.

## Critical Constraints

### WordPress.com Personal Plan Limitations
- **No `functions.php`** — no theme child, no PHP hooks
- **No plugins** — no Redirection, no Custom CSS plugin
- **No `wp-json/wp/v2`** — use `public-api.wordpress.com/rest/v1.1` exclusively
- **No `.htaccess`** — redirects only via slug rename (WP auto-creates 301)
- **wpautop is ON** — WordPress wraps loose HTML in `<p>` tags, breaking grids
- **wp-emoji is ON** — WordPress converts Unicode arrows (↗) into tiny SVG images

### Solutions in Place
| Problem | Solution |
|---------|----------|
| No PHP hooks for nav/footer | Inline HTML in every page template + `TS_NAV`/`TS_FOOTER` constants in `wp_publisher.py` |
| wpautop breaks grids | Gutenberg `<!-- wp:html -->` blocks for pages; CSS `.three-col > p { display: none }` as fallback |
| wp-emoji mangles arrows | Inline SVG `<svg width="12" height="12">` instead of `&#8599;` |
| Kadence theme chrome visible | Additional CSS hides `.site-header`, `#masthead`, `.kadence-header`, `#colophon`, `.kadence-footer` |
| Beige gap between hidden header and content | `body { margin-top: 0 !important }` + `.site-content { margin-top: 0 }` |

## Architecture

```
Templates (local HTML)
  ├── templates/wp_pages/*.html     ← Page content (Home, About, Subscribe, Rapports, Privacy, Terms)
  ├── templates/wp_trend_post.html  ← Blog post template (trend reports)
  └── templates/wp_additional_css.css ← Global styles → WP Additional CSS

Scripts (deployment)
  ├── push_gutenberg_pages.py       ← Strip <style>, wrap <!-- wp:html -->, push pages
  ├── patch_posts_nav.py            ← Inject TS_NAV/TS_FOOTER into existing posts
  ├── update_archive.py             ← Regenerate /rapports/ from live posts
  ├── setup_pages.py                ← Create new pages (first-time setup)
  └── setup_blog.py                 ← Manual clipboard helper (fallback)

Core (Python)
  ├── src/apis/wordpress.py         ← WordPress.com v1.1 REST client
  ├── src/reports/wp_publisher.py   ← Render + publish trend reports (auto TS_NAV/TS_FOOTER)
  └── config/settings.py            ← WPCOM_SITE_ID, WPCOM_TOKEN

MCP (Node.js)
  ├── mcp-wordpress/server.js       ← MCP tools for Claude Code (9 tools)
  └── mcp-wordpress/get-token.js    ← OAuth2 token generator
```

## Page Registry

| Page | WP ID | Slug | Template | Script |
|------|-------|------|----------|--------|
| Accueil | 13 | `accueil` (front page) | `home_forest_wp.html` | `push_gutenberg_pages.py --page home` |
| A propos | 15 | `a-propos` | `about.html` | `push_gutenberg_pages.py --page about` |
| S'abonner | 12 | `sabonner` | `subscribe.html` | `push_gutenberg_pages.py --page subscribe` |
| Rapports | 142 | `rapports` | `rapports.html` | `update_archive.py` |
| Blog | 14 | `blog` | (empty, WP native posts list) | — |
| Privacy | 11 | `privacy-policy` | `privacy.html` | `setup_pages.py --page privacy` |
| Terms | 40 | `terms` | `terms.html` | `setup_pages.py` |

**Site ID:** 225453060
**API endpoint:** `https://public-api.wordpress.com/rest/v1.1/sites/225453060/`
**Auth:** OAuth2 bearer token in `.wpcom_token`

## Deployment Commands

### Pages (static content)
```bash
# Push all 3 main pages (strips <style>, wraps in <!-- wp:html -->)
py -3.13 push_gutenberg_pages.py

# Push a single page
py -3.13 push_gutenberg_pages.py --page home
py -3.13 push_gutenberg_pages.py --page about
py -3.13 push_gutenberg_pages.py --page subscribe

# Preview locally without pushing
py -3.13 push_gutenberg_pages.py --dry-run

# First-time setup (creates pages that don't exist yet)
py -3.13 setup_pages.py --page rapports --force
```

### Posts (trend reports)
```bash
# Publish a new report (auto-wraps with TS_NAV/TS_FOOTER)
# Done programmatically via WPPublisher.publish(report)

# Inject nav/footer into existing posts (idempotent)
py -3.13 patch_posts_nav.py
py -3.13 patch_posts_nav.py --dry-run
py -3.13 patch_posts_nav.py --ids 38 39 40

# Regenerate /rapports/ archive page after new posts
py -3.13 update_archive.py
py -3.13 update_archive.py --dry-run
```

### Additional CSS
```bash
# The file to paste into Apparence > Personnaliser > CSS additionnel:
# templates/wp_additional_css.css (359 lines, 10 sections)
```

## Template Authoring Rules

### For Pages (`templates/wp_pages/*.html`)
1. **Include `<style>` block** for local preview — `push_gutenberg_pages.py` strips it before pushing
2. **Include full `<!DOCTYPE html>`** for standalone preview — script strips it
3. **No HTML comments inside grids** — wpautop wraps them in `<p>`, breaking CSS grid children count
4. **Use inline styles** — WordPress.com strips `<link>` tags and most `<style>` blocks
5. **Use HTML entities** for French accents (`&eacute;`, `&agrave;`, `&egrave;`) — survives all WP processing
6. **Use SVG for icons** — never Unicode characters that wp-emoji converts
7. **All links must use `/a-propos/`** (not `/about/`), `/sabonner/` (not `/subscribe/`), `/blog/` for reports

### For Posts (`wp_publisher.py` + `wp_trend_post.html`)
1. `TS_NAV` and `TS_FOOTER` constants auto-wrap every post — don't add nav/footer to the template
2. Template uses `{{PLACEHOLDER}}` syntax — replaced by `_render()` method
3. WordPress strips `<nav>` and `<footer>` tags (not in allowed HTML list) — the content still renders as links/text, but without semantic tags
4. The `wp_trend_post.html` is a full HTML document for preview; `_render()` extracts relevant sections

### For Additional CSS (`wp_additional_css.css`)
Structure (10 sections):
```
0. FONTS          — Single @import (Newsreader, Inter, Space Grotesk, EB Garamond)
1. KADENCE HIDE   — Header + footer + gap removal
2. VARIABLES      — :root tokens (Artclic purple + Trend Signal forest)
3. TYPOGRAPHY     — Georgia body, system-ui nav, justify + 1.75 line-height
4. WPAUTOP FIX    — .three-col > p, .two-col > p, .four-col > p, .ts-grid > p
5. NAV (.ts-nav)  — Sticky dark nav with brand, links, CTA button
6. FOOTER         — 4-column grid footer with brand, links, legal
7. HOVER STATES   — Cards, buttons, links, SVG arrows, inputs
8. FAQ TOGGLE     — details/summary with rotating +
9. RESPONSIVE     — Mobile-first breakpoints (767/768px)
```

## Design System (Two Palettes)

### Artclic Canonical (purple — used on report posts, about, subscribe)
```
--bg-hero:     #0d0618    --accent:       #6b3fc0
--bg-deep:     #1a0a2e    --accent-light: #8b5cf6
--bg-surface:  #ede8f8    --text-on-dark: #f0ebfc
--bg-page:     #f7f5fb    --text-muted:   #8875a8
```

### Trend Signal Forest (green — used on homepage)
```
--ts-bg:       #EDE8E2    --ts-accent:      #2D3A2D
--ts-dark:     #1A1F1A    --ts-green:       #4A6741
--ts-card-bg:  #ffffff    --ts-section-alt: #E5DFD8
```

### Typography
- **Editorial/body:** Georgia, 'Newsreader', serif — justify, line-height 1.75-1.85
- **Display/titles:** 'EB Garamond', serif (reports) or 'Newsreader', serif (homepage)
- **UI/nav/labels:** 'Space Grotesk', monospace — uppercase, letter-spacing 0.1em
- **Body text:** 'Inter', sans-serif

## Troubleshooting

### Page content looks broken (random grey blocks)
**Cause:** wpautop wrapped HTML comments or whitespace in `<p>` tags inside a CSS grid.
**Fix:** Re-push with `push_gutenberg_pages.py` (wraps in `<!-- wp:html -->` block). If comments exist inside `.three-col`, remove them.

### Duplicate header/footer visible
**Cause:** Kadence theme header/footer not hidden by CSS.
**Fix:** Check that `wp_additional_css.css` section 1 is pasted in Apparence > Personnaliser > CSS additionnel. Look for the exact class name with DevTools (F12) and add it to the selector list.

### Arrow shows as tiny emoji image
**Cause:** WordPress wp-emoji converts Unicode to `<img class="wp-emoji">`.
**Fix:** Replace `&#8599;` with inline SVG:
```html
<svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg"
  style="display:inline-block;vertical-align:middle;margin-left:4px;">
  <path d="M2 10L10 2M10 2H4M10 2V8" stroke="currentColor" stroke-width="1.5"
    stroke-linecap="round" stroke-linejoin="round"/>
</svg>
```

### API returns 403 on page update
**Cause:** WordPress.com v1.1 API sometimes refuses updates via Python `httpx` on pages set as front page.
**Fix:** Use the MCP tool `mcp__wordpress-com__wp_update_post` with `type: "pages"` instead. It uses a different auth flow.

### Nav/footer injected twice in a post
**Cause:** `patch_posts_nav.py` ran twice without idempotency detection working.
**Fix:** Script checks for `"Trend Signal par Hemle</span>"` marker in post content. If WP modifies this string, update the `NAV_MARKER` constant in the script.

### Mixed French/English on the site
**Canonical French labels:**
- Nav: `Rapports` | `A propos` | `S'abonner` (button)
- Cards: `En hausse` (not Surging), `IA & Technologie` (not AI & Technology)
- Footer: `Plateforme` / `Societe` / `Legal` headers, `Abonnement` (not Tarifs), `A propos` (not About)
- Methodology: `Veille` / `Analyse` / `Livraison`

### Slug `/about/` still active
**Fix:** Use MCP to update page 15 — WordPress auto-renamed slug to `a-propos` and created 301 redirect from `/about/`.

## Full Pipeline: New Trend Report

```
1. Research    → /trends analyze "Topic" --full → JSON data
2. Enrich      → NotebookLM deep research (optional)
3. Render      → WPPublisher._render() fills wp_trend_post.html placeholders
4. Wrap        → TS_NAV + rendered HTML + TS_FOOTER (automatic)
5. Publish     → WordPressClient.create_post() → hemle.blog/trend-{slug}/
6. Homepage    → WPPublisher.update_home_hero() updates page 13 hero section
7. Archive     → py -3.13 update_archive.py → regenerates /rapports/ page
8. Distribute  → Newsletter (Brevo), Tumblr, Instagram Reels (optional)
```

## File Quick Reference

| Need | File |
|------|------|
| Change homepage content | `templates/wp_pages/home_forest_wp.html` → `push_gutenberg_pages.py --page home` |
| Change about page | `templates/wp_pages/about.html` → `push_gutenberg_pages.py --page about` |
| Change subscribe page | `templates/wp_pages/subscribe.html` → `push_gutenberg_pages.py --page subscribe` |
| Change global CSS | `templates/wp_additional_css.css` → paste in WP admin |
| Change report post template | `templates/wp_trend_post.html` (affects future reports only) |
| Change nav/footer on posts | `src/reports/wp_publisher.py` → `TS_NAV` / `TS_FOOTER` constants |
| Patch existing posts | `patch_posts_nav.py` |
| Regenerate archive | `update_archive.py` |
| Change WP page IDs | `push_gutenberg_pages.py` → `PAGES` dict; `src/reports/wp_publisher.py` → `HOME_PAGE_ID` |
| Change API auth | `.wpcom_token` file or `WPCOM_TOKEN` in `.env` |
| Change MCP config | `.mcp.json` |
| Design system reference | `artclic-web-builder/SKILL.md` |
