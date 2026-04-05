#!/usr/bin/env python3
"""
Gemini Deep Research -- builds a structured prompt and calls Gemini API
to produce a market research report, saves it locally and as a Google Doc.

Usage:
    # As module
    from gemini_researcher import run_deep_research
    result = run_deep_research("Autonomous Creative Agents")

    # As CLI
    py -3.13 gemini_researcher.py --subject "Autonomous Creative Agents"
    py -3.13 gemini_researcher.py --subject "AI Music" --axes landscape,monetization --lang en
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import google.generativeai as genai
from config import settings
from gws_helper import run_gws

ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# --- Models ---
PRIMARY_MODEL = "gemini-2.0-flash"
FALLBACK_MODEL = "gemini-1.5-pro"

SYSTEM_INSTRUCTION = (
    "Tu es un analyste de marche specialise dans les technologies emergentes "
    "et l'IA creative. Tu produis des analyses rigoureuses, sourcees, et orientees "
    "vers l'action. Tu ne remplis pas. Chaque phrase apporte une information. "
    "Tu signales explicitement tes incertitudes plutot que d'extrapoler."
)

# --- Axes ---
AXES_DEFINITIONS = {
    "landscape": "cartographie exhaustive des acteurs (startups, outils, plateformes, projets open-source) avec leur niveau de maturite",
    "whitespace": "identification des white spaces -- niches techniquement faisables mais non adressees commercialement",
    "signals": "signaux faibles : papers recents, repos GitHub a forte velocite, discussions HN/Reddit/Discord qui emergent",
    "monetization": "analyse des modeles economiques existants et potentiels (SaaS, marketplace, token-gating, freemium, API licensing)",
    "community": "cartographie des communautes actives : forums, subreddits, Discords, newsletters, createurs d'influence",
    "failures": "post-mortems et projets abandonnes -- ce qui n'a pas fonctionne et pourquoi",
    "tech": "stack technologique dominant : frameworks, APIs, modeles fondateurs les plus utilises",
    "ethics": "enjeux ethiques, legaux et reglementaires emergents",
}

DEFAULT_AXES = ["landscape", "whitespace", "signals", "failures"]

# --- Audiences ---
AUDIENCE_DESCRIPTIONS = {
    "indie_creator": "un createur independant / vibe coder cherchant une niche editoriale et technique a fort potentiel",
    "founder": "un fondateur early-stage evaluant une opportunite de marche pour un MVP",
    "investor": "un analyste/investisseur cherchant a comprendre la dynamique competitive",
    "editorial": "un editeur/journaliste cherchant les angles les moins couverts et les sources primaires",
}


# --- Prompt builder ---

def build_research_prompt(subject: str, options: dict | None = None) -> str:
    """Build the full Gemini research prompt from subject + options."""
    opts = options or {}
    horizon = opts.get("horizon", "2025-2028")
    audience_key = opts.get("audience", "indie_creator")
    axes = opts.get("axes", DEFAULT_AXES)
    audience_desc = AUDIENCE_DESCRIPTIONS.get(audience_key, AUDIENCE_DESCRIPTIONS["indie_creator"])

    # Build axes block
    axes_lines = []
    for i, ax in enumerate(axes, 1):
        definition = AXES_DEFINITIONS.get(ax, ax)
        axes_lines.append(f"### Axe {i} : {ax.upper()}\n{definition}\n")
    axes_block = "\n".join(axes_lines)

    return f"""# MISSION : ETUDE DE MARCHE APPROFONDIE
## Domaine : {subject}
## Horizon d'analyse : {horizon}

---

## CONTEXTE DE LA DEMANDE

Tu es mandate pour produire une etude de marche de niveau professionnel sur : **{subject}**
Cette etude est destinee a : {audience_desc}.

L'objectif est d'identifier ce que la majorite des analyses existantes manque :
signaux faibles, acteurs sous-radar, espaces non adresses, dynamiques invisibles.

---

## AXES D'ANALYSE REQUIS

{axes_block}

---

## PROTOCOLE DE RECHERCHE

**Phase 1 -- Sources primaires d'abord**
Priorise : GitHub repos actifs (commits recents), arXiv, Product Hunt (90 derniers jours),
Hacker News, Reddit r/MachineLearning / r/artificial, newsletters specialisees, changelogs produits.

**Phase 2 -- Triangulation**
Chaque claim doit etre valide par au moins 2 sources independantes.
Marque [SOURCE UNIQUE -- a verifier] quand ce n'est pas possible.

**Phase 3 -- Anti-consensus**
Pour chaque tendance evidente, cherche activement la contre-these.
Cette tendance est-elle surevaluee, mal comprise, ou deja en declin ?

**Phase 4 -- Gap analysis**
Apres avoir cartographie ce qui existe, identifie ce qui n'existe PAS encore
mais devrait logiquement exister compte tenu de la trajectoire du marche.

---

## FORMAT DE SORTIE

Produis un executive brief dense de 800 a 1200 mots structure ainsi :

### 1. Signal d'entree
En 3 phrases : pourquoi ce marche est pertinent maintenant.

### 2. Analyse par axe
Une section par axe demande, avec findings concrets et sources.

### 3. Matrice d'opportunite
Tableau : Opportunite | Maturite (1-5) | Barriere d'entree | Signal de validation

### 4. Questions ouvertes
3 a 5 questions que cette recherche souleve sans repondre.
Formulees de facon tranchee, pas generique.

### 5. Sources cles
Les 10 sources les plus importantes identifiees.

---

## CONTRAINTE FINALE

