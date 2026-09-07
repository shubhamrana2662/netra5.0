from __future__ import annotations
"""
CyberDrishti AI — Dataset Validation & Normalization Pipeline

What this module does:
  - Loads backend/ml/data/raw/ner_dataset.jsonl
  - Validates every record: tokens + tags fields, same length, valid BIO format
  - Deduplicates by content hash
  - Splits into train/val/test (80/10/10, seed=42) BEFORE any augmentation
  - Generates dataset_report.json with label distribution and HingBERT compatibility

What this module does NOT do:
  - Does NOT convert PER → PERSON or any other global label remapping.
  - Labels are preserved exactly as-is. Per-model label adjustments happen at training time.
  - Does NOT silently use synthetic data. Missing dataset raises FileNotFoundError.

HingBERT label compatibility:
  The locked HingBERT checkpoint label set is reported separately so that training
  can warn about unsupported labels before fine-tuning begins.
"""
import hashlib
import json
import logging
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── HingBERT locked label set (18 labels from artifacts/hingbert/config.json) ─
# These are the ONLY labels the existing HingBERT checkpoint can classify.
# Any dataset labels outside this set must be reported and handled explicitly.
HINGBERT_LOCKED_LABELS: frozenset = frozenset({
    "O",
    "B-PER", "I-PER",
    "B-PHONE",
    "B-UPI",
    "B-ACCOUNT",
    "B-AMOUNT",           # NOTE: I-AMOUNT is NOT in the HingBERT checkpoint
    "B-BANK", "I-BANK",
    "B-OTP",
    "B-EMAIL",
    "B-URL", "I-URL",
    "B-IFSC",
    "B-LOCATION", "I-LOCATION",
    "B-KEYWORD", "I-KEYWORD",
})  # 18 labels — exactly matches artifacts/hingbert/config.json label2id

_VALID_BIO_PREFIXES = frozenset({"B-", "I-"})


# ── Validation ────────────────────────────────────────────────────────────────

def _is_valid_bio_tag(tag: str) -> bool:
    if tag == "O":
        return True
    if len(tag) > 2 and tag[:2] in _VALID_BIO_PREFIXES and len(tag[2:]) >= 1:
        return True
    return False


def validate_record(record: Dict[str, Any], line_num: int) -> Tuple[bool, str]:
    """
    Validate a single JSONL record.
    Returns (is_valid: bool, error_message: str).
    """
    if not isinstance(record, dict):
        return False, f"Line {line_num}: record is not a JSON object"
    if "tokens" not in record:
        return False, f"Line {line_num}: missing required field 'tokens'"
    if "tags" not in record:
        return False, f"Line {line_num}: missing required field 'tags'"

    tokens = record["tokens"]
    tags = record["tags"]

    if not isinstance(tokens, list):
        return False, f"Line {line_num}: 'tokens' must be a list, got {type(tokens).__name__}"
    if not tokens:
        return False, f"Line {line_num}: 'tokens' is empty"
    if not isinstance(tags, list):
        return False, f"Line {line_num}: 'tags' must be a list, got {type(tags).__name__}"
    if len(tokens) != len(tags):
        return False, (
            f"Line {line_num}: length mismatch — "
            f"tokens={len(tokens)}, tags={len(tags)}"
        )

    for i, token in enumerate(tokens):
        if not isinstance(token, str):
            return False, f"Line {line_num}: token[{i}] is not a string (got {type(token).__name__})"

    for i, tag in enumerate(tags):
        if not isinstance(tag, str):
            return False, f"Line {line_num}: tag[{i}] is not a string"
        if not _is_valid_bio_tag(tag):
            return False, f"Line {line_num}: invalid BIO tag '{tag}' at position {i}"

    return True, ""


# ── Deduplication ─────────────────────────────────────────────────────────────

