"""
Central configuration — loads .env and exposes typed settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# --- Paths ---
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", str(_PROJECT_ROOT / "output"))).resolve()
VIDEOS_DIR = OUTPUT_DIR / "videos"
IMAGES_DIR = OUTPUT_DIR / "images"
AUDIO_DIR = OUTPUT_DIR / "audio"
SUBTITLES_DIR = OUTPUT_DIR / "subtitles"
AVATARS_DIR = OUTPUT_DIR / "avatars"

# --- Meta / Instagram ---
META_APP_ID = os.getenv("META_APP_ID", "")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")

# --- ElevenLabs ---
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

# --- Runway ---
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY", "")
RUNWAY_MODEL = os.getenv("RUNWAY_MODEL", "gen4")

# --- Stability AI ---
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")

# --- OpenAI (DALL-E + Whisper) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# --- Gemini (Flash Image) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# --- HeyGen ---
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY", "")
HEYGEN_AVATAR_ID = os.getenv("HEYGEN_AVATAR_ID", "")

# --- Ayrshare ---
AYRSHARE_API_KEY = os.getenv("AYRSHARE_API_KEY", "")

# --- Keywords Everywhere ---
KEYWORDS_EVERYWHERE_API_KEY = os.getenv("KEYWORDS_EVERYWHERE_API_KEY", "")

# --- WordPress (hemle.blog) ---
# --- WordPress.com (hemle.blog) ---
# Get token: node mcp-wordpress/get-token.js --browser --client-id ID --client-secret SECRET
WPCOM_SITE_ID = os.getenv("WPCOM_SITE_ID", "hemle.blog")
WPCOM_TOKEN = os.getenv("WPCOM_TOKEN", "")

# --- Brevo (email newsletters) ---
# Store key in .brevo_token file or set env var
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "Trend Signal by Hemle")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "hemle.store@gmail.com")

# --- Anthropic (Claude API) ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# --- Defaults ---
DEFAULT_IMAGE_PROVIDER = os.getenv("DEFAULT_IMAGE_PROVIDER", "gemini")
DEFAULT_VIDEO_PROVIDER = os.getenv("DEFAULT_VIDEO_PROVIDER", "runway")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def validate() -> list[str]:
    """Return list of missing required keys (empty = all good)."""
    required = {
        "INSTAGRAM_ACCESS_TOKEN": INSTAGRAM_ACCESS_TOKEN,
        "ELEVENLABS_API_KEY": ELEVENLABS_API_KEY,
    }
    return [k for k, v in required.items() if not v]
