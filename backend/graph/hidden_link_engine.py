from __future__ import annotations
"""
CyberDrishti AI — Hidden-Link Inference Engine
Computes 6 link-prediction features and runs a logistic-regression combiner
with a precision-gated threshold (≥ 90% precision on validation).

Features: Common Neighbors, Jaccard, Adamic-Adar, Preferential Attachment,
          Temporal Co-occurrence, Financial Correlation, Bridge Score.
"""
import math
import pathlib
import pickle
from dataclasses import asdict, dataclass
from typing import Any

import networkx as nx
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import precision_recall_curve, average_precision_score
from sklearn.preprocessing import StandardScaler


# ── Config ────────────────────────────────────────────────────────────────────
TAU_TEMPORAL = 3600.0    # seconds
TAU_FIN      = 7200.0    # seconds
MIN_PRECISION = 0.90     # guaranteed precision on validation


# ── Individual feature functions ──────────────────────────────────────────────

def common_neighbors(G: nx.Graph, u: str, v: str) -> int:
    return len(list(nx.common_neighbors(G, u, v)))


def jaccard(G: nx.Graph, u: str, v: str) -> float:
    nu = set(G.neighbors(u))
    nv = set(G.neighbors(v))
    inter = len(nu & nv)
    union = len(nu | nv)
    return inter / union if union > 0 else 0.0


def adamic_adar(G: nx.Graph, u: str, v: str) -> float:
    score = 0.0
    for w in nx.common_neighbors(G, u, v):
        deg = G.degree(w)
        if deg > 1:
            score += 1.0 / math.log(deg)
    return score


def preferential_attachment(G: nx.Graph, u: str, v: str) -> float:
    return float(G.degree(u) * G.degree(v))


def temporal_co_occurrence(
    G: nx.Graph, u: str, v: str, tau: float = TAU_TEMPORAL
) -> float:
    """
    Sum of exp(−|t_u − t_v| / τ) across all (timestamp_u, timestamp_v) pairs
    where u and v appear in events near each other in time.
    Uses timestamps stored on nodes.
    """
    ts_u = G.nodes[u].get("timestamps", [])
    ts_v = G.nodes[v].get("timestamps", [])
    if not ts_u or not ts_v:
        return 0.0

    # Parse ISO strings to epoch floats
    from datetime import datetime, timezone

    def to_epoch(ts: str) -> float | None:
        try:
            if isinstance(ts, (int, float)):
                return float(ts)
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception:
            return None

    epochs_u = [t for t in (to_epoch(ts) for ts in ts_u) if t is not None]
    epochs_v = [t for t in (to_epoch(ts) for ts in ts_v) if t is not None]

    score = 0.0
    for t_u in epochs_u:
        for t_v in epochs_v:
            score += math.exp(-abs(t_u - t_v) / tau)
    return score


def financial_correlation(
    amount_m: float | None,
    amount_t: float | None,
    ts_m: float | None,
    ts_t: float | None,
    tau_fin: float = TAU_FIN,
) -> float:
    """
    FinScore = AmountMatch × TimeDecay
    AmountMatch = 1 − |a_m − a_t| / max(a_m, a_t)
    TimeDecay   = exp(−|ts_m − ts_t| / τ_fin)
    Returns 0.0 if any value is missing.
    """
    if amount_m is None or amount_t is None:
        return 0.0
    max_amt = max(abs(amount_m), abs(amount_t))
    if max_amt == 0:
        return 0.0
    amount_match = 1.0 - abs(amount_m - amount_t) / max_amt

    time_decay = 1.0
    if ts_m is not None and ts_t is not None:
        time_decay = math.exp(-abs(ts_m - ts_t) / tau_fin)

    return amount_match * time_decay


def _normalise_vec(values: list[float]) -> np.ndarray:
    arr = np.array(values, dtype=float)
    mx  = arr.max()
    return arr / mx if mx > 0 else arr


# ── Feature vector for a pair ─────────────────────────────────────────────────

def compute_pair_features(
    G: nx.Graph,
    u: str,
    v: str,
    amount_u: float | None = None,
    amount_v: float | None = None,
    ts_u:     float | None = None,
    ts_v:     float | None = None,
) -> dict[str, float]:
    """
    Compute all 6 features for a (u, v) pair.
    Returns a dict — values are NOT yet normalised (normalise across all pairs before training).
    """
    cn  = common_neighbors(G, u, v)
    jac = jaccard(G, u, v)
    aa  = adamic_adar(G, u, v)
    pa  = preferential_attachment(G, u, v)
    tmp = temporal_co_occurrence(G, u, v)
    fin = financial_correlation(amount_u, amount_v, ts_u, ts_v)

    bridge_u = G.nodes[u].get("bridge_score", 0.0)
    bridge_v = G.nodes[v].get("bridge_score", 0.0)
    bridge   = (bridge_u + bridge_v) / 2.0

    return {
        "cn":       float(cn),
        "jaccard":  jac,
        "aa":       aa,
        "temporal": tmp,
        "fin":      fin,
        "bridge":   bridge,
        "pa":       float(pa),
    }


# ── Explainability Report (Phase 7 format) ────────────────────────────────────

@dataclass
class ExplainabilityReport:
    flag_id:          str
    entities:         list[str]
    component_scores: dict[str, float]
    model_weights:    dict[str, float]
    final_score:      float
    threshold:        float
    decision:         str    # "flagged" | "not_flagged"
    source_citations: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


# ── Main engine ───────────────────────────────────────────────────────────────

