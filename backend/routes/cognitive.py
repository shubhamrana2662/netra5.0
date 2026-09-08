"""
CyberDrishti AI — Cognitive Forensic Intelligence Router

Exposes all 11 advanced cognitive engines via a unified REST API.
Each endpoint pulls real case data from the database, runs the
corresponding engine, and returns structured forensic intelligence.

Zero disruption to existing routes — this router is additive only.
"""
from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Entity, EvidenceEvent, EvidenceFile, User, Case
from db.session import get_db
from routes.auth import get_current_user
from routes.case_access import require_case_access

router = APIRouter()


# ── Pydantic Schemas ─────────────────────────────────────────────────────────

class CounterfactualRequest(BaseModel):
    freeze_account: str
    freeze_time: str  # ISO-8601

class VerifyDraftRequest(BaseModel):
    draft_text: str
    case_id: Optional[str] = None

class BenchmarkRequest(BaseModel):
    typology: str = "DIGITAL_ARREST"
    seed: int = 42


# ── Helper: pull case evidence from DB ────────────────────────────────────────

async def _get_bank_events(db: AsyncSession, case_id: uuid.UUID) -> list[dict]:
    """Retrieve bank transaction events as structured rows.

    Reads the structured metadata emitted by the CSV/PDF bank parsers
    (model, credit, debit, balance, amount, from_account, to_account, …).
    Falls back to the legacy positional raw_line split only for evidence that
    was ingested before structured parsing existed. Each row is tagged with
    `model` ('ledger'|'transfer') and `has_balance` so callers can route
    ledger-continuity vs money-flow analysis without producing false findings.
    """
    events = (await db.execute(
        select(EvidenceEvent).where(
            EvidenceEvent.case_id == case_id,
            EvidenceEvent.event_type == "bank_txn",
        ).order_by(EvidenceEvent.event_timestamp, EvidenceEvent.id)
    )).scalars().all()

    def _num(v) -> float:
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    rows: list[dict] = []
    for ev in events:
        meta = ev.event_metadata or {}
        ts = ev.event_timestamp.isoformat() if ev.event_timestamp else ""

        # ── Structured path (current parsers) ──────────────────────────────
        structured_keys = ("credit", "debit", "balance", "amount",
                            "from_account", "to_account", "model")
        if any(k in meta for k in structured_keys):
            balance_raw = meta.get("balance")
            balance = _num(balance_raw) if balance_raw not in (None, "") else None
            credit = _num(meta.get("credit"))
            debit = _num(meta.get("debit"))
            amount_val = _num(meta.get("amount")) or credit or debit
            model = meta.get("model") or ("ledger" if balance is not None else "transfer")
            rows.append({
                "credit": credit,
                "debit": debit,
                "balance": balance,
                "amount": f"{amount_val:.2f}",
                "amount_val": amount_val,
                "timestamp": ts,
                "reference": meta.get("ref_no") or meta.get("narration") or (ev.text_content or ""),
                "from": meta.get("from_account"),
                "to": meta.get("to_account"),
                "upi": meta.get("upi_id"),
                "account": meta.get("account") or meta.get("to_account") or meta.get("from_account") or "",
                "event_type": "bank_txn",
                "model": model,
                "has_balance": balance is not None,
            })
            continue

        # ── Legacy fallback: positional CSV split of raw_line ──────────────
        raw_line = meta.get("raw_line", ev.text_content or "")
        parts = raw_line.strip().split(",") if raw_line else []
        try:
            if len(parts) >= 5:
                credit = float(parts[-3] or 0)
                debit = float(parts[-2] or 0)
                balance = float(parts[-1])
                rows.append({
                    "credit": credit, "debit": debit, "balance": balance,
                    "amount": f"{credit or debit:.2f}",
                    "amount_val": credit or debit,
                    "timestamp": ts,
                    "reference": ",".join(parts[1:-3]),
                    "from": None, "to": None, "upi": None,
                    "event_type": "bank_txn",
                    "account": meta.get("account", ""),
                    "model": "ledger",
                    "has_balance": True,
                })
        except (ValueError, IndexError):
            pass
    return rows


