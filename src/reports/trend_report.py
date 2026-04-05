"""
Trend report data model — captures all fields from a /trends analyze --full session.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class GrowthMetrics:
    five_year: str = "N/A"
    one_year: str = "N/A"
    three_month: str = "N/A"


@dataclass
class PestalEntry:
    factor: str
    impact: str


@dataclass
class JobToBeDone:
    job: str
    solution: str


@dataclass
class Competitor:
    name: str
    detail: str


@dataclass
class MarketPlayer:
    name: str
    share: str
    loved: str
    segment: str


@dataclass
class TimelineEvent:
    date: str
    event: str


@dataclass
class TrendReport:
    """Full trend analysis report data."""
    # Core
    trend_name: str
    status: str = "surging"          # surging | steady | peaked
    search_volume: str = "N/A"
    category: str = "Technology > AI"
    generated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

    # Growth
    growth: GrowthMetrics = field(default_factory=GrowthMetrics)

    # Timeline
    timeline: list[TimelineEvent] = field(default_factory=list)

    # Analysis sections
    trigger: str = ""
    pestal: list[PestalEntry] = field(default_factory=list)
    jobs_to_be_done: list[JobToBeDone] = field(default_factory=list)
    market_players: list[MarketPlayer] = field(default_factory=list)
    competitors: list[Competitor] = field(default_factory=list)

    # Consumer trend canvas
    canvas_who: str = ""
    canvas_where: str = ""
    canvas_why_now: str = ""
    canvas_behavior: str = ""
    canvas_unmet: str = ""

    # Takeaways
    takeaways: list[str] = field(default_factory=list)

    # NotebookLM enrichment
    notebook_insights: str = ""
    notebook_id: str = ""

    def status_color(self) -> str:
        return {
            "surging": "#00E676",
            "steady": "#FFC107",
            "peaked": "#FF5252",
        }.get(self.status, "#90A4AE")

    def status_icon(self) -> str:
        return {
            "surging": "&#x25B2;&#x25B2;&#x25B2;",   # ▲▲▲
            "steady": "&#x2192;",                       # →
            "peaked": "&#x25BC;",                       # ▼
        }.get(self.status, "?")
