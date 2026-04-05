"""
Image pipeline — generates all 4 image formats for a trend report.

Usage:
    pipeline = ImagePipeline()
    images = await pipeline.generate(report)
    # images = {"hero": Path, "thumbnail": Path, "og_image": Path, "tumblr_header": Path}
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from src.reports.trend_report import TrendReport
from src.reports.image_prompt_generator import ImagePromptGenerator, ImagePromptSet
from src.apis.image_gen import ImageGenerator
from src.utils.logger import get_logger
from config import settings

log = get_logger("image-pipeline")

# Size configs per format
_FORMATS = {
    "hero":          {"size": "landscape", "style": "vivid"},
    "thumbnail":     {"size": "landscape", "style": "vivid"},
    "og_image":      {"size": "landscape", "style": "natural"},
    "tumblr_header": {"size": "square",    "style": "vivid"},
}


class ImagePipeline:
    """Generates all 4 trend report images."""

    def __init__(self):
        self.prompt_gen = ImagePromptGenerator()
        self.image_gen = ImageGenerator()

    async def generate(self, report: TrendReport) -> dict[str, Path]:
        """
        Generate 4 images for a trend report.

        Returns dict: {"hero": Path, "thumbnail": Path, "og_image": Path, "tumblr_header": Path}
        """
        slug = report.trend_name.lower().replace(" ", "-").replace("/", "-")
        out_dir = settings.IMAGES_DIR / slug
        out_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: Generate prompts (via LLM or fallback)
        log.info(f"Generating image prompts for '{report.trend_name}'...")
        prompts = await self.prompt_gen.generate(report)

        # Step 2: Generate all 4 images in parallel
        log.info("Generating 4 images in parallel...")
        tasks = {}
        for name in ["hero", "thumbnail", "og_image", "tumblr_header"]:
            prompt_text = getattr(prompts, name)
            fmt = _FORMATS[name]
            output_path = out_dir / f"{name}.png"
            tasks[name] = self.image_gen.generate(
                prompt_text,
                size=fmt["size"],
                style=fmt["style"],
                output_path=output_path,
            )

        results = await asyncio.gather(
            tasks["hero"],
            tasks["thumbnail"],
            tasks["og_image"],
            tasks["tumblr_header"],
            return_exceptions=True,
        )

        images = {}
        for name, result in zip(["hero", "thumbnail", "og_image", "tumblr_header"], results):
            if isinstance(result, Exception):
                log.warning(f"Image '{name}' failed: {result}")
            else:
                images[name] = result
                log.info(f"  {name}: {result}")

        return images
