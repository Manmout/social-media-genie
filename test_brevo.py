#!/usr/bin/env python3
"""
Brevo integration test — verify API key, list contacts, generate draft newsletter.

Usage:
    py -3.13 test_brevo.py --draft                     # Generate HTML only
    py -3.13 test_brevo.py --draft --data data.json    # From specific trend data
    py -3.13 test_brevo.py --account                   # Check Brevo account info
    py -3.13 test_brevo.py --lists                     # List contact lists
    py -3.13 test_brevo.py --contacts                  # List contacts
    py -3.13 test_brevo.py --send --to you@email.com   # Send test email
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.apis.brevo import BrevoClient
from src.reports.generator import build_report_from_analysis
from src.reports.newsletter_publisher import NewsletterPublisher


async def main():
    parser = argparse.ArgumentParser(description="Brevo integration test")
    parser.add_argument("--draft", action="store_true", help="Generate newsletter HTML draft")
    parser.add_argument("--account", action="store_true", help="Show Brevo account info")
    parser.add_argument("--lists", action="store_true", help="List contact lists")
    parser.add_argument("--contacts", action="store_true", help="List contacts")
    parser.add_argument("--send", action="store_true", help="Send test newsletter")
    parser.add_argument("--to", default=None, help="Recipient email for --send")
    parser.add_argument("--data", default=None, help="JSON trend data file")
    parser.add_argument("--project", default="hemle", help="Project name (for display)")
    parser.add_argument("--open", action="store_true", help="Open draft in browser")
    args = parser.parse_args()

    brevo = BrevoClient()

    if not brevo.api_key and not args.draft:
        print("\n  No Brevo API key found.")
        print("  Set it up:")
        print('    echo "YOUR_API_KEY" > .brevo_token')
        print("    # or set BREVO_API_KEY in .env\n")
        return

    # Load or create sample trend data
    if args.data:
        data = json.loads(Path(args.data).read_text(encoding="utf-8"))
    else:
        data = {
            "trend_name": "Brevo Test",
            "status": "surging",
            "search_volume": "100K+",
            "category": "Technology > Email Marketing",
            "growth_5y": "+500%",
            "growth_1y": "+120%",
            "growth_3m": "+25%",
            "timeline": [
                {"date": "2023", "event": "SendinBlue rebrands to Brevo"},
                {"date": "2025", "event": "500K+ business customers"},
                {"date": "2026", "event": "AI-powered campaign optimization"},
            ],
            "pestal": [
                {"factor": "Economic", "impact": "Free tier up to 300 emails/day makes it accessible for indie creators"},
                {"factor": "Technological", "impact": "REST API v3 + Python SDK enables full automation"},
            ],
            "takeaways": [
                "Brevo's free tier (300 emails/day) is enough for early-stage newsletters",
                "API-first approach means full automation from trend analysis to email delivery",
                "Contact list segmentation enables free/pro tier content gating",
            ],
        }

    report = build_report_from_analysis(
        trend_name=data.get("trend_name", "Test"),
        status=data.get("status", "surging"),
        search_volume=data.get("search_volume", "N/A"),
        category=data.get("category", "Technology"),
        growth_5y=data.get("growth_5y", "N/A"),
        growth_1y=data.get("growth_1y", "N/A"),
        growth_3m=data.get("growth_3m", "N/A"),
        timeline=data.get("timeline"),
        pestal=data.get("pestal"),
        takeaways=data.get("takeaways"),
    )

    if args.account:
        info = await brevo.get_account()
        print(f"\n  Brevo Account ({args.project}):")
        print(f"    Email:   {info.get('email')}")
        print(f"    Company: {info.get('company')}")
        print(f"    Plan:    {info.get('plan')}")
        print(f"    Credits: {info.get('credits')}\n")

    if args.lists:
        lists = await brevo.list_lists()
        print(f"\n  Contact Lists:")
        for l in lists:
            print(f"    [{l['id']:>3}] {l['name']} ({l['totalSubscribers']} subscribers)")
        print()

    if args.contacts:
        contacts = await brevo.list_contacts(limit=20)
        print(f"\n  Contacts (first 20):")
        for c in contacts:
            name = c.get("attributes", {}).get("FIRSTNAME", "")
            print(f"    {c['email']:<40} {name}")
        print()

    if args.draft:
        publisher = NewsletterPublisher()
        path = await publisher.draft(report)
        print(f"\n  Newsletter draft saved to: {path}")
        if args.open:
            import webbrowser
            webbrowser.open(str(path))
        print()

    if args.send:
        if not args.to:
            print("\n  Error: --to required for --send\n")
            return
        publisher = NewsletterPublisher()
        recipients = [{"email": e.strip()} for e in args.to.split(",")]
        result = await publisher.send_transactional(report, to=recipients)
        print(f"\n  Test email sent!")
        print(f"    Message ID: {result.get('messageId')}")
        print(f"    To:         {args.to}")
        print(f"    Local:      {result.get('local_file')}\n")

    if not any([args.account, args.lists, args.contacts, args.draft, args.send]):
        print("\n  Use --draft, --account, --lists, --contacts, or --send")
        print("  Run with --help for full usage\n")


if __name__ == "__main__":
    asyncio.run(main())
