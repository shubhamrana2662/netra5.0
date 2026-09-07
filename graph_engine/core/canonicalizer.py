"""
CyberDrishti AI — Graph Canonicalizer & Entity Resolution
=========================================================
Implements Union-Find disjoint-set data structure with path compression and
rank-based union. Merges non-hard entities using Levenshtein distance and
token-set ratio (threshold >= 0.85). Preserves hard-identifier integrity
(PHONE, UPI, ACCOUNT, EMAIL, IFSC, IP, IMEI, AADHAAR, PAN, VEHICLE) by
enforcing strict exact matching to prevent wrongful associations.
"""

from __future__ import annotations

from typing import Any
from rapidfuzz import fuzz

# ── Merge threshold ───────────────────────────────────────────────────────────
FUZZY_THRESHOLD = 0.85

# ── Hard-identifier types (exact match only — regex is source of truth) ───────
HARD_ID_TYPES = {
    "PHONE",
    "UPI",
    "ACCOUNT",
    "EMAIL",
    "IFSC",
    "IP",
    "IMEI",
    "AADHAAR",
    "PAN",
    "VEHICLE",
}


# ── Union-Find Disjoint Set ───────────────────────────────────────────────────

class UnionFind:
    """
    Disjoint-set data structure with path compression and union-by-rank.
    Provides near-constant amortized time complexity O(alpha(N)) for finding
    and unioning entity mentions.
    """

    def __init__(self):
        self._parent: dict[str, str] = {}
        self._rank: dict[str, int] = {}

    def find(self, x: str) -> str:
        """Find the representative root of element x with path compression."""
        if x not in self._parent:
            self._parent[x] = x
            self._rank[x] = 0
        if self._parent[x] != x:
            self._parent[x] = self.find(self._parent[x])  # path compression
        return self._parent[x]

    def union(self, x: str, y: str) -> None:
        """Union the sets containing x and y using rank heuristics."""
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        if self._rank[rx] < self._rank[ry]:
            rx, ry = ry, rx
        self._parent[ry] = rx
        if self._rank[rx] == self._rank[ry]:
            self._rank[rx] += 1

    def groups(self) -> dict[str, list[str]]:
        """Return all clusters grouped by their representative root."""
        groups: dict[str, list[str]] = {}
        for x in self._parent:
            root = self.find(x)
            groups.setdefault(root, []).append(x)
        return groups


# ── Canonicalisation Similarity ───────────────────────────────────────────────

def similarity(a: str, b: str, entity_type: str) -> float:
    """
    Compute similarity score between two entity values:
    - Exact match on normalised string -> 1.0
    - Hard-ID types (PHONE, UPI, ACCOUNT, etc.) -> 0.0 unless exact match
    - Names (PER), Locations (LOC/ORG) -> Token-set ratio (handles re-ordered names)
    """
    a_norm = a.strip().lower()
    b_norm = b.strip().lower()
    if a_norm == b_norm:
        return 1.0
    if entity_type.upper() in HARD_ID_TYPES:
        return 0.0
    # Token-set ratio handles permutations like "Sharma, Vikram" vs "Vikram Sharma"
    score = fuzz.token_set_ratio(a_norm, b_norm) / 100.0
    return score


def canonicalise_entities(raw_mentions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """
    Given a list of raw entity mention dicts:
        {"raw_value": str, "entity_type": str, ...}
    Returns a mapping:
        {canonical_key -> [list of raw mention dicts]}

    Merging Rules:
    1. Exact match on normalized value -> identical canonical key.
    2. Hard-ID types: strict exact match only (no fuzzy merging).
    3. Non-hard types with token-set similarity >= FUZZY_THRESHOLD (0.85) -> merged.
    4. Union-Find applies transitive closure (if A~B and B~C, then A~B~C).
    5. The canonical representative is chosen as the most frequent raw value in the cluster.
    """
    uf = UnionFind()
    ids = [m["raw_value"].strip().lower() for m in raw_mentions]

    # Register all elements in Union-Find
    for item_id in ids:
        uf.find(item_id)

    # Compare pairwise candidates
    n = len(ids)
    for i in range(n):
        etype_i = raw_mentions[i].get("entity_type", "UNKNOWN")
        for j in range(i + 1, n):
            etype_j = raw_mentions[j].get("entity_type", "UNKNOWN")
            if etype_i != etype_j:
                continue
            sim = similarity(ids[i], ids[j], etype_i)
            if sim >= FUZZY_THRESHOLD:
                uf.union(ids[i], ids[j])

    groups = uf.groups()
    result: dict[str, list[dict[str, Any]]] = {}

    for root, members in groups.items():
        member_set = set(members)
        # Choose canonical key: the most common raw_value in the cluster
        freq: dict[str, int] = {}
        for m in raw_mentions:
            key = m["raw_value"].strip().lower()
            if key in member_set:
                freq[key] = freq.get(key, 0) + 1

        canonical = max(freq, key=freq.get) if freq else root
        for m in raw_mentions:
            key = m["raw_value"].strip().lower()
            if key in member_set:
                result.setdefault(canonical, []).append(m)

    return result
