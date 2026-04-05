"""
Report generator — renders TrendReport data into a beautiful HTML infographic.
Optionally enriches with NotebookLM insights via CLI subprocess.
"""

from __future__ import annotations

import asyncio
import html
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from src.reports.trend_report import (
    TrendReport,
    GrowthMetrics,
    PestalEntry,
    JobToBeDone,
    Competitor,
    MarketPlayer,
    TimelineEvent,
)
from src.utils.logger import get_logger
from config import settings

log = get_logger("report-generator")

TEMPLATE_PATH = Path(__file__).resolve().parent.parent.parent / "templates" / "trend_infographic.html"
REPORTS_DIR = settings.OUTPUT_DIR / "reports"


class ReportGenerator:
    """Generates HTML infographic reports from TrendReport data."""

    def __init__(self):
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    async def generate(self, report: TrendReport, notebook_id: str | None = None) -> Path:
        """
        Render a TrendReport into a self-contained HTML file.

        If notebook_id is provided, queries NotebookLM for additional insights
        and injects them into the report.
        """
        # Enrich with NotebookLM if requested
        if notebook_id:
            log.info(f"Querying NotebookLM notebook {notebook_id} for insights…")
            report.notebook_id = notebook_id
            report.notebook_insights = await self._query_notebooklm(
                notebook_id, report.trend_name
            )

        # Load template
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        # Build all replacements
        replacements = self._build_replacements(report)
        rendered = template
        for key, value in replacements.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", value)

        # Write output
        slug = report.trend_name.lower().replace(" ", "-").replace("/", "-")
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = REPORTS_DIR / f"trend_{slug}_{stamp}.html"
        output_path.write_text(rendered, encoding="utf-8")

        log.info(f"Report saved: {output_path}")
        return output_path

    def _build_replacements(self, r: TrendReport) -> dict[str, str]:
        """Build template placeholder -> value mapping."""
        return {
            # Header
            "TREND_NAME": _esc(r.trend_name),
            "STATUS_UPPER": r.status.upper(),
            "STATUS_COLOR": r.status_color(),
            "CATEGORY": _esc(r.category),
            "SEARCH_VOLUME": _esc(r.search_volume),
            "GENERATED_AT": _esc(r.generated_at),

            # Growth
            "GROWTH_5Y": _esc(r.growth.five_year),
            "GROWTH_1Y": _esc(r.growth.one_year),
            "GROWTH_3M": _esc(r.growth.three_month),

            # Sparkline
            "SPARKLINE_LINE": self._sparkline_path(r),
            "SPARKLINE_AREA": self._sparkline_area(r),

            # Timeline
            "TIMELINE_ITEMS": self._render_timeline(r.timeline),

            # PESTAL
            "PESTAL_ROWS": self._render_pestal(r.pestal),

            # JTBD
            "JTBD_CARDS": self._render_jtbd(r.jobs_to_be_done),

            # Canvas
            "CANVAS_WHO": _esc(r.canvas_who),
            "CANVAS_WHERE": _esc(r.canvas_where),
            "CANVAS_WHY_NOW": _esc(r.canvas_why_now),
            "CANVAS_BEHAVIOR": _esc(r.canvas_behavior),
            "CANVAS_UNMET": _esc(r.canvas_unmet),

            # Market
            "MARKET_BARS": self._render_market_bars(r.market_players),

            # Companies
            "COMPANIES_CARDS": self._render_companies(r.competitors),

            # NotebookLM
            "NOTEBOOK_DISPLAY": "" if r.notebook_insights else "display:none",
            "NOTEBOOK_INSIGHTS": _esc(r.notebook_insights),

            # Takeaways
            "TAKEAWAY_ITEMS": self._render_takeaways(r.takeaways),
        }

    # ── Section renderers ──────────────────────────────────────────

    def _render_timeline(self, events: list[TimelineEvent]) -> str:
        if not events:
            return '<div class="timeline-item"><span class="t-date">—</span><div class="t-event">No timeline data</div></div>'
        parts = []
        for ev in events:
            parts.append(
                f'<div class="timeline-item">'
                f'<span class="t-date">{_esc(ev.date)}</span>'
                f'<div class="t-event">{_esc(ev.event)}</div>'
                f'</div>'
            )
        return "\n".join(parts)

    def _render_pestal(self, entries: list[PestalEntry]) -> str:
        if not entries:
            return '<tr><td colspan="2" style="text-align:center;color:var(--text-dim)">No PESTAL data</td></tr>'
        factor_map = {
            "Political": "P", "Economic": "E", "Social": "S",
            "Technological": "T", "Environmental": "N", "Legal": "L",
        }
        parts = []
        for entry in entries:
            code = factor_map.get(entry.factor, "S")
            parts.append(
                f'<tr>'
                f'<td><span class="factor-badge factor-{code}">{_esc(entry.factor)}</span></td>'
                f'<td>{_esc(entry.impact)}</td>'
                f'</tr>'
            )
        return "\n".join(parts)

    def _render_jtbd(self, jobs: list[JobToBeDone]) -> str:
        if not jobs:
            return '<div class="jtbd-card"><div class="job">No data</div></div>'
        parts = []
        for j in jobs:
            parts.append(
                f'<div class="jtbd-card">'
                f'<div class="job">{_esc(j.job)}</div>'
                f'<div class="solution">{_esc(j.solution)}</div>'
                f'</div>'
            )
        return "\n".join(parts)

    def _render_market_bars(self, players: list[MarketPlayer]) -> str:
        if not players:
            return '<div style="color:var(--text-dim);text-align:center;">No market data</div>'
        colors = ["p1", "p2", "p3", "p4"]
        parts = []
        for i, p in enumerate(players):
            # Extract numeric share for bar width
            share_num = "".join(c for c in p.share if c.isdigit() or c == ".")
            width = float(share_num) if share_num else 10
            # Cap at 100
            width = min(width, 100)
            color_class = colors[i % len(colors)]
            parts.append(
                f'<div class="market-bar-row">'
                f'<div class="player-name">{_esc(p.name)}</div>'
                f'<div class="bar-track">'
                f'<div class="bar-fill {color_class}" style="width:{width}%">{_esc(p.share)}</div>'
                f'</div>'
                f'<div class="loved-pct">{_esc(p.loved)}</div>'
                f'</div>'
            )
        return "\n".join(parts)

    def _render_companies(self, companies: list[Competitor]) -> str:
        if not companies:
            return '<div class="company-card"><div class="co-name">No data</div></div>'
        parts = []
        for c in companies:
            parts.append(
                f'<div class="company-card">'
                f'<div class="co-name">{_esc(c.name)}</div>'
                f'<div class="co-detail">{_esc(c.detail)}</div>'
                f'</div>'
            )
        return "\n".join(parts)

    def _render_takeaways(self, takeaways: list[str]) -> str:
        if not takeaways:
            return '<li><span class="t-num">-</span>No takeaways generated</li>'
        parts = []
        for i, t in enumerate(takeaways, 1):
            parts.append(
                f'<li><span class="t-num">{i}</span>{_esc(t)}</li>'
            )
        return "\n".join(parts)

    # ── Sparkline SVG generation ───────────────────────────────────

    def _sparkline_path(self, r: TrendReport) -> str:
        """Generate SVG line path from timeline density."""
        points = self._timeline_to_points(r)
        if not points:
            return "M0,80 L1000,80"
        return "M" + " L".join(f"{x},{y}" for x, y in points)

    def _sparkline_area(self, r: TrendReport) -> str:
        """Generate SVG filled area path (line + bottom close)."""
        points = self._timeline_to_points(r)
        if not points:
            return "M0,100 L1000,100 Z"
        line = " L".join(f"{x},{y}" for x, y in points)
        return f"M{points[0][0]},100 L{line} L{points[-1][0]},100 Z"

    def _timeline_to_points(self, r: TrendReport) -> list[tuple[int, int]]:
        """
        Convert timeline events into sparkline data points.
        Maps years 2021-2026 to x=0-1000, with organic growth curve.
        """
        if not r.timeline:
            # Default: flat then exponential for "surging" trends
            if r.status == "surging":
                return [
                    (0, 95), (100, 95), (200, 95), (300, 95), (400, 92),
                    (500, 90), (600, 85), (700, 60), (750, 40), (800, 25),
                    (850, 15), (900, 8), (950, 4), (1000, 2),
                ]
            elif r.status == "peaked":
                return [
                    (0, 95), (200, 80), (400, 30), (500, 10), (600, 5),
                    (700, 15), (800, 30), (900, 50), (1000, 60),
                ]
            else:  # steady
                return [
                    (0, 60), (200, 55), (400, 50), (500, 48), (600, 45),
                    (700, 42), (800, 40), (900, 38), (1000, 35),
                ]

        # Map timeline events to growth curve
        n = len(r.timeline)
        points = []
        for i, ev in enumerate(r.timeline):
            x = int(i / max(n - 1, 1) * 1000)
            # Earlier events = lower interest, later = higher
            progress = i / max(n - 1, 1)
            if r.status == "surging":
                y = int(95 - (progress ** 2) * 93)
            elif r.status == "peaked":
                y = int(95 - abs(progress - 0.5) * 2 * 90)
            else:
                y = int(60 - progress * 20)
            points.append((x, max(2, min(98, y))))
        return points

    # ── NotebookLM integration ─────────────────────────────────────

    async def _query_notebooklm(self, notebook_id: str, trend_name: str) -> str:
        """
        Query NotebookLM for insights about the trend.
        Uses the notebooklm CLI to ask questions and get enriched context.
        """
        questions = [
            f"What are the key market dynamics and competitive landscape for {trend_name}?",
            f"What emerging opportunities and risks should be considered for {trend_name}?",
            f"What consumer behavior shifts are driving {trend_name} adoption?",
        ]

        insights_parts = []
        for q in questions:
            try:
                result = await asyncio.create_subprocess_exec(
                    "py", "-3.13", "-m", "notebooklm",
                    "use", notebook_id,
                    sys.executable, "-3.13", "-m", "notebooklm",
                    "ask", q, "--json",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
                )
                stdout, stderr = await result.communicate()
                if result.returncode == 0 and stdout:
                    data = json.loads(stdout.decode("utf-8", errors="replace"))
                    answer = data.get("answer", data.get("response", ""))
                    if answer:
                        insights_parts.append(answer)
            except Exception as e:
                log.warning(f"NotebookLM query failed: {e}")

        if not insights_parts:
            # Fallback: try single combined query
            try:
                result = await asyncio.create_subprocess_exec(
                    "py", "-3.13", "-m", "notebooklm",
                    "ask", f"Provide a comprehensive analysis of {trend_name}: market dynamics, opportunities, risks, and consumer behavior shifts.",
                    "--json",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
                )
                stdout, stderr = await result.communicate()
                if result.returncode == 0 and stdout:
                    data = json.loads(stdout.decode("utf-8", errors="replace"))
                    answer = data.get("answer", data.get("response", ""))
                    if answer:
                        return answer
            except Exception as e:
                log.warning(f"NotebookLM fallback query failed: {e}")
            return ""

        return "\n\n".join(insights_parts)