async def _get_call_events(db: AsyncSession, case_id: uuid.UUID) -> list[dict]:
    events = (await db.execute(
        select(EvidenceEvent).where(
            EvidenceEvent.case_id == case_id,
            EvidenceEvent.event_type == "call",
        ).order_by(EvidenceEvent.event_timestamp)
    )).scalars().all()
    result = []
    for ev in events:
        meta = ev.event_metadata or {}
        result.append({
            "entity": meta.get("caller", "?"),
            "timestamp": str(ev.event_timestamp) if ev.event_timestamp else "",
            "lat": meta.get("lat"), "lon": meta.get("lon"),
            "source": meta.get("cell_id", "call"),
        })
    return result


def _loc_label(ev: dict) -> str:
    """Human-readable location for a travel-finding endpoint, built from the
    real event dict (cell-tower/cell id plus tower-derived coordinates). No
    fabrication — returns whatever the parsed CDR actually carried."""
    src = ev.get("source") or "unknown"
    lat, lon = ev.get("lat"), ev.get("lon")
    if lat is not None and lon is not None:
        try:
            return f"{src} ({float(lat):.4f}, {float(lon):.4f})"
        except (TypeError, ValueError):
            pass
    return str(src)


async def _get_whatsapp_events(db: AsyncSession, case_id: uuid.UUID) -> list[dict]:
    events = (await db.execute(
        select(EvidenceEvent).where(
            EvidenceEvent.case_id == case_id,
            EvidenceEvent.event_type == "whatsapp_msg",
        ).order_by(EvidenceEvent.id)
    )).scalars().all()
    return [
        {"line_no": i + 1,
         "sender": (ev.event_metadata or {}).get("sender", "?"),
         "text": ev.text_content or "",
         "timestamp": str(ev.event_timestamp) if ev.event_timestamp else ""}
        for i, ev in enumerate(events)
    ]


async def _get_case_entities(db: AsyncSession, case_id: uuid.UUID) -> list[dict]:
    entities = (await db.execute(
        select(Entity).where(Entity.case_id == case_id)
    )).scalars().all()
    return [
        {"entity_type": e.entity_type, "value": e.canonical_value,
         "degree": e.degree_centrality or 0}
        for e in entities
    ]


async def _get_timed_events(db: AsyncSession, case_id: uuid.UUID) -> list[dict]:
    """All events with timestamps for network replay."""
    events = (await db.execute(
        select(EvidenceEvent).where(
            EvidenceEvent.case_id == case_id,
        ).order_by(EvidenceEvent.event_timestamp)
    )).scalars().all()
    result = []
    for ev in events:
        if not ev.event_timestamp:
            continue
        meta = ev.event_metadata or {}
        result.append({
            "event_type": ev.event_type,
            "timestamp": ev.event_timestamp.isoformat(),
            "u": meta.get("caller") or meta.get("sender") or ("ACCOUNT" if ev.event_type == "bank_txn" else "?"),
            "v": meta.get("callee") or meta.get("recipient") or None,
        })
    return result


async def _get_case_facts(db: AsyncSession, case_id: uuid.UUID) -> dict[str, set]:
    """Gather verified facts for the output verifier."""
    bank_rows = await _get_bank_events(db, case_id)
    entities = await _get_case_entities(db, case_id)
    amounts = set()
    phones = set()
    upis = set()
    for r in bank_rows:
        if r.get("balance"):
            amounts.add(str(r["balance"]))
        if r.get("amount"):
            amounts.add(str(r["amount"]))
        if r.get("credit") and r["credit"] > 0:
            amounts.add(str(r["credit"]))
        if r.get("debit") and r["debit"] > 0:
            amounts.add(str(r["debit"]))
    for e in entities:
        if e["entity_type"] == "PHONE":
            phones.add(e["value"])
        elif e["entity_type"] == "UPI":
            upis.add(e["value"])
    return {"amounts": amounts, "phones": phones, "upis": upis}


