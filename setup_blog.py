#!/usr/bin/env python3
"""
Blog setup helper — copies page HTML to clipboard one at a time.

Usage:
    py -3.13 setup_blog.py home
    py -3.13 setup_blog.py about
    py -3.13 setup_blog.py subscribe
    py -3.13 setup_blog.py list
"""

import subprocess
import sys
from pathlib import Path

PAGES_DIR = Path(__file__).parent / "templates" / "wp_pages"

PAGES = {
    "home": {
        "file": "home.html",
        "title": "Home",
        "slug": "home",
        "instructions": [
            "Go to: https://hemle.blog/wp-admin/post-new.php?post_type=page",
            "Title: leave empty (or 'Home')",
            "Click + icon → search 'Custom HTML' → add block",
            "Paste (Ctrl+V)",
            "In Page settings (right panel): set Template to 'Full Width' if available",
            "Publish",
            "Then go to: https://hemle.blog/wp-admin/options-reading.php",
            "Set 'Your homepage displays' → 'A static page'",
            "Homepage: select 'Home'",
            "Posts page: select 'Blog' (create a blank page called 'Blog' first if needed)",
            "Save Changes",
        ],
    },
    "about": {
        "file": "about.html",
        "title": "À propos",
        "slug": "a-propos",
        "instructions": [
            "Go to: https://hemle.blog/wp-admin/post-new.php?post_type=page",
            "Title: 'À propos'",
            "Click + icon → search 'Custom HTML' → add block",
            "Paste (Ctrl+V)",
            "Publish",
        ],
    },
    "subscribe": {
        "file": "subscribe.html",
        "title": "Subscribe",
        "slug": "subscribe",
        "instructions": [
            "Go to: https://hemle.blog/wp-admin/post-new.php?post_type=page",
            "Title: 'Subscribe'",
            "Click + icon → search 'Custom HTML' → add block",
            "Paste (Ctrl+V)",
            "Publish",
        ],
    },
}


def copy_to_clipboard(text: str) -> bool:
    try:
        proc = subprocess.Popen(["clip.exe"], stdin=subprocess.PIPE)
        proc.communicate(text.encode("utf-8"))
        return True
    except Exception:
        return False


def main():
    if len(sys.argv) < 2 or sys.argv[1] == "list":
        print("\n  Blog Setup Pages:\n")
        for key, info in PAGES.items():
            print(f"    py -3.13 setup_blog.py {key:<12}  →  '{info['title']}' page")
        print(f"\n  Run each command, then follow the printed instructions.\n")
        return

    page_key = sys.argv[1].lower()
    if page_key not in PAGES:
        print(f"\n  Unknown page: {page_key}")
        print(f"  Available: {', '.join(PAGES.keys())}\n")
        return

    page = PAGES[page_key]
    file_path = PAGES_DIR / page["file"]

    if not file_path.exists():
        print(f"\n  File not found: {file_path}\n")
        return

    html = file_path.read_text(encoding="utf-8")

    if copy_to_clipboard(html):
        print(f"\n  ✅ '{page['title']}' page copied to clipboard!\n")
    else:
        print(f"\n  ⚠ Could not copy. Open manually: {file_path}\n")

    print(f"  Steps:")
    for i, step in enumerate(page["instructions"], 1):
        print(f"    {i}. {step}")
    print()


if __name__ == "__main__":
    main()
