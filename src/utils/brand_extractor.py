"""Brand Asset Extractor — URL → brand kit JSON for Remotion compositions.

Fetches a website, extracts colors, fonts, logo URL, screenshots, meta,
and outputs a JSON brand kit that can feed directly into Remotion props
or inform content generation.

Usage:
    extractor = BrandExtractor()
    brand = await extractor.extract("https://example.com")
    # → output/brands/example-com.json

CLI:
    py -3.13 cli.py brand-extract --url https://example.com
"""

import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import httpx

from config import settings
from src.utils.logger import get_logger

log = get_logger("brand")

BRANDS_DIR = settings.OUTPUT_DIR / "brands"


class BrandExtractor:
    async def extract(
        self,
        url: str,
        *,
        output_path: str | None = None,
    ) -> Path:
        """Fetch URL and extract brand assets into a JSON file."""
        BRANDS_DIR.mkdir(parents=True, exist_ok=True)

        domain = urlparse(url).netloc or urlparse(url).path
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", domain).strip("-").lower()

        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        ) as client:
            log.info(f"Fetching {url}…")
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text

        brand = {
            "url": url,
            "domain": domain,
            "meta": self._extract_meta(html),
            "colors": self._extract_colors(html),
            "fonts": self._extract_fonts(html),
            "logos": self._extract_logos(html, url),
            "social": self._extract_social(html),
            "screenshots": [],
            "palette_suggestion": {},
        }

        # Generate palette suggestion from extracted colors
        brand["palette_suggestion"] = self._suggest_palette(brand["colors"])

        # Save
        out = Path(output_path) if output_path else BRANDS_DIR / f"{slug}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(brand, indent=2, ensure_ascii=False), encoding="utf-8")
        log.info(f"Brand kit saved: {out}")

        self._print_summary(brand)
        return out

    def _extract_meta(self, html: str) -> dict:
        """Extract title, description, OG tags."""
        meta = {}

        # Title
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if m:
            meta["title"] = m.group(1).strip()

        # Meta description
        m = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', html, re.IGNORECASE)
        if m:
            meta["description"] = m.group(1).strip()

        # OG tags
        for tag in ("og:title", "og:description", "og:image", "og:site_name"):
            m = re.search(rf'<meta[^>]*property=["\']{ re.escape(tag) }["\'][^>]*content=["\'](.*?)["\']', html, re.IGNORECASE)
            if m:
                meta[tag.replace("og:", "og_")] = m.group(1).strip()

        # Favicon
        m = re.search(r'<link[^>]*rel=["\'](?:icon|shortcut icon)["\'][^>]*href=["\'](.*?)["\']', html, re.IGNORECASE)
        if m:
            meta["favicon"] = m.group(1).strip()

        return meta

    def _extract_colors(self, html: str) -> list[str]:
        """Extract hex colors from inline styles, CSS variables, and style blocks."""
        # Hex colors
        hex_colors = re.findall(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", html)

        # CSS variables like --primary: #1a2b3c
        css_vars = re.findall(r"--[\w-]+:\s*(#[0-9a-fA-F]{3,8})", html)

        # rgb/rgba
        rgb_matches = re.findall(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", html)
        rgb_hex = [f"#{int(r):02x}{int(g):02x}{int(b):02x}" for r, g, b in rgb_matches]

        all_colors = hex_colors + css_vars + rgb_hex

        # Normalize to 6-digit lowercase hex
        normalized = []
        for c in all_colors:
            c = c.lower()
            if len(c) == 4:  # #abc → #aabbcc
                c = f"#{c[1]*2}{c[2]*2}{c[3]*2}"
            normalized.append(c)

        # Filter out pure black/white/grey noise
        boring = {"#000000", "#ffffff", "#000", "#fff", "#333333", "#666666",
                  "#999999", "#cccccc", "#eeeeee", "#f5f5f5", "#fafafa"}

        # Count and return top colors by frequency
        counter = Counter(c for c in normalized if c not in boring)
        return [color for color, _ in counter.most_common(12)]

    def _extract_fonts(self, html: str) -> list[str]:
        """Extract font families from Google Fonts links and CSS."""
        fonts = set()

        # Google Fonts
        for m in re.finditer(r"fonts\.googleapis\.com/css2?\?family=([^\"'&]+)", html):
            families = m.group(1).replace("+", " ").split("|")
            for f in families:
                name = f.split(":")[0].strip()
                if name:
                    fonts.add(name)

        # CSS font-family declarations
        for m in re.finditer(r"font-family:\s*[\"']?([^;\"'}{]+)", html, re.IGNORECASE):
            family = m.group(1).split(",")[0].strip().strip("'\"")
            if family and family.lower() not in ("inherit", "initial", "unset", "sans-serif", "serif", "monospace"):
                fonts.add(family)

        return sorted(fonts)

    def _extract_logos(self, html: str, base_url: str) -> list[str]:
        """Find logo images by common patterns."""
        logos = []
        base = base_url.rstrip("/")

        # Look for images with "logo" in src, alt, or class
        for m in re.finditer(
            r'<img[^>]*(?:src|data-src)=["\'](.*?)["\'][^>]*',
            html, re.IGNORECASE
        ):
            tag = m.group(0).lower()
            src = m.group(1)
            if "logo" in tag:
                if src.startswith("/"):
                    src = base + src
                elif not src.startswith("http"):
                    src = base + "/" + src
                logos.append(src)

        # SVG logos inline
        if '<svg' in html.lower() and 'logo' in html.lower():
            logos.append("(inline SVG logo detected — screenshot recommended)")

        return logos[:5]

    def _extract_social(self, html: str) -> dict:
        """Extract social media links."""
        social = {}
        patterns = {
            "twitter": r'href=["\']https?://(?:www\.)?(?:twitter|x)\.com/([^"\'?/]+)',
            "instagram": r'href=["\']https?://(?:www\.)?instagram\.com/([^"\'?/]+)',
            "linkedin": r'href=["\']https?://(?:www\.)?linkedin\.com/(?:company|in)/([^"\'?/]+)',
            "youtube": r'href=["\']https?://(?:www\.)?youtube\.com/(?:@|channel/|c/)([^"\'?/]+)',
            "tiktok": r'href=["\']https?://(?:www\.)?tiktok\.com/@([^"\'?/]+)',
            "facebook": r'href=["\']https?://(?:www\.)?facebook\.com/([^"\'?/]+)',
        }
        for platform, pattern in patterns.items():
            m = re.search(pattern, html, re.IGNORECASE)
            if m:
                social[platform] = m.group(1)
        return social

    def _suggest_palette(self, colors: list[str]) -> dict:
        """Suggest a Remotion-friendly palette from extracted colors."""
        if not colors:
            return {"primary": "#1a1a2e", "accent": "#e94560", "bg": "#16213e", "text": "#ffffff"}

        return {
            "primary": colors[0] if len(colors) > 0 else "#1a1a2e",
            "accent": colors[1] if len(colors) > 1 else "#e94560",
            "tertiary": colors[2] if len(colors) > 2 else "#0f3460",
            "bg": colors[-1] if len(colors) > 2 else "#16213e",
            "text": "#ffffff",
        }

    def _print_summary(self, brand: dict) -> None:
        """Print extracted brand summary."""
        meta = brand.get("meta", {})
        print(f"  Title:    {meta.get('title', 'N/A')}")
        print(f"  Desc:     {meta.get('description', 'N/A')[:80]}")

        colors = brand.get("colors", [])
        if colors:
            print(f"  Colors:   {', '.join(colors[:6])}")

        fonts = brand.get("fonts", [])
        if fonts:
            print(f"  Fonts:    {', '.join(fonts[:4])}")

        logos = brand.get("logos", [])
        if logos:
            print(f"  Logos:    {len(logos)} found")

        social = brand.get("social", {})
        if social:
            print(f"  Social:   {', '.join(f'{k}: @{v}' for k, v in social.items())}")

        palette = brand.get("palette_suggestion", {})
        if palette:
            print(f"  Palette:  primary={palette.get('primary')} accent={palette.get('accent')}")