# ── Endpoint: Feature 02 — Contradictions ─────────────────────────────────────

@router.get("/cases/{case_id}/contradictions")
async def get_contradictions(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Run ledger continuity audit and impossible travel check on case evidence."""
    case = await require_case_access(db, current, case_id)
    from cognitive.contradiction import ledger_audit, impossible_travel

    bank_rows = await _get_bank_events(db, case.id)
    call_events = await _get_call_events(db, case.id)

    # Only balance-bearing (ledger) rows can be audited for running-balance
    # continuity. Transfer-model rows (from/to/amount, no balance) would
    # otherwise coerce to balance=0 and generate spurious ALTERED_BALANCE hits.
    ledger_rows = [r for r in bank_rows if r.get("has_balance")]
    ledger_findings = ledger_audit(ledger_rows) if ledger_rows else []
    travel_findings = impossible_travel(call_events) if call_events else []

    return {
        "case_id": str(case.id),
        "ledger_audit": {
            # Observability: distinguish "audit ran, found nothing" (completed)
            # from "no balance-bearing rows to audit" (insufficient_input). A
            # zero-finding result on zero input is NOT a clean-ledger verdict —
            # the continuity audit could not run. `input_rows` counts only the
            # ledger-shaped (has_balance) rows actually fed to the auditor.
            "analysis_status": "completed" if ledger_rows else "insufficient_input",
            "input_rows": len(ledger_rows),
            "findings": [
                {"kind": f.kind, "row_index": f.row_index,
                 "expected_balance": f.expected_balance,
                 "reported_balance": f.reported_balance,
                 "discrepancy": f.discrepancy,
                 "explanation": f.explanation,
                 "epistemic_status": f.epistemic_status}
                for f in ledger_findings
            ],
        },
        "impossible_travel": {
            # Same distinction: no findings with input_events>0 means "checked,
            # all movement physically plausible"; input_events==0 means there
            # were no geolocated call events to check at all.
            "analysis_status": "completed" if call_events else "insufficient_input",
            "input_events": len(call_events),
            "findings": [
                {"kind": f.kind, "entity": f.entity,
                 "location_a": _loc_label(f.event_a), "location_b": _loc_label(f.event_b),
                 "distance_km": f.distance_km, "time_gap_s": f.time_gap_s,
                 "velocity_kmh": f.velocity_kmh,
                 "explanation": f.explanation,
                 "epistemic_status": f.epistemic_status}
                for f in travel_findings
            ],
        },
    }


# ── Endpoint: Feature 04 + 05 — Hypotheses ───────────────────────────────────

@router.get("/cases/{case_id}/hypotheses")
async def get_hypotheses(
    case_id: str,
    target_entity: Optional[str] = Query(None, description="Entity value to evaluate"),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Evaluate ACH suspect hypotheses with conformal uncertainty bounds."""
    case = await require_case_access(db, current, case_id)
    from cognitive.hypothesis import load_model, evaluate, bucket_value
    from cognitive import data_path

    model = load_model(data_path("hypotheses.json"))

    bank_rows = await _get_bank_events(db, case.id)
    call_events = await _get_call_events(db, case.id)

    # Build observations from available data
    observations: dict[str, float] = {}
    if call_events:
        observations["inbound_victim_calls"] = len(set(e.get("entity") for e in call_events))
    if bank_rows:
        # Calculate pass-through velocity (time between first credit and first debit)
        credits = [r for r in bank_rows if r.get("credit", 0) > 0]
        debits = [r for r in bank_rows if r.get("debit", 0) > 0]
        if credits and debits and credits[0].get("timestamp") and debits[0].get("timestamp"):
            try:
                t_credit = datetime.fromisoformat(credits[0]["timestamp"].replace("Z", "+00:00"))
                t_debit = datetime.fromisoformat(debits[0]["timestamp"].replace("Z", "+00:00"))
                velocity_min = abs((t_debit - t_credit).total_seconds()) / 60
                observations["pass_through_velocity_minutes"] = velocity_min
            except (ValueError, TypeError):
                pass

    result = evaluate(observations, model)
    return {
        "case_id": str(case.id),
        "target_entity": target_entity,
        "assessment_type": result["assessment_type"],
        "ranked_labels": result["ranked_labels"],
        "display_label": result["display_label"],
        "hypotheses": result["hypotheses"],
        "evidence_matrix": result["evidence_matrix"],
        "unobserved_indicators": result.get("unobserved", []),
    }


# ── Endpoint: Feature 06 — Next-Best Actions ─────────────────────────────────

@router.get("/cases/{case_id}/next-best-actions")
async def get_next_best_actions(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Rank investigative actions by Golden-Hours VoI urgency score."""
    case = await require_case_access(db, current, case_id)
    from cognitive.nextbest import load_catalog, rank_actions
    from cognitive import data_path

    catalog = load_catalog(data_path("action_catalog.json"))
    bank_rows = await _get_bank_events(db, case.id)
    entities = await _get_case_entities(db, case.id)

    # Calculate elapsed hours since case creation
    elapsed_hours = 0.0
    if case.created_at:
        elapsed_hours = (datetime.now(timezone.utc) - case.created_at.replace(
            tzinfo=timezone.utc if case.created_at.tzinfo is None else case.created_at.tzinfo
        )).total_seconds() / 3600

    closing_balance = next((r["balance"] for r in reversed(bank_rows) if r.get("balance") is not None), None)
    if closing_balance is None:
        # Transfer-model data carries no running balance; approximate the funds
        # at risk as the largest single traced transfer amount.
        closing_balance = max((r.get("amount_val", 0.0) for r in bank_rows), default=0.0)
    phones = [e["value"] for e in entities if e["entity_type"] == "PHONE"]

    case_state = {
        "elapsed_hours_since_first_credit": elapsed_hours,
        "complaint_ref": case.fir_number,
        "accounts_at_risk": [
            {"account": bank_rows[-1].get("account", "UNKNOWN") if bank_rows else "UNKNOWN",
             "ifsc": None, "bank_name": None,
             "amount_unwithdrawn": closing_balance}
        ] if bank_rows else [],
        "unresolved_phones": [{"phone": p, "_resolves": 1} for p in phones[:5]],
        "crime_window_cells": [],
    }

    result = rank_actions(case_state, catalog)
    return {
        "case_id": str(case.id),
        "elapsed_hours": round(elapsed_hours, 2),
        "golden_hours": catalog.get("golden_hours", 2.0),
        "urgency_factor": result["ranked_actions"][0]["urgency_factor"] if result["ranked_actions"] else 0,
        "ranked_actions": result["ranked_actions"][:10],
    }


# ── Endpoint: Feature 07 — MO Fingerprinting ─────────────────────────────────

@router.get("/cases/{case_id}/mo-fingerprint")
async def get_mo_fingerprint(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Mine WhatsApp messages against I4C crime script playbooks."""
    case = await require_case_access(db, current, case_id)
    from cognitive.mo import classify_case, load_playbooks
    from cognitive import data_path

    playbooks = load_playbooks(data_path("playbooks.json"))
    messages = await _get_whatsapp_events(db, case.id)

    if not messages:
        return {
            "case_id": str(case.id),
            "verdict": "NO_MESSAGES",
            "message": "No WhatsApp or SMS transcript found for MO analysis.",
            "matches": [], "best_match": None, "trace_evidence": [],
        }

    result = classify_case(messages, playbooks)
    return {
        "case_id": str(case.id),
        "verdict": result["verdict"],
        "observed_sequence": result["observed_sequence"],
        "matches": result["matches"][:5],
        "best_match": result["best_match"],
        "trace_evidence": result["trace_evidence"][:10],
        "note": result["note"],
    }


# ── Endpoint: Feature 08 — Counterfactual Freeze ─────────────────────────────

@router.post("/cases/{case_id}/counterfactual-freeze")
async def simulate_counterfactual_freeze(
    case_id: str,
    body: CounterfactualRequest,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Simulate what-if account freeze at time T, compute preserved capital."""
    case = await require_case_access(db, current, case_id)
    from cognitive.counterfactual import simulate_freeze

    bank_rows = await _get_bank_events(db, case.id)
    if not bank_rows:
        raise HTTPException(400, "No bank transaction data available for counterfactual simulation.")

    # Build transfer edges. Prefer the parsed party-to-party transfer shape
    # (debit_account → credit_account, amount); fall back to ledger credit/debit
    # rows with a UPI counterparty parsed from the reference.
    def _iso(ts: str) -> str | None:
        if not ts:
            return None
        return ts if "T" in ts else ts + "T00:00:00"

    transfers = []
    for r in bank_rows:
        ts = _iso(r.get("timestamp", ""))
        if not ts:
            continue
        if r.get("from") and r.get("to") and r.get("amount_val"):
            transfers.append({
                "from": str(r["from"]), "to": str(r["to"]),
                "amount": r["amount_val"], "timestamp": ts,
            })
            continue
        ref = r.get("reference", "") or ""
        upi_match = re.search(r"UPI/\d+/([\w.\-]+@[\w]+)", ref)
        if r.get("credit", 0) > 0 and upi_match:
            transfers.append({
                "from": upi_match.group(1), "to": r.get("account", "ACCOUNT"),
                "amount": r["credit"], "timestamp": ts,
            })
        if r.get("debit", 0) > 0:
            transfers.append({
                "from": r.get("account", "ACCOUNT"), "to": "UNKNOWN-" + ref[:10],
                "amount": r["debit"], "timestamp": ts,
            })

    result = simulate_freeze(transfers, body.freeze_account, body.freeze_time)
    return {
        "case_id": str(case.id),
        "intervention": result["intervention"],
        "preserved_total": result["preserved_total"],
        "assessment_type": result["assessment_type"],
        "blocked_debits": len(result["blocked_out_events"]),
        "stopped_credits": len(result["stopped_in_events"]),
        "completed_transfers": result["completed_transfers"],
        "blocked_out_events": result["blocked_out_events"][:10],
        "stopped_in_events": result["stopped_in_events"][:10],
    }


# ── Endpoint: Feature 10 — Network Replay ────────────────────────────────────

@router.get("/cases/{case_id}/network-replay")
async def get_network_replay(
    case_id: str,
    step_seconds: int = Query(300, ge=60, le=86400),
    tau_seconds: float = Query(1800.0, ge=300, le=86400),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Generate CTDG animation frames for temporal network replay."""
    case = await require_case_access(db, current, case_id)
    from cognitive.replay import build_frames

    events = await _get_timed_events(db, case.id)
    if not events:
        return {"case_id": str(case.id), "frames": [], "total_events": 0}

    frames = build_frames(events, {
        "step_seconds": step_seconds,
        "tau_seconds": tau_seconds,
        "max_frames": 500,
    })
    return {
        "case_id": str(case.id),
        "total_events": len(events),
        "total_frames": len(frames),
        "frames": [f.to_dict() if hasattr(f, 'to_dict') else f for f in frames],
    }


# ── Endpoint: Feature 03 — Cross-Case Blind Index ────────────────────────────

@router.get("/cross-case/collisions")
async def get_cross_case_collisions(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Detect cross-case entity collisions via zero-knowledge HMAC blind index."""
    from cognitive.crosscase import BlindIndex, build_index, find_collisions

    key = os.environ.get("CD_INDEX_KEY", "cyberdrishti-local-dev-key")
    index = BlindIndex(key)

    # Gather all hard identifiers across all cases
    all_entities = (await db.execute(
        select(Entity).where(
            Entity.entity_type.in_(["PHONE", "UPI", "ACCOUNT", "IFSC"])
        )
    )).scalars().all()

    entries = []
    for e in all_entities:
        entries.append({
            "case_id": str(e.case_id),
            "entity_type": e.entity_type,
            "value": e.canonical_value,
            "degree": e.degree_centrality or 1,
            "severity": 1.0,
        })

    store = build_index(entries, index)
    collisions = find_collisions(store)

    return {
        "total_entities_indexed": len(entries),
        "total_collisions": len(collisions),
        "collisions": collisions[:20],
        "note": "Zero-knowledge: only HMAC tokens shown, never raw PII.",
    }


# ── Endpoint: Feature 09 — Verify Draft ──────────────────────────────────────

@router.post("/verify-draft")
async def verify_draft(
    body: VerifyDraftRequest,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Run the deterministic output verifier on any text draft."""
    from cognitive.verifier import load_statutory_db, OutputVerifier
    from cognitive import data_path

    statutory_db = load_statutory_db(data_path("statutory_db.json"))

    facts: dict[str, set] = {"amounts": set(), "phones": set(), "upis": set()}
    if body.case_id:
        try:
            case = await require_case_access(db, current, body.case_id)
            facts = await _get_case_facts(db, case.id)
        except Exception:
            pass

    verifier = OutputVerifier(statutory_db, facts)
    result = verifier.critique(body.draft_text)
    return result.to_dict()


# ── Endpoint: Feature 11 — Benchmark Generator ───────────────────────────────

@router.post("/benchmark/generate")
async def generate_benchmark(
    body: BenchmarkRequest,
    seed_to_db: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Generate a DPDP-compliant synthetic test case and optionally seed it into the database."""
    from cognitive.benchmark import BenchmarkGenerator, load_json
    from cognitive import data_path

    pools = load_json(data_path("pools.json"))
    typologies = load_json(data_path("typologies.json"))
    gen = BenchmarkGenerator(pools, typologies)

    try:
        case = gen.generate_case(body.typology, body.seed)
    except KeyError as e:
        raise HTTPException(400, str(e))

    db_case_id = None
    if seed_to_db:
        try:
            from datetime import datetime, timezone
            typology_label = case["ground_truth"]["typology"].replace("_", " ").title()
            new_case = Case(
                case_number=f"SYN-{body.seed}-{str(uuid.uuid4())[:6].upper()}",
                title=f"Synthetic Benchmark · {typology_label}",
                description=f"DPDP 2023 compliant synthetic benchmark ({typology_label}). Seed: {body.seed}. {len(case['ground_truth']['entities'])} planted entities.",
                crime_type=typology_label[:64],
                priority="medium",
                status="open",
                assigned_officer_id=current.id,
            )
            db.add(new_case)
            await db.flush()

            # Seed ground truth entities
            for ent_val in case["ground_truth"].get("entities", []):
                ent_type = "ACCOUNT" if "acc" in str(ent_val).lower() else "PHONE" if "phone" in str(ent_val).lower() else "PERSON"
                db.add(Entity(
                    case_id=new_case.id,
                    canonical_value=str(ent_val),
                    entity_type=ent_type,
                    first_seen=datetime.now(timezone.utc),
                    last_seen=datetime.now(timezone.utc),
                ))

            await db.commit()
            db_case_id = str(new_case.id)
        except Exception as seed_err:
            await db.rollback()

    return {
        "case_id": case["case_id"],
        "db_case_id": db_case_id,
        "typology": case["ground_truth"]["typology"],
        "entities_count": len(case["ground_truth"]["entities"]),
        "flow_edges_count": len(case["ground_truth"]["money_flow_edges"]),
        "hidden_links_count": len(case["ground_truth"]["planted_hidden_links"]),
        "artifacts": {k: f"{len(v)} items" if isinstance(v, list) else "generated"
                      for k, v in case.get("artifacts", {}).items()},
        "ground_truth": case["ground_truth"],
    }
