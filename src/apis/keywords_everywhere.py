"""
Keywords Everywhere API — keyword research, competitor analysis, traffic metrics, backlinks.

Base URL: https://api.keywordseverywhere.com/v1
Auth: Bearer token via Authorization header
Docs: https://api.keywordseverywhere.com/docs/

Credit costs:
  - Keyword data:           1 credit/keyword
  - Related/PASF keywords:  2 credits/keyword
  - Domain/URL keywords:    2 credits/keyword
  - Domain/URL traffic:     2 credits/domain or URL
  - Domain/page backlinks:  1 credit/backlink
  - Unique backlinks:       5 credits/backlink
"""

import httpx
from config import settings


class KeywordsEverywhereClient:
    BASE = "https://api.keywordseverywhere.com/v1"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or getattr(settings, "KEYWORDS_EVERYWHERE_API_KEY", "")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    # ── Account ──────────────────────────────────

    async def get_credits(self) -> int:
        """Get remaining credit balance."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.BASE}/account/credits",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()[0]

    async def get_countries(self) -> dict[str, str]:
        """Get supported country codes → names mapping."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.BASE}/countries",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_currencies(self) -> dict:
        """Get supported currencies."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.BASE}/currencies",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    # ── Keyword Data ─────────────────────────────

    async def get_keyword_data(
        self,
        keywords: list[str],
        *,
        country: str = "",
        currency: str = "usd",
        data_source: str = "cli",
    ) -> dict:
        """
        Get search volume, CPC, competition, and trend data for keywords.
        Max 100 keywords per request. Cost: 1 credit/keyword.
        """
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.BASE}/get_keyword_data",
                headers=self._headers(),
                data={
                    "kw[]": keywords,
                    "country": country,
                    "currency": currency,
                    "dataSource": data_source,
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def get_pasf_keywords(
        self,
        keyword: str,
        num: int = 10,
    ) -> dict:
        """
        Get "People Also Search For" keywords.
        Cost: 2 credits/keyword returned.
        """
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.BASE}/get_pasf_keywords",
                headers=self._headers(),
                json={"keyword": keyword, "num": num},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_related_keywords(
        self,
        keyword: str,
        num: int = 10,
    ) -> dict:
        """
        Get related keywords. Cost: 2 credits/keyword returned.
        """
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.BASE}/get_related_keywords",
                headers=self._headers(),
                json={"keyword": keyword, "num": num},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_domain_keywords(
        self,
        domain: str,
        country: str = "us",
        num: int = 100,
    ) -> dict:
        """
        Get keywords a domain ranks for with traffic estimates.
        Cost: 2 credits/keyword returned.
        """
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.BASE}/get_domain_keywords",
                headers=self._headers(),
                json={"domain": domain, "country": country, "num": num},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_url_keywords(
        self,
        url: str,
        country: str = "us",
        num: int = 100,
    ) -> dict:
        """
        Get keywords a specific URL ranks for.
        Cost: 2 credits/keyword returned.
        """
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.BASE}/get_url_keywords",
                headers=self._headers(),
                json={"url": url, "country": country, "num": num},
            )
            resp.raise_for_status()
            return resp.json()

    # ── Traffic Metrics ──────────────────────────

    async def get_domain_traffic(
        self,
        domains: list[str],
        country: str = "us",
    ) -> dict:
        """
        Get estimated monthly traffic + ranking keywords for domains.
        Cost: 2 credits/domain.
        """
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.BASE}/get_domain_traffic_metrics",
                headers=self._headers(),
                data={
                    "domains[]": domains,
                    "country": country,
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def get_url_traffic(
        self,
        urls: list[str],
        country: str = "us",
    ) -> dict:
        """
        Get estimated monthly traffic + ranking keywords for URLs.
        Cost: 2 credits/URL.
        """
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.BASE}/get_url_traffic_metrics",
                headers=self._headers(),
                data={
                    "urls[]": urls,
                    "country": country,
                },
            )
            resp.raise_for_status()
            return resp.json()

    # ── Backlinks ────────────────────────────────

    async def get_domain_backlinks(
        self,
        domain: str,
        num: int = 100,
    ) -> dict:
        """
        Get backlinks pointing to a domain.
        Cost: 1 credit/backlink returned.
        """
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.BASE}/get_domain_backlinks",
                headers=self._headers(),
                json={"domain": domain, "num": num},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_unique_domain_backlinks(
        self,
        domain: str,
        num: int = 100,
    ) -> dict:
        """
        Get unique (deduplicated) backlinks to a domain.
        Cost: 5 credits/backlink returned.
        """
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.BASE}/get_unique_domain_backlinks",
                headers=self._headers(),
                json={"domain": domain, "num": num},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_page_backlinks(
        self,
        page: str,
        num: int = 100,
    ) -> dict:
        """
        Get backlinks pointing to a specific page.
        Cost: 1 credit/backlink returned.
        """
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.BASE}/get_page_backlinks",
                headers=self._headers(),
                json={"page": page, "num": num},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_unique_page_backlinks(
        self,
        page: str,
        num: int = 100,
    ) -> dict:
        """
        Get unique (deduplicated) backlinks to a specific page.
        Cost: 5 credits/backlink returned.
        """
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.BASE}/get_unique_page_backlinks",
                headers=self._headers(),
                json={"page": page, "num": num},
            )
            resp.raise_for_status()
            return resp.json()

    # ── Convenience: Competitor Spy ──────────────

    async def competitor_spy(
        self,
        domain: str,
        country: str = "us",
        num_keywords: int = 50,
        num_backlinks: int = 20,
    ) -> dict:
        """
        One-call competitor analysis: traffic + top keywords + backlinks.
        Cost: 2 (traffic) + num_keywords*2 + num_backlinks*1 credits.
        """
        import asyncio

        traffic, keywords, backlinks = await asyncio.gather(
            self.get_domain_traffic([domain], country),
            self.get_domain_keywords(domain, country, num_keywords),
            self.get_domain_backlinks(domain, num_backlinks),
        )

        return {
            "domain": domain,
            "traffic": traffic.get("data", [{}])[0] if traffic.get("data") else {},
            "top_keywords": keywords.get("data", []),
            "backlinks": backlinks.get("data", []),
            "total_credits": sum(
                r.get("credits_consumed", 0)
                for r in [traffic, keywords, backlinks]
            ),
        }
