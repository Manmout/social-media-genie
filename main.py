#!/usr/bin/env python3
"""
Social Media Genie -- Main pipeline orchestrator.

Wires together:
  1. gemini_researcher  → deep research report + Google Doc
  2. report generator   → trend infographic (HTML)
  3. wp_publisher       → hemle.blog post
  4. tumblr_publisher   → hemle.tumblr.com post
  5. newsletter_publisher → Brevo email (draft)
  6. sheets_dashboard   → Google Sheets logging
  7. calendar_trigger   → event deduplication

Usage:
    # Manual run
    py -3.13 main.py --subject "Autonomous Creative Agents"

    # From calendar_trigger (auto)
    py -3.13 main.py --subject "AI Music" --run-source calendar --event-id abc123

    # With options
    py -3.13 main.py --subject "Vibe Coding" --lang fr --platforms wordpress,tumblr
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import settings
from gemini_researcher import run_deep_research
from claude_editorial import generate_editorial_keys
from sheets_dashboard import init_dashboard, log_run_to_dashboard
from calendar_trigger import mark_event_triggered
from src.reports.generator import ReportGenerator, build_report_from_analysis
from src.reports.wp_publisher import WPPublisher
from src.reports.tumblr_publisher import TumblrPublisher
from src.reports.newsletter_publisher import NewsletterPublisher
from src.utils.logger import get_logger

log = get_logger("pipeline")

REPORTS_DIR = Path(__file__).resolve().parent / "reports"


def _parse_research_to_report(research_md: str, subject: str) -> dict:
    """
    Extract structured trend data from Gemini research markdown.
    Returns a dict suitable for build_report_from_analysis().

    This is a best-effort extraction -- the Gemini output is free-form,
    so we provide sensible defaults for missing fields.
    """
    word_count = len(research_md.split())

    # Try to extract the opportunity matrix as takeaways
    takeaways = []
    lines = research_md.split("\n")
    in_takeaways = False
    in_questions = False
    questions = []

    for line in lines:
        stripped = line.strip()
        # Capture questions ouvertes
        if "questions ouvertes" in stripped.lower() or "open questions" in stripped.lower():
            in_questions = True
            in_takeaways = False
            continue
        if "sources" in stripped.lower() and stripped.startswith("#"):
            in_questions = False
            continue
        if in_questions and stripped.startswith(("*", "-", "1.", "2.", "3.", "4.", "5.")):
            q = stripped.lstrip("*-0123456789. ").strip()
            if q:
                questions.append(q)

        # Capture takeaways from opportunity matrix rows
        if "matrice" in stripped.lower() or "opportunity" in stripped.lower():
            in_takeaways = True
            continue
        if in_takeaways and "|" in stripped and "---" not in stripped:
            parts = [p.strip() for p in stripped.split("|") if p.strip()]
            if len(parts) >= 2 and parts[0].lower() not in ("opportunite", "opportunity", "maturite"):
                takeaways.append(f"{parts[0]} (maturite: {parts[1]})" if len(parts) >= 2 else parts[0])
        if in_takeaways and stripped.startswith("#"):
            in_takeaways = False

    # Add questions as takeaways if we didn't find matrix rows
    if not takeaways and questions:
        takeaways = questions[:5]

    # If still empty, extract first few bullet points
    if not takeaways:
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("*", "-")) and len(stripped) > 20:
                takeaways.append(stripped.lstrip("*- ").strip())
                if len(takeaways) >= 5:
                    break

    return {
        "trend_name": subject,
        "status": "surging",
        "search_volume": "N/A",
        "category": "Technology > AI",
        "growth_5y": "N/A",
        "growth_1y": "N/A",
        "growth_3m": "N/A",
        "trigger": f"Deep research via Gemini ({word_count} words)",
        "takeaways": takeaways[:5] if takeaways else [f"Research report available: {word_count} words"],
    }


async def run_pipeline(
    subject: str,
    *,
    run_source: str = "manual",
    event_id: str = "",
    lang: str = "fr",
    platforms: list[str] | None = None,
    research_options: dict | None = None,
    notebook_id: str | None = None,
    tier: str = "pro",
    with_image: bool = False,
) -> dict:
    """
    Full pipeline: research → report → publish → dashboard.

    Returns a summary dict with all URLs and metadata.
    """
    target_platforms = platforms or ["wordpress"]
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    start_time = time.time()

    log.info(f"=== Run {run_id} | Subject: {subject} | Source: {run_source} ===")

    # --- Step 0: Ensure dashboard exists ---
    init_dashboard()

    # --- Step 1: Deep Research via Gemini ---
    log.info("Step 1/4: Gemini deep research...")
    try:
        research = run_deep_research(subject, research_options)
        log.info(f"Research complete: {research['word_count']} words, {research['duration_seconds']}s")
    except Exception as e:
        log.error(f"Research failed: {e}")
        research = {
            "run_id": run_id,
            "subject": subject,
            "report_md_path": "",
            "gdoc_id": "",
            "gdoc_url": "",
            "word_count": 0,
            "gemini_model": "failed",
            "duration_seconds": 0,
        }

    # Read the research markdown for downstream use
    research_context = ""
    if research["report_md_path"] and Path(research["report_md_path"]).exists():
        research_context = Path(research["report_md_path"]).read_text(encoding="utf-8")

    # --- Step 2: Claude Editorial Keys ---
    log.info("Step 2/5: Claude editorial keys...")
    editorial = {}
    if research_context:
        try:
            editorial = generate_editorial_keys(
                subject=subject,
                research_context=research_context,
                lang=lang,
            )
            if not editorial.get("error"):
                log.info(f"Editorial: hook={len(editorial.get('hook', ''))} chars, "
                         f"{len(editorial.get('takeaways', []))} takeaways ({editorial.get('duration_seconds', 0)}s)")
            else:
                log.warning("Editorial generation returned an error, using fallback.")
                editorial = {}
        except Exception as e:
            log.warning(f"Editorial generation failed: {e}")

    # Save editorial keys alongside research
    if editorial and not editorial.get("error"):
        editorial_path = REPORTS_DIR / f"{run_id}_editorial.json"
        editorial_path.write_text(
            json.dumps(editorial, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        log.info(f"Editorial keys saved: {editorial_path}")

    # --- Step 3: Build TrendReport from research + editorial ---
    log.info("Step 3/5: Building trend report...")
    report_data = _parse_research_to_report(research_context, subject)

    # Override with editorial takeaways if available
    if editorial.get("takeaways"):
        report_data["takeaways"] = editorial["takeaways"]

    report = build_report_from_analysis(**report_data)

    # Inject research as NotebookLM-style insights
    if research_context:
        lines = research_context.split("\n")
        condensed = "\n".join(lines[:30])
        if len(condensed) > 1500:
            condensed = condensed[:1500] + "..."
        report.notebook_insights = condensed

    # Enrich with NotebookLM if a notebook_id is provided
    if notebook_id:
        log.info(f"Enriching with NotebookLM notebook {notebook_id}...")
        gen = ReportGenerator()
        nb_insights = await gen._query_notebooklm(notebook_id, subject)
        if nb_insights:
            report.notebook_insights = nb_insights
            report.notebook_id = notebook_id

    # Generate images if requested
    images = None
    if with_image:
        try:
            from src.reports.image_pipeline import ImagePipeline
            img_pipeline = ImagePipeline()
            images = await img_pipeline.generate(report)
            log.info(f"Images generated: {', '.join(images.keys())}")
        except Exception as e:
            log.warning(f"Image generation failed: {e}")

    # --- Step 4: Publish to platforms ---
    log.info(f"Step 4/5: Publishing to {', '.join(target_platforms)}...")
    urls = {"wordpress": "", "logbook": "", "tumblr": "", "brevo": ""}

    # WordPress
    if "wordpress" in target_platforms:
        try:
            publisher = WPPublisher()
            result = await publisher.publish(report, status="draft", tier=tier, images=images)
            urls["wordpress"] = result.get("link", "")
            local_file = result.get("local_file", "")
            log.info(f"WordPress: {urls['wordpress'] or 'draft saved locally'}")
            if local_file:
                log.info(f"Local file: {local_file}")
        except Exception as e:
            log.warning(f"WordPress publish failed: {e}")

    # Tumblr
    if "tumblr" in target_platforms:
        try:
            tumblr_pub = TumblrPublisher()
            result = await tumblr_pub.publish(
                report,
                state="published",
                report_url=urls["wordpress"],
                images=images,
                lang=lang,
            )
            urls["tumblr"] = result.get("url", "")
            log.info(f"Tumblr: {urls['tumblr']}")
        except Exception as e:
            log.warning(f"Tumblr publish failed: {e}")

    # Newsletter (draft only by default)
    if "newsletter" in target_platforms:
        try:
            nl_pub = NewsletterPublisher()
            path = await nl_pub.draft(
                report,
                full_report_url=urls["wordpress"],
                lang=lang,
                images=images,
            )
            urls["brevo"] = str(path)
            log.info(f"Newsletter draft: {path}")
        except Exception as e:
            log.warning(f"Newsletter draft failed: {e}")

    # --- Step 5: Log to dashboard ---
    log.info("Step 5/5: Updating dashboard...")
    # Use editorial angle if available, otherwise first takeaway
    angle = editorial.get("angle", "") or (report.takeaways[0] if report.takeaways else subject)

    run_data = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "subject": subject,
        "trend_score": "",
        "angle_retenu": angle[:100],
        "urls": urls,
        "podcast_status": "pending",
        "gdoc_url": research.get("gdoc_url", ""),
    }

    sheets_url = log_run_to_dashboard(run_data)

    # Mark calendar event as triggered
    if run_source == "calendar" and event_id:
        mark_event_triggered(event_id, run_id, subject)
        log.info(f"Calendar event {event_id} marked as triggered.")

    # --- Summary ---
    elapsed = round(time.time() - start_time, 1)
    published_count = sum(1 for v in urls.values() if v)

    log.info(f"=== Run {run_id} complete in {elapsed}s. {published_count} content(s) published. ===")

    return {
        "run_id": run_id,
        "subject": subject,
        "research": {
            "gemini_model": research.get("gemini_model", ""),
            "word_count": research.get("word_count", 0),
            "gdoc_url": research.get("gdoc_url", ""),
            "duration_seconds": research.get("duration_seconds", 0),
            "report_md_path": research.get("report_md_path", ""),
        },
        "editorial": {
            "hook": editorial.get("hook", ""),
            "angle": editorial.get("angle", ""),
            "headline": editorial.get("headline", ""),
            "model": editorial.get("model", ""),
            "duration_seconds": editorial.get("duration_seconds", 0),
        },
        "urls": urls,
        "sheets_url": sheets_url,
        "elapsed_seconds": elapsed,
    }


def main():
    parser = argparse.ArgumentParser(
        prog="social-media-genie-pipeline",
        description="End-to-end trend intelligence pipeline",
    )
    parser.add_argument("--subject", required=True, help="Research subject")
    parser.add_argument("--run-source", default="manual",
                        choices=["manual", "calendar"], help="How the run was triggered")
    parser.add_argument("--event-id", default="", help="Calendar event ID (for deduplication)")
    parser.add_argument("--lang", default="fr", choices=["fr", "en"], help="Output language")
    parser.add_argument("--platforms", default="wordpress",
                        help="Comma-separated: wordpress,tumblr,newsletter")
    parser.add_argument("--notebook", default=None, help="NotebookLM notebook ID for enrichment")
    parser.add_argument("--tier", default="pro", choices=["free", "pro"],
                        help="Content tier (default: pro)")
    parser.add_argument("--with-image", action="store_true",
                        help="Generate AI images for the report")
    parser.add_argument("--horizon", default="2025-2028", help="Research horizon")
    parser.add_argument("--audience", default="indie_creator",
                        help="Research audience: indie_creator, founder, investor, editorial")
    parser.add_argument("--axes", default=None,
                        help="Comma-separated research axes (default: landscape,whitespace,signals,failures)")

    args = parser.parse_args()

    platforms = [p.strip() for p in args.platforms.split(",")]

    research_options = {
        "horizon": args.horizon,
        "audience": args.audience,
        "lang": args.lang,
    }
    if args.axes:
        research_options["axes"] = [a.strip() for a in args.axes.split(",")]

    result = asyncio.run(run_pipeline(
        subject=args.subject,
        run_source=args.run_source,
        event_id=args.event_id,
        lang=args.lang,
        platforms=platforms,
        research_options=research_options,
        notebook_id=args.notebook,
        tier=args.tier,
        with_image=args.with_image,
    ))

    # Print final summary
    print(f"\n  === Pipeline Complete ===")
    print(f"  Run ID:    {result['run_id']}")
    print(f"  Subject:   {result['subject']}")
    print(f"  Research:  {result['research']['word_count']} words ({result['research']['gemini_model']})")
    print(f"  Google Doc: {result['research']['gdoc_url']}")
    ed = result.get("editorial", {})
    if ed.get("hook"):
        print(f"  Hook:      {ed['hook']}")
        print(f"  Angle:     {ed['angle']}")
        print(f"  Headline:  {ed['headline']}")
    for name, url in result["urls"].items():
        if url:
            print(f"  {name:11}: {url}")
    print(f"  Dashboard: {result['sheets_url']}")
    print(f"  Duration:  {result['elapsed_seconds']}s")
    print()


if __name__ == "__main__":
    main()
