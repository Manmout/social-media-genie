"""OpenAI Whisper — audio → SRT subtitles."""

import httpx
from pathlib import Path
from config import settings


class WhisperClient:
    BASE = "https://api.openai.com/v1/audio"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.OPENAI_API_KEY

    async def transcribe(
        self,
        audio_path: Path,
        output_path: Path,
        *,
        language: str = "en",
        response_format: str = "srt",
    ) -> Path:
        """Transcribe audio to SRT subtitle file."""
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.BASE}/transcriptions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                data={
                    "model": "whisper-1",
                    "language": language,
                    "response_format": response_format,
                },
                files={"file": (audio_path.name, audio_path.read_bytes())},
            )
            resp.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(resp.text, encoding="utf-8")

        return output_path
