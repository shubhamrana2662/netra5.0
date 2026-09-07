from __future__ import annotations
"""
CyberDrishti AI — Model Registry Service

Manages loading, status reporting, and metadata for all ML models:
  CRF Baseline, HingBERT Transformer, CyberDrishtiLM Transformer.

READY criteria (all must be true):
  1. Checkpoint path exists on disk
  2. Model loads without error
  3. Architecture matches checkpoint (no key mismatch)
  4. A probe inference returns a result list without exception

CyberDrishtiLM special status:
  LABEL_MAP_UNKNOWN — weights loaded, architecture verified, but the original
  25-label NER mapping is unrecoverable. predict() returns [].
  run_verification_forward() still proves real transformer inference works.

F1 scores:
  Read from actual eval_metrics.json / test_metrics.json files on disk.
  Hardcoded metrics are NEVER used. Missing metric files → f1_score=None.
"""
import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from config import settings
from ml.crf_model import CRFInferenceEngine
from ml.hingbert_model import HingBERTInferenceEngine
from ml.cyberdrishtilm_model import CyberDrishtiLMInferenceEngine

logger = logging.getLogger(__name__)

# Probe text used to verify real inference (not for metrics)
_PROBE_TEXT = "Rohit Kumar transferred Rs. 50000 to account 9876543210 via UPI paytm@sbi from Delhi."


@dataclass
class ModelInfo:
    model_name: str
    task: str
    status: str          # READY | MISSING_CHECKPOINT | LABEL_MAP_UNKNOWN | UNAVAILABLE | ERROR
    device: str
    checkpoint_path: str
    f1_score: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    probe_result: Optional[str] = None   # "pass" | "fail" | "label_map_unknown" | None


def _read_metric(metrics_dir: Path, key: str = "macro_f1") -> Optional[float]:
    """
    Read a specific metric from eval_metrics.json or test_metrics.json.
    Returns None if neither file exists or the key is absent.
    """
    for fname in ("eval_metrics.json", "test_metrics.json"):
        path = metrics_dir / fname
        if path.exists():
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                for candidate in [key, "macro_f1", "f1", "eval_ner_f1_macro", "ner_f1"]:
                    if candidate in data and data[candidate] is not None:
                        return float(data[candidate])
            except (json.JSONDecodeError, OSError):
                pass
    return None


def _read_all_metrics(metrics_dir: Path) -> Dict[str, Optional[float]]:
    """Read precision, recall, F1 from metrics files."""
    result: Dict[str, Optional[float]] = {
        "f1_score": None,
        "precision": None,
        "recall": None,
    }
    for fname in ("eval_metrics.json", "test_metrics.json"):
        path = metrics_dir / fname
        if not path.exists():
            continue
        try:
            with open(path, "r") as f:
                data = json.load(f)
            for f1_key in ["macro_f1", "f1", "eval_ner_f1_macro", "ner_f1"]:
                if f1_key in data and data[f1_key] is not None:
                    result["f1_score"] = float(data[f1_key])
                    break
            for prec_key in ["macro_precision", "precision"]:
                if prec_key in data and data[prec_key] is not None:
                    result["precision"] = float(data[prec_key])
                    break
            for rec_key in ["macro_recall", "recall"]:
                if rec_key in data and data[rec_key] is not None:
                    result["recall"] = float(data[rec_key])
                    break
            if result["f1_score"] is not None:
                break
        except (json.JSONDecodeError, OSError):
            pass
    return result


def _run_probe(engine, engine_type: str) -> str:
    """
    Run a probe inference to verify real inference works.
    Returns "pass", "fail", or "label_map_unknown".
    """
    try:
        if engine_type == "cyberdrishtilm":
            if engine.status == CyberDrishtiLMInferenceEngine.STATUS_LABEL_MAP_UNKNOWN:
                # Verify forward pass still works
                result = engine.run_verification_forward(_PROBE_TEXT)
                if result.get("forward_pass") == "real_transformer":
                    return "label_map_unknown"
                return "fail"
            preds = engine.predict(_PROBE_TEXT)
            # predict() may return [] for unknown label map, which is expected
            return "pass" if isinstance(preds, list) else "fail"
        else:
            preds = engine.predict(_PROBE_TEXT)
            return "pass" if isinstance(preds, list) else "fail"
    except Exception as exc:
        logger.error("[ModelRegistry] Probe failed for %s: %s", engine_type, exc)
        return "fail"


