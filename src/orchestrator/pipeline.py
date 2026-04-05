"""
Core pipeline — chains API clients into end-to-end content workflows.

Usage:
    pipeline = Pipeline()

    # Default: Remotion (free, template-based, 90% of Reels)
    reel = await pipeline.create_reel(
        script="Your voiceover text here",
        composition_id="KineticText",
        video_props={"hook": "Did you know?", "stats": ["890% ROI", "90% open rate"]},
        caption="Instagram caption #hashtags",
    )

    # Cinematic: Runway (paid, AI-generated visuals)
    reel = await pipeline.create_reel(
        script="Your voiceover text here",
        scene_prompt="Aerial drone shot of tropical rainforest at golden hour",
        caption="Instagram caption #hashtags",
        video_provider="runway",
    )
"""

import asyncio
from pathlib import Path
from datetime import datetime
from typing import Literal

from src.apis import (
    ElevenLabsClient,
    RemotionClient,
    RunwayClient,
    StabilityClient,
    HeyGenClient,
    InstagramClient,
    AyrshareClient,
    WhisperClient,
    OpenAIImageClient,
    GeminiImageClient,
)
from src.utils import ffmpeg
from src.utils.probe import get_duration
from src.utils.cost_tracker import CostTracker
from src.utils.logger import get_logger
from src.reports.generator import ReportGenerator, build_report_from_analysis
from src.reports.trend_report import TrendReport
from config import settings

log = get_logger("pipeline")

VideoProvider = Literal["remotion", "runway"]
ImageProvider = Literal["openai", "gemini", "stability"]


