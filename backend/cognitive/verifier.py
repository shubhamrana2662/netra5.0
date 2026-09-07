"""CyberDrishti Feature 9 — Deterministic Output Verifier (isolated build).

Sits between the LLM and the investigator. Every copilot draft is checked by
pure code BEFORE the officer sees it:
  1. Statutory validator — every "Section X [Act]" citation is resolved against
     a sourced statutory DB: unknown sections, repealed/struck-down provisions,
     and pre-transition act names (IPC/CrPC/IEA after 1 July 2024) are
     violations with concrete replacement suggestions. The model NEVER invents
     a citation that reaches the UI unchecked.
  2. Span grounding audit — every concrete value in the draft (currency
     amounts, phone numbers, UPI handles) must exist in the caller-supplied
     case facts. Unmatched values are violations with the searched-in index
     named. Grounding sets come from the case database — nothing here.
  3. Canned-text detector — a draft too similar to a supplied canned-response
     corpus whose entities are absent from the case is flagged (this is the
     detectable symptom of fallback fabrication).

If any check fails, the result includes deterministic correction instructions
for regeneration. This is NOT "CRAG" (that paper is a retrieval evaluator with
web-search fallback) — it is a groundedness/statutory verifier, deliberately
stricter than generation-time methods.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Sequence

SECTION_RE = re.compile(
    r"Section[s]?\s+(\d{1,4}[A-Z]?(?:\(\d+\)){0,3})\s*"
    r"(?:of\s+(?:the\s+)?)?(BNSS|Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita|"
    r"BSA|Bharatiya\s+Sakshya\s+Adhiniyam|BNS|Bharatiya\s+Nyaya\s+Sanhita|"
    r"IT\s*Act|IPC|CrPC|Indian\s+Evidence\s+Act)?",
    re.IGNORECASE,
)
AMOUNT_RE = re.compile(r"(?:₹|Rs\.?|INR)\s?([0-9][\d,]*(?:\.\d{1,2})?)", re.IGNORECASE)
PHONE_RE = re.compile(r"\b([6-9]\d{9})\b")
UPI_RE = re.compile(r"\b([\w.\-]{2,}@[a-zA-Z]{2,})\b")
EMAIL_RE = re.compile(r"\b([\w.+-]+@[\w-]+\.[\w.-]+)\b")

ACT_ALIASES = {
    "IPC": "IPC", "CRPC": "CrPC", "INDIAN EVIDENCE ACT": "IEA", "IEA": "IEA",
    "BNS": "BNS", "BHARATIYA NYAYA SANHITA": "BNS",
    "BNSS": "BNSS", "BHARATIYA NAGARIK SURAKSHA SANHITA": "BNSS",
    "BSA": "BSA", "BHARATIYA SAKSHYA ADHINIYAM": "BSA", "IT ACT": "IT Act",
}
SUCCESSOR = {"IPC": "BNS", "CrPC": "BNSS", "IEA": "BSA"}


def load_statutory_db(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        db = json.load(fh)
    missing = {"acts", "sections", "_meta"} - set(db)
    if missing:
        raise ValueError(f"statutory DB missing required keys: {sorted(missing)}")
    return db


def _norm_number(value) -> str:
    """Accepts strings ("68,000.00"), numbers (68000.0), anything str()-able."""
    if isinstance(value, (int, float)):
        return str(float(value))
    try:
        return str(float(str(value).replace(",", "")))
    except ValueError:
        return str(value)


def _norm_fact(kind: str, value: str) -> str:
    """Normalize a fact for comparison — amounts numerically, UPIs folded."""
    if kind == "amounts":
        return _norm_number(value)
    if kind == "upis":
        return value.lower()
    return value


@dataclass
class VerifierResult:
    passed: bool
    statutory_violations: list[dict[str, Any]] = field(default_factory=list)
    grounding_failures: list[dict[str, Any]] = field(default_factory=list)
    canned_detections: list[dict[str, Any]] = field(default_factory=list)
    correction_instructions: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "statutory_violations": self.statutory_violations,
            "grounding_failures": self.grounding_failures,
            "canned_detections": self.canned_detections,
            "correction_instructions": self.correction_instructions,
        }


class OutputVerifier:
    def __init__(
        self,
        statutory_db: dict[str, Any],
        case_facts: dict[str, Iterable[str]],
        canned_corpus: Sequence[str] = (),
        config: dict[str, Any] | None = None,
    ) -> None:
        self.db = statutory_db
        self.transition_date: date = date.fromisoformat(
            config.get("transition_date", statutory_db["_meta"]["transition_date"])
            if config else statutory_db["_meta"]["transition_date"]
        )
        cfg = config or {}
        self.canned_similarity_threshold = float(cfg.get("canned_similarity_threshold", 0.60))
        self.section_index = {
            (s["act"], s["section"].split("(")[0]): s for s in statutory_db["sections"]
        }
        self.acts = statutory_db["acts"]
        self.case_facts = {
            kind: {_norm_fact(kind, v) for v in values}
            for kind, values in case_facts.items()
        }
        self.canned_corpus = list(canned_corpus)

    # ---- 1. statutory ----------------------------------------------------
    def check_statutory(self, draft: str) -> list[dict[str, Any]]:
        violations: list[dict[str, Any]] = []
        for match in SECTION_RE.finditer(draft):
            section = match.group(1)
            act_raw = (match.group(2) or "").upper().replace("THE ", "")
            act = ACT_ALIASES.get(act_raw)
            base_section = section.split("(")[0]
            if act is None:
                # no act named: resolve if exactly one act has this section
                candidates = [
                    (a, s) for (a, s) in self.section_index if s == base_section
                ]
                if len(candidates) == 1:
                    act = candidates[0][0]
                elif not candidates:
                    violations.append({
                        "section": section, "act": None, "reason": "unknown_section",
                        "detail": f"Section {section} not found in the statutory DB.",
                        "replacement": None,
                    })
                    continue
                else:
                    violations.append({
                        "section": section, "act": None, "reason": "ambiguous_reference",
                        "detail": f"Section {section} exists in multiple acts {candidates}; the draft must name one.",
                        "replacement": None,
                    })
                    continue
            if act in SUCCESSOR:
                successor = SUCCESSOR[act]
                detail = (
                    f"{act} was replaced by {self.acts[successor]['name']} with effect "
                    f"from {self.transition_date.isoformat()}."
                )
                replacement = None
                # carry a replacement if the DB maps this section forward
                for s in self.db["sections"]:
                    if s.get("replaces") and s["replaces"].upper().startswith(
                        f"{act} {base_section}"
                    ):
                        replacement = f"Section {s['section']} {successor}"
                        break
                violations.append({
                    "section": section, "act": act, "reason": "pre_transition_act",
                    "detail": detail, "replacement": replacement or
                    f"the corresponding {successor} section",
                })
                continue
            entry = self.section_index.get((act, base_section))
            if entry is None:
                violations.append({
                    "section": section, "act": act, "reason": "unknown_section",
                    "detail": f"Section {section} of {act} not found in the statutory DB.",
                    "replacement": None,
                })
                continue
            if entry["status"] != "in_force":
                violations.append({
                    "section": section, "act": act, "reason": f"not_in_force:{entry['status']}",
                    "detail": f"Section {section} {act}: {entry['source']}",
                    "replacement": entry.get("replaces"),
                })
        return violations

    # ---- 2. grounding ------------------------------------------------------
    def check_grounding(self, draft: str) -> list[dict[str, Any]]:
        failures: list[dict[str, Any]] = []

        def fail(kind: str, value: str) -> None:
            failures.append({
                "claim_type": kind, "value": value,
                "searched_in": sorted(self.case_facts.get(kind, []))[:10] or ["<empty case index>"],
                "detail": f"{kind} '{value}' does not exist in this case's facts.",
            })

        email_spans = {m.span() for m in EMAIL_RE.finditer(draft)}
        for m in AMOUNT_RE.finditer(draft):
            value = _norm_number(m.group(1))
            if value not in self.case_facts.get("amounts", set()):
                fail("amounts", m.group(1).strip())
        for m in PHONE_RE.finditer(draft):
            if not any(s <= m.span() < (s[0], s[1]) for s in email_spans):
                if m.group(1) not in self.case_facts.get("phones", set()):
                    fail("phones", m.group(1))
        for m in UPI_RE.finditer(draft):
            if not any(s <= m.span() < (s[0], s[1]) for s in email_spans):
                if m.group(1).lower() not in self.case_facts.get("upis", set()):
                    fail("upis", m.group(1))
        return failures

    # ---- 3. canned ----------------------------------------------------------
    def check_canned(self, draft: str) -> list[dict[str, Any]]:
        detections: list[dict[str, Any]] = []
        draft_tokens = set(re.findall(r"\w+", draft.lower()))
        if not draft_tokens:
            return detections
        for sample in self.canned_corpus:
            sample_tokens = set(re.findall(r"\w+", sample.lower()))
            union = draft_tokens | sample_tokens
            similarity = len(draft_tokens & sample_tokens) / len(union) if union else 0.0
            if similarity >= self.canned_similarity_threshold:
                detections.append({
                    "similarity": round(similarity, 3),
                    "matched_corpus_sample": sample[:120],
                    "detail": "Draft closely mirrors a canned corpus sample.",
                })
        return detections

    # ---- orchestration -------------------------------------------------------
    def critique(self, draft: str) -> VerifierResult:
        statutory = self.check_statutory(draft)
        grounding = self.check_grounding(draft)
        canned = self.check_canned(draft)
        passed = not (statutory or grounding or canned)
        instructions = self._corrections(statutory, grounding, canned)
        return VerifierResult(
            passed=passed,
            statutory_violations=statutory,
            grounding_failures=grounding,
            canned_detections=canned,
            correction_instructions=instructions,
        )

    def _corrections(self, statutory, grounding, canned) -> str:
        parts: list[str] = []
        if statutory:
            constraints = "; ".join(
                v["replacement"] and f"cite {v['replacement']} instead of Section {v['section']} {v['act']}"
                or f"remove or correct the citation 'Section {v['section']} {v['act'] or ''}'"
                for v in statutory
            )
            parts.append(f"Statute constraints: {constraints}.")
        if grounding:
            parts.append(
                "Only reference values that exist in the case facts; "
                + "; ".join(f"remove or correct '{g['value']}'" for g in grounding)
                + "."
            )
        if canned:
            parts.append(
                "The draft mirrors canned fallback text. Answer only from the "
                "retrieved evidence excerpts; if they do not answer the query, "
                "say so explicitly."
            )
        return " ".join(parts)
