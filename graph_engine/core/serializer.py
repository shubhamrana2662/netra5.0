"""
CyberDrishti AI — Graph Serializer
===================================
Prepares NetworkX graphs and inferred hidden links for consumption by
frontend visualizers (React Flow, Three.js 3D Force Graph, Cytoscape, D3.js).
"""

from __future__ import annotations

from typing import Any, Optional
import networkx as nx

from .hidden_link_engine import ExplainabilityReport


def serialize_graph_for_visualization(
    G: nx.Graph,
    hidden_links: Optional[list[ExplainabilityReport]] = None,
    case_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Export nodes, observed evidence edges, and inferred hidden links
    into a standardized, clean JSON payload.
    """
    nodes = []
    for n, attrs in G.nodes(data=True):
        nodes.append({
            "id": str(n),
            "label": str(attrs.get("canonical_value") or n),
            "canonical_value": str(attrs.get("canonical_value") or n),
            "entity_type": attrs.get("entity_type", "UNKNOWN"),
            "db_id": attrs.get("db_id", ""),
            "mention_count": attrs.get("mention_count", 0),
            "degree_centrality": attrs.get("degree_centrality", 0.0),
            "community_id": attrs.get("community_id"),
            "bridge_score": attrs.get("bridge_score", 0.0),
            "first_seen": attrs.get("first_seen"),
            "last_seen": attrs.get("last_seen"),
            "timestamps": attrs.get("timestamps", []),
        })

    edges = []
    for a, b, attrs in G.edges(data=True):
        edges.append({
            "source": str(a),
            "target": str(b),
            "edge_type": attrs.get("edge_type", "co_occurrence"),
            "weight": attrs.get("weight", 1),
            "timestamps": attrs.get("timestamps", []),
        })

    hidden_edges = []
    if hidden_links:
        for r in hidden_links:
            hidden_edges.append({
                "source": r.entities[0],
                "target": r.entities[1],
                "edge_type": "hidden_link",
                "weight": r.final_score,
                "score": r.final_score,
                "threshold": r.threshold,
                "component_scores": r.component_scores,
                "model_weights": r.model_weights,
                "citations": r.source_citations,
            })

    return {
        "case_id": case_id or "case_graph",
        "node_count": len(nodes),
        "edge_count": len(edges),
        "hidden_link_count": len(hidden_edges),
        "nodes": nodes,
        "edges": edges,
        "hidden_edges": hidden_edges,
    }
