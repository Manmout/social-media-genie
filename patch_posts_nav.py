#!/usr/bin/env python3
"""
One-shot script — Inject Trend Signal nav & footer into existing posts.

Reads each post's current content via WordPress.com API v1.1,
prepends TS_NAV and appends TS_FOOTER, then PATCHes it back.

Usage:
    py -3.13 patch_posts_nav.py                # Patch all published posts
    py -3.13 patch_posts_nav.py --dry-run      # Preview without writing
    py -3.13 patch_posts_nav.py --ids 8 9 10   # Patch specific post IDs
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.apis.wordpress import WordPressClient
from src.reports.wp_publisher import TS_NAV, TS_FOOTER
from src.utils.logger import get_logger

log = get_logger("patch-nav")

# Marker to detect posts already patched (avoids double injection).
# WordPress strips <nav> tags and compacts whitespace, so we match
# on a unique string from the injected footer that won't appear
# in normal report content.
NAV_MARKER = "Trend Signal par Hemle</span>"

# Old purple palette markers — used to detect and replace stale nav/footer
OLD_NAV_BG = "background:#0d0618"
OLD_FOOTER_BORDER = "rgba(107,63,192,0.18)"
# New forest palette marker
NEW_NAV_BG = "background:#1A1F1A"


async def get_post_content(wp: WordPressClient, post_id: int) -> dict | None:
    """Fetch a single post with its content."""
    import httpx

    url = f"https://public-api.wordpress.com/rest/v1.1/sites/{wp.site_id}/posts/{post_id}"
    headers = {"Authorization": f"Bearer {wp.token}"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, headers=headers)
        if r.status_code == 200:
            return r.json()
        log.warning(f"Failed to fetch post {post_id}: {r.status_code}")
        return None


def _strip_old_nav_footer(content: str) -> str:
    """Remove existing inline nav/footer (purple or forest) from post content."""
    import re
    # Strip inline <nav ...>...</nav> blocks injected by us
    content = re.sub(
        r'<nav\s+style="background:#[0-9a-fA-F]{6};display:flex.*?</nav>\s*',
        '', content, flags=re.DOTALL
    )
    # Strip inline <footer ...>...</footer> blocks injected by us
    content = re.sub(
        r'<footer\s+style="background:#[0-9a-fA-F]{6};padding.*?</footer>\s*',
        '', content, flags=re.DOTALL
    )
    return content.strip()


async def patch_post(wp: WordPressClient, post_id: int, dry_run: bool = False) -> bool:
    """Inject or replace nav/footer in a single post."""
    post = await get_post_content(wp, post_id)
    if not post:
        print(f"  [{post_id}] SKIP — could not fetch")
        return False

    title = post.get("title", "???")
    content = post.get("content", "")

    # Determine action: replace old, skip if already current, or inject new
    has_old = OLD_NAV_BG in content or OLD_FOOTER_BORDER in content
    has_new = NEW_NAV_BG in content

    if has_new and not has_old:
        print(f"  [{post_id}] SKIP — already has forest nav: {title}")
        return False

    action = "REPLACE purple>forest" if has_old else "INJECT new"

    # Strip any existing nav/footer before re-injecting
    clean_content = _strip_old_nav_footer(content)
    new_content = TS_NAV + "\n" + clean_content + "\n" + TS_FOOTER

    if dry_run:
        print(f"  [{post_id}] DRY RUN — would {action}: {title}")
        return True

    try:
        result = await wp.update_post(post_id, content=new_content)
        print(f"  [{post_id}] OK — {action}: {title}")
        log.info(f"Nav/footer {action} for post {post_id}: {title}")
        return True
    except Exception as e:
        print(f"  [{post_id}] ERROR — {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description="Inject nav/footer into existing posts")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--ids", nargs="+", type=int, default=None,
                        help="Specific post IDs to patch (default: all published)")
    args = parser.parse_args()

    wp = WordPressClient()
    if not wp.token:
        print("  No WordPress.com token found.")
        return

    print(f"\n  Trend Signal — Nav/Footer Injection")
    print(f"  {'=' * 40}\n")

    if args.ids:
        post_ids = args.ids
    else:
        # Fetch all published posts
        posts = await wp.list_posts(number=100, post_type="post")
        post_ids = [p["id"] for p in posts]

    if not post_ids:
        print("  No posts found.")
        return

    print(f"  Posts to patch: {post_ids}")
    if args.dry_run:
        print("  Mode: DRY RUN\n")
    else:
        print()

    patched = 0
    for pid in post_ids:
        if await patch_post(wp, pid, dry_run=args.dry_run):
            patched += 1

    print(f"\n  {'=' * 40}")
    print(f"  Done. {patched}/{len(post_ids)} posts {'would be ' if args.dry_run else ''}patched.\n")


if __name__ == "__main__":
    asyncio.run(main())
