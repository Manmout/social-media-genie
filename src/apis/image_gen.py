"""
Unified image generation — auto-selects the best available provider.

Priority: OpenAI DALL-E 3 → Gemini Imagen → Stability AI
Falls back automatically if a provider's key is missing or the call fails.

Usage:
    gen = ImageGenerator()
    path = await gen.generate("A futuristic city at sunset", style="vivid")
    print(gen.provider_used)  # "openai" | "gemini" | "stability"
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from config import settings
from src.utils.logger import get_logger

log = get_logger("image-gen")

# Size mappings per provider
_SIZES = {
    "openai": {
        "square": "1024x1024",
        "portrait": "1024x1792",
        "landscape": "1792x1024",
    },
    "gemini": {
        "square": "1:1",
        "portrait": "9:16",
        "landscape": "16:9",
    },
    "stability": {
        "square": "1:1",
        "portrait": "9:16",
        "landscape": "16:9",
    },
}


class ImageGenerator:
    """Unified image generation with automatic provider fallback."""

    def __init__(self):
        self.provider_used: str = ""
        self._providers = self._detect_providers()

    def _detect_providers(self) -> list[str]:
        """Return available providers in priority order: Gemini first."""
        available = []
        if settings.GEMINI_API_KEY:
            available.append("gemini")
        if settings.OPENAI_API_KEY:
            available.append("openai")
        if settings.STABILITY_API_KEY:
            available.append("stability")
        if not available:
            log.warning("No image generation API keys configured")
        else:
            log.info(f"Image providers available: {', '.join(available)}")
        return available

    async def generate(
        self,
        prompt: str,
        *,
        style: str = "vivid",
        size: str = "portrait",
        output_path: Path | None = None,
        provider: str | None = None,
    ) -> Path:
        """
        Generate an image from a text prompt.

        Args:
            prompt: Image description
            style: "vivid" or "natural" (OpenAI), ignored by others
            size: "square", "portrait", or "landscape"
            output_path: Where to save (auto-generated if None)
            provider: Force a specific provider ("openai", "gemini", "stability")

        Returns:
            Path to the saved image file
        """
        if output_path is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = settings.IMAGES_DIR / f"gen_{stamp}.png"
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # Determine provider order
        if provider:
            order = [provider]
        else:
            order = list(self._providers)

        if not order:
            raise RuntimeError("No image generation providers available. Set OPENAI_API_KEY, GEMINI_API_KEY, or STABILITY_API_KEY.")

        # Try each provider in order
        last_error = None
        for prov in order:
            try:
                result = await self._generate_with(prov, prompt, output_path, style=style, size=size)
                self.provider_used = prov
                log.info(f"Image generated via {prov}: {result}")
                return result
            except Exception as e:
                last_error = e
                log.warning(f"{prov} failed: {e}")
                continue

        raise RuntimeError(f"All image providers failed. Last error: {last_error}")

    async def _generate_with(
        self,
        provider: str,
        prompt: str,
        output_path: Path,
        *,
        style: str = "vivid",
        size: str = "portrait",
    ) -> Path:
        """Dispatch to the appropriate provider client."""

        if provider == "openai":
            from src.apis.openai_image import OpenAIImageClient
            client = OpenAIImageClient()
            return await client.generate(
                prompt,
                output_path,
                size=_SIZES["openai"].get(size, "1024x1792"),
                style=style,
            )

        elif provider == "gemini":
            from src.apis.gemini_image import GeminiImageClient
            client = GeminiImageClient()
            return await client.generate(
                prompt,
                output_path,
                aspect_ratio=_SIZES["gemini"].get(size, "9:16"),
            )

        elif provider == "stability":
            from src.apis.stability import StabilityClient
            client = StabilityClient()
            return await client.generate(
                prompt,
                output_path,
                aspect_ratio=_SIZES["stability"].get(size, "9:16"),
            )

        else:
            raise ValueError(f"Unknown provider: {provider}")

    @property
    def available_providers(self) -> list[str]:
        return list(self._providers)
