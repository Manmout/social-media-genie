"""OpenAI DALL-E 3 — text → image generation."""

import base64
import httpx
from pathlib import Path
from config import settings


class OpenAIImageClient:
    BASE = "https://api.openai.com/v1/images/generations"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.OPENAI_API_KEY

    async def generate(
        self,
        prompt: str,
        output_path: Path,
        *,
        size: str = "1024x1792",  # portrait for Reels
        quality: str = "hd",
        model: str = "dall-e-3",
        style: str = "vivid",
    ) -> Path:
        """Generate image from text prompt via DALL-E 3."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "quality": quality,
            "style": style,
            "response_format": "b64_json",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(self.BASE, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            b64 = data["data"][0]["b64_json"]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(base64.b64decode(b64))
        return output_path
