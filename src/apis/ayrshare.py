"""Ayrshare — multi-platform scheduling."""

import httpx
from config import settings


class AyrshareClient:
    BASE = "https://app.ayrshare.com/api"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.AYRSHARE_API_KEY

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def schedule_post(
        self,
        text: str,
        platforms: list[str],
        *,
        media_urls: list[str] | None = None,
        schedule_date: str | None = None,
    ) -> dict:
        """Schedule or immediately post to one or more platforms."""
        payload: dict = {
            "post": text,
            "platforms": platforms,
        }
        if media_urls:
            payload["mediaUrls"] = media_urls
        if schedule_date:
            payload["scheduleDate"] = schedule_date

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.BASE}/post",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()
