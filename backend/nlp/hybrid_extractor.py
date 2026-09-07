"""
CyberDrishti AI — Production Hybrid Extractor (Phase 5)
Unifies deterministic normalized regex with contextual sequence modeling (CRF / HingBERT).
Rule of Precedence:
- Deterministic regex has absolute authority over hard identifiers:
  PHONE, UPI, IFSC, ACCOUNT, URL, EMAIL, OTP, AMOUNT.
- Contextual ML (CRF / HingBERT) supplements open-vocabulary entities:
  PER, BANK, KEYWORD, LOCATION.
- Overlaps are adjudicated in favor of deterministic identifiers.
"""
import logging
import pathlib
import pickle
from typing import Any, List, Optional

from correlation.regex_extractors import Extraction, RegexExtractor
from nlp.train_crf import word_features

logger = logging.getLogger(__name__)

BACKEND_DIR = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_CRF_PATH = BACKEND_DIR / "artifacts" / "crf" / "crf_model.pkl"


class HybridExtractor:
    """Production hybrid extraction pipeline."""

    def __init__(self, crf_path: Optional[pathlib.Path] = None):
        self.rx = RegexExtractor()
        self.crf = None
        target_crf = crf_path or DEFAULT_CRF_PATH
        if target_crf.exists():
            try:
                with open(target_crf, "rb") as f:
                    self.crf = pickle.load(f)
            except Exception as exc:
                logger.warning("[HybridExtractor] Could not load CRF from %s: %s", target_crf, exc)

    def extract(self, text: str) -> list[Extraction]:
        """Run hybrid extraction on raw text."""
        # 1. Deterministic extractions (highest precision)
        extractions = self.rx.extract(text)
        claimed_spans = [(e.span_start, e.span_end) for e in extractions]

        def _is_overlapping(start: int, end: int) -> bool:
            return any(not (end <= cs or start >= ce) for cs, ce in claimed_spans)

        # 2. Contextual CRF supplement for PER, KEYWORD, BANK, LOCATION
        if self.crf and text.strip():
            tokens = text.split()
            char_idx = 0
            token_spans = []
            for w in tokens:
                s = text.find(w, char_idx)
                token_spans.append((s, s + len(w)))
                char_idx = s + len(w)

            features = [word_features(tokens, i) for i in range(len(tokens))]
            try:
                tags = self.crf.predict([features])[0]
                curr_type = None
                curr_start = -1
                curr_end = -1
                curr_tokens = []

                for idx, tag in enumerate(tags):
                    ts, te = token_spans[idx]
                    if tag.startswith("B-"):
                        if curr_type and curr_tokens:
                            if curr_type in ("PER", "KEYWORD", "BANK", "LOCATION") and not _is_overlapping(curr_start, curr_end):
                                extractions.append(Extraction(
                                    entity_type=curr_type,
                                    raw_value=" ".join(curr_tokens),
                                    norm_value=" ".join(curr_tokens).strip(),
                                    span_start=curr_start,
                                    span_end=curr_end,
                                    extractor="crf_contextual",
                                    confidence=0.85,
                                ))
                        curr_type = tag[2:]
                        curr_start = ts
                        curr_end = te
                        curr_tokens = [tokens[idx]]
                    elif tag.startswith("I-") and curr_type == tag[2:]:
                        curr_end = te
                        curr_tokens.append(tokens[idx])
                    else:
                        if curr_type and curr_tokens:
                            if curr_type in ("PER", "KEYWORD", "BANK", "LOCATION") and not _is_overlapping(curr_start, curr_end):
                                extractions.append(Extraction(
                                    entity_type=curr_type,
                                    raw_value=" ".join(curr_tokens),
                                    norm_value=" ".join(curr_tokens).strip(),
                                    span_start=curr_start,
                                    span_end=curr_end,
                                    extractor="crf_contextual",
                                    confidence=0.85,
                                ))
                        curr_type = None
                        curr_tokens = []

                if curr_type and curr_tokens:
                    if curr_type in ("PER", "KEYWORD", "BANK", "LOCATION") and not _is_overlapping(curr_start, curr_end):
                        extractions.append(Extraction(
                            entity_type=curr_type,
                            raw_value=" ".join(curr_tokens),
                            norm_value=" ".join(curr_tokens).strip(),
                            span_start=curr_start,
                            span_end=curr_end,
                            extractor="crf_contextual",
                            confidence=0.85,
                        ))
            except Exception as exc:
                logger.debug("[HybridExtractor] CRF pass failed: %s", exc)

        extractions.sort(key=lambda x: x.span_start)
        return extractions
