"""FFmpeg helpers — video assembly, subtitle burn-in, format conversion."""

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

_IS_WIN = sys.platform == "win32"


def _require_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path and _IS_WIN:
        # WinGet installs ffmpeg here but asyncio subprocess may not inherit full PATH
        winget = Path.home() / "AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe"
        if winget.exists():
            path = str(winget)
    if not path:
        raise RuntimeError("ffmpeg not found in PATH")
    return path


async def _run(cmd: list[str]) -> None:
    if _IS_WIN:
        proc = await asyncio.create_subprocess_shell(
            subprocess.list2cmdline(cmd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    else:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {stderr.decode()}")


async def merge_video_audio(
    video: Path, audio: Path, output: Path
) -> Path:
    """Merge video track with audio voiceover."""
    ff = _require_ffmpeg()
    output.parent.mkdir(parents=True, exist_ok=True)
    await _run([
        ff, "-y",
        "-i", str(video),
        "-i", str(audio),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        str(output),
    ])
    return output


async def burn_subtitles(
    video: Path, srt: Path, output: Path
) -> Path:
    """Burn SRT subtitles into video."""
    ff = _require_ffmpeg()
    output.parent.mkdir(parents=True, exist_ok=True)
    # FFmpeg subtitles filter needs: backslashes → forward slashes,
    # colons escaped (\:), and the path single-quoted for spaces
    srt_esc = str(srt).replace("\\", "/").replace(":", "\\:")
    await _run([
        ff, "-y",
        "-i", str(video),
        "-vf", f"subtitles='{srt_esc}'",
        str(output),
    ])
    return output


async def resize_for_reels(
    video: Path, output: Path, width: int = 1080, height: int = 1920
) -> Path:
    """Resize video to Instagram Reels 9:16 format."""
    ff = _require_ffmpeg()
    output.parent.mkdir(parents=True, exist_ok=True)
    await _run([
        ff, "-y",
        "-i", str(video),
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
               f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        str(output),
    ])
    return output


async def concat_clips(clips: list[Path], output: Path) -> Path:
    """Concatenate multiple video clips into one."""
    ff = _require_ffmpeg()
    output.parent.mkdir(parents=True, exist_ok=True)
    list_file = output.parent / "_concat_list.txt"
    list_file.write_text(
        "\n".join(f"file '{c}'" for c in clips), encoding="utf-8"
    )
    await _run([
        ff, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output),
    ])
    list_file.unlink()
    return output
