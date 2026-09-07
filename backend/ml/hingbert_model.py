from __future__ import annotations
"""
CyberDrishti AI — HingBERT Transformer Inference Service
Loads fine-tuned HingBERT (hindi-bert-v2) checkpoint weights, tokenizes input,
runs PyTorch transformer inference, decodes BIO entity labels, and computes softmax confidence.
Gracefully handles CPU / MPS / CUDA devices.
"""
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Check PyTorch & Transformers availability
_torch_available = False
_transformers_available = False

try:
    import torch
    _torch_available = True
except ImportError:
    logger.warning("[HingBERT] PyTorch not installed.")

try:
    from transformers import AutoConfig, AutoModelForTokenClassification, AutoTokenizer
    _transformers_available = True
except ImportError:
    logger.warning("[HingBERT] Transformers library not installed.")


@dataclass
class HingBERTPrediction:
    entity_type: str
    raw_value: str
    canonical_value: str
    span_start: int
    span_end: int
    confidence: float
    model_name: str = "hingbert"


class HingBERTInferenceEngine:
    """HingBERT Fine-Tuned Transformer Inference Engine."""

    def __init__(self, model_dir: Optional[str | Path] = None):
        self.model = None
        self.tokenizer = None
        self.config = None
        self.id2label = {}
        self.device = "cpu"
        self.loaded = False

        if model_dir:
            self.load(model_dir)

    def load(self, model_dir: str | Path) -> bool:
        if not _torch_available or not _transformers_available:
            logger.warning("[HingBERT] PyTorch or Transformers missing — cannot load HingBERT.")
            self.loaded = False
            return False

        path = Path(model_dir)
        if not path.exists():
            logger.warning("[HingBERT] Model directory not found at %s", path)
            self.loaded = False
            return False

        try:
            # Select device (MPS on Apple Silicon, CUDA on GPU server, fallback CPU)
            if torch.backends.mps.is_available():
                self.device = "mps"
            elif torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"

            logger.info("[HingBERT] Loading checkpoint from %s on device: %s", path, self.device)
            self.config = AutoConfig.from_pretrained(str(path))
            self.tokenizer = AutoTokenizer.from_pretrained(str(path))
            self.model = AutoModelForTokenClassification.from_pretrained(str(path), config=self.config)
            self.model.to(self.device)
            self.model.eval()

            self.id2label = getattr(self.config, "id2label", {})
            if not self.id2label and hasattr(self.config, "label2id"):
                self.id2label = {v: k for k, v in self.config.label2id.items()}

            self.loaded = True
            logger.info("[HingBERT] Successfully loaded HingBERT model checkpoint (%d labels)", len(self.id2label))
            return True

        except Exception as exc:
            logger.error("[HingBERT] Error loading model from %s: %s", path, exc)
            self.loaded = False
            return False

    def predict(self, text: str, min_confidence: float = 0.50) -> List[HingBERTPrediction]:
        """Run actual transformer forward pass and decode token classification labels."""
        if not self.loaded or not self.model or not self.tokenizer or not text.strip():
            return []

        try:
            inputs = self.tokenizer(text, return_tensors="pt", return_offsets_mapping=True, truncation=True, max_length=512)
            offset_mapping = inputs.pop("offset_mapping")[0].cpu().numpy()

            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits[0]  # (seq_len, num_labels)
                probs = torch.softmax(logits, dim=-1)
                confidences, predictions_ids = torch.max(probs, dim=-1)

            predictions_ids = predictions_ids.cpu().numpy()
            confidences = confidences.cpu().numpy()

            # Known entity types — filter out garbage labels
            _VALID_ENTITY_TYPES = {"PERSON", "PER", "ORG", "ORGANIZATION", "LOC", "GPE", "LOCATION", "DATE", "AMOUNT", "PHONE", "UPI", "ACCOUNT", "EMAIL", "IP"}

            entities: List[HingBERTPrediction] = []
            current_label = None
            current_start = -1
            current_end = -1
            current_confs = []

            for idx, label_id in enumerate(predictions_ids):
                start, end = offset_mapping[idx]
                if start == end:
                    continue  # Special tokens like [CLS], [SEP]

                label = self.id2label.get(int(label_id), "O")
                conf = float(confidences[idx])

                # Skip low-confidence predictions
                if conf < min_confidence:
                    label = "O"

                if label.startswith("B-"):
                    if current_label and current_start < current_end:
                        val = text[current_start:current_end].strip()
                        avg_conf = sum(current_confs) / len(current_confs) if current_confs else 0.0
                        # Minimum length and valid type check
                        if val and len(val) >= 2 and avg_conf >= min_confidence:
                            entities.append(HingBERTPrediction(
                                entity_type=current_label,
                                raw_value=val,
                                canonical_value=val,
                                span_start=current_start,
                                span_end=current_end,
                                confidence=round(avg_conf, 4),
                                model_name="hingbert",
                            ))
                    etype = label[2:]
                    if etype not in _VALID_ENTITY_TYPES:
                        current_label = None
                        continue
                    current_label = etype
                    current_start = int(start)
                    current_end = int(end)
                    current_confs = [conf]

                elif label.startswith("I-") and current_label and current_label == label[2:]:
                    current_end = int(end)
                    current_confs.append(conf)

                else:
                    if current_label and current_start < current_end:
                        val = text[current_start:current_end].strip()
                        avg_conf = sum(current_confs) / len(current_confs) if current_confs else 0.0
                        if val and len(val) >= 2 and avg_conf >= min_confidence:
                            entities.append(HingBERTPrediction(
                                entity_type=current_label,
                                raw_value=val,
                                canonical_value=val,
                                span_start=current_start,
                                span_end=current_end,
                                confidence=round(avg_conf, 4),
                                model_name="hingbert",
                            ))
                    current_label = None
                    current_confs = []

            if current_label and current_start < current_end:
                val = text[current_start:current_end].strip()
                avg_conf = sum(current_confs) / len(current_confs) if current_confs else 0.0
                if val and len(val) >= 2 and avg_conf >= min_confidence:
                    entities.append(HingBERTPrediction(
                        entity_type=current_label,
                        raw_value=val,
                        canonical_value=val,
                        span_start=current_start,
                        span_end=current_end,
                        confidence=round(avg_conf, 4),
                        model_name="hingbert",
                    ))

            return entities

        except Exception as exc:
            logger.error("[HingBERT] Inference error: %s", exc)
            return []