class ModelRegistry:
    """Singleton Registry for CyberDrishti ML Models."""

    def __init__(self):
        self.crf_engine = CRFInferenceEngine()
        self.hingbert_engine = HingBERTInferenceEngine()
        self.cdlm_engine = CyberDrishtiLMInferenceEngine()
        self.primary_model_name: str = getattr(settings, "primary_ml_model", "crf")
        self.initialized: bool = False
        self._model_infos: Dict[str, ModelInfo] = {}

    def load_all_models(
        self, artifacts_dir: Optional[str | Path] = None
    ) -> Dict[str, ModelInfo]:
        """
        Attempt to load all 3 models from artifact checkpoints.
        F1 scores are read from disk — no hardcoded values.
        Probe inference is run to verify READY status.
        """
        base_dir = Path(artifacts_dir or settings.artifacts_dir)

        # Resolve relative path relative to backend dir if needed
        if not base_dir.is_absolute():
            backend_dir = Path(__file__).resolve().parent.parent
            base_dir = backend_dir / base_dir
        if not base_dir.exists():
            fallback = Path(__file__).resolve().parent.parent / "artifacts"
            if fallback.exists():
                base_dir = fallback

        logger.info(
            "[ModelRegistry] Initializing from %s ...", base_dir.absolute()
        )

        # ── 1. CRF ────────────────────────────────────────────────────────
        crf_path = base_dir / "crf" / "crf_model.pkl"
        crf_ok = self.crf_engine.load(crf_path)
        crf_metrics = _read_all_metrics(base_dir / "crf")

        if crf_ok:
            crf_probe = _run_probe(self.crf_engine, "crf")
            crf_status = "READY" if crf_probe == "pass" else "ERROR"
        else:
            crf_probe = None
            crf_status = "MISSING_CHECKPOINT"

        crf_info = ModelInfo(
            model_name="CRF Baseline",
            task="Named Entity Recognition",
            status=crf_status,
            device="cpu",
            checkpoint_path=str(crf_path),
            f1_score=crf_metrics["f1_score"],
            precision=crf_metrics["precision"],
            recall=crf_metrics["recall"],
            probe_result=crf_probe,
        )

        # ── 2. HingBERT ───────────────────────────────────────────────────
        hingbert_dir = base_dir / "hingbert"
        hingbert_ok = self.hingbert_engine.load(hingbert_dir)
        hingbert_metrics = _read_all_metrics(hingbert_dir)

        if hingbert_ok:
            hingbert_probe = _run_probe(self.hingbert_engine, "hingbert")
            hingbert_status = "READY" if hingbert_probe == "pass" else "ERROR"
        else:
            hingbert_probe = None
            hingbert_status = "MISSING_CHECKPOINT"

        hingbert_info = ModelInfo(
            model_name="HingBERT (Hindi-BERT-v2 Fine-tuned)",
            task="Contextual Cyber NER",
            status=hingbert_status,
            device=self.hingbert_engine.device,
            checkpoint_path=str(hingbert_dir),
            f1_score=hingbert_metrics["f1_score"],
            precision=hingbert_metrics["precision"],
            recall=hingbert_metrics["recall"],
            probe_result=hingbert_probe,
        )

        # ── 3. CyberDrishtiLM ─────────────────────────────────────────────
        cdlm_dir = base_dir / "cyberdrishtilm"
        cdlm_ok = self.cdlm_engine.load(cdlm_dir)
        cdlm_metrics = _read_all_metrics(cdlm_dir)

        if cdlm_ok:
            cdlm_probe = _run_probe(self.cdlm_engine, "cyberdrishtilm")
            if cdlm_probe == "label_map_unknown":
                cdlm_status = CyberDrishtiLMInferenceEngine.STATUS_LABEL_MAP_UNKNOWN
            elif cdlm_probe == "pass":
                cdlm_status = "READY"
            else:
                cdlm_status = "ERROR"
        else:
            cdlm_probe = None
            cdlm_status = "MISSING_CHECKPOINT"

        cdlm_info = ModelInfo(
            model_name="CyberDrishtiLM Custom Transformer",
            task="Contextual NER & Classification",
            status=cdlm_status,
            device=self.cdlm_engine.device,
            checkpoint_path=str(cdlm_dir),
            f1_score=cdlm_metrics["f1_score"],
            precision=cdlm_metrics["precision"],
            recall=cdlm_metrics["recall"],
            probe_result=cdlm_probe,
        )

        self._model_infos = {
            "crf": crf_info,
            "hingbert": hingbert_info,
            "cyberdrishtilm": cdlm_info,
        }
        self.initialized = True

        logger.info(
            "[ModelRegistry] Models loaded — CRF: %s (probe=%s), "
            "HingBERT: %s (probe=%s), CyberDrishtiLM: %s (probe=%s)",
            crf_info.status, crf_probe,
            hingbert_info.status, hingbert_probe,
            cdlm_info.status, cdlm_probe,
        )

        return self._model_infos

    def get_primary_engine(self) -> Tuple[Any, str]:
        """Return the active primary inference engine, with CRF fallback."""
        if (
            self.primary_model_name == "hingbert"
            and self.hingbert_engine.loaded
            and self._is_ready("hingbert")
        ):
            return self.hingbert_engine, "hingbert"
        if (
            self.primary_model_name == "cyberdrishtilm"
            and self.cdlm_engine.loaded
            and self._is_ready("cyberdrishtilm")
        ):
            return self.cdlm_engine, "cyberdrishtilm"
        if self.crf_engine.loaded:
            return self.crf_engine, "crf"
        if self.hingbert_engine.loaded:
            return self.hingbert_engine, "hingbert"
        return None, "none"

    def _is_ready(self, model_name: str) -> bool:
        info = self._model_infos.get(model_name)
        if info is None:
            return False
        return info.status == "READY"

    def get_status(self) -> Dict[str, Any]:
        """Return structured model registry status for frontend / API."""
        primary_engine, active_name = self.get_primary_engine()
        models_status = {}

        for key, info in self._model_infos.items():
            models_status[key] = {
                "name": info.model_name,
                "status": info.status,
                "device": info.device,
                "f1_score": info.f1_score,
                "precision": info.precision,
                "recall": info.recall,
                "probe_result": info.probe_result,
            }

        # Fill in defaults for models not yet loaded
        for key, defaults in [
            ("crf", {"name": "CRF Baseline", "device": "cpu"}),
            ("hingbert", {"name": "HingBERT Fine-tuned", "device": self.hingbert_engine.device}),
            ("cyberdrishtilm", {"name": "CyberDrishtiLM Transformer", "device": self.cdlm_engine.device}),
        ]:
            if key not in models_status:
                models_status[key] = {
                    "name": defaults["name"],
                    "status": "MISSING_CHECKPOINT",
                    "device": defaults["device"],
                    "f1_score": None,
                    "precision": None,
                    "recall": None,
                    "probe_result": None,
                }

        return {
            "initialized": self.initialized,
            "primary_model": active_name,
            "primary_model_loaded": primary_engine is not None,
            "models": models_status,
            "ready_note": (
                "A model is READY only when: checkpoint exists, loads successfully, "
                "architecture matches, and probe inference succeeds. "
                "CyberDrishtiLM LABEL_MAP_UNKNOWN = weights loaded, forward pass verified, "
                "but NER predictions disabled (25-label map unrecoverable)."
            ),
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_registry = ModelRegistry()


def get_model_registry() -> ModelRegistry:
    global _registry
    if not _registry.initialized:
        _registry.load_all_models()
    return _registry
