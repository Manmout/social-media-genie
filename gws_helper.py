"""
Shared gws CLI helper -- finds the binary and runs commands.

On Windows, calls gws.exe directly to avoid cmd.exe mangling
special characters in JSON arguments.
"""

import json
import platform
import subprocess
from pathlib import Path

_IS_WINDOWS = platform.system() == "Windows"


def _find_gws() -> str:
    """Find the gws executable."""
    if not _IS_WINDOWS:
        return "gws"
    # Direct binary — bypasses cmd.exe and node wrapper entirely
    exe_path = (
        Path.home() / "AppData" / "Roaming" / "npm" / "node_modules"
        / "@googleworkspace" / "cli" / "node_modules" / ".bin_real" / "gws.exe"
    )
    if exe_path.exists():
        return str(exe_path)
    cmd_path = Path.home() / "AppData" / "Roaming" / "npm" / "gws.cmd"
    if cmd_path.exists():
        return str(cmd_path)
    return "gws"


GWS_CMD = _find_gws()


def run_gws(*args: str, timeout: int = 60, tag: str = "gws") -> dict | list | None:
    """Run a gws command and return parsed JSON, or None on failure."""
    cmd = [GWS_CMD, *args]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"[{tag}] gws error: {e}")
        return None
    if result.returncode != 0:
        print(f"[{tag}] gws error (rc={result.returncode}): {result.stderr.strip()[:300]}")
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw": result.stdout.strip()}
