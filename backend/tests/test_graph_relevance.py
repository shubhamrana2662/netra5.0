import networkx as nx

from graph.graph_builder import build_case_graph, select_relevant_subgraph


def test_repeated_mentions_do_not_inflate_edge_weight():
    entities = [
        {"id": "1", "canonical_value": "alice", "entity_type": "PER"},
        {"id": "2", "canonical_value": "alice@upi", "entity_type": "UPI"},
    ]
    events = [{
        "id": "event-1",
        "event_type": "bank_txn",
        "event_timestamp": None,
        "entity_mentions": [
            {"canonical_value": "alice", "entity_type": "PER"},
            {"canonical_value": "alice", "entity_type": "PER"},
            {"canonical_value": "alice@upi", "entity_type": "UPI"},
        ],
    }]

    graph = build_case_graph(entities, events)

    assert graph.number_of_edges() == 1
    assert graph["alice"]["alice@upi"]["weight"] == 1


def test_relevant_subgraph_enforces_node_and_edge_limits():
    graph = nx.complete_graph(30)
    for node in graph.nodes:
        graph.nodes[node].update(mention_count=node, bridge_score=0.0)
    for source, target in graph.edges:
        graph[source][target]["weight"] = source + target + 1

    relevant = select_relevant_subgraph(graph, max_nodes=12, max_edges=20)

    assert relevant.number_of_nodes() <= 12
    assert relevant.number_of_edges() <= 20
    assert all(source in relevant and target in relevant for source, target in relevant.edges)
