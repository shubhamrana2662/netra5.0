"""CyberDrishti Feature 4 — Hypothesis Engine (isolated build).

Forces competing theories (kingpin / layer-1 mule / compromised victim) to be
evaluated simultaneously against the SAME evidence, with refutation shown —
the ACH discipline (Heuer) applied to suspect classification.

Mechanics: bucket an observed indicator → look up P(E|H) per hypothesis from
data/hypotheses.json (HAND-SET, documented engineering judgements) → update
log-odds from equal (or supplied) priors → normalize posteriors.

Honesty rules (enforced):
- Posteriors are None unless allow_percentages=True AND a calibration dict is
  supplied. Otherwise every hypothesis carries the label
  "RULE_BASED_ASSESSMENT — not a calibrated probability" and only the RANK
  and the evidence matrix are displayed. (R v T [2010] EWCA Crim 2439:
  courts reject numerical Bayes without an empirical basis.)
- Every indicator result cites its observed value and bucket; missing
  observations are reported as unobserved, never imputed.
- Refuting evidence per hypothesis: the indicator whose P(E|H) for THAT
  hypothesis is lowest (the diagnostic the hypothesis cannot explain).
"""
from __future__ import annotations

import json
import math
from typing import Any


def load_model(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        model = json.load(fh)
    labels = {h["label"] for h in model["hypotheses"]}
    for ind in model["indicators"]:
        for bucket, dist in ind["evidence"].items():
            if set(dist) != labels:
                raise ValueError(f"indicator '{ind['name']}' bucket '{bucket}' "
                                 f"does not cover all hypotheses")
            if abs(sum(dist.values()) - 1.0) > 1e-6:
                raise ValueError(f"indicator '{ind['name']}' bucket '{bucket}' "
                                 f"likelihoods must sum to 1")
    return model


def bucket_value(observation_key: str, value: float, meta: dict[str, Any]) -> str:
    """Bucket an observed value per _meta.indicator_observations rules."""
    spec = meta["indicator_observations"][observation_key]
    for bucket, expr in spec["buckets"].items():
        op, _, rhs = expr.partition(" ")
        threshold = float(rhs)
        if op == "<=" and value <= threshold:
            return bucket
        if op == ">" and value > threshold:
            return bucket
        if op == ">=" and value >= threshold:
            return bucket
        if op == "<" and value < threshold:
            return bucket
    raise ValueError(f"value {value} fits no bucket for {observation_key}")


def evaluate(
    observations: dict[str, float],
    model: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = {"allow_percentages": False, "calibration": None,
           "priors": None, **(config or {})}
    hypotheses = model["hypotheses"]
    labels = [h["label"] for h in hypotheses]
    priors = cfg["priors"] or {h["label"]: h["prior"] for h in hypotheses}
    log_post = {lbl: math.log(priors[lbl]) for lbl in labels}

    used: list[dict[str, Any]] = []
    unobserved: list[str] = []
    for ind in model["indicators"]:
        key = ind["observation_key"]
        if key not in observations or observations[key] is None:
            unobserved.append(ind["name"])
            continue
        bucket = bucket_value(key, observations[key], model["_meta"])
        dist = ind["evidence"][bucket]
        for lbl in labels:
            log_post[lbl] += math.log(dist[lbl])
        # diagnosticity: spread between max and min likelihood across H
        diag = max(dist.values()) - min(dist.values())
        used.append({
            "indicator": ind["name"],
            "observed_value": observations[key],
            "bucket": bucket,
            "likelihoods": {lbl: dist[lbl] for lbl in labels},
            "diagnosticity": round(diag, 4),
            "note": ind["note"],
        })

    total = sum(math.exp(v) for v in log_post.values())
    posteriors = {lbl: math.exp(log_post[lbl]) / total for lbl in labels}
    ranked = sorted(labels, key=lambda l: -posteriors[l])

    per_hypothesis = []
    for lbl in labels:
        refuting = min(used, key=lambda u: u["likelihoods"][lbl]) if used else None
        per_hypothesis.append({
            "label": lbl,
            "posterior": (round(posteriors[lbl], 4)
                          if cfg["allow_percentages"] and cfg["calibration"] else None),
            "refuting_evidence": ({
                "indicator": refuting["indicator"],
                "bucket": refuting["bucket"],
                "likelihood_under_this_hypothesis": refuting["likelihoods"][lbl],
                "why": f"this hypothesis explains '{refuting['indicator']}' = "
                       f"{refuting['bucket']} least well"
            } if refuting else None),
        })
    per_hypothesis.sort(key=lambda h: -posteriors[h["label"]])

    calibrated = bool(cfg["allow_percentages"] and cfg["calibration"])
    return {
        "ranked_labels": ranked,
        "hypotheses": per_hypothesis,
        "evidence_matrix": used,
        "unobserved_indicators": unobserved,
        "assessment_type": ("CALIBRATED_POSTERIOR" if calibrated
                            else "RULE_BASED_ASSESSMENT"),
        "display_label": (None if calibrated else
                          "Ranking from hand-set likelihoods — not a calibrated "
                          "probability. Show the matrix and refuting evidence."),
    }
