from __future__ import annotations
"""
CyberDrishti AI — Correlation / Hidden-Link Routes
POST /correlations/{case_id}/run   — trigger rule-based correlation analysis
GET  /correlations/{case_id}       — list flagged correlations with explanations
POST /correlations/{id}/verify     — investigator confirms/disputes a correlation
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Correlation, Entity, EvidenceEvent, EntityMention, User
from db.session import get_db
from routes.auth import get_current_user, require_role
from routes.case_access import require_case_access
from utils.audit import append_audit

router = APIRouter()


# ── Rule-based weighted scoring constants ─────────────────────────────────────

WEIGHTS = {
    "jaccard":       0.20,
    "adamic_adar":   0.15,
    "temporal":      0.25,
    "financial":     0.20,
    "bridge":        0.10,
    "common_nbrs":   0.10,
}

DEFAULT_THRESHOLD = 0.30  # Conservative — investigator reviews flagged pairs


from typing import Optional

class VerifyPayload(BaseModel):
    verdict: str   # "confirmed" | "disputed"
    notes: Optional[str] = None


# ── Endpoint: Run correlation analysis ──────────────────────────────────────

@router.post("/{case_id}/run")
async def run_correlations(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """
    Trigger rule-based hidden-link analysis for a case.
    Builds a lightweight co-occurrence graph in memory from DB entities/events,
    scores all non-adjacent pairs, and upserts Correlation rows.
    """
    from graph.graph_builder import build_case_graph, canonicalise_entities
    from graph.hidden_link_engine import compute_pair_features, HiddenLinkEngine
    import networkx as nx

    case = await require_case_access(db, current, case_id)
    c_id = case.id

    # ── Load entities ─────────────────────────────────────────────────────────
    entities_db = (await db.execute(
        select(Entity).where(Entity.case_id == c_id)
    )).scalars().all()

    if not entities_db:
        return {"flagged": 0, "message": "No entities found. Upload and process evidence first."}

    # ── Load events with mentions ─────────────────────────────────────────────
    events_db = (await db.execute(
        select(EvidenceEvent).where(EvidenceEvent.case_id == c_id)
    )).scalars().all()

    # Build entity mention lookup
    mention_rows = (await db.execute(
        select(EntityMention).where(
            EntityMention.entity_id.in_([e.id for e in entities_db])
        )
    )).scalars().all()

    # Map event_id -> [canonical_value]
    event_to_entities: dict[str, list[str]] = {}
    entity_id_to_canonical: dict[str, str] = {str(e.id): e.canonical_value for e in entities_db}

    for m in mention_rows:
        eid = str(m.evidence_event_id)
        canon = entity_id_to_canonical.get(str(m.entity_id))
        if canon:
            event_to_entities.setdefault(eid, []).append(canon)

    # ── Build events dicts for graph builder ──────────────────────────────────
    event_dicts = []
    for ev in events_db:
        event_dicts.append({
            "id": str(ev.id),
            "event_type": ev.event_type,
            "event_timestamp": ev.event_timestamp.isoformat() if ev.event_timestamp else None,
            "event_metadata": ev.event_metadata or {},
            "entity_mentions": [
                {"canonical_value": cv}
                for cv in event_to_entities.get(str(ev.id), [])
            ],
        })

    entity_dicts = [
        {
            "id": str(e.id),
            "canonical_value": e.canonical_value,
            "entity_type": e.entity_type,
        }
        for e in entities_db
    ]

    # ── Build graph ───────────────────────────────────────────────────────────
    G = build_case_graph(entity_dicts, event_dicts)

    # ── Score non-adjacent pairs (rule-based) ─────────────────────────────────
    nodes = list(G.nodes())
    engine = HiddenLinkEngine()  # No model loaded — uses rule-based path
    flagged_count = 0

    # Build canonical → db entity mapping
    canonical_to_entity: dict[str, Entity] = {e.canonical_value: e for e in entities_db}

    # Build canonical → financial signals (amounts from bank events)
    amount_signals: dict[str, float] = {}
    ts_signals: dict[str, float] = {}
    for ev in events_db:
        if ev.event_type == "bank_txn" and ev.event_metadata:
            meta = ev.event_metadata
            amount = meta.get("amount") or meta.get("debit") or meta.get("credit")
            if amount:
                try:
                    amount_f = float(str(amount).replace(",", "").replace("₹", "").strip())
                    # Associate with entities from that event
                    for cv in event_to_entities.get(str(ev.id), []):
                        amount_signals[cv] = amount_f
                        if ev.event_timestamp:
                            ts_signals[cv] = ev.event_timestamp.timestamp()
                except (ValueError, TypeError):
                    pass

    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            u, v = nodes[i], nodes[j]

            # Skip if directly connected (already co-occur)
            if G.has_edge(u, v):
                continue

            # Only score cross-entity-type pairs or same-type with shared community
            entity_u = canonical_to_entity.get(u)
            entity_v = canonical_to_entity.get(v)
            if not entity_u or not entity_v:
                continue

            # Do not correlate raw amounts or keywords — focus on investigative entities (phone, UPI, account, email, etc.)
            if entity_u.entity_type in {"AMOUNT", "KEYWORD"} or entity_v.entity_type in {"AMOUNT", "KEYWORD"}:
                continue

            # Don't link entities of same type unless there's real signal
            if entity_u.entity_type == entity_v.entity_type:
                # Still allow within-type if same community
                comm_u = G.nodes[u].get("community_id")
                comm_v = G.nodes[v].get("community_id")
                if comm_u is None or comm_v is None or comm_u == comm_v:
                    continue

            # Compute features
            feats = compute_pair_features(
                G, u, v,
                amount_u=amount_signals.get(u),
                amount_v=amount_signals.get(v),
                ts_u=ts_signals.get(u),
                ts_v=ts_signals.get(v),
            )

            # Rule-based weighted score (normalised)
            cn_norm = min(feats["cn"] / 5.0, 1.0)  # normalise common neighbors
            aa_norm = min(feats["aa"] / 3.0, 1.0)  # normalise adamic-adar
            tmp_norm = min(feats["temporal"] / 5.0, 1.0)

            score = (
                WEIGHTS["jaccard"]     * feats["jaccard"] +
                WEIGHTS["adamic_adar"] * aa_norm +
                WEIGHTS["temporal"]    * tmp_norm +
                WEIGHTS["financial"]   * feats["fin"] +
                WEIGHTS["bridge"]      * feats["bridge"] +
                WEIGHTS["common_nbrs"] * cn_norm
            )

            if score < DEFAULT_THRESHOLD:
                continue

            # Build reason codes
            reasons = []
            if feats["cn"] >= 1:
                reasons.append(f"{int(feats['cn'])} common co-occurrence(s)")
            if feats["jaccard"] >= 0.2:
                reasons.append("shared entity neighborhood")
            if tmp_norm >= 0.3:
                reasons.append("temporal proximity")
            if feats["fin"] >= 0.3:
                reasons.append("financial correlation")
            if feats["bridge"] >= 0.4:
                reasons.append("bridge entity signal")

            component_scores = {
                "jaccard": round(feats["jaccard"], 4),
                "adamic_adar_norm": round(aa_norm, 4),
                "temporal_norm": round(tmp_norm, 4),
                "fin_score": round(feats["fin"], 4),
                "bridge_score": round(feats["bridge"], 4),
                "common_neighbors": int(feats["cn"]),
            }

            # Gather source citations (events where u and v co-appear)
            citations = []
            for ev in events_db:
                ev_entities = event_to_entities.get(str(ev.id), [])
                if u in ev_entities and v in ev_entities:
                    meta = ev.event_metadata or {}
                    citations.append({
                        "event_id": str(ev.id),
                        "file": meta.get("source_doc", ""),
                        "line": ev.source_line,
                        "page": ev.source_page,
                        "event_type": ev.event_type,
                        "timestamp": ev.event_timestamp.isoformat() if ev.event_timestamp else None,
                    })

            # Upsert Correlation
            existing_corr = (await db.execute(
                select(Correlation).where(
                    Correlation.case_id == c_id,
                    Correlation.entity_a_id == entity_u.id,
                    Correlation.entity_b_id == entity_v.id,
                )
            )).scalar_one_or_none()

            if existing_corr:
                existing_corr.final_score = score
                existing_corr.threshold = DEFAULT_THRESHOLD
                existing_corr.decision = "flagged"
                existing_corr.component_scores = component_scores
                existing_corr.model_weights = WEIGHTS
                existing_corr.source_citations = citations
            else:
                db.add(Correlation(
                    case_id=c_id,
                    entity_a_id=entity_u.id,
                    entity_b_id=entity_v.id,
                    link_type="hidden_link",
                    final_score=score,
                    threshold=DEFAULT_THRESHOLD,
                    decision="flagged",
                    component_scores=component_scores,
                    model_weights=WEIGHTS,
                    source_citations=citations,
                ))
                flagged_count += 1

    await append_audit(
        db,
        action="CORRELATION_RUN",
        resource_type="case",
        resource_id=str(c_id),
        details={"flagged_count": flagged_count, "entity_count": len(entities_db)},
        user_id=str(current.id),
    )
    await db.commit()

    return {
        "case_id": str(c_id),
        "case_number": case.case_number,
        "flagged": flagged_count,
        "entity_count": len(entities_db),
        "threshold": DEFAULT_THRESHOLD,
        "message": f"Analysis complete. {flagged_count} potential hidden links detected.",
    }


# ── Endpoint: List correlations ───────────────────────────────────────────────

@router.get("/{case_id}")
async def list_correlations(
    case_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """List flagged correlations for a case, enriched with entity details."""
    case = await require_case_access(db, current, case_id)
    c_id = case.id

    corrs = (await db.execute(
        select(Correlation).where(
            Correlation.case_id == c_id,
            Correlation.decision == "flagged",
        ).order_by(Correlation.final_score.desc()).limit(limit)
    )).scalars().all()

    # Fetch entity details
    entity_ids = set()
    for c in corrs:
        entity_ids.add(c.entity_a_id)
        entity_ids.add(c.entity_b_id)

    entities_map = {}
    if entity_ids:
        rows = (await db.execute(
            select(Entity).where(Entity.id.in_(list(entity_ids)))
        )).scalars().all()
        entities_map = {e.id: e for e in rows}

    result = []
    for c in corrs:
        ea = entities_map.get(c.entity_a_id)
        eb = entities_map.get(c.entity_b_id)
        if ea and ea.entity_type in {"AMOUNT", "KEYWORD"}:
            continue
        if eb and eb.entity_type in {"AMOUNT", "KEYWORD"}:
            continue
        result.append({
            "id": str(c.id),
            "case_id": case_id,
            "entity_a": {
                "id": str(c.entity_a_id),
                "type": ea.entity_type if ea else "UNKNOWN",
                "value": ea.canonical_value if ea else str(c.entity_a_id),
            },
            "entity_b": {
                "id": str(c.entity_b_id),
                "type": eb.entity_type if eb else "UNKNOWN",
                "value": eb.canonical_value if eb else str(c.entity_b_id),
            },
            "final_score": round(c.final_score, 4),
            "threshold": c.threshold,
            "decision": c.decision,
            "component_scores": c.component_scores or {},
            "model_weights": c.model_weights or {},
            "source_citations": c.source_citations or [],
            "verified_by": str(c.verified_by) if c.verified_by else None,
            "verified_at": c.verified_at.isoformat() if c.verified_at else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    return {"case_id": case_id, "count": len(result), "correlations": result}


# ── Endpoint: Verify/dispute a correlation ────────────────────────────────────

@router.post("/{correlation_id}/verify")
async def verify_correlation(
    correlation_id: str,
    payload: VerifyPayload,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role("io", "fiu_analyst", "admin")),
):
    """Investigator confirms or disputes a flagged hidden link."""
    # Coerce the path id to the PK's Python type before db.get. The cross-dialect
    # UUID column (Uuid(as_uuid=True) on SQLite) binds via value.hex and raises
    # 'str has no attribute hex' if handed a raw string — so a bare db.get with
    # the path string 500s on SQLite. Matches routes/case_access.require_case_access.
    try:
        corr_uuid = uuid.UUID(str(correlation_id))
    except (TypeError, ValueError):
        raise HTTPException(404, "Correlation not found")
    corr = await db.get(Correlation, corr_uuid)
    if not corr:
        raise HTTPException(404, "Correlation not found")

    # Case isolation: a correlation may only be verified by someone with access
    # to the case it belongs to (admin, or the assigned officer). Without this
    # an authenticated user could mutate the verdict of any case's correlation
    # by ID (IDOR). require_case_access raises 404 for inaccessible cases.
    await require_case_access(db, current, str(corr.case_id), write=True)

    if payload.verdict not in ("confirmed", "disputed"):
        raise HTTPException(400, "verdict must be 'confirmed' or 'disputed'")

    # Map the investigator's verdict onto the detector-decision domain the schema
    # permits (CHECK ck_correlations_decision IN ('flagged','not_flagged')).
    # verified_by/verified_at record that a human reviewed the link; `decision`
    # holds the post-review truth — a confirmed link stays flagged, a disputed one
    # becomes not_flagged and correctly drops out of the flagged list. The exact
    # human verdict is preserved verbatim in the tamper-evident audit entry below,
    # so no information is lost. Writing the raw verdict into `decision` would
    # violate the CHECK constraint and 500 on every verification.
    corr.decision = "flagged" if payload.verdict == "confirmed" else "not_flagged"
    corr.verified_by = current.id
    corr.verified_at = datetime.now(timezone.utc)
    if payload.notes:
        scores = dict(corr.component_scores or {})
        scores["investigator_notes"] = payload.notes
        corr.component_scores = scores

    await append_audit(
        db,
        action="CORRELATION_VERIFIED",
        resource_type="correlation",
        resource_id=correlation_id,
        details={"verdict": payload.verdict, "notes": payload.notes},
        user_id=str(current.id),
    )
    await db.commit()

    return {"id": correlation_id, "verdict": payload.verdict, "verified_by": str(current.id)}
