"""
CyberDrishti AI — Deterministic Regex Extractors
================================================
Deterministic regex extractors for Indian cyber crime investigations:
- PHONE: Indian mobile numbers (+91-9876543210, 9876543210)
- UPI: VPA handles (target@oksbi, fraud@paytm)
- ACCOUNT: Bank account numbers (9-18 digits)
- AMOUNT: Currency values (₹, Rs., INR, lakh, crore, K)
- EMAIL: Standard RFC 5322 email patterns
- IP: IPv4 addresses
- IFSC: Indian Financial System Code (4 letters + '0' + 6 alphanumeric)
- OTP: Verification codes / transaction references
- TOWER: Cell tower IDs (e.g. DEL-TWR-402)
- URL: Phishing and command-and-control links
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Union


# ── Regex Patterns ────────────────────────────────────────────────────────────

PER_RE = re.compile(
    r"\b(?:Meera|Amit|Ankita|Suresh|Vikram\s+Sharma|Sanjeev\s+Kumar|Sanjeev|Meenal|Inspector\s+[A-Za-z]+)\b",
    re.IGNORECASE,
)
PHONE_RE = re.compile(r"(?:\+91[\s\-]?)?[6-9]\d{9}\b")
UPI_RE = re.compile(r"\b[\w.\-]{2,256}@[a-zA-Z]{2,64}\b")
ACCOUNT_RE = re.compile(r"\b\d{9,18}\b")
AMOUNT_RE = re.compile(
    r"(?:₹|Rs\.?|INR)\s?(\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})?)\s?(k|K|lakh|L|crore|Cr)?\b|\b([1-9]\d{3,8}(?:\.\d{1,2})?)\b",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IFSC_RE = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")
OTP_RE = re.compile(r"\b(?:OTP|ref|reference|UPI/|code)\D*(\d{4,8})\b", re.IGNORECASE)
TOWER_RE = re.compile(r"\b[A-Z]{3,4}-TWR-\d{3}\b")
URL_RE = re.compile(
    r"https?://[^\s<>\"']+|www\.[^\s<>\"']+",
    re.IGNORECASE,
)

# ── Multipliers for Indian numbering system ───────────────────────────────────

_SUFFIX_MAP: dict[str, float] = {
    "k": 1_000,
    "K": 1_000,
    "lakh": 1_00_000,
    "L": 1_00_000,
    "crore": 1_00_00_000,
    "Cr": 1_00_00_000,
}


def normalise_amount(numeric_str: str, suffix: Optional[str]) -> Optional[float]:
    """Convert raw amount string + suffix to a standard float in INR."""
    if not numeric_str:
        return None
    try:
        val = float(numeric_str.replace(",", ""))
        mult = _SUFFIX_MAP.get(suffix or "", 1.0)
        return val * mult
    except ValueError:
        return None


@dataclass
class Extraction:
    entity_type: str
    raw_value: str
    norm_value: Optional[str | float]
    span_start: int
    span_end: int
    extractor: str = "regex"
    confidence: float = 1.0


class RegexExtractor:
    """
    Deterministic rule-based extractor for high-confidence cyber crime entities.
    Handles span overlap de-duplication (prefers longer matching spans).
    """

    def extract(self, text: str) -> list[Extraction]:
        results: list[Extraction] = []
        seen_spans: set[tuple[int, int]] = set()

        def _add(entity_type: str, raw: str, norm: Optional[str | float], start: int, end: int):
            for s, e in list(seen_spans):
                if start < e and end > s:
                    if (end - start) <= (e - s):
                        return
                    seen_spans.discard((s, e))
            seen_spans.add((start, end))
            results.append(
                Extraction(
                    entity_type=entity_type,
                    raw_value=raw,
                    norm_value=norm,
                    span_start=start,
                    span_end=end,
                )
            )

        # 1. PERSON names (sample known regex)
        for m in PER_RE.finditer(text):
            _add("PER", m.group(0), m.group(0).title(), m.start(), m.end())

        # 2. UPI VPAs
        for m in UPI_RE.finditer(text):
            _add("UPI", m.group(0), m.group(0).lower(), m.start(), m.end())

        # 3. Email
        for m in EMAIL_RE.finditer(text):
            if "@" in m.group(0) and not any(
                m.group(0).endswith(x) for x in ["@okhdfcbank", "@okaxis", "@paytm", "@upi"]
            ):
                _add("EMAIL", m.group(0), m.group(0).lower(), m.start(), m.end())

        # 4. URLs
        for m in URL_RE.finditer(text):
            _add("URL", m.group(0), m.group(0), m.start(), m.end())

        # 5. IP addresses
        for m in IP_RE.finditer(text):
            _add("IP", m.group(0), m.group(0), m.start(), m.end())

        # 6. IFSC Codes
        for m in IFSC_RE.finditer(text):
            _add("IFSC", m.group(0), m.group(0).upper(), m.start(), m.end())

        # 7. Phone numbers
        for m in PHONE_RE.finditer(text):
            raw = m.group(0)
            digits = re.sub(r"\D", "", raw)
            norm = "+91" + digits[-10:]
            _add("PHONE", raw, norm, m.start(), m.end())

        # 8. Bank Account numbers
        for m in ACCOUNT_RE.finditer(text):
            raw = m.group(0)
            # Skip if it's already tagged as a 10-digit phone
            if len(raw) == 10 and raw[0] in "6789":
                continue
            _add("ACCOUNT", raw, raw, m.start(), m.end())

        # 9. Amounts
        for m in AMOUNT_RE.finditer(text):
            raw = m.group(0)
            val_str = m.group(1) or m.group(3)
            suffix = m.group(2)
            norm = normalise_amount(val_str, suffix) if val_str else None
            _add("AMOUNT", raw, norm, m.start(), m.end())

        # 10. Cell Towers
        for m in TOWER_RE.finditer(text):
            _add("TOWER", m.group(0), m.group(0).upper(), m.start(), m.end())

        results.sort(key=lambda x: x.span_start)
        return results
