"""Remotion — code-driven video generation via MCP or local render.

Free alternative to Runway for template-based Reels (kinetic text,
product showcases, listicles, branded intros). Covers ~90% of Reel
formats without API costs.
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

# Remotion project location
REMOTION_PROJECT = Path(r"C:\Users\njeng\OneDrive\Bureau\REMOTION")

# Windows requires shell=True for .cmd scripts (npx.cmd)
_IS_WIN = sys.platform == "win32"


class RemotionClient:
    def __init__(self, project_dir: Path | None = None):
        self.project_dir = project_dir or REMOTION_PROJECT

    async def render(
        self,
        composition_id: str,
        output_path: Path,
        *,
        props: dict | None = None,
        width: int = 1080,
        height: int = 1920,
    ) -> Path:
        """Render a Remotion composition to MP4."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd_parts = [
            "npx", "remotion", "render",
            composition_id,
            str(output_path),
            "--width", str(width),
            "--height", str(height),
        ]

        # Windows mangles JSON in shell args — write props to a temp file
        props_file = None
        if props:
            props_file = self.project_dir / "_temp_props.json"
            props_file.write_text(json.dumps(props), encoding="utf-8")
            cmd_parts.extend(["--props", str(props_file)])

        try:
            if _IS_WIN:
                # Quote each part so paths with spaces survive the shell
                cmd_str = subprocess.list2cmdline(cmd_parts)
                proc = await asyncio.create_subprocess_shell(
                    cmd_str,
                    cwd=str(self.project_dir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            else:
                proc = await asyncio.create_subprocess_exec(
                    *cmd_parts,
                    cwd=str(self.project_dir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                err = stderr.decode()
                # Version mismatch warnings contain "errors" but aren't fatal
                is_version_warning = "version mismatch" in err.lower()
                if not is_version_warning or not output_path.exists():
                    raise RuntimeError(f"Remotion render failed (exit {proc.returncode}): {err}")
        finally:
            if props_file and props_file.exists():
                props_file.unlink()

        if not output_path.exists():
            raise RuntimeError(f"Remotion render produced no output file: {output_path}")

        return output_path

    async def list_compositions(self) -> list[str]:
        """List available Remotion compositions."""
        if _IS_WIN:
            proc = await asyncio.create_subprocess_shell(
                "npx remotion compositions",
                cwd=str(self.project_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        else:
            proc = await asyncio.create_subprocess_exec(
                "npx", "remotion", "compositions",
                cwd=str(self.project_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

        stdout, _ = await proc.communicate()
        return [
            line.strip()
            for line in stdout.decode().splitlines()
            if line.strip() and not line.startswith((" ", "─", "│"))
        ]
