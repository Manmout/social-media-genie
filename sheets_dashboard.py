#!/usr/bin/env python3
"""
Google Sheets dashboard -- logs each pipeline run to a shared spreadsheet.

Usage:
    from sheets_dashboard import init_dashboard, log_run_to_dashboard, update_run_field

    init_dashboard()  # no-op if already created

    sheets_url = log_run_to_dashboard({
        "run_id": "20250315-103000",
        "timestamp": "2025-03-15T10:30:00Z",
        "subject": "Autonomous Creative Agents",
        "trend_score": 0.87,
        "angle_retenu": "Le paradoxe du perfectionnisme",
        "urls": {
            "wordpress": "https://hemle.blog/...",
            "logbook": "https://hemle.blog/behind-the-machine/...",
            "tumblr": "https://hemle.tumblr.com/...",
            "brevo": "",
        },
        "podcast_status": "pending",
    })

    update_run_field("20250315-103000", "statut_podcast", "generated")
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from gws_helper import run_gws

ROOT = Path(__file__).resolve().parent
DASHBOARD_CONFIG = ROOT / ".dashboard_config.json"

COLUMNS = [
    "run_id", "timestamp", "subject", "trend_score", "angle_retenu",
    "url_wordpress", "url_logbook", "url_tumblr", "url_brevo", "statut_podcast",
    "gdoc_url",
]

COL_LETTERS = {col: chr(65 + i) for i, col in enumerate(COLUMNS)}  # A-K



def _load_config() -> dict | None:
    if DASHBOARD_CONFIG.exists():
        return json.loads(DASHBOARD_CONFIG.read_text(encoding="utf-8"))
    return None


def _sheets_url(spreadsheet_id: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"


# --- init ---

def init_dashboard() -> str | None:
    """Ensure the Sheets dashboard exists. No-op if already configured."""
    config = _load_config()
    if config and config.get("spreadsheet_id"):
        return config["spreadsheet_id"]

    print("[sheets] Creating dashboard spreadsheet...")

    data = run_gws(
        "sheets", "spreadsheets", "create",
        "--json", json.dumps({"properties": {"title": "Social Media Genie - Dashboard"}}),
    )
    if data is None or "spreadsheetId" not in (data if isinstance(data, dict) else {}):
        print("[sheets] Failed to create spreadsheet.")
        return None

    spreadsheet_id = data["spreadsheetId"]
    sheet_id = data.get("sheets", [{}])[0].get("properties", {}).get("sheetId", 0)

    # Write headers via +append helper
    run_gws(
        "sheets", "+append",
        "--spreadsheet", spreadsheet_id,
        "--values", ",".join(COLUMNS),
    )

    # Rename sheet to "Runs"
    run_gws(
        "sheets", "spreadsheets", "batchUpdate",
        "--params", json.dumps({"spreadsheetId": spreadsheet_id}),
        "--json", json.dumps({"requests": [{
            "updateSheetProperties": {
                "properties": {"sheetId": sheet_id, "title": "Runs"},
                "fields": "title",
            }
        }]}),
    )

    # Format header: #1a0a2e background, white bold text
    run_gws(
        "sheets", "spreadsheets", "batchUpdate",
        "--params", json.dumps({"spreadsheetId": spreadsheet_id}),
        "--json", json.dumps({"requests": [{
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
        }]}),
    )

    config = {
        "spreadsheet_id": spreadsheet_id,
        "sheet_name": "Runs",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    DASHBOARD_CONFIG.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[sheets] Dashboard created: {_sheets_url(spreadsheet_id)}")
    return spreadsheet_id


# --- log a run ---

def log_run_to_dashboard(run_data: dict) -> str:
    """Append a new row to the dashboard. Returns the Sheets URL."""
    config = _load_config()
    if not config:
        print("[sheets] No dashboard configured. Run gws_setup.py first.")
        return ""

    spreadsheet_id = config["spreadsheet_id"]
    urls = run_data.get("urls", {})

    row = [
        str(run_data.get("run_id", "")),
        str(run_data.get("timestamp", datetime.now(timezone.utc).isoformat())),
        str(run_data.get("subject", "")),
        str(run_data.get("trend_score", "")),
        str(run_data.get("angle_retenu", "")),
        str(urls.get("wordpress", "")),
        str(urls.get("logbook", "")),
        str(urls.get("tumblr", "")),
        str(urls.get("brevo", "")),
        str(run_data.get("podcast_status", "pending")),
        str(run_data.get("gdoc_url", "")),
    ]

    # Use +append helper with --json-values for proper escaping
    result = run_gws(
        "sheets", "+append",
        "--spreadsheet", spreadsheet_id,
        "--json-values", json.dumps([row]),
    )

    url = _sheets_url(spreadsheet_id)
    if result is not None:
        print(f"[sheets] Dashboard updated -> {url}")
    else:
        print(f"[sheets] Failed to append row. Dashboard: {url}")

    return url


# --- update a field ---

def _find_row_by_run_id(spreadsheet_id: str, sheet_name: str, run_id: str) -> int | None:
    """Find the row number (1-based) for a given run_id."""
    data = run_gws(
        "sheets", "+read",
        "--spreadsheet", spreadsheet_id,
        "--range", f"{sheet_name}!A:A",
    )
    if data is None:
        return None
    for i, row in enumerate(data.get("values", []), 1):
        if row and row[0] == run_id:
            return i
    return None


def update_run_field(run_id: str, field: str, value: str) -> bool:
    """Update a single cell in an existing row (identified by run_id)."""
    if field not in COL_LETTERS:
        print(f"[sheets] Unknown field: {field}. Must be one of {COLUMNS}")
        return False

    config = _load_config()
    if not config:
        print("[sheets] No dashboard configured.")
        return False

    spreadsheet_id = config["spreadsheet_id"]
    sheet_name = config.get("sheet_name", "Runs")
    col = COL_LETTERS[field]

    row_num = _find_row_by_run_id(spreadsheet_id, sheet_name, run_id)
    if row_num is None:
        print(f"[sheets] run_id '{run_id}' not found in dashboard.")
        return False

    cell_range = f"{sheet_name}!{col}{row_num}"

    result = run_gws(
        "sheets", "spreadsheets", "values", "update",
        "--params", json.dumps({
            "spreadsheetId": spreadsheet_id,
            "range": cell_range,
            "valueInputOption": "USER_ENTERED",
        }),
        "--json", json.dumps({"values": [[value]]}),
    )

    if result is not None:
        print(f"[sheets] Updated {field}='{value}' for run {run_id}")
        return True
    else:
        print(f"[sheets] Failed to update {field} for run {run_id}")
        return False


# --- CLI ---

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sheets dashboard management")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="Create the dashboard spreadsheet")
    sub.add_parser("url", help="Print the dashboard URL")

    p_update = sub.add_parser("update", help="Update a field for a run")
    p_update.add_argument("--run-id", required=True)
    p_update.add_argument("--field", required=True, choices=COLUMNS)
    p_update.add_argument("--value", required=True)

    args = parser.parse_args()

    if args.command == "init":
        init_dashboard()
    elif args.command == "url":
        cfg = _load_config()
        if cfg:
            print(_sheets_url(cfg["spreadsheet_id"]))
        else:
            print("Dashboard not configured. Run: py -3.13 gws_setup.py")
    elif args.command == "update":
        update_run_field(args.run_id, args.field, args.value)
    else:
        parser.print_help()
