"""
Newsletter publisher — renders trend reports into the Hemle-branded
email template and sends via Brevo (transactional or campaign).

Template: templates/newsletter_trend.html (purple Hemle branding, French,
inline styles, table layout, Outlook-compatible).

Usage:
    publisher = NewsletterPublisher()
    path = await publisher.draft(report)                              # HTML only
    result = await publisher.send_transactional(report, to=[...])     # single send
    result = await publisher.send_campaign(report, list_ids=[2])      # campaign
"""

from __future__ import annotations

import html as html_mod
from pathlib import Path
from datetime import datetime

from src.reports.trend_report import (
    TrendReport,
    TimelineEvent,
)
from src.apis.brevo import BrevoClient
from src.utils.logger import get_logger
from config import settings

log = get_logger("newsletter")

TEMPLATE_PATH = Path(__file__).resolve().parent.parent.parent / "templates" / "newsletter_trend.html"
NEWSLETTERS_DIR = settings.OUTPUT_DIR / "newsletters"

_STRINGS = {
    "fr": {
        "cta": "Lire le rapport complet",
        "paywall_label": "Abonnez-vous pour accéder à tous les points + analyse PESTAL",
        "paywall_cta": "Accès complet",
        # Chrome (template labels)
        "eyebrow": "Intelligence Hebdomadaire",
        "by": "par",
        "tagline": "Intelligence Marché IA",
        "5y": "5 ans",
        "1y": "1 an",
        "3m": "3 mois",
        "timeline": "Chronologie",
        "takeaways": "Points actionnables",
        "full_report": "Rapport complet",
        "powered_by": "propulsé par",
        "footer_tag": "Intelligence marché alimentée par l'IA",
        "unsub": "Se désabonner",
    },
    "en": {
        "cta": "Read the full report",
        "paywall_label": "Subscribe to unlock all takeaways + PESTAL analysis",
        "paywall_cta": "Get full access",
        # Chrome (template labels)
        "eyebrow": "Weekly Intelligence",
        "by": "by",
        "tagline": "AI Market Intelligence",
        "5y": "5 years",
        "1y": "1 year",
        "3m": "3 months",
        "timeline": "Timeline",
        "takeaways": "Actionable Takeaways",
        "full_report": "Full Report",
        "powered_by": "powered by",
        "footer_tag": "AI-powered market intelligence",
        "unsub": "Unsubscribe",
    },
}


