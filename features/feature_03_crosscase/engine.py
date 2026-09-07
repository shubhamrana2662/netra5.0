"""CyberDrishti Feature 3 — Cross-Case Intelligence / Blind Index (isolated build).

Detects when the SAME hard identifier (phone / UPI / account / IMEI) is active
in multiple cases WITHOUT exposing identifiers or case content across case
boundaries.

Mechanics:
- Canonicalization: phone → digits only (E.164-lite), UPI → lowercase, account
  → digits, IMEI → digits. Variants that differ only in formatting MUST
  produce the same token.
- Tokenization: HMAC-SHA256(canonical_value, key) — the department supplies the
  key (env/param); it is NEVER hardcoded and a missing key is an error, not a
  default. Tokens are one-way: an operator of the index cannot invert them.
- Alerts carry ONLY the token, entity type, case ids, and a severity score —
  never the raw identifier, never case notes (zero-knowledge collision alert).
- Syndicate ingress score: S(e) = Σ_c Severity(c) × log(1 + Degree_c(e)) — a
  transparent heuristic over per-case severity and degree.

Scope honesty: this engine links cases WITHIN one deployment. Cross-station
federation is an institutional/legal track (I4C already runs a national
suspect registry + CFCFRMS + MuleHunter integration) — integration, not
rebuild.
"""
from __future__ import annotations

import hashlib
import hmac
import math
import re
from typing import Any


class MissingKeyError(RuntimeError):
    pass


_NON_DIGIT = re.compile(r"\D+")


def canonicalize(entity_type: str, value: str) -> str:
    v = str(value).strip()
    t = entity_type.upper()
    if t in ("PHONE", "ACCOUNT", "IMEI", "MAC"):
        digits = _NON_DIGIT.sub("", v)
        if t == "PHONE":
            # Indian numbering variants must collide: +91XXXXXXXXXX, 0XXXXXXXXXX
            if len(digits) == 12 and digits.startswith("91"):
                digits = digits[2:]
            elif len(digits) == 11 and digits.startswith("0"):
                digits = digits[1:]
        return digits
    if t == "UPI":
        return v.lower()
    if t == "IFSC":
        return v.upper()
    raise ValueError(f"unsupported entity_type: {entity_type}")


class BlindIndex:
    def __init__(self, key: str | bytes) -> None:
        if not key:
            raise MissingKeyError(
                "BlindIndex requires a department key (env/param). "
                "Refusing to operate with a default key."
            )
        if isinstance(key, str):
            key = key.encode("utf-8")
        self._key = key

    def token(self, entity_type: str, value: str) -> str:
        canonical = canonicalize(entity_type, value)
        if not canonical:
            raise ValueError(f"empty canonical value for {entity_type}:{value!r}")
        return hmac.new(self._key, f"{entity_type.upper()}:{canonical}".encode(),
                        hashlib.sha256).hexdigest()

    def tokens_for_entity(self, entity: dict[str, Any]) -> list[dict[str, str]]:
        """entity: {type, value, ...} → [{entity_type, token}]"""
        out = []
        for etype in entity.get("types", [entity["type"]]):
            for val in entity.get("values", [entity["value"]]):
                out.append({"entity_type": etype.upper(),
                            "token": self.token(etype, val)})
        return out


def build_index(
    entries: list[dict[str, Any]], index: BlindIndex
) -> dict[str, list[dict[str, Any]]]:
    """entries: [{case_id, entity_type, value, degree (optional), severity (optional)}]

    Returns the index: token → [{case_id, entity_type, degree, severity}].
    Duplicate (token, case) pairs collapse to one entry keeping max degree.
    """
    store: dict[str, list[dict[str, Any]]] = {}
    for e in entries:
        tok = index.token(e["entity_type"], e["value"])
        bucket = store.setdefault(tok, [])
        for existing in bucket:
            if existing["case_id"] == e["case_id"]:
                existing["degree"] = max(existing["degree"], int(e.get("degree", 1)))
                break
        else:
            bucket.append({
                "case_id": e["case_id"],
                "entity_type": e["entity_type"].upper(),
                "degree": int(e.get("degree", 1)),
                "severity": float(e.get("severity", 1.0)),
            })
    return store


def find_collisions(
    index_store: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    """Collisions = tokens present in >= 2 DISTINCT cases. Alert carries no raw
    identifiers and no case content — only token, type, case ids, score."""
    alerts = []
    for tok, occurrences in index_store.items():
        case_ids = sorted({o["case_id"] for o in occurrences})
        if len(case_ids) < 2:
            continue
        etype = occurrences[0]["entity_type"]
        score = syndicate_ingress_score(occurrences)
        alerts.append({
            "blind_token": tok,
            "entity_type": etype,
            "case_ids": case_ids,
            "case_count": len(case_ids),
            "syndicate_score": round(score, 4),
            "alert_status": "active",
            "note": "Collision on a hard identifier. Raw value and case content "
                    "are not disclosed; use the requisition flow to coordinate.",
        })
    alerts.sort(key=lambda a: -a["syndicate_score"])
    return alerts


def syndicate_ingress_score(occurrences: list[dict[str, Any]]) -> float:
    """S(e) = Σ_c Severity(c) × log(1 + Degree_c(e)) — disclosed heuristic."""
    return sum(o["severity"] * math.log1p(o["degree"]) for o in occurrences)
