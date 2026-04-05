"""
Niche Inspirer — discover profitable Instagram niches and generate content angles.

Combines Keywords Everywhere keyword/trend data with scoring heuristics
to surface niches with high engagement potential and low competition.

Usage:
    inspirer = NicheInspirer()

    # Explore niches around a seed topic
    niches = await inspirer.explore("personal finance for millennials", country="us")

    # Get content angles for a chosen niche
    angles = await inspirer.generate_angles(niches[0])

    # Full pipeline: seed → ranked niches → top angles → content calendar
    calendar = await inspirer.full_pipeline("AI tools for creators", num_niches=5, days=14)
"""

import asyncio
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path

from src.apis import KeywordsEverywhereClient
from src.utils.logger import get_logger
from config import settings

log = get_logger("niche_inspirer")


@dataclass
class Niche:
    keyword: str
    volume: int = 0
    cpc: float = 0.0
    competition: float = 0.0
    trend: list[int] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    score: float = 0.0

    @property
    def trend_direction(self) -> str:
        """Rising / Stable / Declining based on last 6 months of trend data."""
        if len(self.trend) < 3:
            return "unknown"
        recent = self.trend[-3:]
        older = self.trend[:3] if len(self.trend) >= 6 else self.trend[:len(self.trend) // 2]
        avg_recent = sum(recent) / len(recent) if recent else 0
        avg_older = sum(older) / len(older) if older else 1
        if avg_older == 0:
            return "rising" if avg_recent > 0 else "stable"
        ratio = avg_recent / avg_older
        if ratio > 1.2:
            return "rising"
        elif ratio < 0.8:
            return "declining"
        return "stable"


@dataclass
class ContentAngle:
    hook: str
    format: str  # reel, carousel, story, image
    caption_seed: str
    hashtags: list[str] = field(default_factory=list)


@dataclass
class CalendarEntry:
    date: str
    niche: str
    angle: ContentAngle
    priority: str = "normal"  # high, normal, low


CONTENT_FORMATS = ["reel", "carousel", "image", "story"]

# Angle templates keyed by niche trait
ANGLE_TEMPLATES = {
    "rising": [
        {"hook": "Why everyone's talking about {kw} right now", "format": "reel"},
        {"hook": "{kw} is blowing up — here's what you need to know", "format": "carousel"},
        {"hook": "I tested {kw} for 30 days — results shocked me", "format": "reel"},
    ],
    "high_cpc": [
        {"hook": "The {kw} mistake costing you money", "format": "reel"},
        {"hook": "{kw}: free vs paid — honest breakdown", "format": "carousel"},
        {"hook": "How I saved $1,000 with {kw}", "format": "reel"},
    ],
    "low_competition": [
        {"hook": "Nobody's talking about {kw} yet", "format": "reel"},
        {"hook": "{kw} — the untapped opportunity for 2026", "format": "carousel"},
        {"hook": "First-mover advantage: {kw}", "format": "image"},
    ],
    "high_volume": [
        {"hook": "The truth about {kw} nobody tells you", "format": "reel"},
        {"hook": "5 {kw} tips that actually work", "format": "carousel"},
        {"hook": "{kw} beginner guide (save this)", "format": "carousel"},
    ],
    "default": [
        {"hook": "What I wish I knew about {kw} sooner", "format": "reel"},
        {"hook": "{kw} explained in 60 seconds", "format": "reel"},
        {"hook": "3 things about {kw} that will surprise you", "format": "carousel"},
        {"hook": "{kw} — myth vs reality", "format": "image"},
    ],
}


class NicheInspirer:
    def __init__(self):
        self.ke = KeywordsEverywhereClient()

    # ── Explore ──────────────────────────────────

    async def explore(
        self,
        seed: str,
        *,
        country: str = "us",
        num_related: int = 20,
    ) -> list[Niche]:
        """
        From a seed topic, discover and rank sub-niches.

        1. Get keyword data for the seed
        2. Fetch related + PASF keywords
        3. Get volume/CPC/competition for all candidates
        4. Score and rank
        """
        log.info(f"Exploring niches around '{seed}'…")

        # Parallel: related keywords + PASF
        related_task = self.ke.get_related_keywords(seed, num=num_related)
        pasf_task = self.ke.get_pasf_keywords(seed, num=num_related)
        related_resp, pasf_resp = await asyncio.gather(related_task, pasf_task)

        # Collect unique candidate keywords
        candidates = {seed}
        for item in related_resp.get("data", []):
            kw = item if isinstance(item, str) else item.get("keyword", "")
            if kw:
                candidates.add(kw.lower())
        for item in pasf_resp.get("data", []):
            kw = item if isinstance(item, str) else item.get("keyword", "")
            if kw:
                candidates.add(kw.lower())

        if not candidates:
            log.warning("No candidate keywords found.")
            return []

        # Get volume/CPC/competition data for all candidates (max 100)
        candidate_list = list(candidates)[:100]
        log.info(f"Fetching data for {len(candidate_list)} candidate keywords…")
        kw_data = await self.ke.get_keyword_data(candidate_list, country=country)

        # Build Niche objects
        niches = []
        for item in kw_data.get("data", []):
            trend_data = item.get("trend", [])
            trend_values = []
            if isinstance(trend_data, list):
                for t in trend_data:
                    if isinstance(t, dict):
                        trend_values.append(t.get("value", 0))
                    elif isinstance(t, (int, float)):
                        trend_values.append(int(t))

            niche = Niche(
                keyword=item.get("keyword", ""),
                volume=item.get("vol", 0),
                cpc=float(item.get("cpc", {}).get("value", 0)) if isinstance(item.get("cpc"), dict) else float(item.get("cpc", 0)),
                competition=float(item.get("competition", 0)),
                trend=trend_values,
            )
            niche.score = self._score(niche)
            niches.append(niche)

        # Sort by score descending
        niches.sort(key=lambda n: n.score, reverse=True)
        log.info(f"Found {len(niches)} niches, top: '{niches[0].keyword}' (score={niches[0].score:.1f})" if niches else "No niches scored.")
        return niches

    def _score(self, niche: Niche) -> float:
        """
        Score a niche 0–100 based on:
        - Volume (higher = better, log scale)
        - CPC (higher = monetizable)
        - Competition (lower = easier to rank)
        - Trend (rising = bonus)
        """
        import math

        vol_score = min(30, math.log10(max(niche.volume, 1)) * 10)
        cpc_score = min(25, niche.cpc * 5)
        comp_score = 25 * (1 - niche.competition)

        trend_bonus = 0
        direction = niche.trend_direction
        if direction == "rising":
            trend_bonus = 20
        elif direction == "stable":
            trend_bonus = 10
        elif direction == "declining":
            trend_bonus = 0
        else:
            trend_bonus = 5  # unknown

        return vol_score + cpc_score + comp_score + trend_bonus

    # ── Content Angles ───────────────────────────

    def generate_angles(self, niche: Niche, num: int = 5) -> list[ContentAngle]:
        """Generate content angle ideas based on niche traits."""
        templates = list(ANGLE_TEMPLATES["default"])

        if niche.trend_direction == "rising":
            templates = ANGLE_TEMPLATES["rising"] + templates
        if niche.cpc >= 2.0:
            templates = ANGLE_TEMPLATES["high_cpc"] + templates
        if niche.competition < 0.3:
            templates = ANGLE_TEMPLATES["low_competition"] + templates
        if niche.volume >= 10000:
            templates = ANGLE_TEMPLATES["high_volume"] + templates

        # Deduplicate by hook
        seen = set()
        unique = []
        for t in templates:
            hook = t["hook"]
            if hook not in seen:
                seen.add(hook)
                unique.append(t)

        # Build ContentAngle objects
        kw = niche.keyword
        base_tag = kw.replace(" ", "").lower()
        base_hashtags = [f"#{base_tag}", "#socialmedia", "#contentcreator", "#growthhacks"]

        angles = []
        for t in unique[:num]:
            angles.append(ContentAngle(
                hook=t["hook"].format(kw=kw),
                format=t["format"],
                caption_seed=f"{t['hook'].format(kw=kw)}\n\nDrop a 🔥 if you want more {kw} content.",
                hashtags=base_hashtags[:4],
            ))

        return angles

    # ── Full Pipeline ────────────────────────────

    async def full_pipeline(
        self,
        seed: str,
        *,
        country: str = "us",
        num_niches: int = 5,
        num_angles: int = 3,
        days: int = 14,
    ) -> dict:
        """
        End-to-end: seed → ranked niches → content angles → 2-week calendar.

        Returns dict with:
          - niches: top N scored niches
          - angles: content angles per niche
          - calendar: day-by-day posting plan
        """
        niches = await self.explore(seed, country=country)
        top = niches[:num_niches]

        # Generate angles for each top niche
        niche_angles: dict[str, list[ContentAngle]] = {}
        for n in top:
            niche_angles[n.keyword] = self.generate_angles(n, num=num_angles)

        # Build calendar — rotate niches, vary formats
        calendar: list[CalendarEntry] = []
        start = datetime.now() + timedelta(days=1)
        all_angles = []
        for n in top:
            for a in niche_angles[n.keyword]:
                all_angles.append((n, a))

        for day_offset in range(days):
            date = (start + timedelta(days=day_offset)).strftime("%Y-%m-%d")
            idx = day_offset % len(all_angles)
            niche, angle = all_angles[idx]
            priority = "high" if niche.score >= 70 else "normal"
            calendar.append(CalendarEntry(
                date=date,
                niche=niche.keyword,
                angle=angle,
                priority=priority,
            ))

        result = {
            "seed": seed,
            "country": country,
            "niches": [asdict(n) for n in top],
            "angles": {k: [asdict(a) for a in v] for k, v in niche_angles.items()},
            "calendar": [asdict(c) for c in calendar],
        }

        # Save to output
        out_dir = settings.OUTPUT_DIR / "niches"
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"niche_{stamp}.json"
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        log.info(f"Pipeline complete → {out_path}")

        return result

    # ── Display Helpers ──────────────────────────

    @staticmethod
    def print_niches(niches: list[Niche], limit: int = 10):
        """Pretty-print ranked niches to console."""
        print(f"\n  Top {min(limit, len(niches))} Niches:\n")
        for i, n in enumerate(niches[:limit], 1):
            arrow = {"rising": "↑", "declining": "↓", "stable": "→"}.get(n.trend_direction, "?")
            print(f"  {i:>2}. [{n.score:5.1f}] {n.keyword:<40} "
                  f"vol={n.volume:<8} cpc=${n.cpc:<6.2f} comp={n.competition:.2f} {arrow}")
        print()

    @staticmethod
    def print_calendar(calendar: list[CalendarEntry]):
        """Pretty-print content calendar to console."""
        print(f"\n  Content Calendar ({len(calendar)} days):\n")
        for entry in calendar:
            icon = {"reel": "🎬", "carousel": "📸", "image": "🖼️", "story": "📱"}.get(entry.angle.format, "📝")
            pri = "★" if entry.priority == "high" else " "
            print(f"  {pri} {entry.date}  {icon} [{entry.angle.format:<9}] {entry.angle.hook}")
        print()
