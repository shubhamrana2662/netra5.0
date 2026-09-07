"""
CyberDrishti AI — Graph Engine Core Package
============================================
Components:
- Canonicalizer & UnionFind: Entity resolution and fuzzy clustering.
- GraphBuilder: NetworkX case graph construction, community detection, bridge scoring.
- HiddenLinkEngine: 6-feature link prediction with precision-gated logistic regression.
- Deterministic Extractors: Indian cyber crime hard-identifier regex extraction.
- Serializer: Export to 2D/3D graph visualization formats.
"""

from .canonicalizer import UnionFind, canonicalise_entities, HARD_ID_TYPES, FUZZY_THRESHOLD
from .builder import build_case_graph, graph_to_json
from .hidden_link_engine import (
    HiddenLinkEngine,
    ExplainabilityReport,
    compute_pair_features,
    common_neighbors,
    jaccard,
    adamic_adar,
    preferential_attachment,
    temporal_co_occurrence,
    financial_correlation,
)
from .extractors import RegexExtractor, Extraction
from .serializer import serialize_graph_for_visualization

__all__ = [
    "UnionFind",
    "canonicalise_entities",
    "HARD_ID_TYPES",
    "FUZZY_THRESHOLD",
    "build_case_graph",
    "graph_to_json",
    "HiddenLinkEngine",
    "ExplainabilityReport",
    "compute_pair_features",
    "common_neighbors",
    "jaccard",
    "adamic_adar",
    "preferential_attachment",
    "temporal_co_occurrence",
    "financial_correlation",
    "RegexExtractor",
    "Extraction",
    "serialize_graph_for_visualization",
]