def build_report_from_analysis(
    trend_name: str,
    status: str = "surging",
    search_volume: str = "N/A",
    category: str = "Technology > AI",
    growth_5y: str = "N/A",
    growth_1y: str = "N/A",
    growth_3m: str = "N/A",
    trigger: str = "",
    timeline: list[dict] | None = None,
    pestal: list[dict] | None = None,
    jobs: list[dict] | None = None,
    market: list[dict] | None = None,
    competitors: list[dict] | None = None,
    canvas: dict | None = None,
    takeaways: list[str] | None = None,
) -> TrendReport:
    """
    Convenience builder — takes raw dicts (from CLI JSON or web search results)
    and returns a structured TrendReport.
    """
    report = TrendReport(
        trend_name=trend_name,
        status=status,
        search_volume=search_volume,
        category=category,
        growth=GrowthMetrics(
            five_year=growth_5y,
            one_year=growth_1y,
            three_month=growth_3m,
        ),
        trigger=trigger,
    )

    if timeline:
        report.timeline = [TimelineEvent(**e) for e in timeline]
    if pestal:
        report.pestal = [PestalEntry(**p) for p in pestal]
    if jobs:
        report.jobs_to_be_done = [JobToBeDone(**j) for j in jobs]
    if market:
        report.market_players = [MarketPlayer(**m) for m in market]
    if competitors:
        report.competitors = [Competitor(**c) for c in competitors]
    if canvas:
        report.canvas_who = canvas.get("who", "")
        report.canvas_where = canvas.get("where", "")
        report.canvas_why_now = canvas.get("why_now", "")
        report.canvas_behavior = canvas.get("behavior", "")
        report.canvas_unmet = canvas.get("unmet", "")
    if takeaways:
        report.takeaways = takeaways

    return report


def _esc(text: str) -> str:
    """HTML-escape text for safe rendering."""
    return html.escape(str(text)) if text else ""