def _record_hash(record: Dict[str, Any]) -> str:
    """Compute a stable hash for deduplication."""
    canonical = json.dumps(
        {"tokens": record["tokens"], "tags": record["tags"]},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.md5(canonical.encode("utf-8")).hexdigest()


# ── HingBERT compatibility ─────────────────────────────────────────────────────

def check_hingbert_compatibility(sentences: List[Dict]) -> Dict[str, Any]:
    """
    Inspect every tag in the dataset and report which labels are outside the
    locked HingBERT label set. Does NOT modify any labels.

    Returns a dict with counts of unsupported labels and affected sentences.
    This report is purely informational — training code uses it to warn and decide.
    """
    unsupported_label_counts: Dict[str, int] = {}
    sentences_with_unsupported = 0
    total_unsupported_tokens = 0

    for sent in sentences:
        found_unsupported = False
        for tag in sent.get("tags", []):
            if tag not in HINGBERT_LOCKED_LABELS:
                unsupported_label_counts[tag] = unsupported_label_counts.get(tag, 0) + 1
                total_unsupported_tokens += 1
                found_unsupported = True
        if found_unsupported:
            sentences_with_unsupported += 1

    return {
        "locked_label_set": sorted(HINGBERT_LOCKED_LABELS),
        "total_sentences_checked": len(sentences),
        "sentences_with_unsupported_labels": sentences_with_unsupported,
        "total_unsupported_label_tokens": total_unsupported_tokens,
        "unsupported_labels": dict(
            sorted(unsupported_label_counts.items(), key=lambda x: -x[1])
        ),
        "hingbert_fully_compatible_sentences": len(sentences) - sentences_with_unsupported,
        "note": (
            "Unsupported labels are NOT silently converted. "
            "Train script must explicitly decide how to handle them."
        ),
    }


# ── File hash ────────────────────────────────────────────────────────────────

def compute_dataset_hash(path: Path) -> str:
    """Compute SHA-256 hash of the raw dataset file for provenance tracking."""
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


# ── Main pipeline ─────────────────────────────────────────────────────────────

def normalize_and_split_data(
    input_file: Path,
    output_dir: Path,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    require_real_data: bool = True,
) -> Dict[str, Any]:
    """
    Load, validate, deduplicate, and split the JSONL dataset.

    Labels are preserved exactly as-is. No global BIO normalization.

    Args:
        input_file:       Path to raw JSONL file (one JSON record per line).
        output_dir:       Where to write train.jsonl, val.jsonl, test.jsonl,
                          and dataset_report.json.
        train_ratio:      Fraction of data for training (default 0.8).
        val_ratio:        Fraction for validation (default 0.1).
        test_ratio:       Fraction for held-out test (default 0.1).
        require_real_data: If True, raise FileNotFoundError when input is missing.
                           If False, return error dict (for testing only).

    Returns:
        dataset_report dict (also written to output_dir/dataset_report.json).

    Raises:
        FileNotFoundError: If input_file is missing and require_real_data=True.
        ValueError:        If ratios do not sum to 1.0.
    """
    if abs(train_ratio + val_ratio + test_ratio - 1.0) > 1e-6:
        raise ValueError(
            f"train + val + test ratios must sum to 1.0, "
            f"got {train_ratio + val_ratio + test_ratio}"
        )

    if not input_file.exists():
        if require_real_data:
            raise FileNotFoundError(
                f"\n[FATAL] Dataset not found: {input_file}\n"
                "Expected format: JSONL file with one record per line.\n"
                "Each record must have:\n"
                '  {"tokens": ["word1", "word2", ...], "tags": ["B-PER", "O", ...]}\n'
                "Place your dataset at this path before running prepare_data.py.\n"
            )
        else:
            logger.warning(
                "[PrepareData] Dataset not found at %s — returning empty splits.", input_file
            )
            return {"error": "dataset_not_found", "path": str(input_file)}

    dataset_hash = compute_dataset_hash(input_file)

    # ── Load and validate ──────────────────────────────────────────────────
    raw_sentences: List[Dict] = []
    validation_errors: List[str] = []

    with open(input_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                validation_errors.append(f"Line {line_num}: JSON parse error: {e}")
                continue

            ok, err = validate_record(record, line_num)
            if not ok:
                validation_errors.append(err)
                continue

            raw_sentences.append({"tokens": record["tokens"], "tags": record["tags"]})

    if validation_errors:
        # Log first 20 errors, truncate the rest
        for err in validation_errors[:20]:
            logger.warning("[PrepareData] %s", err)
        if len(validation_errors) > 20:
            logger.warning(
                "[PrepareData] ... and %d more validation errors (truncated).",
                len(validation_errors) - 20,
            )

    # ── Deduplicate ────────────────────────────────────────────────────────
    seen: set = set()
    sentences: List[Dict] = []
    duplicate_count = 0

    for sent in raw_sentences:
        h = _record_hash(sent)
        if h in seen:
            duplicate_count += 1
        else:
            seen.add(h)
            sentences.append(sent)

    total = len(sentences)

    # ── Deterministic shuffle + split (BEFORE any augmentation) ───────────
    random.seed(42)
    random.shuffle(sentences)

    n_train = int(total * train_ratio)
    n_val = int(total * val_ratio)

    train_set = sentences[:n_train]
    val_set = sentences[n_train:n_train + n_val]
    test_set = sentences[n_train + n_val:]

    # ── Write splits ───────────────────────────────────────────────────────
    output_dir.mkdir(parents=True, exist_ok=True)

    for split_name, split_data in [("train", train_set), ("val", val_set), ("test", test_set)]:
        out_path = output_dir / f"{split_name}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for item in split_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # ── Label distribution (raw, no normalization) ─────────────────────────
    label_counts: Dict[str, int] = {}
    for sent in sentences:
        for tag in sent["tags"]:
            label_counts[tag] = label_counts.get(tag, 0) + 1

    # ── HingBERT compatibility report ──────────────────────────────────────
    # Check against the full dataset so training can filter before splitting
    hingbert_compat = check_hingbert_compatibility(sentences)

    # ── Write dataset report ───────────────────────────────────────────────
    report: Dict[str, Any] = {
        "dataset_hash_sha256": dataset_hash,
        "input_file": str(input_file.absolute()),
        "random_seed": 42,
        "total_raw_lines": total + duplicate_count + len(validation_errors),
        "validation_errors_count": len(validation_errors),
        "validation_errors_sample": validation_errors[:10],
        "duplicates_removed": duplicate_count,
        "total_valid_unique_records": total,
        "split_ratios": {
            "train": train_ratio,
            "val": val_ratio,
            "test": test_ratio,
        },
        "train_records": len(train_set),
        "validation_records": len(val_set),
        "test_records": len(test_set),
        "label_distribution": dict(sorted(label_counts.items())),
        "unique_label_count": len(label_counts),
        "hingbert_label_compatibility": hingbert_compat,
        "label_preservation_note": (
            "Labels are preserved exactly as-is. "
            "No global BIO normalization is applied in this pipeline. "
            "Per-model label adjustments happen at training time only."
        ),
    }

    with open(output_dir / "dataset_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(
        "[PrepareData] Processed %d valid unique records → "
        "train=%d, val=%d, test=%d | dupes removed=%d | errors=%d",
        total, len(train_set), len(val_set), len(test_set),
        duplicate_count, len(validation_errors),
    )

    return report


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="CyberDrishti Dataset Preparation — Validates and splits JSONL NER data."
    )
    parser.add_argument(
        "--input", default=None,
        help="Path to raw JSONL file (default: backend/ml/data/raw/ner_dataset.jsonl)"
    )
    parser.add_argument(
        "--output", default=None,
        help="Output directory for processed splits (default: backend/ml/data/processed)"
    )
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent.parent
    raw_file = Path(args.input) if args.input else base_dir / "data" / "raw" / "ner_dataset.jsonl"
    proc_dir = Path(args.output) if args.output else base_dir / "data" / "processed"

    try:
        report = normalize_and_split_data(
            raw_file, proc_dir,
            train_ratio=args.train_ratio,
            val_ratio=args.val_ratio,
            test_ratio=args.test_ratio,
            require_real_data=True,
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