class Pipeline:
    def __init__(self):
        self.elevenlabs = ElevenLabsClient()
        self.remotion = RemotionClient()
        self.runway = RunwayClient()
        self.stability = StabilityClient()
        self.heygen = HeyGenClient()
        self.instagram = InstagramClient()
        self.ayrshare = AyrshareClient()
        self.whisper = WhisperClient()
        self.openai_image = OpenAIImageClient()
        self.gemini_image = GeminiImageClient()
        self.costs = CostTracker()

    def _stamp(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    async def create_reel(
        self,
        script: str,
        caption: str,
        *,
        video_provider: VideoProvider = "remotion",
        # Remotion params (default provider)
        composition_id: str = "MyComp",
        video_props: dict | None = None,
        # Runway params (cinematic provider)
        scene_prompt: str = "",
        # Common params
        language: str = "en",
        publish: bool = False,
        video_url_for_publish: str | None = None,
    ) -> Path:
        """
        Full Reel pipeline:
        1. ElevenLabs → voiceover (parallel with step 2)
        2. Video generation:
           - "remotion" (default) → code-driven, free, template-based
           - "runway" → AI-generated cinematic video ($$$)
        3. FFmpeg → merge video + audio
        4. Whisper → SRT subtitles
        5. FFmpeg → burn subtitles
        6. (Optional) Instagram → publish
        """
        stamp = self._stamp()
        audio_path = settings.AUDIO_DIR / f"vo_{stamp}.mp3"
        video_raw = settings.VIDEOS_DIR / f"raw_{stamp}.mp4"
        video_merged = settings.VIDEOS_DIR / f"merged_{stamp}.mp4"
        srt_path = settings.SUBTITLES_DIR / f"subs_{stamp}.srt"
        video_final = settings.VIDEOS_DIR / f"reel_{stamp}.mp4"

        # Step 1 + 2: parallel — voiceover and video generation
        if video_provider == "remotion":
            log.info(f"Generating voiceover + Remotion video [{composition_id}] in parallel…")
            audio_path, video_raw = await asyncio.gather(
                self.elevenlabs.generate_speech(script, audio_path),
                self.remotion.render(composition_id, video_raw, props=video_props),
            )
            self.costs.log("elevenlabs", chars=len(script), meta={"step": "voiceover"})
            self.costs.log("remotion", renders=1, meta={"composition": composition_id})
        elif video_provider == "runway":
            if not scene_prompt:
                raise ValueError("scene_prompt is required when video_provider='runway'")
            log.info("Generating voiceover + Runway cinematic video in parallel…")
            audio_path, video_raw = await asyncio.gather(
                self.elevenlabs.generate_speech(script, audio_path),
                self.runway.text_to_video(scene_prompt, video_raw),
            )
            self.costs.log("elevenlabs", chars=len(script), meta={"step": "voiceover"})
            self.costs.log("runway", video_seconds=10, meta={"step": "video"})

        # Step 3: merge
        log.info("Merging video + audio…")
        await ffmpeg.merge_video_audio(video_raw, audio_path, video_merged)

        # Step 4: subtitles
        log.info("Generating subtitles…")
        await self.whisper.transcribe(audio_path, srt_path, language=language)
        audio_size = audio_path.stat().st_size
        est_seconds = audio_size / 16_000  # rough MP3 estimate
        self.costs.log("whisper", audio_seconds=est_seconds, meta={"step": "subtitles"})

        # Step 5: burn subtitles
        log.info("Burning subtitles into video…")
        await ffmpeg.burn_subtitles(video_merged, srt_path, video_final)

        log.info(f"Reel ready: {video_final}")

        # Step 6: optional publish
        if publish and video_url_for_publish:
            log.info("Publishing to Instagram…")
            media_id = await self.instagram.publish_reel(
                video_url_for_publish, caption
            )
            self.costs.log("instagram", calls=1, meta={"step": "publish"})
            log.info(f"Published! Media ID: {media_id}")

        # Cost report
        self.costs.summary()
        self.costs.save()

        return video_final

    async def create_batch_reel(
        self,
        sequences: list[dict],
        caption: str,
        *,
        video_provider: VideoProvider = "remotion",
        language: str = "en",
        publish: bool = False,
        video_url_for_publish: str | None = None,
    ) -> Path:
        """
        Batch Reel pipeline — generate multiple sequences and concatenate.

        Each sequence dict contains:
          - script: str — voiceover text for this segment
          - composition_id: str (remotion) or scene_prompt: str (runway)
          - video_props: dict (remotion only, optional)

        Steps per sequence:
        1. ElevenLabs → voiceover + video generation (parallel)
        2. FFmpeg → merge video + audio
        3. Whisper → subtitles
        4. FFmpeg → burn subtitles
        Then: FFmpeg → concatenate all segments into one final reel.
        """
        stamp = self._stamp()
        segment_paths: list[Path] = []

        for i, seq in enumerate(sequences, 1):
            seg_stamp = f"{stamp}_seg{i:02d}"
            script = seq["script"]
            audio_path = settings.AUDIO_DIR / f"vo_{seg_stamp}.mp3"
            video_raw = settings.VIDEOS_DIR / f"raw_{seg_stamp}.mp4"
            video_merged = settings.VIDEOS_DIR / f"merged_{seg_stamp}.mp4"
            srt_path = settings.SUBTITLES_DIR / f"subs_{seg_stamp}.srt"
            video_sub = settings.VIDEOS_DIR / f"sub_{seg_stamp}.mp4"

            comp_id = seq.get("composition_id", "KineticText")
            props = seq.get("video_props")
            scene = seq.get("scene_prompt", "")

            log.info(f"[Segment {i}/{len(sequences)}] Generating voiceover + video…")

            if video_provider == "remotion":
                audio_path, video_raw = await asyncio.gather(
                    self.elevenlabs.generate_speech(script, audio_path),
                    self.remotion.render(comp_id, video_raw, props=props),
                )
                self.costs.log("elevenlabs", chars=len(script), meta={"step": f"voiceover_seg{i}"})
                self.costs.log("remotion", renders=1, meta={"composition": comp_id})
            elif video_provider == "runway":
                if not scene:
                    raise ValueError(f"scene_prompt required for sequence {i} with runway provider")
                audio_path, video_raw = await asyncio.gather(
                    self.elevenlabs.generate_speech(script, audio_path),
                    self.runway.text_to_video(scene, video_raw),
                )
                self.costs.log("elevenlabs", chars=len(script), meta={"step": f"voiceover_seg{i}"})
                self.costs.log("runway", video_seconds=10, meta={"step": f"video_seg{i}"})

            log.info(f"[Segment {i}] Merging video + audio…")
            await ffmpeg.merge_video_audio(video_raw, audio_path, video_merged)

            log.info(f"[Segment {i}] Generating subtitles…")
            await self.whisper.transcribe(audio_path, srt_path, language=language)
            audio_size = audio_path.stat().st_size
            self.costs.log("whisper", audio_seconds=audio_size / 16_000, meta={"step": f"subtitles_seg{i}"})

            log.info(f"[Segment {i}] Burning subtitles…")
            await ffmpeg.burn_subtitles(video_merged, srt_path, video_sub)
            segment_paths.append(video_sub)

        # Concatenate all segments
        video_final = settings.VIDEOS_DIR / f"batch_{stamp}.mp4"
        log.info(f"Concatenating {len(segment_paths)} segments…")
        await ffmpeg.concat_clips(segment_paths, video_final)

        log.info(f"Batch reel ready: {video_final}")

        if publish and video_url_for_publish:
            log.info("Publishing to Instagram…")
            media_id = await self.instagram.publish_reel(video_url_for_publish, caption)
            self.costs.log("instagram", calls=1, meta={"step": "publish"})
            log.info(f"Published! Media ID: {media_id}")

        self.costs.summary()
        self.costs.save()
        return video_final

    async def create_image_reel(
        self,
        slides: list[dict],
        caption: str,
        *,
        script: str | None = None,
        hook: str = "Watch This",
        cta: str = "Follow for more",
        image_provider: ImageProvider = "openai",
        palette: str = "dark",
        handle: str = "",
        language: str = "en",
    ) -> Path:
        """
        AI Image Reel pipeline — generate images + CinematicSlides composition.

        Each slide dict:
          - prompt: str — image generation prompt
          - title: str (optional) — text overlay
          - subtitle: str (optional) — text overlay

        Steps:
        1. Generate all images in parallel (OpenAI DALL-E / Gemini / Stability)
        2. Copy images to Remotion public/slides/
        3. Render CinematicSlides composition
        4. (Optional) Add voiceover + subtitles if script provided
        """
        import shutil

        stamp = self._stamp()
        remotion_slides_dir = self.remotion.project_dir / "public" / "slides"
        remotion_slides_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: Generate all images in parallel
        log.info(f"Generating {len(slides)} images via {image_provider}…")

        async def _gen_image(i: int, slide: dict) -> Path:
            filename = f"slide_{i + 1:02d}.png"
            out = settings.IMAGES_DIR / f"cinematic_{stamp}_{filename}"
            prompt = slide["prompt"]

            if image_provider == "openai":
                await self.openai_image.generate(prompt, out)
                self.costs.log("openai_dalle", images=1, meta={"slide": i + 1})
            elif image_provider == "gemini":
                await self.gemini_image.generate(prompt, out)
                self.costs.log("gemini_image", images=1, meta={"slide": i + 1})
            elif image_provider == "stability":
                await self.stability.generate(prompt, out)
                self.costs.log("stability", images=1, meta={"slide": i + 1})

            # Copy to Remotion public/slides/
            dest = remotion_slides_dir / filename
            shutil.copy2(out, dest)
            return out

        # Step 1b: Generate voiceover in parallel with images (if script)
        audio_path = None
        duration_seconds = None
        if script:
            audio_path = settings.AUDIO_DIR / f"vo_{stamp}.mp3"
            log.info("Generating images + voiceover in parallel…")
            await asyncio.gather(
                asyncio.gather(*[_gen_image(i, s) for i, s in enumerate(slides)]),
                self.elevenlabs.generate_speech(script, audio_path),
            )
            self.costs.log("elevenlabs", chars=len(script), meta={"step": "voiceover"})

            # Probe audio duration so Remotion matches it exactly
            duration_seconds = await get_duration(audio_path)
            log.info(f"Voiceover duration: {duration_seconds:.1f}s — composition will match")
        else:
            await asyncio.gather(*[_gen_image(i, s) for i, s in enumerate(slides)])

        # Step 2: Build props for CinematicSlides composition
        slide_props = []
        for i, slide in enumerate(slides):
            slide_props.append({
                "image": f"slide_{i + 1:02d}.png",
                "title": slide.get("title", ""),
                "subtitle": slide.get("subtitle", ""),
            })

        video_props = {
            "hook": hook,
            "slides": slide_props,
            "cta": cta,
            "palette": palette,
            "handle": handle,
        }
        if duration_seconds:
            video_props["durationSeconds"] = duration_seconds

        # Step 3: Render (duration auto-matches voiceover)
        video_raw = settings.VIDEOS_DIR / f"cinematic_raw_{stamp}.mp4"
        log.info("Rendering CinematicSlides composition…")
        await self.remotion.render("CinematicSlides", video_raw, props=video_props)
        self.costs.log("remotion", renders=1, meta={"composition": "CinematicSlides"})

        # Step 4: Merge audio + subtitles (video already matches audio length)
        if audio_path:
            video_merged = settings.VIDEOS_DIR / f"cinematic_merged_{stamp}.mp4"
            srt_path = settings.SUBTITLES_DIR / f"subs_{stamp}.srt"
            video_final = settings.VIDEOS_DIR / f"cinematic_{stamp}.mp4"

            log.info("Merging video + audio…")
            await ffmpeg.merge_video_audio(video_raw, audio_path, video_merged)

            log.info("Generating subtitles…")
            await self.whisper.transcribe(audio_path, srt_path, language=language)
            audio_size = audio_path.stat().st_size
            self.costs.log("whisper", audio_seconds=audio_size / 16_000, meta={"step": "subtitles"})

            log.info("Burning subtitles…")
            await ffmpeg.burn_subtitles(video_merged, srt_path, video_final)
        else:
            video_final = video_raw

        log.info(f"Image reel ready: {video_final}")
        self.costs.summary()
        self.costs.save()
        return video_final

    async def create_image_post(
        self,
        image_prompt: str,
        caption: str,
        *,
        publish: bool = False,
        image_url_for_publish: str | None = None,
    ) -> Path:
        """Generate an image and optionally publish it."""
        stamp = self._stamp()
        image_path = settings.IMAGES_DIR / f"post_{stamp}.png"

        log.info("Generating image…")
        await self.stability.generate(image_prompt, image_path)
        self.costs.log("stability", images=1, meta={"step": "image"})
        log.info(f"Image ready: {image_path}")

        if publish and image_url_for_publish:
            media_id = await self.instagram.publish_image(
                image_url_for_publish, caption
            )
            self.costs.log("instagram", calls=1, meta={"step": "publish"})
            log.info(f"Published! Media ID: {media_id}")

        self.costs.summary()
        self.costs.save()
        return image_path

    async def create_avatar_video(
        self,
        script: str,
        output_name: str = "avatar",
    ) -> Path:
        """Generate a HeyGen spokesperson video."""
        stamp = self._stamp()
        output_path = settings.AVATARS_DIR / f"{output_name}_{stamp}.mp4"

        log.info("Generating avatar video…")
        await self.heygen.generate_video(script, output_path)
        self.costs.log("heygen", video_seconds=30, meta={"step": "avatar"})
        log.info(f"Avatar video ready: {output_path}")

        self.costs.summary()
        self.costs.save()
        return output_path

    async def create_trend_report(
        self,
        report: TrendReport,
        *,
        notebook_id: str | None = None,
    ) -> Path:
        """Generate a trend infographic report, optionally enriched by NotebookLM."""
        generator = ReportGenerator()
        output = await generator.generate(report, notebook_id=notebook_id)
        log.info(f"Trend report ready: {output}")
        return output

    async def schedule_post(
        self,
        text: str,
        platforms: list[str],
        *,
        media_urls: list[str] | None = None,
        schedule_date: str | None = None,
    ) -> dict:
        """Schedule content via Ayrshare."""
        log.info(f"Scheduling post to {platforms}…")
        result = await self.ayrshare.schedule_post(
            text, platforms, media_urls=media_urls, schedule_date=schedule_date
        )
        self.costs.log("ayrshare", posts=1, meta={"platforms": platforms})
        log.info(f"Scheduled: {result}")

        self.costs.summary()
        self.costs.save()
        return result
