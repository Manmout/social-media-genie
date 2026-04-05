"""Runway Gen-4 — image/text → video clip."""

import httpx
import asyncio
from pathlib import Path
from config import settings


class RunwayClient:
    BASE = "https://api.dev.runwayml.com/v1"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.RUNWAY_API_KEY
        self.model = settings.RUNWAY_MODEL

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-Runway-Version": "2024-11-06",
        }

    async def image_to_video(
        self,
        image_url: str,
        prompt: str,
        output_path: Path,
        *,
        duration: int = 10,
        ratio: str = "1080:1920",
    ) -> Path:
        """Generate video from image + prompt, poll until ready, download."""
        async with httpx.AsyncClient(timeout=300) as client:
            # Start generation
            resp = await client.post(
                f"{self.BASE}/image_to_video",
                headers=self._headers(),
                json={
                    "model": self.model,
                    "promptImage": image_url,
                    "promptText": prompt,
                    "duration": duration,
                    "ratio": ratio,
                },
            )
            resp.raise_for_status()
            task_id = resp.json()["id"]

            # Poll for completion
            video_url = await self._poll_task(client, task_id)

            # Download
            dl = await client.get(video_url)
            dl.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(dl.content)

        return output_path

    async def text_to_video(
        self,
        prompt: str,
        output_path: Path,
        *,
        duration: int = 10,
        ratio: str = "1080:1920",
    ) -> Path:
        """Generate video from text prompt."""
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                f"{self.BASE}/text_to_video",
                headers=self._headers(),
                json={
                    "model": self.model,
                    "promptText": prompt,
                    "duration": duration,
                    "ratio": ratio,
                },
            )
            resp.raise_for_status()
            task_id = resp.json()["id"]

            video_url = await self._poll_task(client, task_id)

            dl = await client.get(video_url)
            dl.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(dl.content)

        return output_path

    async def _poll_task(self, client: httpx.AsyncClient, task_id: str) -> str:
        """Poll task status until SUCCEEDED, return output URL."""
        url = f"{self.BASE}/tasks/{task_id}"
        for _ in range(60):
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status")
            if status == "SUCCEEDED":
                return data["output"][0]
            if status == "FAILED":
                raise RuntimeError(f"Runway task {task_id} failed: {data}")
            await asyncio.sleep(5)
        raise TimeoutError(f"Runway task {task_id} timed out")
