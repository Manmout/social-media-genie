"""
WordPress.com REST API v1.1 client — works on ALL plans (Personal, Premium, Business).

Uses public-api.wordpress.com with OAuth2 bearer token.
Does NOT require wp-json/wp/v2 (which needs Business plan).

Usage:
    wp = WordPressClient()
    result = await wp.create_post(
        title="Claude Code — Trend Intelligence Report",
        content="<html>...</html>",
        categories="Trend Intelligence,AI & Technology",
        tags="claude-code,surging",
        status="draft",
    )
"""

import httpx
from typing import Literal

from config import settings
from src.utils.logger import get_logger

log = get_logger("wordpress")

PostStatus = Literal["draft", "publish", "pending", "private"]

WPCOM_API = "https://public-api.wordpress.com/rest/v1.1/sites"


class WordPressClient:
    """Async WordPress.com REST API v1.1 client for hemle.blog."""

    def __init__(self):
        self.site_id = settings.WPCOM_SITE_ID or "225453060"
        self.token = settings.WPCOM_TOKEN or self._load_token_file()
        self.api_base = f"{WPCOM_API}/{self.site_id}"
        self.auth_header = {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @staticmethod
    def _load_token_file() -> str:
        """Read token from .wpcom_token file (avoids shell escaping issues)."""
        from pathlib import Path
        token_path = Path(__file__).resolve().parent.parent.parent / ".wpcom_token"
        try:
            return token_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return ""

    async def create_post(
        self,
        title: str,
        content: str,
        *,
        excerpt: str = "",
        categories: str = "",
        tags: str = "",
        status: PostStatus = "draft",
        slug: str = "",
        post_type: str = "post",
    ) -> dict:
        """
        Create a new post or page via WordPress.com API v1.1.

        Categories and tags are comma-separated strings.
        They are created automatically if they don't exist.
        """
        form = {
            "title": title,
            "content": content,
            "status": status,
        }
        if post_type == "page":
            form["type"] = "page"
        if excerpt:
            form["excerpt"] = excerpt
        if categories:
            form["categories"] = categories
        if tags:
            form["tags"] = tags
        if slug:
            form["slug"] = slug

        data = await self._post_form("/posts/new", form)

        result = {
            "id": data["ID"],
            "link": data["URL"],
            "short_url": data.get("short_URL", ""),
            "status": data["status"],
            "slug": data.get("slug", ""),
            "categories": list(data.get("categories", {}).keys()),
            "tags": list(data.get("tags", {}).keys()),
        }
        log.info(f"Post created: {result['link']} (status={result['status']})")
        return result

    async def update_post(self, post_id: int, **fields) -> dict:
        """Update an existing post by ID."""
        data = await self._post_form(f"/posts/{post_id}", fields)
        log.info(f"Post {post_id} updated")
        return {"id": data["ID"], "link": data["URL"], "status": data["status"]}

    async def upload_media(self, file_path: str, mime_type: str = "image/png") -> int | None:
        """Upload media file via WordPress.com API. Returns media ID."""
        from pathlib import Path
        p = Path(file_path)
        if not p.exists():
            log.warning(f"Media file not found: {file_path}")
            return None

        url = f"{self.api_base}/media/new"
        headers = {**self.auth_header}

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                url,
                headers=headers,
                files={"media[]": (p.name, p.read_bytes(), mime_type)},
            )
            if not resp.is_success:
                log.error(f"Media upload {resp.status_code}: {resp.text[:200]}")
            resp.raise_for_status()
            data = resp.json()

        media = data.get("media", [{}])
        if media:
            media_id = media[0].get("ID")
            media_url = media[0].get("URL", "")
            log.info(f"Media uploaded: ID={media_id}, url={media_url}")
            return media_id
        return None

    async def delete_post(self, post_id: int) -> dict:
        """Trash a post by ID."""
        data = await self._post_form(f"/posts/{post_id}/delete", {})
        return {"id": data["ID"], "status": data["status"]}

    async def get_post(self, post_id: int) -> dict:
        """Get a single post by ID."""
        data = await self._get(f"/posts/{post_id}")
        return {
            "id": data["ID"],
            "title": data["title"],
            "link": data["URL"],
            "status": data["status"],
            "date": data["date"],
            "categories": list(data.get("categories", {}).keys()),
            "tags": list(data.get("tags", {}).keys()),
        }

    async def list_posts(
        self,
        number: int = 10,
        status: str = "any",
        post_type: str = "post",
    ) -> list[dict]:
        """List recent posts."""
        params = {"number": number, "status": status, "type": post_type}
        data = await self._get("/posts", params=params)
        return [
            {
                "id": p["ID"],
                "title": p["title"],
                "link": p["URL"],
                "status": p["status"],
                "date": p["date"],
            }
            for p in data.get("posts", [])
        ]

    async def get_site_info(self) -> dict:
        """Get site info (name, plan, post count)."""
        data = await self._get("")
        return {
            "id": data["ID"],
            "name": data.get("name"),
            "description": data.get("description"),
            "url": data.get("URL"),
            "post_count": data.get("post_count"),
            "plan": data.get("plan", {}).get("product_name_short"),
        }

    async def manage_categories(self, action: str = "list", name: str = "") -> list | dict:
        """List or create categories."""
        if action == "list":
            data = await self._get("/categories", params={"number": 100})
            return [
                {"id": c["ID"], "name": c["name"], "slug": c["slug"], "count": c["post_count"]}
                for c in data.get("categories", [])
            ]
        elif action == "create" and name:
            data = await self._post_form("/categories/new", {"name": name})
            return {"id": data["ID"], "name": data["name"], "slug": data["slug"]}
        return []

    async def update_settings(self, **settings_dict) -> dict:
        """Update site settings (blogname, blogdescription, timezone_string)."""
        data = await self._post_form("/settings", settings_dict)
        return data.get("updated", settings_dict)

    # ── HTTP helpers ─────────────────────────────────────

    async def _get(self, path: str, params: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.api_base}{path}",
                params=params,
                headers=self.auth_header,
            )
            resp.raise_for_status()
            return resp.json()

    async def _post_form(self, path: str, form: dict) -> dict:
        from urllib.parse import urlencode
        body = urlencode(form, encoding="utf-8")
        headers = {
            **self.auth_header,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.api_base}{path}",
                content=body.encode("utf-8"),
                headers=headers,
            )
            if not resp.is_success:
                log.error(f"WP API {resp.status_code}: {resp.text[:500]}")
            resp.raise_for_status()
            return resp.json()
