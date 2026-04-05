"""ElevenLabs TTS — text → voiceover audio file."""

import httpx
from pathlib import Path
from config import settings


class ElevenLabsClient:
    BASE = "https://api.elevenlabs.io/v1"

    def __init__(self, api_key: str | None = None, voice_id: str | None = None):
        self.api_key = api_key or settings.ELEVENLABS_API_KEY
        self.voice_id = voice_id or settings.ELEVENLABS_VOICE_ID
        self.model = settings.ELEVENLABS_MODEL

    async def generate_speech(
        self,
        text: str,
        output_path: Path,
        *,
        voice_id: str | None = None,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
    ) -> Path:
        """Generate speech audio and save to output_path."""
        vid = voice_id or self.voice_id
        url = f"{self.BASE}/text-to-speech/{vid}"

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                url,
                headers={"xi-api-key": self.api_key},
                json={
                    "text": text,
                    "model_id": self.model,
                    "voice_settings": {
                        "stability": stability,
                        "similarity_boost": similarity_boost,
                    },
                },
            )
            resp.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(resp.content)

        return output_path
