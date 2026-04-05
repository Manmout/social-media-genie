"""Generate hand-drawn lifestyle illustrations for trend reports via Gemini."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.apis.gemini_image import GeminiImageClient

OUTPUT = Path("output/images/reports")

# Shared style directive
STYLE = (
    "Hand-drawn ink illustration on off-white textured paper. "
    "Minimalist line art with subtle watercolor washes in muted earth tones "
    "(sage green, warm beige, terracotta, soft charcoal). "
    "Lifestyle editorial aesthetic — like a New Yorker magazine spot illustration. "
    "NO photorealism. NO 3D renders. NO gradients. NO digital look. "
    "Loose confident pen strokes, intentional imperfections, breathing white space. "
    "Aspect ratio 16:9, landscape orientation. No text, no labels, no UI elements."
)

PROMPTS = {
    "agentic-ai": (
        f"{STYLE} "
        "A person sitting cross-legged on the floor with a laptop, surrounded by "
        "small friendly robot helpers carrying papers, coffee cups, and plants. "
        "The robots are simple round shapes with stick legs. "
        "A cat sleeping nearby. Warm morning light from a window."
    ),
    "suno-ai": (
        f"{STYLE} "
        "A pair of headphones resting on a wooden desk next to a cup of coffee "
        "and a small potted succulent. Musical notes float gently upward from "
        "the headphones like steam from the coffee. A notebook with hand-drawn "
        "treble clefs sits open. Calm, meditative atmosphere."
    ),
    "claude-code": (
        f"{STYLE} "
        "A cozy workspace seen from above: an open laptop, a mechanical keyboard, "
        "a hand-thrown ceramic mug of tea, scattered sticky notes, and a small "
        "rubber duck. Thin ink lines show code symbols floating like thought "
        "bubbles. A houseplant in the corner. Peaceful maker energy."
    ),
    "agentic-music": (
        f"{STYLE} "
        "A hand placing a vinyl record on a turntable, but the grooves of the "
        "record transform into circuit-board traces that bloom into wildflowers. "
        "A microphone wrapped in ivy sits beside it. The fusion of analog warmth "
        "and digital creation. Serene, poetic."
    ),
    "open-source-pme": (
        f"{STYLE} "
        "A small storefront with an 'OPEN' sign, seen through a window. Inside, "
        "simple geometric shapes (circles, squares, triangles) collaborate around "
        "a table like a team meeting. One shape holds a wrench, another a "
        "magnifying glass. A bicycle parked outside. Community and craft."
    ),
}


async def main():
    client = GeminiImageClient()
    OUTPUT.mkdir(parents=True, exist_ok=True)

    for name, prompt in PROMPTS.items():
        out = OUTPUT / f"hero_{name}.png"
        print(f"\n--- {name} ---")
        print(f"Prompt: {prompt[:80]}...")
        try:
            result = await client.generate(prompt, out)
            print(f"OK: {result} ({result.stat().st_size // 1024} KB)")
        except Exception as e:
            print(f"FAILED: {e}")


if __name__ == "__main__":
    asyncio.run(main())
