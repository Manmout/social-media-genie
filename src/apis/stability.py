"""Stability AI — text → image generation."""

import httpx
from pathlib import Path
from config import settings


class StabilityClient:
    BASE = "https://api.stability.ai/v2beta/stable-image"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.STABILITY_API_KEY

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "image/*",
        }

    async def generate(
        self,
        prompt: str,
        output_path: Path,
        *,
        negative_prompt: str = "",
        aspect_ratio: str = "9:16",
        model: str = "ultra",
    ) -> Path:
        """Generate image from text prompt."""
        url = f"{self.BASE}/generate/{model}"

        form_data = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "output_format": "png",
        }
        if negative_prompt:
            form_data["negative_prompt"] = negative_prompt

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                url,
                headers=self._headers(),
                data=form_data,
            )
            resp.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(resp.content)

        return output_path

    async def style_transfer(
        self,
        image_path: Path,
        prompt: str,
        output_path: Path,
        *,
        fidelity: float = 0.5,
    ) -> Path:
        """Apply style transfer to an existing image."""
        url = f"{self.BASE}/control/style"

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                url,
                headers=self._headers(),
                data={"prompt": prompt, "fidelity": fidelity, "output_format": "png"},
                files={"image": image_path.read_bytes()},
            )
            resp.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(resp.content)

        return output_path
