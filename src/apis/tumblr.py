"""
Tumblr API v2 client — publishes trend reports to hemle.tumblr.com.

Auth: OAuth1 tokens stored in .tumblr_token (JSON).
Endpoint: https://api.tumblr.com/v2/

Usage:
    tumblr = TumblrClient()
    result = await tumblr.create_post(
        blog="hemle",
        title="Claude Code — Trend Signal",
        body="<html>...</html>",
        tags=["trend-signal", "claude-code"],
    )
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from requests_oauthlib import OAuth1Session

from src.utils.logger import get_logger

log = get_logger("tumblr")

TOKEN_FILE = Path(__file__).resolve().parent.parent.parent / ".tumblr_token"
TUMBLR_API = "https://api.tumblr.com/v2"


def _load_tokens() -> dict:
    try:
        return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def _session(tokens: dict) -> OAuth1Session:
    return OAuth1Session(
        tokens["consumer_key"],
        client_secret=tokens["consumer_secret"],
        resource_owner_key=tokens["oauth_token"],
        resource_owner_secret=tokens["oauth_token_secret"],
    )


class TumblrClient:
    """Tumblr API v2 client using requests-oauthlib (OAuth1 signed)."""

    def __init__(self, blog: str = "hemle"):
        self.tokens = _load_tokens()
        self.blog = blog

    async def create_post(
        self,
        title: str,
        body: str,
        *,
        tags: list[str] | None = None,
        state: str = "published",
        blog: str | None = None,
    ) -> dict:
        blog_name = blog or self.blog
        url = f"{TUMBLR_API}/blog/{blog_name}.tumblr.com/post"
        payload = {
            "type": "text",
            "state": state,
            "title": title,
            "body": body,
            "format": "html",
        }
        if tags:
            payload["tags"] = ",".join(tags)

        data = await asyncio.to_thread(self._post_json, url, payload)

        post_id = data.get("response", {}).get("id", "")
        log.info(f"Post created: https://{blog_name}.tumblr.com/post/{post_id}")
        return {
            "id": post_id,
            "url": f"https://{blog_name}.tumblr.com/post/{post_id}",
            "state": state,
        }

    async def create_npf_post(
        self,
        content: list[dict],
        *,
        tags: list[str] | None = None,
        state: str = "published",
        blog: str | None = None,
        media_sources: dict[str, str] | None = None,
    ) -> dict:
        """
        Create a post using Tumblr NPF (Neue Post Format).

        Args:
            content: List of NPF content blocks
            tags: Post tags
            state: published, draft, queue
            media_sources: {"identifier": "/path/to/file.png"} for inline image uploads
        """
        blog_name = blog or self.blog
        url = f"{TUMBLR_API}/blog/{blog_name}.tumblr.com/posts"

        if media_sources:
            # Multipart upload: JSON payload + binary files
            data = await asyncio.to_thread(
                self._post_multipart_npf, url, content, tags, state, media_sources
            )
        else:
            payload = {"content": content, "state": state}
            if tags:
                payload["tags"] = ",".join(tags)
            data = await asyncio.to_thread(self._post_json, url, payload)

        post_id = data.get("response", {}).get("id", "")
        log.info(f"NPF post created: https://{blog_name}.tumblr.com/post/{post_id}")
        return {
            "id": post_id,
            "url": f"https://{blog_name}.tumblr.com/post/{post_id}",
            "state": state,
        }

    def _post_multipart_npf(
        self, url: str, content: list, tags: list | None, state: str, media_sources: dict
    ) -> dict:
        """Send NPF post with inline images via multipart/form-data."""
        import json as json_mod

        session = _session(self.tokens)

        # Build the JSON part
        payload_json = json_mod.dumps({
            "content": content,
            "state": state,
            **({"tags": ",".join(tags)} if tags else {}),
        })

        # Build multipart: 'json' part + one file per identifier
        files = {"json": (None, payload_json, "application/json")}
        for identifier, file_path in media_sources.items():
            p = Path(file_path)
            if p.exists():
                files[identifier] = (p.name, p.read_bytes(), "image/png")
            else:
                log.warning(f"Media file not found: {file_path}")

        resp = session.post(url, files=files)
        if not resp.ok:
            log.error(f"Tumblr multipart {resp.status_code}: {resp.text[:300]}")
            resp.raise_for_status()
        return resp.json()

    async def delete_post(self, post_id: int, blog: str | None = None) -> dict:
        blog_name = blog or self.blog
        url = f"{TUMBLR_API}/blog/{blog_name}.tumblr.com/post/delete"
        data = await asyncio.to_thread(self._post_json, url, {"id": str(post_id)})
        log.info(f"Post {post_id} deleted")
        return {"id": post_id, "status": "deleted"}

    async def get_blog_info(self, blog: str | None = None) -> dict:
        blog_name = blog or self.blog
        url = f"{TUMBLR_API}/blog/{blog_name}.tumblr.com/info"
        data = await asyncio.to_thread(self._get, url)
        blog_data = data.get("response", {}).get("blog", {})
        return {
            "name": blog_data.get("name"),
            "title": blog_data.get("title"),
            "posts": blog_data.get("posts"),
            "url": blog_data.get("url"),
        }

    # ── Sync HTTP (runs in thread) ───────────────────────

    def _post_json(self, url: str, payload: dict) -> dict:
        session = _session(self.tokens)
        resp = session.post(url, json=payload)
        if not resp.ok:
            log.error(f"Tumblr API {resp.status_code}: {resp.text[:300]}")
            resp.raise_for_status()
        return resp.json()

    def _get(self, url: str) -> dict:
        session = _session(self.tokens)
        resp = session.get(url)
        resp.raise_for_status()
        return resp.json()
