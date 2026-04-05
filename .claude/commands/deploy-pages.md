---
description: Push static pages (home, about, subscribe, etc.) to hemle.blog
allowed-tools: Bash, Read, Grep, Glob, WebFetch
---

# Deploy Static Pages

Push the forest-themed page templates to hemle.blog via WordPress.com API v1.1.

## Page registry (v1.1 IDs)
| Page | Slug | WP ID |
|------|------|-------|
| Home | / | 13 |
| About | /a-propos/ | 15 |
| Subscribe | /sabonner/ | 12 |
| Blog | /blog/ | 14 |
| Privacy | /politique-de-confidentialite/ | 11 |
| Terms | /conditions-utilisation/ | 40 |

## Steps

1. Dry-run first to preview changes:
   ```bash
   PYTHONIOENCODING=utf-8 py -3.13 setup_pages.py --dry-run
   ```
2. Show the user what will be pushed
3. If approved, push all pages:
   ```bash
   PYTHONIOENCODING=utf-8 py -3.13 setup_pages.py --force
   ```
4. Verify each page loads correctly via WebFetch

## Single page push
```bash
PYTHONIOENCODING=utf-8 py -3.13 setup_blog.py home    # or: about, subscribe
```

## Templates
Source files in `templates/wp_pages/`:
- `home_forest.html` / `home_forest_wp.html` (latest)
- `about.html`, `subscribe.html`, `terms.html`, `privacy.html`
- `rapports.html` (blog archive)

## Post-deploy checks
- Homepage hero displays latest report data
- Nav links resolve (no 404 on /a-propos/, /sabonner/)
- Forest green palette consistent (#2D3A2D / #EDE8E2)
