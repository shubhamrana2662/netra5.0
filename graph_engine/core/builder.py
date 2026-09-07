"""
CyberDrishti AI — Graph Builder
================================
Constructs a NetworkX undirected graph from extracted entities and evidence events.
Computes:
- Node degree centrality
- Louvain community detection (with greedy modularity & connected components fallbacks)
- BridgeScore: Fraction of a node's edges that cross community boundaries
- Edge co-occurrence weights and observation timestamps
"""

from __future__ import annotations

from typing import Any, Optional
import networkx as nx


def build_case_graph(
    entities: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> nx.Graph:
    """
    Build a NetworkX undirected graph for an investigation case.

    Node attributes:
        entity_type: e.g. PER, PHONE, UPI, ACCOUNT, AMOUNT, IP
        canonical_value: standardized entity identifier
        mention_count: total times observed across events
        first_seen, last_seen: earliest and latest event ISO timestamps
        timestamps: list of all occurrence timestamps
        degree_centrality: normalized degree centrality [0, 1]
        community_id: integer cluster assigned by Louvain modularity
        bridge_score: fraction of edges traversing between communities

    Edge attributes:
        edge_type: communication / transaction / co_occurrence / ownership
        weight: number of co-occurring events
        timestamps: list of event timestamps where co-occurrence occurred
    """
    G = nx.Graph()
    node_lookup: dict[str, str] = {}

    # 1. Register explicit entities
    for e in entities:
        cval = e.get("canonical_value") or e.get("id") or ""
        if not cval:
            continue
        G.add_node(
            cval,
            entity_type=e.get("entity_type", "UNKNOWN"),
            canonical_value=cval,
            db_id=str(e.get("id", "")),
            mention_count=0,
            community_id=e.get("community_id"),
            bridge_score=float(e.get("bridge_score") or 0.0),
            first_seen=e.get("first_seen"),
            last_seen=e.get("last_seen"),
            timestamps=[],
        )
        node_lookup[cval.lower()] = cval

    # 2. Add edges and dynamic nodes from events
    for event in events:
        mentions = event.get("entity_mentions", [])
        ts = event.get("event_timestamp")
        evtype = event.get("event_type", "co_occurrence")

        # Ensure all entities in event are added to graph
        for m in mentions:
            raw_cval = m.get("canonical_value") or m.get("raw_value")
            if not raw_cval:
                continue
            lower_cval = raw_cval.lower()
            if lower_cval not in node_lookup:
                G.add_node(
                    raw_cval,
                    entity_type=m.get("entity_type", "UNKNOWN"),
                    canonical_value=raw_cval,
                    db_id="",
                    mention_count=0,
                    community_id=None,
                    bridge_score=0.0,
                    first_seen=ts,
                    last_seen=ts,
                    timestamps=[],
                )
                node_lookup[lower_cval] = raw_cval

        if len(mentions) < 2:
            continue

        # Form clique / pairwise edges for all entities co-occurring in the event
        for i in range(len(mentions)):
            for j in range(i + 1, len(mentions)):
                raw_a = mentions[i].get("canonical_value") or mentions[i].get("raw_value")
                raw_b = mentions[j].get("canonical_value") or mentions[j].get("raw_value")
                if not raw_a or not raw_b or raw_a.lower() == raw_b.lower():
                    continue

                a = node_lookup.get(raw_a.lower(), raw_a)
                b = node_lookup.get(raw_b.lower(), raw_b)

                if G.has_edge(a, b):
                    G[a][b]["weight"] += 1
                    if ts and ts not in G[a][b]["timestamps"]:
                        G[a][b]["timestamps"].append(ts)
                else:
                    G.add_edge(
                        a,
                        b,
                        edge_type=evtype,
                        weight=1,
                        timestamps=[ts] if ts else [],
                    )

    # 3. Update mention counts and node timestamps
    for event in events:
        ts = event.get("event_timestamp")
        for m in event.get("entity_mentions", []):
            raw_cval = m.get("canonical_value") or m.get("raw_value")
            if not raw_cval:
                continue
            cval = node_lookup.get(raw_cval.lower(), raw_cval)
            if G.has_node(cval):
                G.nodes[cval]["mention_count"] += 1
                if ts:
                    G.nodes[cval]["timestamps"].append(ts)
                    if not G.nodes[cval].get("first_seen"):
                        G.nodes[cval]["first_seen"] = ts
                    G.nodes[cval]["last_seen"] = ts

    # 4. Compute Degree Centrality
    if len(G.nodes) > 0:
        deg_centrality = nx.degree_centrality(G)
        for node, val in deg_centrality.items():
            G.nodes[node]["degree_centrality"] = round(val, 4)

    # 5. Community Detection & BridgeScore
    if len(G.nodes) > 1 and len(G.edges) > 0:
        partition: dict[str, int] = {}
        try:
            # Primary: Native NetworkX Louvain
            communities = list(nx.community.louvain_communities(G, seed=42))
            for idx, comm in enumerate(communities):
                for node in comm:
                    partition[node] = idx
        except Exception:
            try:
                # Fallback 1: Greedy Modularity
                communities = list(nx.community.greedy_modularity_communities(G))
                for idx, comm in enumerate(communities):
                    for node in comm:
                        partition[node] = idx
            except Exception:
                try:
                    # Fallback 2: Connected Components
                    for idx, comp in enumerate(nx.connected_components(G)):
                        for node in comp:
                            partition[node] = idx
                except Exception:
                    pass

        if partition:
            for node, comm_id in partition.items():
                if G.has_node(node):
                    G.nodes[node]["community_id"] = comm_id

            # BridgeScore: fraction of a node's edges that cross into other communities
            for node in G.nodes():
                node_comm = G.nodes[node].get("community_id")
                if node_comm is None:
                    continue
                neighbors = list(G.neighbors(node))
                if not neighbors:
                    G.nodes[node]["bridge_score"] = 0.0
                    continue
                cross_edges = sum(
                    1 for nb in neighbors if G.nodes[nb].get("community_id") != node_comm
                )
                G.nodes[node]["bridge_score"] = round(cross_edges / len(neighbors), 4)

    return G


def graph_to_json(G: nx.Graph) -> dict[str, Any]:
    """Serialise NetworkX graph to a dictionary compatible with web visualization engines."""
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

    return {"nodes": nodes, "edges": edges}