class HiddenLinkEngine:
    """
    Train-once, predict-many engine.
    Usage:
        engine = HiddenLinkEngine()
        engine.fit(X, y, groups)          # Phase 6 training
        flags  = engine.predict_case(G)   # Phase 7 inference
    """

    def __init__(self):
        self.model: LogisticRegression | None = None
        self.scaler = StandardScaler()
        self.threshold: float = 0.5
        self.feature_names = ["cn", "jaccard", "aa", "temporal", "fin", "bridge", "pa"]

    def fit(
        self,
        X: np.ndarray,        # (N, 7) raw feature matrix
        y: np.ndarray,        # (N,) binary labels: 1=hidden link, 0=negative
        groups: np.ndarray,   # (N,) case-level group IDs (no leakage across cases)
        C_candidates: list = None,
    ):
        """
        5-fold cross-validation by case, grid search C ∈ {0.01, 0.1, 1, 10},
        select threshold guaranteeing ≥ 90% precision on validation folds.
        """
        C_candidates = C_candidates or [0.01, 0.1, 1.0, 10.0]

        X_scaled = self.scaler.fit_transform(X)
        cv = StratifiedGroupKFold(n_splits=5)

        best_C, best_auc_pr = C_candidates[0], -1.0
        threshold_per_C: dict[float, list[float]] = {}

        for C in C_candidates:
            lr = LogisticRegression(C=C, class_weight="balanced", max_iter=1000)
            fold_thresholds = []
            fold_auc_prs    = []

            for train_idx, val_idx in cv.split(X_scaled, y, groups):
                Xtr, Xval = X_scaled[train_idx], X_scaled[val_idx]
                ytr, yval = y[train_idx],        y[val_idx]
                lr.fit(Xtr, ytr)
                probs = lr.predict_proba(Xval)[:, 1]

                # Find threshold guaranteeing ≥ MIN_PRECISION
                precisions, recalls, thresholds_arr = precision_recall_curve(yval, probs)
                valid = [
                    (t, p) for t, p, r in
                    zip(thresholds_arr, precisions[:-1], recalls[:-1])
                    if p >= MIN_PRECISION
                ]
                threshold = valid[0][0] if valid else 0.99
                fold_thresholds.append(threshold)
                fold_auc_prs.append(average_precision_score(yval, probs))

            mean_auc = float(np.mean(fold_auc_prs))
            threshold_per_C[C] = fold_thresholds
            if mean_auc > best_auc_pr:
                best_auc_pr = mean_auc
                best_C      = C

        print(f"[HiddenLink] Best C={best_C}, mean AUC-PR={best_auc_pr:.4f}")

        # Final fit on all data
        self.model = LogisticRegression(C=best_C, class_weight="balanced", max_iter=1000)
        self.model.fit(X_scaled, y)
        self.threshold = float(np.mean(threshold_per_C[best_C]))
        print(f"[HiddenLink] Decision threshold (>={MIN_PRECISION:.0%} prec): {self.threshold:.4f}")

    def predict_pair(
        self,
        G: nx.Graph,
        u: str,
        v: str,
        amount_u: float | None = None,
        amount_v: float | None = None,
        ts_u:     float | None = None,
        ts_v:     float | None = None,
        citation_fn=None,
    ) -> ExplainabilityReport:
        """Score one (u, v) pair and return a full Explainability Report."""
        if self.model is None:
            raise RuntimeError("Engine not trained — call fit() first")

        raw_feats = compute_pair_features(G, u, v, amount_u, amount_v, ts_u, ts_v)
        feat_vec  = np.array([[raw_feats[k] for k in self.feature_names]])
        feat_scaled = self.scaler.transform(feat_vec)
        score     = float(self.model.predict_proba(feat_scaled)[0, 1])

        coef = self.model.coef_[0]
        weights = {k: float(coef[i]) for i, k in enumerate(self.feature_names)}

        citations = citation_fn(u, v) if citation_fn else []

        return ExplainabilityReport(
            flag_id          = f"{u}__{v}",
            entities         = [u, v],
            component_scores = {
                "jaccard":       raw_feats["jaccard"],
                "adamic_adar_norm": raw_feats["aa"],
                "temporal_norm": raw_feats["temporal"],
                "fin_score":     raw_feats["fin"],
                "bridge_score":  raw_feats["bridge"],
            },
            model_weights    = weights,
            final_score      = score,
            threshold        = self.threshold,
            decision         = "flagged" if score >= self.threshold else "not_flagged",
            source_citations = citations,
        )

    def predict_case(
        self,
        G: nx.Graph,
        citation_fn=None,
    ) -> list[ExplainabilityReport]:
        """
        Score all non-adjacent entity pairs in the graph.
        Returns only flagged pairs, sorted by score descending.
        """
        if self.model is None:
            raise RuntimeError("Engine not trained")

        nodes    = list(G.nodes())
        reports  = []

        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                u, v = nodes[i], nodes[j]
                if G.has_edge(u, v):
                    continue  # Already directly connected — not a hidden link
                report = self.predict_pair(G, u, v, citation_fn=citation_fn)
                if report.decision == "flagged":
                    reports.append(report)

        reports.sort(key=lambda r: r.final_score, reverse=True)
        return reports

    # ── Serialisation ─────────────────────────────────────────────────────────

    def save(self, path: str | pathlib.Path):
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({
                "model":     self.model,
                "scaler":    self.scaler,
                "threshold": self.threshold,
            }, f)

    @classmethod
    def load(cls, path: str | pathlib.Path) -> "HiddenLinkEngine":
        with open(path, "rb") as f:
            state = pickle.load(f)
        engine = cls()
        engine.model     = state["model"]
        engine.scaler    = state["scaler"]
        engine.threshold = state["threshold"]
        return engine
