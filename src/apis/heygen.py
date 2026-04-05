"""HeyGen — script → AI avatar spokesperson video."""

import httpx
import asyncio
from pathlib import Path
from config import settings


class HeyGenClient:
    BASE = "https://api.heygen.com"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.HEYGEN_API_KEY
        self.avatar_id = settings.HEYGEN_AVATAR_ID

    def _headers(self) -> dict:
        return {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
        }

    async def generate_video(
        self,
        script: str,
        output_path: Path,
        *,
        avatar_id: str | None = None,
        dimension: dict | None = None,
    ) -> Path:
        """Generate talking-head video from script text."""
        dim = dimension or {"width": 1080, "height": 1920}
        avid = avatar_id or self.avatar_id

        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                f"{self.BASE}/v2/video/generate",
                headers=self._headers(),
                json={
                    "video_inputs": [
                        {
                            "character": {
                                "type": "avatar",
                                "avatar_id": avid,
                                "avatar_style": "normal",
                            },
                            "voice": {
                                "type": "text",
                                "input_text": script,
                            },
                        }
                    ],
                    "dimension": dim,
                },
            )
            resp.raise_for_status()
            video_id = resp.json()["data"]["video_id"]

            video_url = await self._poll_video(client, video_id)

            dl = await client.get(video_url)
            dl.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(dl.content)

        return output_path

    async def _poll_video(self, client: httpx.AsyncClient, video_id: str) -> str:
        """Poll until video is ready, return download URL."""
        url = f"{self.BASE}/v1/video_status.get"
        for _ in range(120):
            resp = await client.get(
                url,
                headers=self._headers(),
                params={"video_id": video_id},
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            if data["status"] == "completed":
                return data["video_url"]
            if data["status"] == "failed":
                raise RuntimeError(f"HeyGen video {video_id} failed: {data}")
            await asyncio.sleep(5)
        raise TimeoutError(f"HeyGen video {video_id} timed out")