class NewsletterPublisher:
    """Renders trend reports as Hemle-branded email HTML and sends via Brevo."""

    def __init__(self):
        NEWSLETTERS_DIR.mkdir(parents=True, exist_ok=True)
        self.brevo = BrevoClient()

    # ── Public API ───────────────────────────────────────────────

    async def draft(
        self,
        report: TrendReport,
        full_report_url: str = "",
        tier: str = "free",
        lang: str = "fr",
        images: dict | None = None,
    ) -> Path:
        """Generate newsletter HTML and save locally (no send)."""
        html = self._render(report, full_report_url=full_report_url, tier=tier, lang=lang,
                           thumbnail=images.get("thumbnail") if images else None)
        path = self._save(report, html)
        log.info(f"Newsletter draft saved: {path}")
        return path

    async def send_transactional(
        self,
        report: TrendReport,
        to: list[dict],
        *,
        full_report_url: str = "",
        tier: str = "free",
        lang: str = "fr",
        images: dict | None = None,
    ) -> dict:
        """Render and send as transactional email to specific recipients."""
        html = self._render(report, full_report_url=full_report_url, tier=tier, lang=lang,
                           thumbnail=images.get("thumbnail") if images else None)
        path = self._save(report, html)

        subject = self._build_subject(report)
        result = await self.brevo.send_transactional(
            to=to,
            subject=subject,
            html_content=html,
            tags=["trend-report", report.status],
        )
        result["local_file"] = str(path)
        return result

    async def send_campaign(
        self,
        report: TrendReport,
        list_ids: list[int],
        *,
        full_report_url: str = "",
        tier: str = "free",
        lang: str = "fr",
        images: dict | None = None,
        scheduled_at: str | None = None,
        send_now: bool = False,
    ) -> dict:
        """Create a Brevo campaign and optionally send it."""
        html = self._render(report, full_report_url=full_report_url, tier=tier, lang=lang,
                           thumbnail=images.get("thumbnail") if images else None)
        path = self._save(report, html)

        slug = report.trend_name.lower().replace(" ", "-").replace("/", "-")
        stamp = datetime.now().strftime("%Y%m%d")
        subject = self._build_subject(report)

        campaign = await self.brevo.create_campaign(
            name=f"Trend Signal — {report.trend_name} ({stamp})",
            subject=subject,
            html_content=html,
            list_ids=list_ids,
            scheduled_at=scheduled_at,
            tag=f"trend-{slug}",
        )

        campaign_id = campaign.get("id")
        if send_now and campaign_id:
            await self.brevo.send_campaign(campaign_id)
            campaign["sent"] = True

        campaign["local_file"] = str(path)
        return campaign

    # ── Rendering ────────────────────────────────────────────────

    def _render(self, r: TrendReport, full_report_url: str = "", tier: str = "free", lang: str = "fr",
                thumbnail: "Path | None" = None) -> str:
        """Render the Hemle newsletter template with all placeholders."""
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        # Inject thumbnail hero image after header if provided
        if thumbnail and thumbnail.exists():
            import base64
            b64 = base64.b64encode(thumbnail.read_bytes()).decode()
            img_row = (
                '<tr><td style="padding:0;">'
                f'<img src="data:image/png;base64,{b64}" alt="{_esc(r.trend_name)}" '
                f'width="600" style="width:100%;display:block;border-radius:0;"/>'
                '</td></tr>'
            )
            # Insert after the header closing </td></tr> (before TOPIC BLOCK)
            template = template.replace(
                '<!-- ═══ TOPIC BLOCK',
                f'{img_row}\n\n  <!-- ═══ TOPIC BLOCK',
            )

        if not full_report_url:
            slug = r.trend_name.lower().replace(" ", "-").replace("/", "-")
            full_report_url = f"https://hemle.blog/trend-{slug}/"

        # Translate data content if French
        timeline = r.timeline
        takeaways = r.takeaways
        if lang == "fr":
            timeline = self._translate_timeline(r.timeline)
            takeaways = self._translate_takeaways(r.takeaways)
            # Validate — warn about untranslated segments
            warnings = self._validate_translation(timeline, takeaways)
            for w in warnings:
                log.warning(f"Mixed language: {w}")

        # Build editorial content
        hook = self._build_hook(r, lang)
        body_intro = self._build_body_intro(r, lang)
        angle_short = self._build_angle(r, lang)

        # Localized strings
        L = _STRINGS[lang]

        replacements = {
            # Header
            "SUBJECT": self._build_subject(r, lang),
            "STATUS_FR": self._status_label(r.status, lang),
            "VOLUME": _esc(r.search_volume),
            "DATE": datetime.now().strftime("%d %B %Y"),

            # Topic block
            "TOPIC": _esc(r.trend_name),
            "CATEGORY_PATH": _esc(r.category),
            "ANGLE_SHORT": _esc(angle_short),

            # Metrics
            "GROWTH_5Y": _esc(r.growth.five_year),
            "GROWTH_1Y": _esc(r.growth.one_year),
            "GROWTH_3M": _esc(r.growth.three_month),

            # Editorial
            "HOOK": _esc(hook),
            "BODY_INTRO": _esc(body_intro),

            # Sections
            "TIMELINE": self._render_timeline_email(timeline),
            "TAKEAWAYS": self._render_takeaways_email(takeaways, tier=tier),
            "PAYWALL_BLOCK": self._render_paywall_block(tier, lang),

            # CTA
            "PROJECT_URL": full_report_url,
            "CTA_TEXT": L["cta"],
            "PS_LINE": self._build_ps(r, lang),

            # Footer
            "YEAR": str(datetime.now().year),
            "UNSUBSCRIBE": "{{ unsubscribe }}",  # Brevo merge tag

            # Chrome (localized template labels)
            "LANG": lang,
            "CHROME_EYEBROW": L["eyebrow"],
            "CHROME_BY": L["by"],
            "CHROME_TAGLINE": L["tagline"],
            "CHROME_5Y": L["5y"],
            "CHROME_1Y": L["1y"],
            "CHROME_3M": L["3m"],
            "CHROME_TIMELINE": L["timeline"],
            "CHROME_TAKEAWAYS": L["takeaways"],
            "CHROME_FULL_REPORT": L["full_report"],
            "CHROME_POWERED_BY": L["powered_by"],
            "CHROME_FOOTER_TAG": L["footer_tag"],
            "CHROME_UNSUB": L["unsub"],
        }

        rendered = template
        for key, value in replacements.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", value)
        return rendered

    # ── Localized strings ────────────────────────────────────────

    def _status_label(self, status: str, lang: str = "fr") -> str:
        labels = {
            "fr": {"surging": "En explosion", "steady": "Stable", "peaked": "En recul"},
            "en": {"surging": "Surging", "steady": "Steady", "peaked": "Peaked"},
        }
        return labels.get(lang, labels["fr"]).get(status.lower(), status.capitalize())

    def _build_subject(self, r: TrendReport, lang: str = "fr") -> str:
        emoji = {"surging": "🚀", "steady": "→", "peaked": "📉"}.get(r.status, "📊")
        return f"{emoji} {r.trend_name} — Trend Signal"

    def _build_hook(self, r: TrendReport, lang: str = "fr") -> str:
        if lang == "fr":
            verb = {"surging": "explose", "steady": "se maintient", "peaked": "ralentit"}.get(r.status, "évolue")
            return (
                f"{r.trend_name} {verb}. "
                f"Volume de recherche : {r.search_volume}. "
                f"Croissance sur 1 an : {r.growth.one_year}."
            )
        verb = {"surging": "is exploding", "steady": "holds steady", "peaked": "is cooling down"}.get(r.status, "is trending")
        return (
            f"{r.trend_name} {verb}. "
            f"Search volume: {r.search_volume}. "
            f"1-year growth: {r.growth.one_year}."
        )

    def _build_body_intro(self, r: TrendReport, lang: str = "fr") -> str:
        if lang == "fr":
            return (
                f"{r.trend_name} affiche une croissance de {r.growth.one_year} sur un an "
                f"et {r.growth.three_month} sur les 3 derniers mois. "
                f"Voici notre analyse complète : chronologie, points actionnables, et le rapport détaillé."
            )
        return (
            f"{r.trend_name} shows {r.growth.one_year} year-over-year growth "
            f"and {r.growth.three_month} over the last 3 months. "
            f"Here's our full analysis: timeline, actionable takeaways, and the detailed report."
        )

    def _build_angle(self, r: TrendReport, lang: str = "fr") -> str:
        if r.takeaways:
            return r.takeaways[0][:80]
        label = self._status_label(r.status, lang).lower()
        if lang == "fr":
            return f"Analyse {label} — {r.category}"
        return f"{label.capitalize()} analysis — {r.category}"

    def _build_ps(self, r: TrendReport, lang: str = "fr") -> str:
        if r.competitors:
            names = ", ".join(c.name for c in r.competitors[:3])
            if lang == "fr":
                return f"Les acteurs à surveiller cette semaine : {names}."
            return f"Companies to watch this week: {names}."
        if lang == "fr":
            return "Chaque vendredi, une nouvelle analyse de tendance dans votre boîte mail."
        return "Every Friday, a new trend analysis in your inbox."

    # ── Content translation (EN → FR) ─────────────────────────────
    #
    # Full-sentence translation: each English sentence maps to its
    # complete French equivalent. No partial phrase substitution.

    _MONTH_EN_FR = {
        "Jan ": "Jan. ", "Feb ": "Fév. ", "Mar ": "Mars ",
        "Apr ": "Avr. ", "May ": "Mai ", "Jun ": "Juin ",
        "Jul ": "Juil. ", "Aug ": "Août ", "Sep ": "Sept. ",
        "Oct ": "Oct. ", "Nov ": "Nov. ", "Dec ": "Déc. ",
        "Early ": "Début ", "Mid ": "Mi-", "Late ": "Fin ",
    }

    # Full-sentence lookup: English sentence → French sentence
    # Key = exact English text from JSON data, value = full French translation
    _SENTENCE_EN_FR: dict[str, str] = {
        # ── Claude Code timeline ──
        "Public launch of Claude Code CLI":
            "Lancement public de Claude Code CLI",
        "$500M run-rate revenue":
            "500 M$ de revenus annualisés",
        "$1B ARR — developer mindshare shift from Copilot":
            "1 Md$ ARR — les développeurs basculent depuis Copilot",
        "Claude app hits #1 in app stores, displacing ChatGPT":
            "L'app Claude atteint le n°1 des stores, détrônant ChatGPT",
        "$2.5B ARR — paid subscriptions double":
            "2,5 Md$ ARR — les abonnements payants doublent",
        "4% of all GitHub public commits authored by Claude Code":
            "4 % des commits publics GitHub rédigés par Claude Code",

        # ── Claude Code takeaways ──
        'Content creators: "Claude Code" is a high-volume, low-competition keyword. Tutorials, workflows, and comparison content will rank easily — the niche is still forming':
            'Créateurs de contenu : "Claude Code" est un mot-clé à fort volume et faible concurrence. Les tutoriels, workflows et comparatifs se positionneront facilement — la niche est encore en formation',
        "Product builders: Build MCP servers and integrations — the Claude Code ecosystem is where the plugin/extension gold rush happens in 2026":
            "Développeurs produit : Créez des serveurs MCP et des intégrations — l'écosystème Claude Code est le théâtre de la ruée vers les plugins en 2026",
        "Investors: Anthropic's revenue trajectory suggests potential market leader by H2 2026. Agentic coding is the growth vector":
            "Investisseurs : La trajectoire de revenus d'Anthropic laisse entrevoir un leadership de marché d'ici mi-2026. Le coding agentique est le vecteur de croissance",
        "Developers: If you're not using an agentic coding tool yet, Claude Code has the highest satisfaction rate (46% most loved) and the fastest-growing ecosystem":
            "Développeurs : Si vous n'utilisez pas encore d'outil de coding agentique, Claude Code a le taux de satisfaction le plus élevé (46 % « most loved ») et l'écosystème à la croissance la plus rapide",

        # ── Suno AI timeline ──
        "Suno v3 launches — first high-quality AI music generator":
            "Lancement de Suno v3 — premier générateur musical IA de haute qualité",
        "1M+ users, viral TikTok adoption wave":
            "1M+ utilisateurs, vague d'adoption virale via TikTok",
        "$150M ARR — Series C at $2.45B valuation":
            "150 M$ ARR — Série C à 2,45 Md$ de valorisation",
        "$200M ARR after $250M fundraise":
            "200 M$ ARR après une levée de 250 M$",
        "2M paid subscribers, $300M ARR (50% jump in 3 months)":
            "2M d'abonnés payants, 300 M$ ARR (bond de 50 % en 3 mois)",
        "100M+ total users — 27 min avg session length":
            "100M+ utilisateurs au total — sessions de 27 min en moyenne",

        # ── Suno AI takeaways ──
        "Content creators: Suno is the fastest path to original background music for videos/podcasts. $10/mo replaces $500+ per commissioned track":
            "Créateurs de contenu : Suno est le moyen le plus rapide d'obtenir une musique originale pour vidéos/podcasts. 10 $/mois remplace 500 $+ par morceau commandé",
        "Developers: The Suno API is underexplored — build integrations for video editors, game engines, and social media tools":
            "Développeurs : L'API Suno est sous-exploitée — créez des intégrations pour les éditeurs vidéo, moteurs de jeu et outils de réseaux sociaux",
        "Investors: $300M ARR at 50% quarterly growth. Legal risk from major label lawsuits is the main overhang, but user adoption is undeniable":
            "Investisseurs : 300 M$ ARR avec 50 % de croissance trimestrielle. Le risque juridique des majors est le principal frein, mais l'adoption est indéniable",
        "Educators: Universities are already integrating AI music tools. Course content and certification programs are a wide-open market":
            "Éducateurs : Les universités intègrent déjà les outils musicaux IA. Contenus de formation et certifications constituent un marché grand ouvert",

        # ── Agentic AI timeline ──
        "AutoGPT goes viral — first mainstream agentic AI demo":
            "AutoGPT devient viral — première démo grand public d'IA agentique",
        "OpenAI GPTs, Anthropic tool use, Google Gemini function calling launch":
            "Lancement des GPTs OpenAI, tool use Anthropic, function calling Gemini",
        "Claude Code, Cursor, Devin push agentic coding mainstream":
            "Claude Code, Cursor, Devin propulsent le coding agentique dans le mainstream",
        "Enterprise adoption: 4 in 5 enterprises adopt AI agents in some form":
            "Adoption entreprise : 4 entreprises sur 5 adoptent les agents IA sous une forme ou une autre",
        "Market hits $9.14B. 40% of enterprises scaling implementation":
            "Le marché atteint 9,14 Md$. 40 % des entreprises passent à l'échelle",
        "BCG sizes the opportunity at $200B for tech service providers":
            "BCG estime l'opportunité à 200 Md$ pour les prestataires tech",

        # ── Agentic AI takeaways ──
        "Service providers: BCG sizes the agentic AI services opportunity at $200B. Consulting, implementation, and managed agent services are the next gold rush":
            "Prestataires : BCG estime l'opportunité des services d'IA agentique à 200 Md$. Conseil, implémentation et services managés sont la prochaine ruée vers l'or",
        "Enterprise leaders: 40% of apps will embed agents by year-end (Gartner). Start with high-ROI workflows: customer support, code review, data pipeline management":
            "Dirigeants : 40 % des apps intégreront des agents d'ici fin d'année (Gartner). Commencez par les workflows à fort ROI : support client, revue de code, gestion de pipelines",
        "Developers: MCP protocol is the standard — build MCP servers for your domain. The agent ecosystem needs connectors, not more models":
            "Développeurs : Le protocole MCP est le standard — créez des serveurs MCP pour votre domaine. L'écosystème d'agents a besoin de connecteurs, pas de plus de modèles",
        "Content creators: 'Agentic AI' search volume is 500K+ and growing 45% quarterly. Tutorials, use-case breakdowns, and vendor comparisons are high-value, low-competition content":
            "Créateurs de contenu : Le volume de recherche « Agentic AI » dépasse 500K et croît de 45 % par trimestre. Tutoriels, cas d'usage et comparatifs sont du contenu à forte valeur et faible concurrence",
    }

    def _translate_date(self, date_str: str) -> str:
        """Translate English date strings to French (May 2025 → Mai 2025)."""
        result = date_str
        for en, fr in self._MONTH_EN_FR.items():
            if en in result:
                result = result.replace(en, fr)
        return result

    def _translate_sentence(self, text: str) -> str:
        """
        Translate a full sentence using the lookup table.
        Falls back to the original text if no match found.
        """
        # Exact match
        if text in self._SENTENCE_EN_FR:
            return self._SENTENCE_EN_FR[text]
        # Try stripped version
        stripped = text.strip()
        if stripped in self._SENTENCE_EN_FR:
            return self._SENTENCE_EN_FR[stripped]
        return text

    def _translate_timeline(self, events: list[TimelineEvent]) -> list[TimelineEvent]:
        """Return timeline events with French dates and translated text."""
        return [
            TimelineEvent(
                date=self._translate_date(ev.date),
                event=self._translate_sentence(ev.event),
            )
            for ev in events
        ]

    def _translate_takeaways(self, takeaways: list[str]) -> list[str]:
        """Translate takeaway strings to French via full-sentence lookup."""
        return [self._translate_sentence(t) for t in takeaways]

    def _validate_translation(self, timeline: list[TimelineEvent], takeaways: list[str]) -> list[str]:
        """
        Validate that translated content doesn't contain mixed languages.
        Returns list of warnings (empty = all clean).
        """
        from src.utils.lang_validator import validate_language
        warnings = []
        for i, ev in enumerate(timeline):
            r = validate_language(ev.event, "fr")
            if not r.is_clean:
                warnings.append(f"timeline[{i}] mixed: {ev.event[:60]}...")
        for i, t in enumerate(takeaways):
            r = validate_language(t, "fr")
            if not r.is_clean:
                warnings.append(f"takeaway[{i}] mixed: {t[:60]}...")
        return warnings

    # ── Email-safe section renderers ─────────────────────────────

    def _render_timeline_email(self, events: list[TimelineEvent]) -> str:
        if not events:
            return ""
        rows = []
        for i, ev in enumerate(events):
            is_last = (i == len(events) - 1)
            dot_color = "#0e7a5a" if is_last else "#9b7fd4"

            rows.append(
                f'<table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%"'
                f' style="margin-bottom:{"0" if is_last else "10px"};">'
                f'<tr>'
                f'<td width="72" valign="top" style="padding-right:16px;">'
                f'<p style="margin:0 0 6px;font-size:10px;color:#9b7fd4;letter-spacing:1px;'
                f'text-transform:uppercase;white-space:nowrap;'
                f'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif;">'
                f'{_esc(ev.date)}</p>'
                f'<table role="presentation" cellspacing="0" cellpadding="0" border="0">'
                f'<tr><td width="8" align="center">'
                f'<div style="width:8px;height:8px;border-radius:50%;background:{dot_color};"></div>'
                f'</td>'
                f'{"" if is_last else "<td style=\"width:1px;border-left:1px solid #e8e2f8;height:100%;\"></td>"}'
                f'</tr></table>'
                f'</td>'
                f'<td valign="top">'
                f'<p style="margin:0;font-size:13px;color:#444444;line-height:1.6;'
                f'font-family:Georgia,\'Times New Roman\',serif;">'
                f'{_esc(ev.event)}</p>'
                f'</td>'
                f'</tr></table>'
            )
        return "\n".join(rows)

    def _render_takeaways_email(self, takeaways: list[str], tier: str = "free") -> str:
        if not takeaways:
            return ""

        visible = takeaways if tier == "pro" else takeaways[:4]
        rows = []
        for i, text in enumerate(visible):
            num = i + 1
            is_blurred = (tier == "free" and i == 3)

            blur_style = (
                "filter:blur(3px);pointer-events:none;user-select:none;"
                if is_blurred else ""
            )

            rows.append(
                f'<table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%"'
                f' style="margin-bottom:12px;{blur_style}">'
                f'<tr>'
                f'<td width="32" valign="top" style="padding-right:14px;padding-top:1px;">'
                f'<div style="width:24px;height:24px;border-radius:50%;background:#f0eafc;'
                f'text-align:center;line-height:24px;'
                f'font-size:11px;font-weight:500;color:#7b4fd4;'
                f'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif;">'
                f'{num}</div>'
                f'</td>'
                f'<td valign="top">'
                f'<p style="margin:0;font-size:14px;color:#333333;line-height:1.65;'
                f'font-family:Georgia,\'Times New Roman\',serif;">'
                f'{_esc(text)}</p>'
                f'</td>'
                f'</tr></table>'
            )
        return "\n".join(rows)

    def _render_paywall_block(self, tier: str, lang: str = "fr") -> str:
        if tier != "free":
            return ""
        L = _STRINGS.get(lang, _STRINGS["fr"])
        return (
            '<table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%"'
            ' style="margin-top:16px;">'
            '<tr><td style="background:#f7f5ff;border-radius:8px;padding:14px 20px;text-align:center;">'
            '<p style="margin:0 0 6px;font-size:12px;color:#8a7aaa;'
            'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif;">'
            f'{L["paywall_label"]}'
            '</p>'
            '<a href="https://hemle.blog/subscribe/"'
            ' style="font-size:12px;color:#7b4fd4;font-weight:500;text-decoration:none;'
            'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif;">'
            f'{L["paywall_cta"]} &rarr;'
            '</a>'
            '</td></tr></table>'
        )

    # ── Helpers ──────────────────────────────────────────────────

    def _save(self, report: TrendReport, html: str) -> Path:
        slug = report.trend_name.lower().replace(" ", "-").replace("/", "-")
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = NEWSLETTERS_DIR / f"newsletter_{slug}_{stamp}.html"
        path.write_text(html, encoding="utf-8")
        return path


def _esc(text: str) -> str:
    return html_mod.escape(str(text)) if text else ""
