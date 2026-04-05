#!/usr/bin/env python3
"""
Automated blog page setup — publishes Home, About, Subscribe pages
to hemle.blog via WordPress.com API v1.1, then sets the static front page.

Usage:
    py -3.13 setup_pages.py                  # Publish all 3 pages
    py -3.13 setup_pages.py --page home      # Publish one page only
    py -3.13 setup_pages.py --dry-run        # Show what would be published
    py -3.13 setup_pages.py --status draft   # Create as drafts
    py -3.13 setup_pages.py --list           # List existing pages on hemle.blog
    py -3.13 setup_pages.py --delete ID      # Delete a page by ID
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.apis.wordpress import WordPressClient
from src.utils.logger import get_logger

log = get_logger("setup-pages")

PAGES_DIR = Path(__file__).parent / "templates" / "wp_pages"

PAGES = {
    "home": {
        "file": "home_forest_wp.html",
        "title": "Accueil",
        "slug": "accueil",
        "set_as_front": True,
    },
    "about": {
        "file": "about.html",
        "title": "À propos",
        "slug": "a-propos",
    },
    "subscribe": {
        "file": "subscribe.html",
        "title": "S'abonner",
        "slug": "subscribe",
    },
    "rapports": {
        "file": "rapports.html",
        "title": "Rapports",
        "slug": "rapports",
    },
    "privacy": {
        "file": "privacy.html",
        "title": "Politique de Confidentialité",
        "slug": "privacy",
    },
}


async def list_pages(wp: WordPressClient):
    """List existing pages on the site."""
    pages = await wp.list_posts(number=50, post_type="page")
    print(f"\n  Pages on hemle.blog ({len(pages)}):\n")
    for p in pages:
        print(f"    [{p['status']:>7}] ID={p['id']:<6} {p['title']}")
    print()
    return pages


async def find_existing_page(wp: WordPressClient, slug: str) -> dict | None:
    """Check if a page with this slug already exists."""
    pages = await wp.list_posts(number=50, post_type="page")
    for p in pages:
        # WordPress.com returns the slug in the URL
        if f"/{slug}/" in p.get("link", "") or f"/{slug}" in p.get("link", ""):
            return p
    return None


async def publish_page(
    wp: WordPressClient,
    key: str,
    status: str = "publish",
    dry_run: bool = False,
    force: bool = False,
) -> dict | None:
    """Publish a single page."""
    if key not in PAGES:
        print(f"  Unknown page: {key}. Available: {', '.join(PAGES.keys())}")
        return None

    page_def = PAGES[key]
    file_path = PAGES_DIR / page_def["file"]

    if not file_path.exists():
        print(f"  File not found: {file_path}")
        return None

    content = file_path.read_text(encoding="utf-8")
    title = page_def["title"]
    slug = page_def["slug"]

    # Check if page already exists
    if not force:
        existing = await find_existing_page(wp, slug)
        if existing:
            print(f"  [{key}] Already exists: ID={existing['id']} ({existing['status']})")
            print(f"         URL: {existing['link']}")
            print(f"         Use --force to overwrite or --delete {existing['id']} first")
            return existing

    if dry_run:
        print(f"  [DRY RUN] Would publish '{title}' (slug: {slug}, {len(content)} chars)")
        return None

    print(f"  Publishing '{title}'...", end=" ", flush=True)
    result = await wp.create_post(
        title=title,
        content=content,
        status=status,
        slug=slug,
        post_type="page",
    )
    print(f"OK → ID={result['id']} ({result['status']})")
    print(f"         URL: {result['link']}")
    return result


async def set_front_page(wp: WordPressClient, page_id: int):
    """Set a page as the static front page."""
    print(f"\n  Setting page ID={page_id} as front page...", end=" ", flush=True)
    try:
        await wp.update_settings(
            show_on_front="page",
            page_on_front=str(page_id),
        )
        print("OK")
    except Exception as e:
        print(f"SKIP (may require Business plan: {e})")
        print("  → Set manually: Settings → Reading → Static page → Accueil")


async def create_blog_page(wp: WordPressClient, status: str = "publish") -> dict | None:
    """Create an empty 'Blog' page for the posts listing."""
    existing = await find_existing_page(wp, "blog")
    if existing:
        print(f"  [blog] Already exists: ID={existing['id']}")
        return existing

    print(f"  Creating 'Blog' page...", end=" ", flush=True)
    result = await wp.create_post(
        title="Blog",
        content="",
        status=status,
        slug="blog",
        post_type="page",
    )
    print(f"OK → ID={result['id']}")
    return result


async def delete_page(wp: WordPressClient, page_id: int):
    """Delete a page by ID."""
    print(f"  Deleting page ID={page_id}...", end=" ", flush=True)
    result = await wp.delete_post(page_id)
    print(f"OK ({result['status']})")


async def main():
    parser = argparse.ArgumentParser(description="Publish blog pages to hemle.blog")
    parser.add_argument("--page", choices=list(PAGES.keys()), default=None,
                        help="Publish a single page (default: all)")
    parser.add_argument("--status", choices=["publish", "draft"], default="publish",
                        help="Page status (default: publish)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")
    parser.add_argument("--force", action="store_true", help="Overwrite existing pages")
    parser.add_argument("--list", action="store_true", help="List existing pages")
    parser.add_argument("--delete", type=int, default=None, help="Delete a page by ID")
    parser.add_argument("--no-front", action="store_true",
                        help="Don't set Home as front page")
    args = parser.parse_args()

    wp = WordPressClient()

    if not wp.token:
        print("\n  No WordPress.com token found.")
        print("  Run: node mcp-wordpress/get-token.js --browser --client-id ID --client-secret SECRET\n")
        return

    print(f"\n  Hemle.blog Page Setup")
    print(f"  {'=' * 40}\n")

    if args.list:
        await list_pages(wp)
        return

    if args.delete:
        await delete_page(wp, args.delete)
        return

    # Publish pages
    pages_to_publish = [args.page] if args.page else list(PAGES.keys())
    results = {}

    for key in pages_to_publish:
        result = await publish_page(wp, key, status=args.status, dry_run=args.dry_run, force=args.force)
        if result:
            results[key] = result

    # Create Blog page (for posts listing)
    if not args.page and not args.dry_run:
        blog = await create_blog_page(wp, status=args.status)
        if blog:
            results["blog"] = blog

    # Set front page
    if not args.no_front and not args.dry_run and "home" in results:
        home_id = results["home"]["id"]
        await set_front_page(wp, home_id)

    # Summary
    if not args.dry_run and results:
        print(f"\n  {'=' * 40}")
        print(f"  Done! {len(results)} pages published.\n")
        for key, r in results.items():
            print(f"    {key:<12} → {r.get('link', 'N/A')}")
        print()
        if "home" not in results:
            print("  Note: Home page was not published (already exists?).")
            print("  Run with --force to overwrite.\n")


if __name__ == "__main__":
    asyncio.run(main())
