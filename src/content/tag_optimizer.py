"""
Tag optimizer — validates and enriches tags via Keywords Everywhere
before publishing across platforms (WordPress, Tumblr, Brevo).

Ensures every tag has real search volume. Replaces zero-volume tags
with high-volume alternatives. Adds related keywords if budget allows.

Usage:
    optimizer = TagOptimizer()
    result = await optimizer.optimize(
        seed_tags=["trend-signal", "claude-code", "agentic-coding"],
        category="Technology > AI",
        trend_name="Claude Code",
    )
    print(result.tags)           # Validated + enriched tags
    print(result.rejected)       # Tags with zero volume
    print(result.added)          # New tags discovered
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.apis.keywords_everywhere import KeywordsEverywhereClient
from src.utils.logger import get_logger

log = get_logger("tag-optimizer")

# Minimum monthly volume to keep a tag
MIN_VOLUME = 10

# Tags that are always kept regardless of volume (brand + structural)
PROTECTED_TAGS = {
    "trend-signal", "hemle", "trend signal", "trend-intelligence",
}

# Tags derived from trend name are always kept (the topic itself)
# These are added dynamically in optimize()


@dataclass
class TagResult:
    """Result of tag optimization."""
    tags: list[str]                         # Final optimized tag list
    rejected: list[dict] = field(default_factory=list)  # {tag, volume, reason}
    added: list[dict] = field(default_factory=list)     # {tag, volume, source}
    credits_used: int = 0


class TagOptimizer:
    """Validates tags against real search data and discovers better alternatives."""

    def __init__(self):
        self.ke = KeywordsEverywhereClient()

    async def optimize(
        self,
        seed_tags: list[str],
        *,
        category: str = "",
        trend_name: str = "",
        country: str = "us",
        max_related: int = 5,
        max_total: int = 20,
    ) -> TagResult:
        """
        Optimize a tag list:
        1. Check volume for each seed tag
        2. Remove zero-volume tags (keep protected ones)
        3. Fetch related keywords for the trend name
        4. Add high-volume related keywords up to max_total
        """
        result = TagResult(tags=[])

        # Normalize seed tags
        seeds = [t.strip().lower().replace("_", "-") for t in seed_tags if t.strip()]
        seeds = list(dict.fromkeys(seeds))  # dedupe

        # Trend name slug is always protected
        trend_slug = trend_name.lower().replace(" ", "-").replace("/", "-") if trend_name else ""
        dynamic_protected = set(PROTECTED_TAGS)
        if trend_slug:
            dynamic_protected.add(trend_slug)

        # Prepare human-readable versions for KE lookup (spaces, not hyphens)
        lookup_tags = [tag.replace("-", " ") for tag in seeds]

        log.info(f"Checking {len(lookup_tags)} tags via Keywords Everywhere (country={country})...")

        # Step 1: Get volume data — try target country, fallback to US
        vol_map: dict[str, int] = {}
        try:
            kw_data = await self.ke.get_keyword_data(lookup_tags, country=country)
            result.credits_used += kw_data.get("credits_consumed", 0)
            for item in kw_data.get("data", []):
                kw = item.get("keyword", "").lower()
                vol_map[kw] = item.get("vol", 0)

            # If non-US country returned mostly zeros, also check US
            if country != "us":
                non_zero = sum(1 for v in vol_map.values() if v >= MIN_VOLUME)
                if non_zero < len(lookup_tags) // 2:
                    log.info(f"  Low coverage in country={country} ({non_zero}/{len(lookup_tags)}), also checking US...")
                    us_data = await self.ke.get_keyword_data(lookup_tags, country="us")
                    result.credits_used += us_data.get("credits_consumed", 0)
                    for item in us_data.get("data", []):
                        kw = item.get("keyword", "").lower()
                        us_vol = item.get("vol", 0)
                        # Keep the higher volume between the two countries
                        vol_map[kw] = max(vol_map.get(kw, 0), us_vol)
        except Exception as e:
            log.warning(f"Keywords Everywhere lookup failed: {e}. Keeping all seed tags.")
            result.tags = seeds[:max_total]
            return result

        # Step 2: Filter seed tags
        kept = []
        for tag in seeds:
            readable = tag.replace("-", " ")
            volume = vol_map.get(readable, 0)

            if tag in dynamic_protected:
                kept.append(tag)
                log.info(f"  [KEEP]     {tag:<30} vol={volume} (protected)")
            elif volume >= MIN_VOLUME:
                kept.append(tag)
                log.info(f"  [KEEP]     {tag:<30} vol={volume}")
            else:
                result.rejected.append({"tag": tag, "volume": volume, "reason": "zero_volume"})
                log.info(f"  [REJECT]   {tag:<30} vol={volume}")

        # Step 3: Fetch related keywords for enrichment
        if trend_name and len(kept) < max_total:
            try:
                log.info(f"Fetching related keywords for '{trend_name}'...")
                related = await self.ke.get_related_keywords(
                    trend_name, num=max_related * 2
                )
                result.credits_used += related.get("credits_consumed", 0)

                for item in related.get("data", []):
                    if len(kept) >= max_total:
                        break
                    kw = item if isinstance(item, str) else item.get("keyword", "")
                    tag = kw.lower().strip().replace(" ", "-")
                    if tag and tag not in kept and tag not in PROTECTED_TAGS:
                        # Check volume for this related keyword
                        kw_check = await self.ke.get_keyword_data([kw], country=country)
                        result.credits_used += kw_check.get("credits_consumed", 0)
                        vol = 0
                        for d in kw_check.get("data", []):
                            vol = d.get("vol", 0)
                        if vol >= MIN_VOLUME:
                            kept.append(tag)
                            result.added.append({"tag": tag, "volume": vol, "source": "related"})
                            log.info(f"  [ADD]      {tag:<30} vol={vol} (related)")
            except Exception as e:
                log.warning(f"Related keywords fetch failed: {e}")

        # Step 4: Also try category-based tags
        if category and len(kept) < max_total:
            cat_tags = [
                part.strip().lower().replace(" ", "-")
                for part in category.split(">")
                if part.strip()
            ]
            for tag in cat_tags:
                if tag not in kept and len(kept) < max_total:
                    kept.append(tag)

        result.tags = kept[:max_total]
        log.info(f"Final tags ({len(result.tags)}): {', '.join(result.tags)}")
        log.info(f"Credits used: {result.credits_used}")
        return result

    async def validate_only(
        self,
        tags: list[str],
        country: str = "us",
    ) -> dict[str, int]:
        """Quick check: return {tag: volume} without modification."""
        lookup = [t.replace("-", " ") for t in tags]
        try:
            data = await self.ke.get_keyword_data(lookup, country=country)
            return {
                item.get("keyword", "").lower().replace(" ", "-"): item.get("vol", 0)
                for item in data.get("data", [])
            }
        except Exception as e:
            log.warning(f"Validation failed: {e}")
            return {}
