"""Cost tracker — logs API spend per pipeline run and accumulates lifetime totals.

Usage:
    tracker = CostTracker()
    tracker.log("elevenlabs", chars=180)
    tracker.log("whisper", audio_seconds=12.5)
    tracker.log("remotion")  # free
    tracker.summary()        # prints table
    tracker.save()           # appends to output/costs.jsonl
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from config import settings
from src.utils.logger import get_logger

log = get_logger("cost")

# ── Pricing tables (USD, updated 2026-03) ──────────────────

PRICING = {
    "elevenlabs": {
        "unit": "characters",
        "tiers": {
            "free":    {"limit": 10_000,  "cost_per_unit": 0.0},
            "starter": {"limit": 30_000,  "cost_per_unit": 0.00018},   # $5 / 30k chars
            "creator": {"limit": 100_000, "cost_per_unit": 0.00022},   # $22 / 100k chars
            "pro":     {"limit": 500_000, "cost_per_unit": 0.000198},  # $99 / 500k chars
        },
        "default_tier": "creator",
    },
    "whisper": {
        "unit": "minutes",
        "cost_per_unit": 0.006,  # $0.006 / min
    },
    "stability": {
        "unit": "images",
        "cost_per_unit": 0.04,  # Ultra: ~4 credits = $0.04
    },
    "runway": {
        "unit": "seconds",
        "cost_per_unit": 0.05,  # Gen-4: ~$0.05/sec
    },
    "heygen": {
        "unit": "seconds",
        "cost_per_unit": 0.033,  # Creator: ~$2/min
    },
    "ayrshare": {
        "unit": "posts",
        "cost_per_unit": 0.0,  # Included in plan
    },
    "remotion": {
        "unit": "renders",
        "cost_per_unit": 0.0,  # Free (local render)
    },
    "instagram": {
        "unit": "calls",
        "cost_per_unit": 0.0,  # Free (Meta Graph API)
    },
    "keywords_everywhere": {
        "unit": "credits",
        "cost_per_unit": 0.00001,  # $10 / 1M credits
    },
    "openai_dalle": {
        "unit": "images",
        "cost_per_unit": 0.08,  # DALL-E 3 HD 1024x1792: $0.080/image
    },
    "gemini_image": {
        "unit": "images",
        "cost_per_unit": 0.0,  # Free tier / included in Gemini API
    },
}


@dataclass
class CostEntry:
    service: str
    quantity: float
    unit: str
    cost_usd: float
    timestamp: float = field(default_factory=time.time)
    meta: dict = field(default_factory=dict)


class CostTracker:
    def __init__(self, elevenlabs_tier: str = "creator"):
        self.entries: list[CostEntry] = []
        self.elevenlabs_tier = elevenlabs_tier
        self._costs_file = settings.OUTPUT_DIR / "costs.jsonl"

    def log(
        self,
        service: str,
        *,
        chars: int = 0,
        audio_seconds: float = 0,
        images: int = 0,
        video_seconds: float = 0,
        posts: int = 0,
        renders: int = 0,
        credits: int = 0,
        calls: int = 0,
        meta: dict | None = None,
    ) -> CostEntry:
        """Log an API call and compute its cost."""
        pricing = PRICING.get(service)
        if not pricing:
            log.warning(f"Unknown service: {service}")
            return CostEntry(service=service, quantity=0, unit="?", cost_usd=0)

        # Determine quantity and unit
        quantity = 0.0
        unit = pricing["unit"]

        if service == "elevenlabs":
            quantity = chars
            tier = pricing["tiers"].get(self.elevenlabs_tier, {})
            cost_per = tier.get("cost_per_unit", 0)
        elif service == "whisper":
            quantity = audio_seconds / 60  # convert to minutes
            cost_per = pricing["cost_per_unit"]
        elif service == "stability":
            quantity = images
            cost_per = pricing["cost_per_unit"]
        elif service == "runway":
            quantity = video_seconds
            cost_per = pricing["cost_per_unit"]
        elif service == "heygen":
            quantity = video_seconds
            cost_per = pricing["cost_per_unit"]
        elif service == "ayrshare":
            quantity = posts
            cost_per = pricing["cost_per_unit"]
        elif service == "remotion":
            quantity = renders or 1
            cost_per = pricing["cost_per_unit"]
        elif service == "instagram":
            quantity = calls or 1
            cost_per = pricing["cost_per_unit"]
        elif service == "keywords_everywhere":
            quantity = credits
            cost_per = pricing["cost_per_unit"]
        elif service in ("openai_dalle", "gemini_image"):
            quantity = images
            cost_per = pricing["cost_per_unit"]
        else:
            cost_per = 0

        cost_usd = round(quantity * cost_per, 6)
        entry = CostEntry(
            service=service,
            quantity=quantity,
            unit=unit,
            cost_usd=cost_usd,
            meta=meta or {},
        )
        self.entries.append(entry)
        log.info(f"${cost_usd:.4f} — {service} ({quantity:.1f} {unit})")
        return entry

    @property
    def total(self) -> float:
        return round(sum(e.cost_usd for e in self.entries), 6)

    def summary(self) -> str:
        """Print a cost summary table and return it as a string."""
        lines = ["\n  Pipeline Cost Summary\n"]
        by_service: dict[str, float] = {}
        for e in self.entries:
            by_service[e.service] = by_service.get(e.service, 0) + e.cost_usd

        for svc, cost in sorted(by_service.items(), key=lambda x: -x[1]):
            lines.append(f"  {svc:<22} ${cost:.4f}")
        lines.append(f"  {'-' * 30}")
        lines.append(f"  {'TOTAL':<22} ${self.total:.4f}\n")

        text = "\n".join(lines)
        print(text)
        return text

    def save(self) -> Path:
        """Append all entries to costs.jsonl for lifetime tracking."""
        self._costs_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._costs_file, "a", encoding="utf-8") as f:
            for e in self.entries:
                f.write(json.dumps({
                    "service": e.service,
                    "quantity": e.quantity,
                    "unit": e.unit,
                    "cost_usd": e.cost_usd,
                    "timestamp": e.timestamp,
                    "date": datetime.fromtimestamp(e.timestamp).isoformat(),
                    "meta": e.meta,
                }) + "\n")
        log.info(f"Costs saved to {self._costs_file}")
        return self._costs_file

    @staticmethod
    def load_history(costs_file: Path | None = None) -> list[dict]:
        """Load all historical cost entries."""
        path = costs_file or (settings.OUTPUT_DIR / "costs.jsonl")
        if not path.exists():
            return []
        entries = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entries.append(json.loads(line))
        return entries

    @staticmethod
    def lifetime_total(costs_file: Path | None = None) -> float:
        """Sum all historical costs."""
        return round(sum(e["cost_usd"] for e in CostTracker.load_history(costs_file)), 4)
