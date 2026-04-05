#!/usr/bin/env python3
"""
Google Calendar trigger — polls for "Publish: ..." events and launches the pipeline.

Usage:
    # One-shot scan (for cron / Task Scheduler)
    py -3.13 calendar_trigger.py

    # Continuous loop (every 15 min)
    py -3.13 calendar_trigger.py --loop --interval 900
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from gws_helper import run_gws

ROOT = Path(__file__).resolve().parent
GWS_CONFIG = ROOT / ".gws_config.json"
TRIGGERED_RUNS = ROOT / ".triggered_runs.json"

PREFIX = "Publish:"



def _log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[calendar_trigger] {ts} — {msg}")


# ─── deduplication ───────────────────────────────────────────────────────────

def _load_triggered() -> dict:
    if TRIGGERED_RUNS.exists():
        return json.loads(TRIGGERED_RUNS.read_text(encoding="utf-8"))
    return {}


def _save_triggered(data: dict):
    TRIGGERED_RUNS.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _cleanup_old_entries(data: dict, max_age_days: int = 30) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    cleaned = {}
    for eid, info in data.items():
        try:
            triggered_at = datetime.fromisoformat(info["triggered_at"])
            if triggered_at > cutoff:
                cleaned[eid] = info
        except (KeyError, ValueError):
            pass
    return cleaned


def mark_event_triggered(event_id: str, run_id: str, subject: str = ""):
    """Mark a calendar event as already processed."""
    data = _load_triggered()
    data[event_id] = {
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "subject": subject,
        "run_id": run_id,
    }
    data = _cleanup_old_entries(data)
    _save_triggered(data)


# ─── core scan ───────────────────────────────────────────────────────────────

def _get_calendar_id() -> str:
    if GWS_CONFIG.exists():
        config = json.loads(GWS_CONFIG.read_text(encoding="utf-8"))
        return config.get("calendar_id", "primary")
    return "primary"


def _parse_event_params(description: str | None) -> dict:
    """Try to parse optional JSON params from event description."""
    if not description:
        return {}
    try:
        return json.loads(description)
    except (json.JSONDecodeError, TypeError):
        return {}


def scan_and_trigger() -> int:
    """
    Scan Google Calendar for Publish events in the window [-30min, +2h].
    Returns the number of pipelines triggered.
    """
    cal_id = _get_calendar_id()
    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(minutes=30)).isoformat()
    time_max = (now + timedelta(hours=2)).isoformat()

    _log("Scan calendar...")

    params = json.dumps({
        "calendarId": cal_id,
        "timeMin": time_min,
        "timeMax": time_max,
        "singleEvents": True,
        "orderBy": "startTime",
    })

    data = run_gws(
        "calendar", "events", "list",
        "--params", params,
        tag="calendar_trigger",
    )

    if data is None:
        _log("Could not fetch calendar events.")
        return 0

    items = data.get("items", [])
    if not items:
        _log("No events in window.")
        return 0

    triggered = _load_triggered()
    triggered = _cleanup_old_entries(triggered)
    count = 0

    for event in items:
        summary = event.get("summary", "")
        if not summary.startswith(PREFIX):
            continue

        event_id = event.get("id", "")
        if event_id in triggered:
            _log(f"Already processed: \"{summary}\" (event_id: {event_id})")
            continue

        subject = summary[len(PREFIX):].strip()
        if not subject:
            _log(f"Empty subject in event \"{summary}\", skipping.")
            continue

        params = _parse_event_params(event.get("description"))
        run_id = now.strftime("%Y%m%d-%H%M%S")

        _log(f"Event detected: \"{summary}\" (event_id: {event_id})")
        _log(f"Triggering pipeline → run_id: {run_id}")

        # Build pipeline command
        cmd = [
            sys.executable, str(ROOT / "main.py"),
            "--subject", subject,
            "--run-source", "calendar",
            "--event-id", event_id,
        ]

        # Forward optional params from event description
        if params.get("lang"):
            cmd.extend(["--lang", params["lang"]])
        if params.get("platforms"):
            cmd.extend(["--platforms", ",".join(params["platforms"])])

        try:
            result = subprocess.run(cmd, timeout=600)
            if result.returncode == 0:
                _log(f"Pipeline completed successfully (run_id: {run_id})")
            else:
                _log(f"Pipeline exited with code {result.returncode}")
        except subprocess.TimeoutExpired:
            _log(f"Pipeline timed out after 10 minutes")
        except FileNotFoundError:
            _log(f"main.py not found at {ROOT / 'main.py'}")

        # Mark as triggered regardless of outcome (avoid infinite retries)
        mark_event_triggered(event_id, run_id, subject)
        count += 1

    if count == 0:
        _log("No new Publish events to process.")
    else:
        _log(f"{count} pipeline(s) triggered.")

    _save_triggered(triggered)
    return count


# ─── entry point ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Google Calendar → pipeline trigger")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=900,
                        help="Seconds between scans in loop mode (default: 900 = 15 min)")
    args = parser.parse_args()

    if args.loop:
        _log(f"Starting continuous mode (every {args.interval}s). Ctrl+C to stop.")
        while True:
            try:
                scan_and_trigger()
                time.sleep(args.interval)
            except KeyboardInterrupt:
                _log("Stopped.")
                break
    else:
        scan_and_trigger()


if __name__ == "__main__":
    main()
