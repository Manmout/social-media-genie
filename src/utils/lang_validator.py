"""
Language validator — detects mixed-language content and flags untranslated segments.

Usage:
    from src.utils.lang_validator import validate_language, ValidationReport
    report = validate_language(text, expected_lang="fr")
    if not report.is_clean:
        print(report)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# Common English words that should NOT appear in French text
_EN_MARKERS = {
    # Articles & prepositions
    "the", "is", "are", "was", "were", "has", "have", "had",
    "this", "that", "these", "those", "which", "where", "when",
    "with", "from", "into", "onto", "upon", "about", "after",
    "before", "between", "through", "during", "without",
    # Verbs
    "will", "would", "could", "should", "can", "may", "might",
    "being", "been", "does", "doing", "did",
    # Conjunctions
    "and", "but", "however", "although", "because", "since",
    "while", "whereas", "whether",
    # Common content words
    "growth", "market", "share", "revenue", "users", "launch",
    "report", "shows", "suggests", "driven", "ahead",
    "currently", "already", "enough", "every", "still",
    "happening", "happens", "happened",
}

# Common French words — if these appear, the text has some French
_FR_MARKERS = {
    "le", "la", "les", "un", "une", "des", "du", "de", "en",
    "est", "sont", "était", "ont", "avec", "pour", "dans",
    "sur", "par", "qui", "que", "cette", "ces", "mais",
    "aussi", "encore", "très", "plus", "moins",
}

# Words that are valid in both languages (brands, numbers, tech terms)
_NEUTRAL = {
    "claude", "code", "ai", "api", "mcp", "arr", "arv", "saas",
    "copilot", "github", "anthropic", "openai", "google", "cursor",
    "suno", "udio", "brevo", "remotion", "hemle", "trend", "signal",
    "h1", "h2", "q1", "q2", "q3", "q4", "pro", "vs",
    "$", "€", "%", "+", "—", "·",
}


@dataclass
class ValidationReport:
    """Result of language validation."""
    expected_lang: str
    total_words: int = 0
    en_words: list[str] = field(default_factory=list)
    fr_words: list[str] = field(default_factory=list)
    en_ratio: float = 0.0
    fr_ratio: float = 0.0
    is_clean: bool = True
    mixed_segments: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        status = "CLEAN" if self.is_clean else "MIXED"
        lines = [f"[{status}] lang={self.expected_lang} words={self.total_words} en={self.en_ratio:.0%} fr={self.fr_ratio:.0%}"]
        if self.en_words and self.expected_lang == "fr":
            lines.append(f"  English detected: {', '.join(self.en_words[:20])}")
        if self.mixed_segments:
            lines.append(f"  Mixed segments ({len(self.mixed_segments)}):")
            for seg in self.mixed_segments[:5]:
                lines.append(f"    → {seg[:100]}")
        return "\n".join(lines)


def validate_language(text: str, expected_lang: str = "fr", threshold: float = 0.15) -> ValidationReport:
    """
    Validate that text is predominantly in the expected language.

    Args:
        text: Text to validate
        expected_lang: "fr" or "en"
        threshold: Max ratio of wrong-language words before flagging (default 15%)

    Returns:
        ValidationReport with diagnostics
    """
    # Tokenize: lowercase, strip punctuation, split
    words = re.findall(r"[a-zA-ZàâäéèêëïîôùûüÿçœæÀÂÄÉÈÊËÏÎÔÙÛÜŸÇŒÆ]+", text.lower())
    words = [w for w in words if len(w) > 1 and w not in _NEUTRAL]

    report = ValidationReport(expected_lang=expected_lang, total_words=len(words))

    if not words:
        return report

    en_found = [w for w in words if w in _EN_MARKERS]
    fr_found = [w for w in words if w in _FR_MARKERS]

    report.en_words = list(dict.fromkeys(en_found))  # dedupe, preserve order
    report.fr_words = list(dict.fromkeys(fr_found))
    report.en_ratio = len(en_found) / len(words)
    report.fr_ratio = len(fr_found) / len(words)

    # Check for wrong language
    if expected_lang == "fr" and report.en_ratio > threshold:
        report.is_clean = False
    elif expected_lang == "en" and report.fr_ratio > threshold:
        report.is_clean = False

    # Find mixed segments (sentences with both EN and FR markers)
    sentences = re.split(r'[.!?;]\s+', text)
    for sent in sentences:
        sent_words = set(re.findall(r"[a-zA-ZàâäéèêëïîôùûüÿçœæÀÂÄÉÈÊËÏÎÔÙÛÜŸÇŒÆ]+", sent.lower()))
        has_en = bool(sent_words & _EN_MARKERS)
        has_fr = bool(sent_words & _FR_MARKERS)
        if has_en and has_fr:
            report.mixed_segments.append(sent.strip())
        elif expected_lang == "fr" and has_en and not has_fr and len(sent_words) > 3:
            report.mixed_segments.append(sent.strip())

    if report.mixed_segments:
        report.is_clean = False

    return report


def validate_newsletter_content(
    timeline_texts: list[str],
    takeaway_texts: list[str],
    expected_lang: str = "fr",
) -> dict:
    """
    Validate all newsletter content fields for language consistency.

    Returns dict with per-field validation results + overall status.
    """
    results = {}
    all_clean = True

    for i, text in enumerate(timeline_texts):
        key = f"timeline_{i}"
        r = validate_language(text, expected_lang)
        results[key] = r
        if not r.is_clean:
            all_clean = False

    for i, text in enumerate(takeaway_texts):
        key = f"takeaway_{i}"
        r = validate_language(text, expected_lang)
        results[key] = r
        if not r.is_clean:
            all_clean = False

    results["_all_clean"] = all_clean
    return results
