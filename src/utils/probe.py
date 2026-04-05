"""FFprobe helpers — extract media metadata."""

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

_IS_WIN = sys.platform == "win32"


def _require_ffprobe() -> str:
    path = shutil.which("ffprobe")
    if not path and _IS_WIN:
        winget = Path.home() / "AppData/Local/Microsoft/WinGet/Links/ffprobe.exe"
        if winget.exists():
            path = str(winget)
    if not path:
        raise RuntimeError("ffprobe not found in PATH")
    return path


async def get_duration(media_path: Path) -> float:
    """Return duration of a media file in seconds."""
    fp = _require_ffprobe()
    cmd = [
        fp, "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        str(media_path),
    ]

    if _IS_WIN:
        proc = await asyncio.create_subprocess_shell(
            subprocess.list2cmdline(cmd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    else:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    stdout, _ = await proc.communicate()
    return float(stdout.decode().strip())
