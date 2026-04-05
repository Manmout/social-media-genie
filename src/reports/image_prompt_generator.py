"""
Image prompt generator — creates 4 editorial lifestyle prompts per trend report.

Uses Gemini 2.0 Flash to generate art-directed prompts, with generic fallback.
Style: Monocle / Kinfolk / Wired covers — lifestyle minimaliste, scene humaine
sans visage, objet symbolique, palette froide, evocation > illustration.

Outputs: hero (1792x1024), thumbnail (1200x630), og_image (1200x628), tumblr_header (540x540).

Usage:
    gen = ImagePromptGenerator()
    prompts = await gen.generate(report)
    print(prompts.hero)
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import google.generativeai as genai

from src.reports.trend_report import TrendReport
from src.utils.logger import get_logger
from config import settings

log = get_logger("image-prompt")

GEMINI_MODEL = "gemini-2.0-flash"

SYSTEM_PROMPT = """\
Tu es directeur artistique pour un magazine economique premium \
(reference : Monocle, Kinfolk, Wired covers).

Regles absolues pour chaque prompt :
- Scene humaine sans visage identifiable (mains, silhouette, dos, epaule)
- Objet symbolique lie au trend au premier plan
- Arriere-plan epure ou bokeh leger
- Palette froide dominante (#0d0618, gris ardoise, blanc casse, noir)
- Un seul accent chaud subtil (ambre dore, teal #0a5c42, ou violet #6b3fc0)
- Lumiere naturelle laterale ou contre-jour doux
- AUCUN texte, AUCUN logo, AUCUN ecran lisible, AUCUN chiffre
- L'image EVOQUE l'emotion du trend sans l'illustrer litteralement
- PAS de robot, PAS d'illustration de concept tech litterale
- Style : photographie editoriale lifestyle minimaliste moderne

Formats :
- hero (1792x1024) : scene large, respiration, cinematique, profondeur de champ
- thumbnail (1200x630) : objet seul ou detail, tres epure, lisible en petit
- og_image (1200x628) : sobre, fort contraste, lisible en miniature
- tumblr_header (540x540) : carre, composition centree, bold

Retourne UNIQUEMENT un JSON valide avec les cles : hero, thumbnail, og_image, tumblr_header.
Chaque valeur est le prompt complet en anglais pour un modele de generation d'image."""


@dataclass
class ImagePromptSet:
    """Four image prompts for a trend report."""
    hero: str          # 1792x1024 — article header, wide landscape
    thumbnail: str     # 1200x630 — email hero, social share
    og_image: str      # 1200x628 — Open Graph meta image
    tumblr_header: str # 540x540  — Tumblr post image, square


class ImagePromptGenerator:
    """Generates art-directed editorial image prompts via Gemini with fallback."""

    async def generate(self, report: TrendReport) -> ImagePromptSet:
        """Generate 4 image prompts for a trend report."""
        if settings.GEMINI_API_KEY:
            try:
                return await self._generate_via_gemini(report)
            except Exception as e:
                log.warning(f"Gemini prompt generation failed: {e}. Using fallback.")

        return self._generate_fallback(report)

    async def _generate_via_gemini(self, r: TrendReport) -> ImagePromptSet:
        """Generate prompts via Gemini 2.0 Flash."""
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT,
            generation_config={
                "temperature": 0.8,
                "max_output_tokens": 1500,
            },
        )

        user_prompt = (
            f"Rapport : {r.trend_name}\n"
            f"Statut : {r.status} (croissance {r.growth.one_year} sur 1 an)\n"
            f"Categorie : {r.category}\n"
            f"Volume : {r.search_volume}\n"
            f"Contexte : {r.trigger or 'N/A'}\n\n"
            f"Genere 4 prompts lifestyle minimalistes editoriaux.\n"
            f"Rappel : l'image ne doit PAS illustrer le sujet tech litteralement.\n"
            f"Elle doit evoquer une atmosphere, une tension, une emotion humaine liee au trend."
        )

        response = model.generate_content(user_prompt)
        raw_text = response.text.strip()

        # Parse JSON (handle code fences)
        json_str = raw_text
        if "```json" in json_str:
            json_str = json_str.split("```json", 1)[1]
            json_str = json_str.split("```", 1)[0]
        elif "```" in json_str:
            json_str = json_str.split("```", 1)[1]
            json_str = json_str.split("```", 1)[0]
        json_str = json_str.strip()

        prompts = json.loads(json_str)

        result = ImagePromptSet(
            hero=prompts.get("hero", ""),
            thumbnail=prompts.get("thumbnail", ""),
            og_image=prompts.get("og_image", ""),
            tumblr_header=prompts.get("tumblr_header", ""),
        )
        log.info(f"Gemini generated 4 editorial prompts for '{r.trend_name}'")
        return result

    def _generate_fallback(self, r: TrendReport) -> ImagePromptSet:
        """Lifestyle editorial fallback prompts. No LLM needed."""
        topic = r.trend_name

        base = (
            f"Editorial lifestyle photography evoking the concept of {topic}. "
            f"Minimalist scene, human hands or silhouette without identifiable face, "
            f"symbolic object in foreground, clean background with soft bokeh. "
            f"Cool palette: dark charcoal #0d0618, slate grey, off-white. "
            f"Single warm accent: amber or teal #0a5c42. "
            f"Natural side lighting, no text, no logos, no screens. "
            f"Monocle magazine aesthetic, Kinfolk editorial style. "
        )

        log.info(f"Fallback editorial prompts for '{topic}'")
        return ImagePromptSet(
            hero=base + "Wide cinematic composition, deep depth of field, atmospheric, breathing space. 1792x1024.",
            thumbnail=base + "Single object detail shot, ultra clean, high contrast, readable at small size. 1200x630.",
            og_image=base + "Sober wide shot, strong contrast, moody lighting, editorial feel. 1200x628.",
            tumblr_header=base + "Square centered composition, bold single element, strong visual impact. 540x540.",
        )
