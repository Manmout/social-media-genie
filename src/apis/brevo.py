"""
Brevo (ex-SendinBlue) API v3 client — email newsletters for trend reports.

Auth: API key stored in .brevo_token file (or BREVO_API_KEY env var).
Endpoint: https://api.brevo.com/v3/

Usage:
    brevo = BrevoClient()
    # Send newsletter to a contact list
    await brevo.send_campaign(
        subject="Claude Code — Trend Intelligence Report",
        html_content="<html>...</html>",
        list_ids=[2],
        sender={"name": "Trend Signal", "email": "hello@hemle.blog"},
    )
    # Or send single transactional email
    await brevo.send_transactional(
        to=[{"email": "user@example.com", "name": "User"}],
        subject="Your weekly trend brief",
        html_content="<html>...</html>",
    )
"""

from __future__ import annotations

import httpx
from pathlib import Path

from config import settings
from src.utils.logger import get_logger

log = get_logger("brevo")

BREVO_API = "https://api.brevo.com/v3"


class BrevoClient:
    """Async Brevo API v3 client for email newsletters."""

    def __init__(self):
        self.api_key = settings.BREVO_API_KEY or self._load_token_file()
        self.sender = {
            "name": settings.BREVO_SENDER_NAME or "Trend Signal by Hemle",
            "email": settings.BREVO_SENDER_EMAIL or "hello@hemle.blog",
        }
        self._headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @staticmethod
    def _load_token_file() -> str:
        token_path = Path(__file__).resolve().parent.parent.parent / ".brevo_token"
        try:
            return token_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            # Also check src/.brevo_token for compat
            alt = Path(__file__).resolve().parent.parent / ".brevo_token"
            try:
                return alt.read_text(encoding="utf-8").strip()
            except FileNotFoundError:
                return ""

    # ── Transactional email ──────────────────────────────

    async def send_transactional(
        self,
        to: list[dict],
        subject: str,
        html_content: str,
        *,
        sender: dict | None = None,
        params: dict | None = None,
        tags: list[str] | None = None,
        reply_to: dict | None = None,
    ) -> dict:
        """
        Send a single transactional email.

        Args:
            to: [{"email": "...", "name": "..."}]
            subject: Email subject
            html_content: Full HTML body
            params: Dynamic template variables {{params.key}}
            tags: Tags for tracking
        """
        payload = {
            "sender": sender or self.sender,
            "to": to,
            "subject": subject,
            "htmlContent": html_content,
        }
        if params:
            payload["params"] = params
        if tags:
            payload["tags"] = tags
        if reply_to:
            payload["replyTo"] = reply_to

        data = await self._post("/smtp/email", payload)
        log.info(f"Transactional email sent: messageId={data.get('messageId')}")
        return data

    # ── Email campaigns ──────────────────────────────────

    async def create_campaign(
        self,
        name: str,
        subject: str,
        html_content: str,
        list_ids: list[int],
        *,
        sender: dict | None = None,
        reply_to: str | None = None,
        scheduled_at: str | None = None,
        tag: str | None = None,
    ) -> dict:
        """
        Create an email campaign (newsletter).

        Args:
            name: Internal campaign name
            subject: Email subject
            html_content: Full HTML body
            list_ids: Contact list IDs to send to
            scheduled_at: ISO datetime for scheduling (None = manual send)
            tag: Campaign tag for tracking
        """
        payload = {
            "name": name,
            "subject": subject,
            "sender": sender or self.sender,
            "htmlContent": html_content,
            "recipients": {"listIds": list_ids},
            "type": "classic",
        }
        if reply_to:
            payload["replyTo"] = {"email": reply_to}
        if scheduled_at:
            payload["scheduledAt"] = scheduled_at
        if tag:
            payload["tag"] = tag

        data = await self._post("/emailCampaigns", payload)
        campaign_id = data.get("id")
        log.info(f"Campaign created: ID={campaign_id}, name={name}")
        return data

    async def send_campaign(self, campaign_id: int) -> dict:
        """Send a created campaign immediately."""
        data = await self._post(f"/emailCampaigns/{campaign_id}/sendNow", {})
        log.info(f"Campaign {campaign_id} sent")
        return data

    async def list_campaigns(self, limit: int = 10, status: str = "draft") -> list[dict]:
        """List email campaigns."""
        data = await self._get("/emailCampaigns", params={
            "type": "classic",
            "status": status,
            "limit": limit,
        })
        return [
            {
                "id": c["id"],
                "name": c["name"],
                "subject": c["subject"],
                "status": c["status"],
                "scheduledAt": c.get("scheduledAt"),
            }
            for c in data.get("campaigns", [])
        ]

    # ── Contact management ───────────────────────────────

    async def create_contact(
        self,
        email: str,
        *,
        first_name: str = "",
        last_name: str = "",
        list_ids: list[int] | None = None,
        attributes: dict | None = None,
    ) -> dict:
        """Add a contact to Brevo."""
        payload: dict = {"email": email, "updateEnabled": True}
        attrs = {}
        if first_name:
            attrs["FIRSTNAME"] = first_name
        if last_name:
            attrs["LASTNAME"] = last_name
        if attributes:
            attrs.update(attributes)
        if attrs:
            payload["attributes"] = attrs
        if list_ids:
            payload["listIds"] = list_ids

        data = await self._post("/contacts", payload)
        log.info(f"Contact created/updated: {email}")
        return data

    async def list_contacts(self, limit: int = 50, list_id: int | None = None) -> list[dict]:
        """List contacts, optionally filtered by list."""
        params = {"limit": limit}
        if list_id:
            params["listId"] = list_id  # type: ignore
        data = await self._get("/contacts", params=params)
        return [
            {"email": c["email"], "id": c["id"], "attributes": c.get("attributes", {})}
            for c in data.get("contacts", [])
        ]

    async def create_list(self, name: str, folder_id: int = 1) -> dict:
        """Create a contact list."""
        data = await self._post("/contacts/lists", {"name": name, "folderId": folder_id})
        log.info(f"List created: ID={data.get('id')}, name={name}")
        return data

    async def list_lists(self, limit: int = 50) -> list[dict]:
        """List all contact lists."""
        data = await self._get("/contacts/lists", params={"limit": limit})
        return [
            {"id": l["id"], "name": l["name"], "totalSubscribers": l.get("totalSubscribers", 0)}
            for l in data.get("lists", [])
        ]

    # ── Account info ─────────────────────────────────────

    async def get_account(self) -> dict:
        """Get account info (plan, credits, email)."""
        data = await self._get("/account")
        return {
            "email": data.get("email"),
            "company": data.get("companyName"),
            "plan": [p["type"] for p in data.get("plan", [])],
            "credits": data.get("credits", {}).get("emails", {}).get("remaining"),
        }

    # ── HTTP helpers ─────────────────────────────────────

    async def _get(self, path: str, params: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{BREVO_API}{path}",
                params=params,
                headers=self._headers,
            )
            if not resp.is_success:
                log.error(f"Brevo API {resp.status_code}: {resp.text[:300]}")
            resp.raise_for_status()
            return resp.json()

    async def _post(self, path: str, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{BREVO_API}{path}",
                json=payload,
                headers=self._headers,
            )
            if not resp.is_success:
                log.error(f"Brevo API {resp.status_code}: {resp.text[:300]}")
            resp.raise_for_status()
            return resp.json() if resp.text else {}
