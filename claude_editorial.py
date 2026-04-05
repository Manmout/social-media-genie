#!/usr/bin/env python3
"""
Editorial Key Generator -- generates editorial keys from a research report.

Uses Gemini 2.0 Flash (same key as gemini_researcher.py).
Fallback: Anthropic Claude if ANTHROPIC_API_KEY is set and Gemini fails.

Takes raw research markdown and produces structured editorial output:
  - hook: one-line attention grabber
  - angle: the editorial perspective / thesis
  - body_intro: first paragraph of the article
  - headline: blog post title
  - seo_excerpt: meta description (150 chars)
  - social_caption: Instagram/Twitter-ready caption
  - takeaways: 3-5 actionable bullet points

Usage:
    from claude_editorial import generate_editorial_keys

    keys = generate_editorial_keys(
        subject="Agentic Music Composition",
        research_context="... markdown from gemini ...",
        lang="fr",
    )

    # CLI
    py -3.13 claude_editorial.py --subject "AI Music" --research reports/20260330_report.md
"""

import json
import time
from pathlib import Path

import google.generativeai as genai

from config import settings
from src.utils.logger import get_logger

log = get_logger("editorial")

GEMINI_MODEL = "gemini-2.0-flash"

SYSTEM_INSTRUCTION = (
    "Tu es le directeur editorial de Hemle, un media independant specialise "
    "dans l'intelligence de marche et les tendances tech/IA. "
    "Ton style: incisif, factuel, zero bullshit. Chaque phrase doit "
    "meriter sa place. Tu ecris pour des createurs independants et des "
    "fondateurs early-stage qui cherchent des angles que personne ne couvre.\n\n"
    "Regles:\n"
    "- Jamais de platitudes (\"le marche est en pleine croissance\")\n"
    "- Toujours un angle contrarian ou un insight non-evident\n"
    "- Le hook doit creer un micro-choc cognitif\n"
    "- Le body_intro doit donner envie de lire la suite sans tout reveler\n"
    "- Les takeaways doivent etre actionnables, pas descriptifs\n"
    "- Tu reponds TOUJOURS en JSON valide, sans texte avant/apres"
)


def _build_editorial_prompt(subject: str, research_context: str, lang: str) -> str:
    """Build the prompt for editorial key generation."""
    lang_instruction = {
        "fr": "Reponds ENTIEREMENT en francais.",
        "en": "Respond ENTIRELY in English.",
    }.get(lang, "Reponds en francais.")

    return f"""{lang_instruction}

Voici un rapport de recherche approfondie sur : **{subject}**

---
{research_context}
---

A partir de ce rapport, genere les cles editoriales suivantes.
Reponds UNIQUEMENT avec un bloc JSON valide, sans commentaire avant/apres.

{{
  "hook": "Une phrase d'accroche percutante (max 120 chars). Doit creer un declic.",
  "angle": "La these editoriale en 1-2 phrases. L'angle que personne ne prend.",
  "headline": "Titre d'article de blog (max 80 chars). Magnetique mais pas clickbait.",
  "body_intro": "Premier paragraphe de l'article (3-4 phrases). Pose le cadre, cree la tension, annonce la promesse.",
  "seo_excerpt": "Meta description SEO (max 155 chars). Inclut le mot-cle principal.",
  "social_caption": "Caption Instagram/LinkedIn (2-3 lignes + 5 hashtags pertinents).",
  "takeaways": [
    "Point actionnable 1 (commence par un verbe d'action)",
    "Point actionnable 2",
    "Point actionnable 3"
  ],
  "content_angles": [
    "Angle de contenu complementaire 1 (pour un futur article/reel)",
    "Angle de contenu complementaire 2"
  ]
}}"""


def _parse_json_response(raw_text: str) -> dict | None:
    """Extract JSON from a model response, handling code fences."""
    json_str = raw_text.strip()
    if "```json" in json_str:
        json_str = json_str.split("```json", 1)[1]
        json_str = json_str.split("```", 1)[0]
    elif "```" in json_str:
        json_str = json_str.split("```", 1)[1]
        json_str = json_str.split("```", 1)[0]
    json_str = json_str.strip()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


def _call_gemini(prompt: str) -> str:
    """Call Gemini API and return raw response text."""
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=SYSTEM_INSTRUCTION,
        generation_config={
            "temperature": 0.4,
            "top_p": 0.9,
            "max_output_tokens": 2048,
        },
    )
    response = model.generate_content(prompt)
    return response.text


