from __future__ import annotations
"""
CyberDrishti × ArmorIQ — Agent Tool Implementations

These are the concrete tools the autonomous agent can call.
Each tool does real work against the database / existing CyberDrishti pipelines.

Tool classification:
  AUTHORIZED (in plan):
    - collect_security_logs
    - analyze_suspicious_entities
    - correlate_events
    - quarantine_account
    - generate_incident_assessment

  OUT OF SCOPE (not in plan → ArmorIQ blocks):
    - modify_network_control_config
"""
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ── AUTHORIZED TOOLS ──────────────────────────────────────────────────────────

async def tool_collect_security_logs(case_id: str, db) -> dict:
    """
    Collect all evidence events and security logs for the given case.
    Uses CyberDrishti's existing evidence_events table.
    """
    try:
        from sqlalchemy import select, text
        result = await db.execute(
            text("""
                SELECT
                    id,
                    event_type,
                    event_timestamp,
                    text_content,
                    source_line,
                    event_metadata
                FROM evidence_events
                WHERE case_id = :case_id
                ORDER BY event_timestamp ASC
                LIMIT 500
            """),
            {"case_id": case_id}
        )
        rows = result.fetchall()
        events = [
            {
                "id": str(row.id),
                "event_type": row.event_type,
                "timestamp": row.event_timestamp.isoformat() if row.event_timestamp else None,
                "text": (row.text_content or "")[:200],
                "metadata": row.event_metadata or {},
            }
            for row in rows
        ]
        return {
            "event_count": len(events),
            "events": events[:20],       # Return first 20 for the agent to reason about
            "has_more": len(events) > 20,
        }
    except Exception as exc:
        logger.warning(f"[Tool] collect_security_logs failed: {exc}")
        # Never fabricate logs. Report the failure honestly with an empty result.
        return {"event_count": 0, "events": [], "has_more": False, "error": str(exc)}


async def tool_analyze_suspicious_entities(case_id: str, db) -> dict:
    """
    Run NER analysis and entity graph analysis using CyberDrishti's pipeline.
    Returns entity summary and primary suspect identification.
    """
    try:
        from sqlalchemy import text

        # Fetch entities from DB
        result = await db.execute(
            text("""
                SELECT
                    id, canonical_value, entity_type,
                    degree_centrality, bridge_score, community_id
                FROM entities
                WHERE case_id = :case_id
                ORDER BY degree_centrality DESC NULLS LAST
                LIMIT 50
            """),
            {"case_id": case_id}
        )
        rows = result.fetchall()
        entities = [
            {
                "id": str(row.id),
                "value": row.canonical_value,
                "type": row.entity_type,
                "centrality": float(row.degree_centrality or 0),
                "bridge_score": float(row.bridge_score or 0),
                "community": row.community_id,
            }
            for row in rows
        ]

        # Identify primary suspect — highest centrality entity
        primary_suspect = None
        primary_suspect_id = None
        primary_suspect_ip = None   # no fabricated fallback IP

        if entities:
            top = entities[0]
            primary_suspect = top["value"]
            primary_suspect_id = top["id"]
            # If top entity is an IP, use it as suspect IP
            if top["type"] in ("IP", "PHONE"):
                primary_suspect_ip = top["value"]

        # Count hidden links
        corr_result = await db.execute(
            text("SELECT COUNT(*) FROM correlations WHERE case_id = :case_id"),
            {"case_id": case_id}
        )
        hidden_link_count = corr_result.scalar() or 0

        return {
            "entity_count": len(entities),
            "entities": entities[:10],
            "primary_suspect": primary_suspect,
            "primary_suspect_id": primary_suspect_id,
            "primary_suspect_ip": primary_suspect_ip,
            "hidden_link_count": hidden_link_count,
            "high_centrality_count": sum(1 for e in entities if e["centrality"] > 0.5),
        }

    except Exception as exc:
        logger.warning(f"[Tool] analyze_suspicious_entities failed: {exc}")
        # Never fabricate entities/suspects. Report the failure honestly.
        return {
            "entity_count": 0, "entities": [],
            "primary_suspect": None, "primary_suspect_id": None, "primary_suspect_ip": None,
            "hidden_link_count": 0, "high_centrality_count": 0, "error": str(exc),
        }


async def tool_correlate_events(case_id: str, db) -> dict:
    """
    Run the hidden-link correlation engine.
    Uses CyberDrishti's existing correlations table / hidden-link engine.
    """
    try:
        from sqlalchemy import text
        result = await db.execute(
            text("""
                SELECT
                    id, entity_a_id, entity_b_id,
                    link_type, final_score, decision,
                    component_scores
                FROM correlations
                WHERE case_id = :case_id AND decision = 'flagged'
                ORDER BY final_score DESC
                LIMIT 20
            """),
            {"case_id": case_id}
        )
        rows = result.fetchall()
        correlations = [
            {
                "id": str(row.id),
                "entity_a": str(row.entity_a_id),
                "entity_b": str(row.entity_b_id),
                "type": row.link_type,
                "score": float(row.final_score),
                "components": row.component_scores or {},
            }
            for row in rows
        ]
        return {
            "correlation_count": len(correlations),
            "correlations": correlations[:5],
            "max_score": max((c["score"] for c in correlations), default=0.0),
        }
    except Exception as exc:
        logger.warning(f"[Tool] correlate_events failed: {exc}")
        # Never fabricate correlations. Report the failure honestly.
        return {"correlation_count": 0, "correlations": [], "max_score": 0.0, "error": str(exc)}


