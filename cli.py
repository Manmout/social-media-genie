#!/usr/bin/env python3
"""
Social Media Genie — CLI entry point.

Usage:
    py -3.13 cli.py reel --script "..." --scene "..." --caption "..."
    py -3.13 cli.py image --prompt "..." --caption "..."
    py -3.13 cli.py avatar --script "..."
    py -3.13 cli.py schedule --text "..." --platforms instagram --date 2026-04-01T10:00:00Z
    py -3.13 cli.py check-keys
    py -3.13 cli.py spy --domain competitor.com --country us
    py -3.13 cli.py keywords --kw "instagram automation" "ai reels" --country us
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import settings
from src.orchestrator.pipeline import Pipeline
from src.utils.logger import get_logger

log = get_logger("cli")


def check_keys():
    """Validate which API keys are configured."""
    keys = {
        "META_APP_ID": settings.META_APP_ID,
        "INSTAGRAM_ACCESS_TOKEN": settings.INSTAGRAM_ACCESS_TOKEN,
        "INSTAGRAM_BUSINESS_ACCOUNT_ID": settings.INSTAGRAM_BUSINESS_ACCOUNT_ID,
        "ELEVENLABS_API_KEY": settings.ELEVENLABS_API_KEY,
        "ELEVENLABS_VOICE_ID": settings.ELEVENLABS_VOICE_ID,
        "RUNWAY_API_KEY": settings.RUNWAY_API_KEY,
        "STABILITY_API_KEY": settings.STABILITY_API_KEY,
        "OPENAI_API_KEY": settings.OPENAI_API_KEY,
        "HEYGEN_API_KEY": settings.HEYGEN_API_KEY,
        "AYRSHARE_API_KEY": settings.AYRSHARE_API_KEY,
        "KEYWORDS_EVERYWHERE_API_KEY": settings.KEYWORDS_EVERYWHERE_API_KEY,
    }
    print("\n  Social Media Genie — API Key Status\n")
    for name, value in keys.items():
        status = "OK" if value else "MISSING"
        icon = "+" if value else "-"
        print(f"  [{icon}] {name}: {status}")
    print()

    configured = sum(1 for v in keys.values() if v)
    print(f"  {configured}/{len(keys)} keys configured.\n")


async def cmd_reel(args):
    pipeline = Pipeline()
    kwargs = {
        "script": args.script,
        "caption": args.caption,
        "language": args.lang,
        "video_provider": args.provider,
    }
    if args.provider == "runway":
        kwargs["scene_prompt"] = args.scene
    elif args.provider == "remotion":
        kwargs["composition_id"] = args.composition
        if args.props:
            import json
            kwargs["video_props"] = json.loads(args.props)
    result = await pipeline.create_reel(**kwargs)
    print(f"\nReel created: {result}")


async def cmd_batch_reel(args):
    import json
    pipeline = Pipeline()

    # Load sequences from JSON file or inline JSON string
    if args.sequences.endswith(".json"):
        seq_data = json.loads(Path(args.sequences).read_text(encoding="utf-8"))
    else:
        seq_data = json.loads(args.sequences)

    result = await pipeline.create_batch_reel(
        sequences=seq_data,
        caption=args.caption,
        video_provider=args.provider,
        language=args.lang,
    )
    print(f"\nBatch reel created: {result}")


async def cmd_image_reel(args):
    import json
    pipeline = Pipeline()

    # Load slides from JSON file or inline JSON string
    if args.slides.endswith(".json"):
        slide_data = json.loads(Path(args.slides).read_text(encoding="utf-8"))
    else:
        slide_data = json.loads(args.slides)

    result = await pipeline.create_image_reel(
        slides=slide_data,
        caption=args.caption,
        script=args.script,
        hook=args.hook,
        cta=args.cta,
        image_provider=args.image_provider,
        palette=args.palette,
        handle=args.handle,
        language=args.lang,
    )
    print(f"\nImage reel created: {result}")


async def cmd_image(args):
    pipeline = Pipeline()
    result = await pipeline.create_image_post(
        image_prompt=args.prompt,
        caption=args.caption,
    )
    print(f"\nImage created: {result}")


async def cmd_avatar(args):
    pipeline = Pipeline()
    result = await pipeline.create_avatar_video(
        script=args.script,
        output_name=args.name,
    )
    print(f"\nAvatar video created: {result}")


async def cmd_schedule(args):
    pipeline = Pipeline()
    result = await pipeline.schedule_post(
        text=args.text,
        platforms=args.platforms,
        media_urls=args.media_urls,
        schedule_date=args.date,
    )
    print(f"\nScheduled: {result}")


async def cmd_spy(args):
    import json
    from src.apis import KeywordsEverywhereClient
    ke = KeywordsEverywhereClient()
    print(f"\nAnalyzing {args.domain} ({args.country})…\n")
    result = await ke.competitor_spy(
        args.domain,
        country=args.country,
        num_keywords=args.keywords,
        num_backlinks=args.backlinks,
    )
    # Traffic summary
    t = result.get("traffic", {})
    print(f"  Monthly traffic: {t.get('estimated_monthly_traffic', 'N/A')}")
    print(f"  Ranking keywords: {t.get('total_ranking_keywords', 'N/A')}")
    print(f"  Credits used: {result.get('total_credits', 'N/A')}\n")
    # Top keywords
    kws = result.get("top_keywords", [])
    if kws:
        print(f"  Top {len(kws)} keywords:")
        for kw in kws[:20]:
            print(f"    [{kw.get('serp_position', '?'):>3}] {kw.get('keyword', '')} "
                  f"(~{kw.get('estimated_monthly_traffic', 0)} visits/mo)")
    # Backlinks
    bls = result.get("backlinks", [])
    if bls:
        print(f"\n  Top {len(bls)} backlinks:")
        for bl in bls[:10]:
            print(f"    {bl.get('domain_source', '')} → {bl.get('anchor_text', '(no anchor)')}")
    print()


async def cmd_keywords(args):
    import json
    from src.apis import KeywordsEverywhereClient
    ke = KeywordsEverywhereClient()
    print(f"\nResearching {len(args.kw)} keywords ({args.country})…\n")
    result = await ke.get_keyword_data(args.kw, country=args.country)
    for item in result.get("data", []):
        vol = item.get("vol", 0)
        cpc = item.get("cpc", {}).get("value", "0")
        comp = item.get("competition", 0)
        print(f"  {item.get('keyword', ''):<40} vol={vol:<8} cpc=${cpc:<8} comp={comp:.2f}")
    print(f"\n  Credits used: {result.get('credits_consumed', 'N/A')}")

    if args.related > 0:
        print(f"\n  Fetching {args.related} related keywords per term…\n")
        for kw in args.kw:
            related = await ke.get_related_keywords(kw, num=args.related)
            print(f"  Related to '{kw}': {', '.join(related.get('data', []))}")
    print()


def cmd_costs(args):
    from src.utils.cost_tracker import CostTracker
    entries = CostTracker.load_history()
    if not entries:
        print("\n  No cost history yet. Run a pipeline first.\n")
        return

    # Show last N entries
    recent = entries[-args.last:]
    print(f"\n  Last {len(recent)} API calls:\n")
    for e in recent:
        date = e.get("date", "?")[:19]
        svc = e.get("service", "?")
        cost = e.get("cost_usd", 0)
        qty = e.get("quantity", 0)
        unit = e.get("unit", "?")
        print(f"  {date}  {svc:<22} {qty:>8.1f} {unit:<12} ${cost:.4f}")

    # Totals by service
    by_service: dict[str, float] = {}
    for e in entries:
        svc = e.get("service", "?")
        by_service[svc] = by_service.get(svc, 0) + e.get("cost_usd", 0)

    total = sum(by_service.values())
    print(f"\n  Lifetime totals ({len(entries)} calls):\n")
    for svc, cost in sorted(by_service.items(), key=lambda x: -x[1]):
        print(f"  {svc:<22} ${cost:.4f}")
    print(f"  {'-' * 30}")
    print(f"  {'TOTAL':<22} ${total:.4f}\n")


async def cmd_niche(args):
    from src.content.niche_inspirer import NicheInspirer
    inspirer = NicheInspirer()

    if args.mode == "explore":
        niches = await inspirer.explore(args.seed, country=args.country, num_related=args.related)
        inspirer.print_niches(niches, limit=args.top)
    elif args.mode == "full":
        result = await inspirer.full_pipeline(
            args.seed,
            country=args.country,
            num_niches=args.top,
            days=args.days,
        )
        niches_data = result["niches"]
        calendar_data = result["calendar"]
        print(f"\n  Top {len(niches_data)} niches for '{args.seed}':\n")
        for i, n in enumerate(niches_data, 1):
            print(f"  {i}. [{n['score']:5.1f}] {n['keyword']}")
        from src.content.niche_inspirer import CalendarEntry, ContentAngle
        cal_entries = [
            CalendarEntry(
                date=c["date"],
                niche=c["niche"],
                angle=ContentAngle(**c["angle"]),
                priority=c["priority"],
            )
            for c in calendar_data
        ]
        inspirer.print_calendar(cal_entries)
        print(f"  Full results saved to output/niches/\n")


async def cmd_brand_extract(args):
    from src.utils.brand_extractor import BrandExtractor
    extractor = BrandExtractor()
    print(f"\nExtracting brand assets from {args.url}…\n")
    result = await extractor.extract(args.url, output_path=args.output)
    print(f"  Brand kit saved to: {result}\n")


async def cmd_report(args):
    import json
    from src.reports.generator import ReportGenerator, build_report_from_analysis

    # Load trend data from JSON file or inline
    if args.data:
        if args.data.endswith(".json"):
            data = json.loads(Path(args.data).read_text(encoding="utf-8"))
        else:
            data = json.loads(args.data)
    else:
        # Build minimal report from CLI flags
        data = {
            "trend_name": args.trend,
            "status": args.status,
            "search_volume": args.volume or "N/A",
            "category": args.category or "Technology > AI",
        }

    report = build_report_from_analysis(
        trend_name=data.get("trend_name", args.trend),
        status=data.get("status", args.status),
        search_volume=data.get("search_volume", "N/A"),
        category=data.get("category", "Technology > AI"),
        growth_5y=data.get("growth_5y", "N/A"),
        growth_1y=data.get("growth_1y", "N/A"),
        growth_3m=data.get("growth_3m", "N/A"),
        trigger=data.get("trigger", ""),
        timeline=data.get("timeline"),
        pestal=data.get("pestal"),
        jobs=data.get("jobs"),
        market=data.get("market"),
        competitors=data.get("competitors"),
        canvas=data.get("canvas"),
        takeaways=data.get("takeaways"),
    )

    generator = ReportGenerator()
    output = await generator.generate(report, notebook_id=args.notebook)
    print(f"\n  Trend infographic report generated!")
    print(f"  Output: {output}\n")

    if args.open:
        import webbrowser
        webbrowser.open(str(output))


def _load_report(data_path: str):
    """Load trend data JSON and build a TrendReport."""
    import json
    from src.reports.generator import build_report_from_analysis
    if data_path.endswith(".json"):
        data = json.loads(Path(data_path).read_text(encoding="utf-8"))
    else:
        data = json.loads(data_path)
    return build_report_from_analysis(
        trend_name=data.get("trend_name", "Trend"),
        status=data.get("status", "surging"),
        search_volume=data.get("search_volume", "N/A"),
        category=data.get("category", "Technology > AI"),
        growth_5y=data.get("growth_5y", "N/A"),
        growth_1y=data.get("growth_1y", "N/A"),
        growth_3m=data.get("growth_3m", "N/A"),
        trigger=data.get("trigger", ""),
        timeline=data.get("timeline"),
        pestal=data.get("pestal"),
        jobs=data.get("jobs"),
        market=data.get("market"),
        competitors=data.get("competitors"),
        canvas=data.get("canvas"),
        takeaways=data.get("takeaways"),
    )


async def _generate_images(report, with_image: bool) -> dict | None:
    """Generate 4 trend images if --with-image is set."""
    if not with_image:
        return None
    from src.reports.image_pipeline import ImagePipeline
    pipeline = ImagePipeline()
    images = await pipeline.generate(report)
    print(f"  Images generated: {', '.join(images.keys())}")
    return images


async def cmd_publish(args):
    import subprocess
    from src.reports.wp_publisher import WPPublisher

    report = _load_report(args.data)

    # Enrich with NotebookLM if requested
    if args.notebook:
        from src.reports.generator import ReportGenerator
        gen = ReportGenerator()
        report.notebook_insights = await gen._query_notebooklm(args.notebook, report.trend_name)
        report.notebook_id = args.notebook

    # Generate images if requested
    images = await _generate_images(report, args.with_image)

    publisher = WPPublisher()
    result = await publisher.publish(report, status="draft", tier=args.tier, images=images)

    local_file = result["local_file"]

    # Copy to clipboard for easy WP paste
    if args.copy:
        html_content = Path(local_file).read_text(encoding="utf-8")
        try:
            proc = subprocess.Popen(
                ["clip.exe"], stdin=subprocess.PIPE, shell=False
            )
            proc.communicate(html_content.encode("utf-8"))
            print(f"\n  Copied to clipboard!")
        except Exception:
            print(f"\n  Could not copy to clipboard. Open the file and copy manually.")

    print(f"\n  WP blog post ready for '{report.trend_name}'")
    print(f"  Tier:   {args.tier.upper()}")
    print(f"  File:   {local_file}")
    if args.copy:
        print(f"\n  Next steps:")
        print(f"  1. Go to https://hemle.blog/wp-admin/post-new.php")
        print(f"  2. Add a Custom HTML block (+ icon → search 'HTML')")
        print(f"  3. Paste (Ctrl+V) — the full styled report is in your clipboard")
        print(f"  4. Set title: '{report.trend_name} — Trend Intelligence Report'")
        print(f"  5. Add categories: Trend Intelligence, {report.category.split(' > ')[-1]}")
        print(f"  6. Preview → Publish")
    print()


async def cmd_newsletter(args):
    from src.reports.newsletter_publisher import NewsletterPublisher

    report = _load_report(args.data)
    images = await _generate_images(report, args.with_image)

    publisher = NewsletterPublisher()
    full_url = args.url or ""
    lang = args.lang

    if args.mode == "draft":
        path = await publisher.draft(report, full_report_url=full_url, lang=lang, images=images)
        print(f"\n  Newsletter draft generated! (lang={lang})")
        print(f"  File: {path}")
        if args.open:
            import webbrowser
            webbrowser.open(str(path))

    elif args.mode == "send":
        if not args.to:
            print("\n  Error: --to is required for --mode send\n")
            return
        recipients = [{"email": e.strip()} for e in args.to.split(",")]
        result = await publisher.send_transactional(report, to=recipients, full_report_url=full_url, lang=lang, images=images)
        print(f"\n  Newsletter sent! (lang={lang})")
        print(f"  Message ID: {result.get('messageId')}")
        print(f"  Recipients: {len(recipients)}")
        print(f"  Local:      {result.get('local_file')}")

    elif args.mode == "campaign":
        if not args.list_id:
            print("\n  Error: --list-id is required for --mode campaign\n")
            return
        result = await publisher.send_campaign(
            report, list_ids=[args.list_id], full_report_url=full_url, lang=lang, images=images, send_now=args.send_now,
        )
        print(f"\n  Campaign {'sent' if args.send_now else 'created as draft'}!")
        print(f"  Campaign ID: {result.get('id')}")
        print(f"  Local:       {result.get('local_file')}")

    print()


async def cmd_tags(args):
    from src.content.tag_optimizer import TagOptimizer

    report = _load_report(args.data)
    slug = report.trend_name.lower().replace(" ", "-").replace("/", "-")
    seed_tags = [slug, report.status, "trend-analysis", "market-intelligence", "trend-signal"]
    # Add category parts
    for part in report.category.split(">"):
        t = part.strip().lower().replace(" ", "-")
        if t:
            seed_tags.append(t)

    optimizer = TagOptimizer()
    result = await optimizer.optimize(
        seed_tags=seed_tags,
        category=report.category,
        trend_name=report.trend_name,
        country=args.country,
    )

    print(f"\n  Tag Optimization for '{report.trend_name}'\n  {'=' * 40}\n")
    print(f"  Final tags ({len(result.tags)}):")
    for t in result.tags:
        print(f"    ✓ {t}")
    if result.rejected:
        print(f"\n  Rejected ({len(result.rejected)}):")
        for r in result.rejected:
            print(f"    ✗ {r['tag']:<30} vol={r['volume']} ({r['reason']})")
    if result.added:
        print(f"\n  Discovered ({len(result.added)}):")
        for a in result.added:
            print(f"    + {a['tag']:<30} vol={a['volume']} ({a['source']})")
    print(f"\n  Credits used: {result.credits_used}\n")


async def cmd_tumblr(args):
    from src.reports.tumblr_publisher import TumblrPublisher

    report = _load_report(args.data)
    images = await _generate_images(report, args.with_image)

    publisher = TumblrPublisher(blog=args.blog)
    result = await publisher.publish(
        report,
        state=args.state,
        report_url=args.url or "",
        images=images,
        lang=args.lang,
    )

    print(f"\n  Tumblr post {'published' if args.state == 'published' else 'created'}!")
    print(f"  URL:   {result.get('url')}")
    print(f"  State: {result.get('state')}")
    if images:
        print(f"  Image: tumblr_header.png injected")
    print()


def main():
    parser = argparse.ArgumentParser(
        prog="social-media-genie",
        description="Instagram automation pipeline powered by Claude Code",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # check-keys
    sub.add_parser("check-keys", help="Show API key status")

    # reel
    p_reel = sub.add_parser("reel", help="Create an Instagram Reel")
    p_reel.add_argument("--script", required=True, help="Voiceover script text")
    p_reel.add_argument("--caption", required=True, help="Instagram caption")
    p_reel.add_argument("--provider", choices=["remotion", "runway"], default="remotion",
                        help="Video provider: remotion (free, default) or runway (cinematic, paid)")
    p_reel.add_argument("--scene", default="", help="Visual scene prompt (required for --provider runway)")
    p_reel.add_argument("--composition", default="MyComp", help="Remotion composition ID (default: MyComp)")
    p_reel.add_argument("--props", default=None, help="JSON props for Remotion composition")
    p_reel.add_argument("--lang", default="en", help="Voiceover language (default: en)")

    # batch-reel
    p_batch = sub.add_parser("batch-reel", help="Create a longer reel from multiple sequences")
    p_batch.add_argument("--sequences", required=True,
                         help="JSON file path or inline JSON array of sequence objects. "
                              'Each object: {"script": "...", "composition_id": "...", "video_props": {...}}')
    p_batch.add_argument("--caption", required=True, help="Instagram caption for the final reel")
    p_batch.add_argument("--provider", choices=["remotion", "runway"], default="remotion")
    p_batch.add_argument("--lang", default="en", help="Voiceover language (default: en)")

    # image-reel
    p_ir = sub.add_parser("image-reel", help="AI-generated images + cinematic animations")
    p_ir.add_argument("--slides", required=True,
                      help='JSON file or inline array: [{"prompt":"...","title":"...","subtitle":"..."},...]')
    p_ir.add_argument("--caption", required=True, help="Instagram caption")
    p_ir.add_argument("--script", default=None, help="Optional voiceover script (adds audio + subtitles)")
    p_ir.add_argument("--hook", default="Watch This", help="Intro hook text (default: Watch This)")
    p_ir.add_argument("--cta", default="Follow for more", help="Outro CTA text")
    p_ir.add_argument("--image-provider", choices=["openai", "gemini", "stability"], default="openai",
                      help="Image generation provider (default: openai)")
    p_ir.add_argument("--palette", default="dark", choices=["dark", "warm", "ocean", "mint"],
                      help="Color palette (default: dark)")
    p_ir.add_argument("--handle", default="", help="Social handle watermark")
    p_ir.add_argument("--lang", default="en", help="Voiceover language (default: en)")

    # image
    p_img = sub.add_parser("image", help="Create an image post")
    p_img.add_argument("--prompt", required=True, help="Image generation prompt")
    p_img.add_argument("--caption", required=True, help="Instagram caption")

    # avatar
    p_av = sub.add_parser("avatar", help="Create an avatar spokesperson video")
    p_av.add_argument("--script", required=True, help="Script for the avatar to speak")
    p_av.add_argument("--name", default="avatar", help="Output filename prefix")

    # schedule
    p_sched = sub.add_parser("schedule", help="Schedule a post via Ayrshare")
    p_sched.add_argument("--text", required=True, help="Post text/caption")
    p_sched.add_argument("--platforms", nargs="+", default=["instagram"], help="Target platforms")
    p_sched.add_argument("--media-urls", nargs="*", help="Media URLs to attach")
    p_sched.add_argument("--date", help="ISO schedule date (e.g., 2026-04-01T10:00:00Z)")

    # spy (competitor analysis)
    p_spy = sub.add_parser("spy", help="Competitor analysis via Keywords Everywhere")
    p_spy.add_argument("--domain", required=True, help="Competitor domain (e.g., competitor.com)")
    p_spy.add_argument("--country", default="us", help="Country code (default: us)")
    p_spy.add_argument("--keywords", type=int, default=50, help="Max keywords to retrieve (default: 50)")
    p_spy.add_argument("--backlinks", type=int, default=20, help="Max backlinks to retrieve (default: 20)")

    # keywords
    p_kw = sub.add_parser("keywords", help="Keyword research via Keywords Everywhere")
    p_kw.add_argument("--kw", nargs="+", required=True, help="Keywords to research (max 100)")
    p_kw.add_argument("--country", default="us", help="Country code (default: us)")
    p_kw.add_argument("--related", type=int, default=0, help="Also fetch N related keywords per term")

    # costs
    p_costs = sub.add_parser("costs", help="Show API cost history")
    p_costs.add_argument("--last", type=int, default=20, help="Show last N entries (default: 20)")

    # niche
    p_niche = sub.add_parser("niche", help="Discover profitable niches and generate content angles")
    p_niche.add_argument("--seed", required=True, help="Seed topic (e.g., 'AI tools for creators')")
    p_niche.add_argument("--mode", choices=["explore", "full"], default="explore",
                         help="explore = ranked niches only; full = niches + angles + calendar")
    p_niche.add_argument("--country", default="us", help="Country code (default: us)")
    p_niche.add_argument("--top", type=int, default=10, help="Number of top niches to show (default: 10)")
    p_niche.add_argument("--related", type=int, default=20, help="Related keywords to fetch per seed (default: 20)")
    p_niche.add_argument("--days", type=int, default=14, help="Calendar days for full mode (default: 14)")

    # brand-extract
    p_brand = sub.add_parser("brand-extract", help="Extract brand assets from a URL")
    p_brand.add_argument("--url", required=True, help="Website URL to analyze")
    p_brand.add_argument("--output", default=None, help="Output JSON path (default: output/brands/<domain>.json)")

    # report (trend infographic)
    p_report = sub.add_parser("report", help="Generate a trend infographic report (HTML)")
    p_report.add_argument("--trend", default="Trend", help="Trend name (e.g., 'Claude Code')")
    p_report.add_argument("--data", default=None,
                          help="JSON file path or inline JSON with full trend analysis data")
    p_report.add_argument("--notebook", default=None, help="NotebookLM notebook ID for enriched insights")
    p_report.add_argument("--status", choices=["surging", "steady", "peaked"], default="surging",
                          help="Trend status (default: surging)")
    p_report.add_argument("--volume", default=None, help="Search volume (e.g., '1M+')")
    p_report.add_argument("--category", default=None, help="Category path (e.g., 'Technology > AI')")
    p_report.add_argument("--open", action="store_true", help="Auto-open report in browser after generation")

    # publish (WordPress blog post)
    p_pub = sub.add_parser("publish", help="Generate + publish trend report to hemle.blog")
    p_pub.add_argument("--data", required=True, help="JSON file with trend analysis data")
    p_pub.add_argument("--notebook", default=None, help="NotebookLM notebook ID for enrichment")
    p_pub.add_argument("--status", choices=["draft", "publish"], default="draft",
                        help="WordPress post status (default: draft)")
    p_pub.add_argument("--tier", choices=["free", "pro"], default="pro",
                        help="Content tier: free (truncated + CTA) or pro (full report)")
    p_pub.add_argument("--copy", action="store_true", default=True,
                        help="Copy HTML to clipboard for WP paste (default: true)")
    p_pub.add_argument("--no-copy", dest="copy", action="store_false",
                        help="Don't copy to clipboard")
    p_pub.add_argument("--with-image", action="store_true",
                        help="Generate 4 AI images (hero, thumbnail, og_image, tumblr_header)")

    # newsletter (Brevo email)
    p_nl = sub.add_parser("newsletter", help="Generate + send trend report as email newsletter via Brevo")
    p_nl.add_argument("--data", required=True, help="JSON file with trend analysis data")
    p_nl.add_argument("--mode", choices=["draft", "send", "campaign"], default="draft",
                       help="draft = generate HTML only; send = transactional email; campaign = Brevo campaign")
    p_nl.add_argument("--to", default=None,
                       help="Recipient email (for --mode send). Comma-separated for multiple.")
    p_nl.add_argument("--list-id", type=int, default=None,
                       help="Brevo contact list ID (for --mode campaign)")
    p_nl.add_argument("--send-now", action="store_true",
                       help="Send campaign immediately (default: create as draft in Brevo)")
    p_nl.add_argument("--url", default=None,
                       help="Full report URL on hemle.blog (auto-generated if omitted)")
    p_nl.add_argument("--lang", choices=["fr", "en"], default="fr",
                       help="Newsletter language (default: fr)")
    p_nl.add_argument("--with-image", action="store_true",
                       help="Generate + inject thumbnail hero image")
    p_nl.add_argument("--open", action="store_true", help="Open generated HTML in browser")

    # tags (validate + optimize)
    p_tags = sub.add_parser("tags", help="Validate and optimize tags via Keywords Everywhere")
    p_tags.add_argument("--data", required=True, help="JSON file with trend analysis data")
    p_tags.add_argument("--country", default="us", help="Country code (default: us)")

    # tumblr
    p_tumblr = sub.add_parser("tumblr", help="Publish trend report to hemle.tumblr.com")
    p_tumblr.add_argument("--data", required=True, help="JSON file with trend analysis data")
    p_tumblr.add_argument("--blog", default="hemle", help="Tumblr blog name (default: hemle)")
    p_tumblr.add_argument("--state", choices=["published", "draft", "queue"], default="published",
                           help="Post state (default: published)")
    p_tumblr.add_argument("--url", default=None, help="Full report URL on hemle.blog")
    p_tumblr.add_argument("--with-image", action="store_true",
                           help="Generate + inject tumblr_header image")
    p_tumblr.add_argument("--lang", choices=["fr", "en"], default="fr",
                           help="Post language (default: fr)")

    args = parser.parse_args()

    if args.command == "check-keys":
        check_keys()
    elif args.command == "reel":
        asyncio.run(cmd_reel(args))
    elif args.command == "batch-reel":
        asyncio.run(cmd_batch_reel(args))
    elif args.command == "image-reel":
        asyncio.run(cmd_image_reel(args))
    elif args.command == "image":
        asyncio.run(cmd_image(args))
    elif args.command == "avatar":
        asyncio.run(cmd_avatar(args))
    elif args.command == "schedule":
        asyncio.run(cmd_schedule(args))
    elif args.command == "spy":
        asyncio.run(cmd_spy(args))
    elif args.command == "keywords":
        asyncio.run(cmd_keywords(args))
    elif args.command == "costs":
        cmd_costs(args)
    elif args.command == "niche":
        asyncio.run(cmd_niche(args))
    elif args.command == "brand-extract":
        asyncio.run(cmd_brand_extract(args))
    elif args.command == "report":
        asyncio.run(cmd_report(args))
    elif args.command == "publish":
        asyncio.run(cmd_publish(args))
    elif args.command == "newsletter":
        asyncio.run(cmd_newsletter(args))
    elif args.command == "tumblr":
        asyncio.run(cmd_tumblr(args))
    elif args.command == "tags":
        asyncio.run(cmd_tags(args))


if __name__ == "__main__":
    main()