Precision et honnetete sur les incertitudes > completude apparente.
Un finding solide sur 3 axes vaut mieux qu'un survol superficiel sur 10.
"""


def create_gdoc(title: str, content: str) -> dict:
    """Create a Google Doc with the given title and content via gws."""
    # Step 1: create blank doc
    data = run_gws(
        "docs", "documents", "create",
        "--json", json.dumps({"title": title}),
        tag="researcher",
    )
    if data is None or "documentId" not in (data if isinstance(data, dict) else {}):
        print("[researcher] Failed to create Google Doc.")
        return {"doc_id": "", "doc_url": ""}

    doc_id = data["documentId"]

    # Step 2: insert text in chunks to stay within command line limits
    CHUNK_SIZE = 5000
    chunks = [content[i:i + CHUNK_SIZE] for i in range(0, len(content), CHUNK_SIZE)]

    # Insert in reverse order since each insert pushes at index 1
    for chunk in reversed(chunks):
        body = json.dumps({
            "requests": [{
                "insertText": {
                    "location": {"index": 1},
                    "text": chunk,
                }
            }]
        }, ensure_ascii=False)
        run_gws(
            "docs", "documents", "batchUpdate",
            "--params", json.dumps({"documentId": doc_id}),
            "--json", body,
            tag="researcher",
        )

    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    print(f"[researcher] Google Doc created -> {doc_url}")
    return {"doc_id": doc_id, "doc_url": doc_url}


# --- Gemini API call ---

def _call_gemini(prompt: str, model_name: str) -> str:
    """Call Gemini API and return the response text."""
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=SYSTEM_INSTRUCTION,
        generation_config={
            "temperature": 0.3,
            "top_p": 0.85,
            "max_output_tokens": 8192,
        },
    )
    response = model.generate_content(prompt)
    return response.text


# --- Main function ---

def run_deep_research(subject: str, options: dict | None = None) -> dict:
    """
    Run deep research on a subject via Gemini API.

    Returns dict with: run_id, subject, report_md_path, gdoc_id, gdoc_url,
                        word_count, gemini_model, duration_seconds
    """
    opts = options or {}
    axes = opts.get("axes", DEFAULT_AXES)
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")

    print(f"[researcher] Building prompt (axes: {', '.join(axes)})...")
    prompt = build_research_prompt(subject, opts)
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]

    # Call Gemini with fallback
    model_used = PRIMARY_MODEL
    start = time.time()
    print(f"[researcher] Calling {PRIMARY_MODEL}...")

    try:
        report_text = _call_gemini(prompt, PRIMARY_MODEL)
    except Exception as e:
        print(f"[researcher] {PRIMARY_MODEL} failed: {e}")
        print(f"[researcher] Falling back to {FALLBACK_MODEL}...")
        model_used = FALLBACK_MODEL
        try:
            report_text = _call_gemini(prompt, FALLBACK_MODEL)
        except Exception as e2:
            print(f"[researcher] {FALLBACK_MODEL} also failed: {e2}")
            raise RuntimeError(f"Both Gemini models failed. Last error: {e2}") from e2

    duration = round(time.time() - start, 1)
    word_count = len(report_text.split())
    print(f"[researcher] Report: {word_count} words in {duration}s")

    # Save locally
    report_path = REPORTS_DIR / f"{run_id}_report.md"
    report_path.write_text(report_text, encoding="utf-8")
    print(f"[researcher] Saved -> {report_path}")

    # Create Google Doc
    doc_title = f"Research Report - {subject} - {run_id}"
    gdoc = create_gdoc(doc_title, report_text)

    # Save metadata
    metadata = {
        "run_id": run_id,
        "subject": subject,
        "prompt_hash": prompt_hash,
        "gemini_model": model_used,
        "options_used": opts,
        "word_count": word_count,
        "duration_seconds": duration,
        "gdoc_id": gdoc.get("doc_id", ""),
        "gdoc_url": gdoc.get("doc_url", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    meta_path = REPORTS_DIR / f"{run_id}_metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "run_id": run_id,
        "subject": subject,
        "report_md_path": str(report_path),
        "gdoc_id": gdoc.get("doc_id", ""),
        "gdoc_url": gdoc.get("doc_url", ""),
        "word_count": word_count,
        "gemini_model": model_used,
        "duration_seconds": duration,
    }


# --- CLI ---

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gemini Deep Research")
    parser.add_argument("--subject", required=True, help="Research subject")
    parser.add_argument("--horizon", default="2025-2028", help="Analysis horizon (default: 2025-2028)")
    parser.add_argument("--audience", default="indie_creator",
                        choices=list(AUDIENCE_DESCRIPTIONS.keys()),
                        help="Target audience (default: indie_creator)")
    parser.add_argument("--axes", default=None,
                        help="Comma-separated axes (default: landscape,whitespace,signals,failures)")
    parser.add_argument("--lang", default="fr", choices=["fr", "en"], help="Output language (default: fr)")

    args = parser.parse_args()

    opts = {
        "horizon": args.horizon,
        "audience": args.audience,
        "lang": args.lang,
    }
    if args.axes:
        opts["axes"] = [a.strip() for a in args.axes.split(",")]

    result = run_deep_research(args.subject, opts)
    print(f"\n  Research complete!")
    print(f"  Report:     {result['report_md_path']}")
    print(f"  Google Doc: {result['gdoc_url']}")
    print(f"  Words:      {result['word_count']}")
    print(f"  Model:      {result['gemini_model']}")
    print(f"  Duration:   {result['duration_seconds']}s")