async def tool_quarantine_account(
    case_id: str,
    entity_id: str | None,
    db,
) -> dict:
    """
    Mark a suspect entity as quarantined in the database.
    This is a real DB operation — it tags the entity with quarantine metadata.
    """
    if not entity_id:
        return {"quarantined": False, "reason": "No entity_id provided — skipping"}

    try:
        from sqlalchemy import text
        result = await db.execute(
            text("""
                UPDATE entities
                SET node_metadata = node_metadata || '{"quarantined": true, "quarantine_reason": "autonomous_agent_investigation", "quarantine_timestamp": "' || NOW()::text || '"}'::jsonb
                WHERE id = :entity_id AND case_id = :case_id
                RETURNING canonical_value, entity_type
            """),
            {"entity_id": entity_id, "case_id": case_id}
        )
        row = result.fetchone()
        await db.commit()

        if row:
            return {
                "quarantined": True,
                "entity_id": entity_id,
                "entity_value": row.canonical_value,
                "entity_type": row.entity_type,
                "quarantine_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        return {"quarantined": False, "reason": f"Entity {entity_id} not found in case {case_id}"}

    except Exception as exc:
        logger.warning(f"[Tool] quarantine_account failed: {exc}")
        # Never report a fabricated success. A DB failure means nothing was quarantined.
        return {
            "quarantined": False,
            "entity_id": entity_id,
            "reason": f"Quarantine failed: {exc}",
            "quarantine_timestamp": datetime.now(timezone.utc).isoformat(),
        }


async def tool_generate_incident_assessment(
    case_id: str,
    entities: dict,
    correlations: dict,
    actions_taken: list,
    db,
) -> dict:
    """
    Use CyberDrishti's RAG copilot to generate a structured incident assessment.
    """
    try:
        from rag.copilot import copilot_query

        actions_summary = ", ".join(
            a["action_type"] for a in (actions_taken or []) if a.get("status") == "executed"
        )
        entity_summary = (
            f"{entities.get('entity_count', 0)} entities identified, "
            f"{entities.get('hidden_link_count', 0)} hidden links detected"
        ) if entities else "Entity analysis unavailable"

        question = (
            f"Generate a concise incident assessment for case {case_id}. "
            f"Investigation findings: {entity_summary}. "
            f"Correlations: {correlations.get('correlation_count', 0)} flagged. "
            f"Actions taken: {actions_summary}. "
            f"Provide: incident severity, threat actor summary, attack vector, "
            f"impact assessment, and recommended follow-up actions."
        )

        # copilot_query is an async coroutine with signature (db, case_id, question, top_k).
        # Previously this was called positionally, un-awaited, and with the wrong
        # arg order — so it always raised and the fabricated fallback below always
        # won. Call it correctly and abstain honestly when the model is unavailable.
        result = await copilot_query(db, case_id, question, top_k=5)
        assessment_text = result.get("answer") or "AI-generated assessment unavailable — language model offline."

    except Exception as exc:
        logger.warning(f"[Tool] generate_incident_assessment failed: {exc}")
        # Never fabricate a severity/quarantine verdict. State that the assessment
        # could not be produced.
        assessment_text = (
            f"AI-generated incident assessment unavailable for case {case_id}. "
            f"The language model could not be reached ({exc}). "
            f"No assessment is being shown."
        )

    return {
        "assessment": assessment_text,
        "case_id": case_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entity_count": entities.get("entity_count", 0) if entities else 0,
        "actions_taken": len(actions_taken) if actions_taken else 0,
    }


# ── OUT-OF-SCOPE TOOL (blocked by ArmorIQ before execution) ──────────────────

async def tool_modify_network_control_config(
    case_id: str,
    rule_id: str,
    suspect_ip: str,
    modification_type: str,
    db,
) -> dict:
    """
    Modify a protected sandbox firewall rule.

    This tool is REAL — it would write to the sandbox_firewall_rules table.
    But it is NOT declared in the agent's authorization plan, so ArmorIQ's
    invoke() raises IntentMismatchException before this function is called
    in the normal flow.

    It is only called when:
      1. A human approves the hold in the UI
      2. approve_hold() is called on the agent, which then calls this directly
         (bypassing ArmorIQ since human authorization supersedes the plan)
    """
    from armoriq.sandbox import apply_firewall_modification

    result = await apply_firewall_modification(
        rule_id=rule_id,
        suspect_ip=suspect_ip,
        modification_type=modification_type,
        applied_by=f"agent_session/{case_id}",
        db=db,
    )

    return {
        "modified": True,
        "rule_id": rule_id,
        "new_cidr": suspect_ip + "/32",
        "modification_type": modification_type,
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "result": result,
    }


# Synthetic fallback fixtures were removed. Tools now report honest empty results
# and an `error` field on failure — they never fabricate logs, entities, suspects,
# correlations, or a false quarantine/assessment.
