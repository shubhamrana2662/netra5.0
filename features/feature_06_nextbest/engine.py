"""CyberDrishti Feature 6 — Next-Best Investigation Engine (isolated build).

Ranks the single investigative actions that save the most money or resolve the
most uncertainty RIGHT NOW, given a case state. Design honesty:

- Transparent weighted utility with DISCLOSED weights, not a black-box
  Value-of-Information estimate. True VoI needs a response model of the world
  we do not have; the output therefore says what it is: a weighted priority
  heuristic, every component visible.
- Asset actions score by unwithdrawn amount × urgency (exponential decay over
  the configurable golden-hours window). Evidence-expansion actions score by
  how many unresolved targets they clear, discounted by latency.
- Drafts are filled ONLY from case data. A required field that is missing
  BLOCKS the draft and names the missing fields — the engine never invents
  values. Every draft carries the DRAFT banner (IO signature + legal review).
- The action catalog (statutes, latencies, templates) is data:
  data/action_catalog.json.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any

DEFAULT_WEIGHTS = {"asset": 1.0, "urgency": 0.5, "latency": 0.3, "friction": 0.4}
BANNER_REQUIRED_SUBSTRING = "DRAFT"


def load_catalog(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        cat = json.load(fh)
    for action in cat["actions"]:
        for key in ("code", "statute", "latency_hours", "friction_cost",
                    "requires", "draft_template", "asset_scoped"):
            if key not in action:
                raise ValueError(f"catalog action missing '{key}': {action.get('code')}")
    return cat


def _norm_ts(value: Any) -> datetime:
    dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def rank_actions(
    case_state: dict[str, Any],
    catalog: dict[str, Any],
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    golden_hours = float(catalog.get("golden_hours", 2.0))
    elapsed = float(case_state.get("elapsed_hours_since_first_credit", 0.0))
    urgency = math.exp(-elapsed / max(golden_hours, 1e-6))

    results: list[dict[str, Any]] = []
    for action in catalog["actions"]:
        targets = _targets_for(action, case_state)
        for target in targets:
            missing = [f for f in action["requires"] if not target.get(f)]
            entry: dict[str, Any] = {
                "action_code": action["code"],
                "description": action["description"],
                "category": action["category"],
                "statutory_basis": action["statute"],
                "target": {k: v for k, v in target.items() if not k.startswith("_")},
                "urgency_factor": round(urgency, 4),
                "latency_hours": action["latency_hours"],
                "friction_cost": action["friction_cost"],
                "weights_used": dict(w),
                "golden_hours": golden_hours,
            }
            if missing:
                entry.update({
                    "status": "blocked_missing_fields",
                    "missing_fields": missing,
                    "draft": None,
                    "utility_score": None,
                })
                results.append(entry)
                continue

            asset = float(target.get("amount_unwithdrawn") or 0)
            if action["asset_scoped"]:
                asset_component = asset / 100000.0            # per ₹1 lakh
                resolution_component = 0.0
            else:
                asset_component = 0.0
                resolution_component = float(target.get("_resolves", 1))
            latency_component = 1.0 / max(action["latency_hours"], 0.25)
            score = (
                w["asset"] * asset_component
                + w["urgency"] * urgency * max(asset_component, resolution_component)
                + w["latency"] * latency_component
                - w["friction"] * action["friction_cost"]
            )
            entry.update({
                "status": "ready",
                "missing_fields": [],
                "components": {
                    "asset_component": round(asset_component, 4),
                    "resolution_component": resolution_component,
                    "urgency_factor": round(urgency, 4),
                    "latency_component": round(latency_component, 4),
                    "friction_penalty": round(w["friction"] * action["friction_cost"], 4),
                },
                "utility_score": round(score, 4),
                "draft": action["draft_template"].format(
                    **{k: v for k, v in target.items() if k in action["requires"]}),
                "banner": "DRAFT — requires IO signature and legal verification before issue.",
            })
            results.append(entry)

    results.sort(key=lambda r: (
        0 if r["status"] == "ready" else 1,
        -(r["utility_score"] if r["utility_score"] is not None else float("-inf")),
    ))
    return {
        "ranked_actions": results,
        "elapsed_hours_since_first_credit": elapsed,
        "note": ("Weighted priority heuristic with disclosed weights — not a "
                 "calibrated Value-of-Information estimate."),
    }


def _targets_for(action: dict[str, Any], case_state: dict[str, Any]) -> list[dict[str, Any]]:
    """Produce concrete action instances from case state."""
    targets: list[dict[str, Any]] = []
    if action["code"] == "HELPLINE_1930_REFERRAL":
        if case_state.get("complaint_ref"):
            targets.append({"complaint_ref": case_state["complaint_ref"],
                            "_resolves": 1})
        return targets
    if action["asset_scoped"]:
        for acct in case_state.get("accounts_at_risk", []):
            targets.append({**acct, "_resolves": 1})
        return targets
    if action["code"] == "REQUISITION_CDR_IPDR":
        for phone in case_state.get("unresolved_phones", [])[:1] or []:
            targets.append({**phone, "_resolves": len(case_state.get("unresolved_phones", []))})
        return targets
    if action["code"] == "TOWER_DUMP":
        for cell in case_state.get("crime_window_cells", [])[:1] or []:
            targets.append({**cell, "_resolves": 1})
        return targets
    if action["code"] == "KYC_FETCH":
        for acct in case_state.get("accounts_at_risk", [])[:1] or []:
            targets.append({**acct, "_resolves": 1})
        return targets
    return targets
