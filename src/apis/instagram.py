"""Meta Instagram Graph API — publish, comment, DM."""

import httpx
from config import settings


class InstagramClient:
    BASE = "https://graph.facebook.com/v21.0"

    def __init__(self, access_token: str | None = None, account_id: str | None = None):
        self.token = access_token or settings.INSTAGRAM_ACCESS_TOKEN
        self.account_id = account_id or settings.INSTAGRAM_BUSINESS_ACCOUNT_ID

    def _params(self, **extra) -> dict:
        return {"access_token": self.token, **extra}

    async def publish_reel(
        self,
        video_url: str,
        caption: str,
        *,
        share_to_feed: bool = True,
    ) -> str:
        """Two-step Reel publish: create container → publish. Returns media ID."""
        async with httpx.AsyncClient(timeout=120) as client:
            # Step 1: Create media container
            resp = await client.post(
                f"{self.BASE}/{self.account_id}/media",
                params=self._params(
                    media_type="REELS",
                    video_url=video_url,
                    caption=caption,
                    share_to_feed=str(share_to_feed).lower(),
                ),
            )
            resp.raise_for_status()
            container_id = resp.json()["id"]

            # Step 2: Publish
            resp = await client.post(
                f"{self.BASE}/{self.account_id}/media_publish",
                params=self._params(creation_id=container_id),
            )
            resp.raise_for_status()
            return resp.json()["id"]

    async def publish_image(self, image_url: str, caption: str) -> str:
        """Publish a single image post."""
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.BASE}/{self.account_id}/media",
                params=self._params(
                    image_url=image_url,
                    caption=caption,
                ),
            )
            resp.raise_for_status()
            container_id = resp.json()["id"]

            resp = await client.post(
                f"{self.BASE}/{self.account_id}/media_publish",
                params=self._params(creation_id=container_id),
            )
            resp.raise_for_status()
            return resp.json()["id"]

    async def get_comments(self, media_id: str) -> list[dict]:
        """Fetch comments on a media post."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.BASE}/{media_id}/comments",
                params=self._params(fields="id,text,username,timestamp"),
            )
            resp.raise_for_status()
            return resp.json().get("data", [])

    async def reply_to_comment(self, comment_id: str, message: str) -> str:
        """Reply to a specific comment."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.BASE}/{comment_id}/replies",
                params=self._params(message=message),
            )
            resp.raise_for_status()
            return resp.json()["id"]

    async def send_dm(self, recipient_id: str, message: str) -> str:
        """Send a DM to a user (requires instagram_manage_messages permission)."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.BASE}/me/messages",
                params=self._params(),
                json={
                    "recipient": {"id": recipient_id},
                    "message": {"text": message},
                },
            )
            resp.raise_for_status()
            return resp.json()["message_id"]
