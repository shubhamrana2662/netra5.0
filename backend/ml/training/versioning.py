from __future__ import annotations
"""
CyberDrishti AI — Checkpoint Versioning Utility

Manages versioned model directories and safe production promotion.

Rules:
  - Production paths (artifacts/crf/, artifacts/hingbert/, artifacts/cyberdrishtilm/)
    are NEVER written to during training.
  - Training always writes to artifacts/models/<model>/v<N>/.
  - Promotion happens only when new_f1 > prod_f1 on the same held-out test set.
  - Production F1=1.0 is treated as suspicious (synthetic data leakage) and is NOT
    used as a barrier to promotion.
"""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

MODELS_SUBDIR = "models"
MANIFEST_FILENAME = "training_manifest.json"


# ── Directory helpers ─────────────────────────────────────────────────────────

def get_production_dir(artifacts_dir: Path, model_name: str) -> Path:
    """Return the live production checkpoint path. Never write here during training."""
    return artifacts_dir / model_name


def get_versioned_base(artifacts_dir: Path, model_name: str) -> Path:
    """Return the base directory for all versioned training runs."""
    return artifacts_dir / MODELS_SUBDIR / model_name


def get_next_version_dir(artifacts_dir: Path, model_name: str) -> Tuple[Path, int]:
    """
    Find the next available vN directory.
    Starts at v2 (v1 is considered the original/production checkpoint).
    Returns (path, version_number).
    """
    base = get_versioned_base(artifacts_dir, model_name)
    base.mkdir(parents=True, exist_ok=True)
    version = 2
    while (base / f"v{version}").exists():
        version += 1
    path = base / f"v{version}"
    path.mkdir(parents=True, exist_ok=True)
    return path, version


# ── Metrics helpers ───────────────────────────────────────────────────────────

def _extract_f1(metrics: Dict[str, Any]) -> Optional[float]:
    """Try multiple common metric keys to extract F1 score."""
    for key in ["macro_f1", "f1", "eval_ner_f1_macro", "ner_f1", "eval_f1"]:
        if key in metrics:
            try:
                return float(metrics[key])
            except (TypeError, ValueError):
                pass
    return None


def read_production_metrics(artifacts_dir: Path, model_name: str) -> Optional[Dict[str, Any]]:
    """
    Read current production model metrics from disk.
    Returns None if no metrics file is found.
    Does NOT use any hardcoded/synthetic metrics.
    """
    prod_dir = get_production_dir(artifacts_dir, model_name)
    for fname in ("eval_metrics.json", "test_metrics.json"):
        path = prod_dir / fname
        if path.exists():
            with open(path, "r") as f:
                return json.load(f)
    return None


def compute_file_hash(path: Path) -> str:
    """Compute SHA-256 hash of a file for provenance tracking."""
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


# ── Training manifest ─────────────────────────────────────────────────────────

def write_training_manifest(
    version_dir: Path,
    model_name: str,
    version: int,
    dataset_hash: str,
    seed: int,
    training_config: Dict[str, Any],
    pre_train_prod_metrics: Optional[Dict[str, Any]],
    post_train_metrics: Optional[Dict[str, Any]] = None,
    promoted: bool = False,
) -> None:
    """Write training_manifest.json to a versioned checkpoint directory."""
    manifest = {
        "model_name": model_name,
        "version": f"v{version}",
        "version_dir": str(version_dir.absolute()),
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_hash_sha256": dataset_hash,
        "random_seed": seed,
        "training_config": training_config,
        "production_metrics_before_training": pre_train_prod_metrics,
        "post_training_metrics_on_held_out_test": post_train_metrics,
        "promoted": promoted,
        "promoted_at_utc": None,
    }
    with open(version_dir / MANIFEST_FILENAME, "w") as f:
        json.dump(manifest, f, indent=2)


def update_manifest_promotion(version_dir: Path) -> None:
    """Mark a manifest as promoted after actual promotion."""
    path = version_dir / MANIFEST_FILENAME
    if path.exists():
        with open(path, "r") as f:
            manifest = json.load(f)
        manifest["promoted"] = True
        manifest["promoted_at_utc"] = datetime.now(timezone.utc).isoformat()
        with open(path, "w") as f:
            json.dump(manifest, f, indent=2)


# ── Promotion logic ───────────────────────────────────────────────────────────

def should_promote(
    new_metrics: Dict[str, Any],
    prod_metrics_on_new_test: Optional[Dict[str, Any]],
    min_threshold: float = 0.0,
) -> Tuple[bool, str]:
    """
    Decide whether to promote the new model to production.

    Comparison policy:
    - Both new and production models are evaluated on the SAME held-out test set.
    - We never compare against stored synthetic metrics (e.g. CRF F1=1.0).
    - If the production model cannot be evaluated on the new test set (no real data
      was available when it was trained), promote the new model automatically.
    - Production F1 >= 0.999 is treated as suspicious (synthetic/leakage) and is
      NOT used as a barrier to promotion.

    Args:
        new_metrics:               Metrics of the new model on held-out test.
        prod_metrics_on_new_test:  Production model evaluated on the SAME test set.
        min_threshold:             Minimum acceptable F1 for promotion.

    Returns:
        (promote: bool, reason: str)
    """
    new_f1 = _extract_f1(new_metrics)
    if new_f1 is None:
        return False, "New model has no extractable F1 metric — cannot promote."

    if new_f1 < min_threshold:
        return False, (
            f"New model F1={new_f1:.4f} is below minimum threshold {min_threshold:.4f}."
        )

    if prod_metrics_on_new_test is None:
        return True, "Production model could not be evaluated on new test set — promoting new model."

    prod_f1 = _extract_f1(prod_metrics_on_new_test)
    if prod_f1 is None:
        return True, "Production model F1 is unknown on new test set — promoting new model."

    # Suspicious production F1 (synthetic data leakage)
    if prod_f1 >= 0.999:
        return True, (
            f"Production model F1={prod_f1:.4f} on new test set is suspiciously perfect "
            f"(likely synthetic data leakage). Promoting new model with F1={new_f1:.4f}."
        )

    if new_f1 > prod_f1:
        delta = new_f1 - prod_f1
        return True, (
            f"New F1={new_f1:.4f} > Production F1={prod_f1:.4f} (Δ={delta:+.4f}) — promoting."
        )
    else:
        return False, (
            f"New F1={new_f1:.4f} <= Production F1={prod_f1:.4f} — NOT promoting. "
            f"Production checkpoint preserved."
        )


def promote_to_production(
    version_dir: Path,
    production_dir: Path,
    files_to_copy: list,
) -> None:
    """
    Copy specific files from versioned dir to production dir.
    Creates a timestamped backup of existing production files first.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    if production_dir.exists():
        backup_dir = production_dir.parent / f"{production_dir.name}_backup_{ts}"
        shutil.copytree(production_dir, backup_dir)
        print(f"  📦 Production backup saved to: {backup_dir}")

    production_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for fname in files_to_copy:
        src = version_dir / fname
        dst = production_dir / fname
        if src.exists():
            shutil.copy2(src, dst)
            copied.append(fname)
            print(f"  ✓ Promoted: {fname}")
        else:
            print(f"  ⚠ Skipped (not found): {fname}")

    update_manifest_promotion(version_dir)
    print(f"  ✓ Promotion complete. {len(copied)} files copied.")
