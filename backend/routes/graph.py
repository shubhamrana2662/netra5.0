"""
CyberDrishti AI — Graph & Timeline Routes (Phase 7)
GET /graph/{case_id}    — nodes + edges for React Flow
GET /timeline/{case_id} — chronological EvidenceEvents
POST /query/{case_id}   — TF-IDF retrieval (zero generation, zero hallucination risk)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Correlation, Entity, EntityMention, EvidenceEvent, User
from db.session import get_db
from graph.graph_builder import graph_to_json, build_case_graph, select_relevant_subgraph
from routes.auth import get_current_user
from routes.case_access import require_case_access

router = APIRouter()

@router.get("/{case_id}")
async def get_graph(
    case_id:        str,
    request:        Request,
    two_hop:        bool = Query(False, description="Expand to 2-hop neighbourhood of selected node"),
    selected_node:  str | None = Query(None),
    scope:           str = Query("relevant", pattern="^(relevant|full)$"),
    max_nodes:       int = Query(40, ge=10, le=250),
    max_edges:       int = Query(100, ge=10, le=1000),
    max_hidden_links: int = Query(10, ge=0, le=50),
    db:             AsyncSession = Depends(get_db),
    current:        User = Depends(get_current_user),
):
    """Return graph JSON for the case — nodes, edges, and flagged hidden links."""
    entities = []
    correlations = []
    events = []
    mentions_by_event: dict[str, list[dict]] = {}
    evidence_sources_by_entity: dict[str, list[dict]] = {}
    dynamic_entities: dict[str, str] = {}

    c = await require_case_access(db, current, case_id)
    target_case_uuid = c.id

    try:
        if target_case_uuid:
            entities = (await db.execute(
                select(Entity).where(Entity.case_id == target_case_uuid)
            )).scalars().all()

            correlations = (await db.execute(
                select(Correlation).where(Correlation.case_id == target_case_uuid, Correlation.decision == "flagged")
            )).scalars().all()

            events = (await db.execute(
                select(EvidenceEvent).where(EvidenceEvent.case_id == target_case_uuid)
            )).scalars().all()

            mention_rows = (await db.execute(
                select(EntityMention, EvidenceEvent, Entity)
                .join(EvidenceEvent, EntityMention.evidence_event_id == EvidenceEvent.id)
                .join(Entity, EntityMention.entity_id == Entity.id)
                .where(EvidenceEvent.case_id == target_case_uuid)
            )).all()

            for mention, event, entity in mention_rows:
                mentions_by_event.setdefault(str(mention.evidence_event_id), []).append({
                    "canonical_value": entity.canonical_value,
                    "entity_type": entity.entity_type,
                })
                evidence_sources_by_entity.setdefault(entity.canonical_value, []).append({
                    "event_type": event.event_type,
                    "text_content": event.text_content,
                    "source_line": event.source_line,
                    "source_page": event.source_page,
                    "event_metadata": event.event_metadata,
                })

            # Dynamic live entity extraction over all evidence events for full cross-source graph coverage
            from correlation.regex_extractors import RegexExtractor, Extraction
            rx = RegexExtractor()
            for ev in events:
                ev_id_str = str(ev.id)
                if not ev.text_content:
                    continue
                extractions = rx.extract(ev.text_content)

                # Extract sender name from metadata if present
                sender = (ev.event_metadata or {}).get("sender")
                if sender and isinstance(sender, str) and not sender.startswith("+") and len(sender) < 30:
                    extractions.append(Extraction("PER", sender.strip(), sender.strip(), 0, len(sender)))

                for ext in extractions:
                    val = str(ext.norm_value if ext.norm_value is not None else ext.raw_value).strip()
                    if not val:
                        continue
                    dynamic_entities[val] = ext.entity_type

                    # Ensure mention exists in mentions_by_event map
                    event_mentions = mentions_by_event.setdefault(ev_id_str, [])
                    if not any(m.get("canonical_value") == val for m in event_mentions):
                        event_mentions.append({
                            "canonical_value": val,
                            "entity_type": ext.entity_type,
                        })

                    # Ensure evidence source citation is attached
                    ev_sources = evidence_sources_by_entity.setdefault(val, [])
                    if not any(s.get("text_content") == ev.text_content for s in ev_sources):
                        ev_sources.append({
                            "event_type": ev.event_type,
                            "text_content": ev.text_content,
                            "source_line": ev.source_line,
                            "source_page": ev.source_page,
                            "event_metadata": ev.event_metadata,
                        })
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, "Graph data could not be loaded") from exc

    # Combine DB entities + dynamically extracted entities
    all_entity_dict: dict[str, dict] = {}
    for e in entities:
        all_entity_dict[e.canonical_value] = {
            "id": str(e.id), "canonical_value": e.canonical_value, "entity_type": e.entity_type,
            "bridge_score": e.bridge_score or 0.0, "community_id": e.community_id
        }

    for val, etype in dynamic_entities.items():
        if val not in all_entity_dict:
            all_entity_dict[val] = {
                "id": val, "canonical_value": val, "entity_type": etype,
                "bridge_score": 0.0, "community_id": None
            }

    entity_dicts = list(all_entity_dict.values())

    # If case has no entities or events, provide a rich initial sample investigation graph
    if not entity_dicts:
        return {
          "case_id": case_id,
          "nodes": [],
          "edges": [],
          "hidden_edges": [],
        }
    event_dicts = [
        {"id": str(ev.id), "event_type": ev.event_type,
         "event_timestamp": ev.event_timestamp.isoformat() if ev.event_timestamp else None,
         "entity_mentions": []}
        for ev in events
    ]
    for event_dict in event_dicts:
        event_dict["entity_mentions"] = mentions_by_event.get(event_dict["id"], [])

    G = build_case_graph(entity_dicts, event_dicts)

    # Add hidden link edges — exclude AMOUNT entities which are not investigatively meaningful
    entity_values = {str(entity.id): entity.canonical_value for entity in entities}
    entity_types = {str(entity.id): entity.entity_type for entity in entities}
    EXCLUDED_HIDDEN_LINK_TYPES = {"AMOUNT", "KEYWORD"}
    hidden_edges = []
    for c in sorted(correlations, key=lambda item: item.final_score, reverse=True):
        a_type = entity_types.get(str(c.entity_a_id), "")
        b_type = entity_types.get(str(c.entity_b_id), "")
        if a_type in EXCLUDED_HIDDEN_LINK_TYPES or b_type in EXCLUDED_HIDDEN_LINK_TYPES:
            continue
        a_val = entity_values.get(str(c.entity_a_id), str(c.entity_a_id))
        b_val = entity_values.get(str(c.entity_b_id), str(c.entity_b_id))
        hidden_edges.append({
            "source":       a_val,
            "target":       b_val,
            "source_label": a_val,
            "target_label": b_val,
            "source_type":  a_type,
            "target_type":  b_type,
            "edge_type":    "hidden_link",
            "weight":       round(c.final_score, 4),
            "score":        c.final_score,
            "threshold":    c.threshold,
            "component_scores": c.component_scores,
            "model_weights": c.model_weights,
            "source_citations": c.source_citations or [],
        })
        if len(hidden_edges) >= max_hidden_links:
            break

    # Run ML HiddenLinkEngine live on G if correlations empty
    if not hidden_edges and len(G.nodes) > 1:
        hl_engine = getattr(request.app.state, "models", {}).get("hidden_link_lr")
        if hl_engine and hasattr(hl_engine, "predict_case"):
            try:
                inference_graph = select_relevant_subgraph(
                    G, max_nodes=max_nodes, max_edges=max_edges
                )
                reports = hl_engine.predict_case(inference_graph)
                for r in sorted(reports, key=lambda item: item.final_score, reverse=True)[:max_hidden_links]:
                    hidden_edges.append({
                        "source": r.entities[0],
                        "target": r.entities[1],
                        "edge_type": "hidden_link",
                        "weight": round(r.final_score, 4),
                        "score": r.final_score,
                        "threshold": r.threshold,
                        "component_scores": r.component_scores,
                        "source_citations": r.source_citations or [],
                    })
            except Exception as exc:
                print(f"[WARN] Hidden link prediction error: {exc}")

    total_nodes = len(G)
    total_edges = G.number_of_edges()
    if scope == "relevant":
        seeds = [value for edge in hidden_edges for value in (edge["source"], edge["target"])]
        G = select_relevant_subgraph(
            G,
            seed_nodes=seeds,
            selected_node=selected_node,
            hops=2 if two_hop else 1,
            max_nodes=max_nodes,
            max_edges=max_edges,
        )

    graph_data = graph_to_json(G)
    visible_nodes = {node["id"] for node in graph_data.get("nodes", [])}
    hidden_edges = [edge for edge in hidden_edges if edge["source"] in visible_nodes and edge["target"] in visible_nodes]
    for node in graph_data.get("nodes", []):
        node["evidence_sources"] = evidence_sources_by_entity.get(node["id"], [])[:10]

    graph_data["hidden_edges"] = hidden_edges
    graph_data["case_id"]      = case_id
    graph_data["selection"] = {
        "scope": scope,
        "total_nodes": total_nodes,
        "returned_nodes": len(graph_data.get("nodes", [])),
        "total_edges": total_edges,
        "returned_edges": len(graph_data.get("edges", [])),
        "truncated": total_nodes > len(graph_data.get("nodes", [])) or total_edges > len(graph_data.get("edges", [])),
    }
    graph_data["hidden_link_status"] = {
        "evaluated": bool(correlations) or getattr(request.app.state, "models", {}).get("hidden_link_lr") is not None,
        "reason": "links_returned" if hidden_edges else "no_candidates_above_threshold",
    }

    return graph_data


# ── Timeline router (separate prefix /timeline) ───────────────────────────────

timeline_router = APIRouter()


@timeline_router.get("/{case_id}")
async def get_timeline(
    case_id:   str,
    event_type: str | None = Query(None),
    limit:     int = Query(200, ge=1, le=1000),
    db:        AsyncSession = Depends(get_db),
    current:   User = Depends(get_current_user),
):
    """All evidence events for a case, sorted chronologically."""
    c = await require_case_access(db, current, case_id)
    case_uuid = c.id
    q = select(EvidenceEvent).where(EvidenceEvent.case_id == case_uuid)

    if event_type and event_type != "all":
        q = q.where(EvidenceEvent.event_type == event_type)
    q = q.order_by(EvidenceEvent.created_at.desc()).limit(limit)

    events = (await db.execute(q)).scalars().all()

    if not events:
        return {
            "case_id": case_id,
            "count": 0,
            "events": []
        }

    return {
        "case_id": case_id,
        "count":   len(events),
        "events":  [
            {
                "id":         str(ev.id),
                "timestamp":  ev.event_timestamp.isoformat() if ev.event_timestamp else ev.created_at.isoformat(),
                "event_type": ev.event_type,
                "text":       (ev.text_content or "")[:300],
                "text_content": (ev.text_content or "")[:300],
                "source_doc": ev.event_metadata.get("source_doc") if ev.event_metadata else None,
                "source_line": ev.source_line,
                "source_page": ev.source_page,
                "metadata":   ev.event_metadata or {},
            }
            for ev in events
        ],
    }


# ── Semantic search / retrieval-only query ────────────────────────────────────

query_router = APIRouter()


@query_router.post("/{case_id}")
async def query_case(
    case_id: str,
    body:    dict,
    db:      AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """
    TF-IDF retrieval over case text.
    Returns ranked evidence snippets with citations.
    NO generated output — zero hallucination risk by design.
    """
    c = await require_case_access(db, current, case_id)
    case_uuid = c.id
    question = body.get("question", "")
    top_k    = int(body.get("top_k", 5))

    # Use direct lexical retrieval for the core investigation workflow. This
    # is deterministic, fast and works offline; optional vector retrieval can
    # be enabled later without blocking the API on a model download.
    terms = [term for term in question.lower().split() if len(term) > 2]
    events = (await db.execute(
        select(EvidenceEvent)
        .where(EvidenceEvent.case_id == case_uuid)
        .order_by(EvidenceEvent.event_timestamp.desc())
        .limit(500)
    )).scalars().all()
    scored = []
    for event in events:
        text = event.text_content or ""
        score = sum(term in text.lower() for term in terms)
        if score:
            scored.append((score, event))
    scored.sort(key=lambda item: item[0], reverse=True)
    snippets = [
        {
            "rank": rank,
            "text": event.text_content or "",
            "file": event.event_metadata.get("source_doc", "") if event.event_metadata else "",
            "line": event.source_line or "",
            "page": event.source_page or "",
        }
        for rank, (_, event) in enumerate(scored[:top_k], start=1)
    ]

    return {
        "case_id":  case_id,
        "question": question,
        "mode":     "retrieval-only",
        "results":  snippets,
    }