def _call_claude(prompt: str) -> str:
    """Fallback: call Claude API and return raw response text."""
    import anthropic
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=SYSTEM_INSTRUCTION,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def generate_editorial_keys(
    subject: str,
    research_context: str,
    *,
    lang: str = "fr",
) -> dict:
    """
    Generate editorial keys from research context.

    Primary: Gemini 2.0 Flash (uses existing GEMINI_API_KEY).
    Fallback: Claude Sonnet (if ANTHROPIC_API_KEY is set).

    Returns dict with: hook, angle, headline, body_intro, seo_excerpt,
                        social_caption, takeaways, content_angles,
                        model, duration_seconds
    """
    if not settings.GEMINI_API_KEY and not settings.ANTHROPIC_API_KEY:
        log.error("Neither GEMINI_API_KEY nor ANTHROPIC_API_KEY set in .env")
        return _empty_result(subject)

    prompt = _build_editorial_prompt(subject, research_context, lang)
    model_used = GEMINI_MODEL
    start = time.time()

    # Try Gemini first
    raw_text = ""
    if settings.GEMINI_API_KEY:
        log.info(f"Calling {GEMINI_MODEL} for editorial keys...")
        try:
            raw_text = _call_gemini(prompt)
        except Exception as e:
            log.warning(f"Gemini editorial failed: {e}")

    # Fallback to Claude
    if not raw_text and settings.ANTHROPIC_API_KEY:
        model_used = "claude-sonnet-4-20250514"
        log.info(f"Falling back to {model_used}...")
        try:
            raw_text = _call_claude(prompt)
        except Exception as e:
            log.error(f"Claude editorial also failed: {e}")
            return _empty_result(subject)

    if not raw_text:
        log.error("No response from any model.")
        return _empty_result(subject)

    duration = round(time.time() - start, 1)
    log.info(f"Response received in {duration}s")

    keys = _parse_json_response(raw_text)
    if keys is None:
        log.error(f"Failed to parse response as JSON")
        log.error(f"Raw response: {raw_text[:500]}")
        return _empty_result(subject, raw_text=raw_text)

    keys["model"] = model_used
    keys["duration_seconds"] = duration

    log.info(f"Editorial keys generated: hook={len(keys.get('hook', ''))} chars, "
             f"{len(keys.get('takeaways', []))} takeaways")
    return keys


def _empty_result(subject: str, raw_text: str = "") -> dict:
    """Return a default empty result when generation fails."""
    return {
        "hook": "",
        "angle": "",
        "headline": subject,
        "body_intro": "",
        "seo_excerpt": "",
        "social_caption": "",
        "takeaways": [],
        "content_angles": [],
        "model": "",
        "duration_seconds": 0,
        "raw_text": raw_text,
        "error": True,
    }


# --- CLI ---

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Editorial Key Generator")
    parser.add_argument("--subject", required=True, help="Research subject")
    parser.add_argument("--research", required=True,
                        help="Path to research markdown file")
    parser.add_argument("--lang", default="fr", choices=["fr", "en"],
                        help="Output language (default: fr)")
    parser.add_argument("--save", default=None,
                        help="Save output JSON to this path")

    args = parser.parse_args()

    research_path = Path(args.research)
    if not research_path.exists():
        print(f"Error: {research_path} not found")
        raise SystemExit(1)

    research_text = research_path.read_text(encoding="utf-8")
    keys = generate_editorial_keys(
        subject=args.subject,
        research_context=research_text,
        lang=args.lang,
    )

    if keys.get("error"):
        print(f"\n  Editorial generation failed.")
        if keys.get("raw_text"):
            print(f"  Raw response: {keys['raw_text'][:300]}")
        raise SystemExit(1)

    # Display
    print(f"\n  === Editorial Keys for '{args.subject}' ===\n")
    print(f"  Hook:      {keys['hook']}")
    print(f"  Angle:     {keys['angle']}")
    print(f"  Headline:  {keys['headline']}")
    print(f"  SEO:       {keys['seo_excerpt']}")
    print(f"\n  Body intro:")
    print(f"    {keys['body_intro']}")
    print(f"\n  Social caption:")
    print(f"    {keys['social_caption']}")
    print(f"\n  Takeaways:")
    for i, t in enumerate(keys.get("takeaways", []), 1):
        print(f"    {i}. {t}")
    print(f"\n  Content angles:")
    for a in keys.get("content_angles", []):
        print(f"    - {a}")
    print(f"\n  Model: {keys['model']} | Duration: {keys['duration_seconds']}s")

    if args.save:
        save_path = Path(args.save)
        save_path.write_text(json.dumps(keys, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n  Saved to: {save_path}")
    print()
