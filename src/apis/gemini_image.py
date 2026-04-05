"""Gemini Flash — text → image generation via Imagen / Gemini API."""

import base64
import httpx
from pathlib import Path
from config import settings


class GeminiImageClient:
    BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.GEMINI_API_KEY

    async def generate(
        self,
        prompt: str,
        output_path: Path,
        *,
        model: str = "gemini-2.5-flash-image",
        aspect_ratio: str = "9:16",
    ) -> Path:
        """Generate image from text prompt via Gemini generateContent with image output."""
        url = f"{self.BASE}/{model}:generateContent?key={self.api_key}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
            },
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        # Extract image from response parts
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini returned no candidates")

        for part in candidates[0].get("content", {}).get("parts", []):
            if "inlineData" in part:
                b64 = part["inlineData"]["data"]
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(base64.b64decode(b64))
                return output_path

        raise RuntimeError("Gemini response contained no image data")
