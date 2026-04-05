#!/usr/bin/env python3
"""
One-shot setup -- verify gws, authenticate, pick calendar, create Sheets dashboard.

Usage:
    py -3.13 gws_setup.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from gws_helper import run_gws, GWS_CMD

ROOT = Path(__file__).resolve().parent
GWS_CONFIG = ROOT / ".gws_config.json"
DASHBOARD_CONFIG = ROOT / ".dashboard_config.json"


def check_gws_installed() -> bool:
    print("\n  1. Checking gws installation...")
    import subprocess
    result = subprocess.run(
        [GWS_CMD, "--version"], capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("  [FAIL] gws not found. Install: npm install -g @googleworkspace/cli")
        return False
    version = result.stdout.strip().split("\n")[0]
    print(f"  [OK] {version}")
    return True


def check_auth() -> bool:
    print("\n  2. Checking authentication...")
    data = run_gws("auth", "status")
    if data is None:
        print("  [FAIL] Cannot check auth status.")
        return False

    has_creds = data.get("plain_credentials_exists") or data.get("encrypted_credentials_exists")
    if not has_creds:
        print("  [WARN] Not authenticated yet.")
        print("  Run:  gws auth login")
        return False

    print(f"  [OK] Authenticated (project: {data.get('project_id', '?')})")
    return True


def pick_calendar() -> str | None:
    print("\n  3. Selecting calendar...")

    if GWS_CONFIG.exists():
        existing = json.loads(GWS_CONFIG.read_text(encoding="utf-8"))
        cal_id = existing.get("calendar_id")
        if cal_id:
            print(f"  [OK] Already configured: {cal_id}")
            resp = input("  Keep this calendar? (Y/n): ").strip().lower()
            if resp != "n":
                return cal_id

    data = run_gws(
        "calendar", "calendarList", "list",
    )
    if data is None:
        print("  [FAIL] Could not list calendars.")
        return None

    items = data.get("items", [])
    if not items:
        print("  [FAIL] No calendars found.")
        return None

    print(f"\n  Found {len(items)} calendar(s):\n")
    for i, cal in enumerate(items, 1):
        summary = cal.get("summary", "(no name)")
        cal_id = cal.get("id", "?")
        primary = " (primary)" if cal.get("primary") else ""
        print(f"    {i}. {summary}{primary}")
        print(f"       ID: {cal_id}")

    choice = input(f"\n  Pick a calendar [1-{len(items)}] (default: 1): ").strip()
    idx = int(choice) - 1 if choice.isdigit() and 1 <= int(choice) <= len(items) else 0
    selected = items[idx]
    cal_id = selected["id"]

    config = {"calendar_id": cal_id, "calendar_name": selected.get("summary", "")}
    GWS_CONFIG.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  [OK] Calendar saved: {selected.get('summary')}")
    return cal_id


def create_dashboard() -> str | None:
    print("\n  4. Setting up Sheets dashboard...")

    if DASHBOARD_CONFIG.exists():
        existing = json.loads(DASHBOARD_CONFIG.read_text(encoding="utf-8"))
        sid = existing.get("spreadsheet_id")
        if sid:
            print(f"  [OK] Dashboard already exists: {sid}")
            resp = input("  Re-create? (y/N): ").strip().lower()
            if resp != "y":
                return sid

    # Create spreadsheet
    data = run_gws(
        "sheets", "spreadsheets", "create",
        "--json", json.dumps({"properties": {"title": "Social Media Genie - Dashboard"}}),
    )
    if data is None:
        print("  [FAIL] Could not create spreadsheet.")
        return None

    spreadsheet_id = data.get("spreadsheetId")
    if not spreadsheet_id:
        print(f"  [FAIL] Unexpected response: {json.dumps(data)[:200]}")
        return None

    sheet_id = data.get("sheets", [{}])[0].get("properties", {}).get("sheetId", 0)
    print(f"  [OK] Spreadsheet created: {spreadsheet_id}")

    # Write header row using +append helper
    headers = [
        "run_id", "timestamp", "subject", "trend_score", "angle_retenu",
        "url_wordpress", "url_logbook", "url_tumblr", "url_brevo", "statut_podcast",
        "gdoc_url",
    ]
    run_gws(
        "sheets", "+append",
        "--spreadsheet", spreadsheet_id,
        "--values", ",".join(headers),
    )

    # Rename sheet to "Runs"
    run_gws(
        "sheets", "spreadsheets", "batchUpdate",
        "--params", json.dumps({"spreadsheetId": spreadsheet_id}),
        "--json", json.dumps({
            "requests": [{
                "updateSheetProperties": {
                    "properties": {"sheetId": sheet_id, "title": "Runs"},
                    "fields": "title",
                }
            }]
        }),
    )

    # Format header: #1a0a2e background, white bold text
    run_gws(
        "sheets", "spreadsheets", "batchUpdate",
        "--params", json.dumps({"spreadsheetId": spreadsheet_id}),
        "--json", json.dumps({
            "requests": [{
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0, "endRowIndex": 1,
                        "startColumnIndex": 0, "endColumnIndex": 11,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.1, "green": 0.04, "blue": 0.18},
                            "textFormat": {
                                "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                                "bold": True,
                            },
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat)",
                }
            }]
        }),
    )

    # Save config
    config = {
        "spreadsheet_id": spreadsheet_id,
        "sheet_name": "Runs",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    DASHBOARD_CONFIG.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    print(f"  [OK] Dashboard configured")
    print(f"  [OK] URL: {url}")
    return spreadsheet_id


def summary():
    print("\n  --- Configuration Summary ---\n")
    if GWS_CONFIG.exists():
        c = json.loads(GWS_CONFIG.read_text(encoding="utf-8"))
        print(f"  Calendar:  {c.get('calendar_name', '?')} ({c.get('calendar_id', '?')})")
    else:
        print("  Calendar:  NOT CONFIGURED")

    if DASHBOARD_CONFIG.exists():
        d = json.loads(DASHBOARD_CONFIG.read_text(encoding="utf-8"))
        sid = d.get("spreadsheet_id", "?")
        print(f"  Dashboard: https://docs.google.com/spreadsheets/d/{sid}")
    else:
        print("  Dashboard: NOT CREATED")
    print()


def main():
    print("\n  === Social Media Genie -- gws Setup ===")

    if not check_gws_installed():
        sys.exit(1)

    if not check_auth():
        sys.exit(1)

    pick_calendar()
    create_dashboard()
    summary()


if __name__ == "__main__":
    main()
