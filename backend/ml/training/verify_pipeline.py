from __future__ import annotations
"""
CyberDrishti AI — Pipeline Verification Suite

Verifies all architectural fixes WITHOUT training anything or modifying files.

Tests:
  1. Dataset validation — valid/invalid JSONL records pass/fail correctly
  2. BIO label preservation — labels not altered by prepare_data.py
  3. HingBERT label compatibility report — unsupported labels detected
  4. CRF checkpoint loads and is READY
  5. HingBERT checkpoint loads (may be READY or MISSING_CHECKPOINT)
  6. CyberDrishtiLM checkpoint loads (expect LABEL_MAP_UNKNOWN)
  7. Real CRF inference — predict() returns a list on probe text
  8. Real HingBERT inference — if loaded: forward pass returns predictions list
  9. Real CyberDrishtiLM forward pass — transformer computes real tensors
     (expected ner_logits=[1, 64, 25], fraud_logits=[1, 2])
 10. Production checkpoint integrity — byte sizes unchanged

Usage:
    cd backend && python3 -m ml.training.verify_pipeline

Exit codes:
    0 — all tests passed
    1 — one or more tests failed
"""
import json
import os
import sys
import tempfile
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# ── Production checkpoint baseline sizes (recorded before any changes) ────────
PRODUCTION_CHECKPOINT_SIZES = {
    "artifacts/crf/crf_model.pkl":                    74014,
    "artifacts/hingbert/model.safetensors":       947941256,
    "artifacts/hingbert/config.json":                  1549,
    "artifacts/hingbert/tokenizer.json":            6408647,
    "artifacts/cyberdrishtilm/pytorch_model.bin":  4932133,
    "artifacts/cyberdrishtilm/config.json":             249,
    "artifacts/cyberdrishtilm/tokenizer.json":      198851,
}

# ── Test runner ───────────────────────────────────────────────────────────────

_results = []


def test(name: str):
    """Decorator that wraps a test function."""
    def decorator(fn):
        _results.append((name, fn))
        return fn
    return decorator


def _pass(name, msg=""):
    print(f"  ✓ PASS: {name}" + (f" — {msg}" if msg else ""))
    return True


def _fail(name, msg=""):
    print(f"  ✗ FAIL: {name}" + (f" — {msg}" if msg else ""))
    return False


# ─────────────────────────────────────────────────────────────────────────────
# TEST 1: Dataset validation
# ─────────────────────────────────────────────────────────────────────────────

def test_dataset_validation():
    name = "Dataset validation"
    try:
        from ml.training.prepare_data import validate_record, _is_valid_bio_tag

        # Valid record
        ok, err = validate_record(
            {"tokens": ["Rohit", "transferred", "50000"], "tags": ["B-PER", "O", "B-AMOUNT"]},
            line_num=1,
        )
        if not ok:
            return _fail(name, f"Valid record failed: {err}")

        # Missing tokens
        ok, err = validate_record({"tags": ["O"]}, line_num=2)
        if ok:
            return _fail(name, "Should reject record missing 'tokens'")

        # Missing tags
        ok, err = validate_record({"tokens": ["word"]}, line_num=3)
        if ok:
            return _fail(name, "Should reject record missing 'tags'")

        # Length mismatch
        ok, err = validate_record(
            {"tokens": ["a", "b"], "tags": ["B-PER"]}, line_num=4
        )
        if ok:
            return _fail(name, "Should reject tokens/tags length mismatch")

        # Invalid BIO tag
        ok, err = validate_record(
            {"tokens": ["word"], "tags": ["PERSON"]}, line_num=5
        )
        if ok:
            return _fail(name, "Should reject invalid BIO tag 'PERSON' (missing B-/I- prefix)")

        # Valid BIO tags
        for tag in ["O", "B-PER", "I-PER", "B-AMOUNT", "I-AMOUNT", "B-LOCATION"]:
            if not _is_valid_bio_tag(tag):
                return _fail(name, f"Should accept valid tag: {tag}")

        return _pass(name, "all 6 validation cases correct")

    except Exception as exc:
        return _fail(name, f"Exception: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 2: BIO label preservation (no global PER→PERSON conversion)
# ─────────────────────────────────────────────────────────────────────────────

def test_bio_label_preservation():
    name = "BIO label preservation"
    try:
        from ml.training.prepare_data import normalize_and_split_data

        test_records = [
            {"tokens": ["Rohit", "Kumar"], "tags": ["B-PER", "I-PER"]},
            {"tokens": ["Delhi"], "tags": ["B-LOCATION"]},
            {"tokens": ["50000"], "tags": ["B-AMOUNT"]},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            raw_file = Path(tmpdir) / "ner_dataset.jsonl"
            proc_dir = Path(tmpdir) / "processed"

            with open(raw_file, "w") as f:
                for rec in test_records:
                    f.write(json.dumps(rec) + "\n")

            report = normalize_and_split_data(
                raw_file, proc_dir,
                train_ratio=1.0, val_ratio=0.0, test_ratio=0.0,
                require_real_data=True,
            )

            # Load train.jsonl and check labels are unchanged
            train_path = proc_dir / "train.jsonl"
            if not train_path.exists():
                return _fail(name, "train.jsonl not created")

            loaded = []
            with open(train_path) as f:
                for line in f:
                    loaded.append(json.loads(line.strip()))

            all_tags = [t for r in loaded for t in r["tags"]]
            if "B-PER" not in all_tags:
                return _fail(name, "B-PER was lost or converted — expected B-PER in output")
            if "B-PERSON" in all_tags:
                return _fail(name, "B-PER was incorrectly converted to B-PERSON")
            if "I-PER" not in all_tags:
                return _fail(name, "I-PER was lost")
            if "B-LOCATION" not in all_tags:
                return _fail(name, "B-LOCATION was lost")

        return _pass(name, "B-PER, I-PER, B-LOCATION preserved exactly")

    except Exception as exc:
        return _fail(name, f"Exception: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 3: HingBERT label compatibility report
# ─────────────────────────────────────────────────────────────────────────────

def test_hingbert_compatibility_report():
    name = "HingBERT label compatibility report"
    try:
        from ml.training.prepare_data import check_hingbert_compatibility, HINGBERT_LOCKED_LABELS

        # Mix of supported and unsupported labels
        sentences = [
            {"tokens": ["a", "b"], "tags": ["B-PER", "O"]},       # supported
            {"tokens": ["c"], "tags": ["B-PERSON"]},               # unsupported (PERSON vs PER)
            {"tokens": ["d", "e"], "tags": ["B-AMOUNT", "B-ORG"]}, # AMOUNT ok, ORG unsupported
        ]

        report = check_hingbert_compatibility(sentences)

        if report["sentences_with_unsupported_labels"] != 2:
            return _fail(
                name,
                f"Expected 2 sentences with unsupported labels, got "
                f"{report['sentences_with_unsupported_labels']}"
            )

        unsupported = report["unsupported_labels"]
        if "B-PERSON" not in unsupported:
            return _fail(name, "B-PERSON should be flagged as unsupported")
        if "B-ORG" not in unsupported:
            return _fail(name, "B-ORG should be flagged as unsupported")
        if "B-PER" in unsupported:
            return _fail(name, "B-PER should NOT be flagged — it is in the locked set")

        # Verify locked set is correct
        if "B-PER" not in HINGBERT_LOCKED_LABELS:
            return _fail(name, "HINGBERT_LOCKED_LABELS must contain B-PER")
        if "B-PERSON" in HINGBERT_LOCKED_LABELS:
            return _fail(name, "HINGBERT_LOCKED_LABELS must NOT contain B-PERSON")
        if len(HINGBERT_LOCKED_LABELS) != 18:
            return _fail(name, f"Expected 18 locked labels, got {len(HINGBERT_LOCKED_LABELS)}")

        return _pass(name, f"2 unsupported labels detected, locked set has 18 labels")

    except Exception as exc:
        return _fail(name, f"Exception: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 4: CRF checkpoint loading
# ─────────────────────────────────────────────────────────────────────────────

def test_crf_loading():
    name = "CRF checkpoint loading"
    try:
        from ml.crf_model import CRFInferenceEngine

        crf_path = BACKEND_DIR / "artifacts" / "crf" / "crf_model.pkl"
        if not crf_path.exists():
            return _fail(name, f"Checkpoint not found: {crf_path}")

        engine = CRFInferenceEngine()
        ok = engine.load(crf_path)
        if not ok:
            return _fail(name, "load() returned False")
        if not engine.loaded:
            return _fail(name, "engine.loaded is False after load()")
        if not hasattr(engine.model, "predict"):
            return _fail(name, "Loaded model has no predict() method")

        classes = getattr(engine.model, "classes_", None)
        if classes is None:
            return _fail(name, "CRF model has no classes_ attribute")

        return _pass(name, f"CRF loaded, {len(classes)} classes: {list(classes)[:5]}...")

    except Exception as exc:
        return _fail(name, f"Exception: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 5: HingBERT checkpoint loading
# ─────────────────────────────────────────────────────────────────────────────

def test_hingbert_loading():
    name = "HingBERT checkpoint loading"
    try:
        from ml.hingbert_model import HingBERTInferenceEngine

        hingbert_dir = BACKEND_DIR / "artifacts" / "hingbert"
        if not hingbert_dir.exists():
            return _fail(name, f"Checkpoint directory not found: {hingbert_dir}")

        engine = HingBERTInferenceEngine()
        ok = engine.load(hingbert_dir)

        if not ok:
            return _fail(name, "load() returned False — check PyTorch/transformers install")
        if not engine.loaded:
            return _fail(name, "engine.loaded is False after load()")

        num_labels = len(engine.id2label)
        if num_labels == 0:
            return _fail(name, "id2label is empty — config.json may be missing label mappings")
        if num_labels != 18:
            return _fail(name, f"Expected 18 labels, got {num_labels}")

        return _pass(name, f"HingBERT loaded, {num_labels} labels, device={engine.device}")

    except Exception as exc:
        return _fail(name, f"Exception: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 6: CyberDrishtiLM checkpoint loading
# ─────────────────────────────────────────────────────────────────────────────

def test_cdlm_loading():
    name = "CyberDrishtiLM checkpoint loading"
    try:
        from ml.cyberdrishtilm_model import CyberDrishtiLMInferenceEngine

        cdlm_dir = BACKEND_DIR / "artifacts" / "cyberdrishtilm"
        if not cdlm_dir.exists():
            return _fail(name, f"Checkpoint directory not found: {cdlm_dir}")

        engine = CyberDrishtiLMInferenceEngine()
        ok = engine.load(cdlm_dir)

        if not ok:
            return _fail(name, "load() returned False")
        if not engine.loaded:
            return _fail(name, "engine.loaded is False")
        if engine.model is None:
            return _fail(name, "engine.model is None after load()")

        expected_status = CyberDrishtiLMInferenceEngine.STATUS_LABEL_MAP_UNKNOWN
        if engine.status != expected_status:
            # Could be READY if label2id was somehow added — that's fine too
            if engine.status != CyberDrishtiLMInferenceEngine.STATUS_READY:
                return _fail(
                    name,
                    f"Expected status LABEL_MAP_UNKNOWN or READY, got: {engine.status}"
                )

        return _pass(
            name,
            f"Loaded successfully. status={engine.status}, "
            f"id2label count={len(engine.id2label)}"
        )

    except Exception as exc:
        return _fail(name, f"Exception: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 7: Real CRF inference
# ─────────────────────────────────────────────────────────────────────────────

def test_crf_inference():
    name = "Real CRF inference"
    probe = "Rohit Kumar transferred Rs. 50000 to account 9876543210 via UPI from Delhi."
    try:
        from ml.crf_model import CRFInferenceEngine

        crf_path = BACKEND_DIR / "artifacts" / "crf" / "crf_model.pkl"
        engine = CRFInferenceEngine()
        ok = engine.load(crf_path)
        if not ok:
            return _fail(name, "CRF not loaded — skipping inference test")

        preds = engine.predict(probe)
        if not isinstance(preds, list):
            return _fail(name, f"predict() returned {type(preds).__name__}, expected list")

        return _pass(
            name,
            f"{len(preds)} prediction(s): "
            + ", ".join(f"[{p.entity_type}] {p.raw_value!r}" for p in preds[:3])
        )

    except Exception as exc:
        return _fail(name, f"Exception: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 8: Real HingBERT inference
# ─────────────────────────────────────────────────────────────────────────────

def test_hingbert_inference():
    name = "Real HingBERT inference"
    probe = "Rohit Kumar transferred Rs. 50000 to account 9876543210 via UPI from Delhi."
    try:
        from ml.hingbert_model import HingBERTInferenceEngine

        hingbert_dir = BACKEND_DIR / "artifacts" / "hingbert"
        engine = HingBERTInferenceEngine()
        ok = engine.load(hingbert_dir)
        if not ok:
            print(f"  ⚠ SKIP: {name} — HingBERT not loaded (torch/transformers may be missing)")
            return True  # Not a hard failure if deps missing

        preds = engine.predict(probe)
        if not isinstance(preds, list):
            return _fail(name, f"predict() returned {type(preds).__name__}, expected list")

        # Verify at least the forward pass ran (preds may be empty if confidence low)
        return _pass(
            name,
            f"Real transformer forward pass completed. {len(preds)} prediction(s): "
            + ", ".join(f"[{p.entity_type}] {p.raw_value!r}" for p in preds[:3])
        )

    except Exception as exc:
        return _fail(name, f"Exception: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 9: Real CyberDrishtiLM forward pass (transformer computes real tensors)
# ─────────────────────────────────────────────────────────────────────────────

def test_cdlm_forward_pass():
    name = "Real CyberDrishtiLM forward pass"
    probe = "Rohit Kumar transferred Rs. 50000 via UPI from Delhi account."
    try:
        from ml.cyberdrishtilm_model import CyberDrishtiLMInferenceEngine

        cdlm_dir = BACKEND_DIR / "artifacts" / "cyberdrishtilm"
        engine = CyberDrishtiLMInferenceEngine()
        ok = engine.load(cdlm_dir)
        if not ok:
            return _fail(name, "CyberDrishtiLM not loaded")
        if engine.tokenizer is None:
            return _fail(name, "BPE tokenizer not loaded (install: pip3 install tokenizers)")

        result = engine.run_verification_forward(probe)

        # Verify it's a real forward pass (not heuristics)
        if result.get("forward_pass") != "real_transformer":
            return _fail(name, f"Expected 'real_transformer', got: {result.get('forward_pass')}")

        ner_shape = result.get("ner_logits_shape")
        fraud_shape = result.get("fraud_logits_shape")

        if ner_shape is None or len(ner_shape) != 3:
            return _fail(name, f"ner_logits_shape invalid: {ner_shape}")
        if ner_shape[0] != 1:
            return _fail(name, f"Expected batch=1, got {ner_shape[0]}")
        if ner_shape[1] != 64:
            return _fail(name, f"Expected seq_len=64, got {ner_shape[1]}")
        if ner_shape[2] != 25:
            return _fail(name, f"Expected 25 NER classes (from checkpoint), got {ner_shape[2]}")

        if fraud_shape is None or fraud_shape != [1, 2]:
            return _fail(name, f"Expected fraud_logits=[1, 2], got {fraud_shape}")

        return _pass(
            name,
            f"Real transformer output: ner_logits={ner_shape}, "
            f"fraud_logits={fraud_shape}, device={result.get('device')}, "
            f"status={result.get('label_map_status')}"
        )

    except Exception as exc:
        return _fail(name, f"Exception: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 10: Production checkpoint integrity
# ─────────────────────────────────────────────────────────────────────────────

def test_checkpoint_integrity():
    name = "Production checkpoint integrity"
    try:
        mismatches = []
        for rel_path, expected_size in PRODUCTION_CHECKPOINT_SIZES.items():
            full_path = BACKEND_DIR / rel_path
            if not full_path.exists():
                mismatches.append(f"MISSING: {rel_path}")
                continue
            actual_size = os.path.getsize(full_path)
            if actual_size != expected_size:
                mismatches.append(
                    f"SIZE CHANGED: {rel_path} "
                    f"(expected={expected_size}, actual={actual_size})"
                )

        if mismatches:
            for m in mismatches:
                print(f"     {m}")
            return _fail(name, f"{len(mismatches)} checkpoint file(s) modified or missing")

        return _pass(
            name,
            f"All {len(PRODUCTION_CHECKPOINT_SIZES)} production checkpoint files intact"
        )

    except Exception as exc:
        return _fail(name, f"Exception: {exc}")


# ── Run all tests ─────────────────────────────────────────────────────────────

TESTS = [
    ("Dataset validation",                  test_dataset_validation),
    ("BIO label preservation",              test_bio_label_preservation),
    ("HingBERT label compatibility report", test_hingbert_compatibility_report),
    ("CRF checkpoint loading",              test_crf_loading),
    ("HingBERT checkpoint loading",         test_hingbert_loading),
    ("CyberDrishtiLM checkpoint loading",   test_cdlm_loading),
    ("Real CRF inference",                  test_crf_inference),
    ("Real HingBERT inference",             test_hingbert_inference),
    ("Real CyberDrishtiLM forward pass",    test_cdlm_forward_pass),
    ("Production checkpoint integrity",     test_checkpoint_integrity),
]


def main() -> int:
    print("=" * 72)
    print("  CyberDrishti AI — ML Pipeline Verification Suite")
    print("  (No training, no file modifications)")
    print("=" * 72)
    print()

    passed = 0
    failed = 0
    skipped = 0

    for test_name, test_fn in TESTS:
        print(f"[{TESTS.index((test_name, test_fn)) + 1:2d}] {test_name}")
        try:
            result = test_fn()
            if result is True:
                passed += 1
            elif result is None:
                skipped += 1
            else:
                failed += 1
        except Exception as exc:
            _fail(test_name, f"Unhandled exception: {exc}")
            failed += 1
        print()

    print("=" * 72)
    print(f"  Results: {passed} passed | {failed} failed | {skipped} skipped")
    print("=" * 72)

    if failed > 0:
        print(f"\n❌ {failed} test(s) failed. Fix issues before training.")
        return 1
    else:
        print("\n✅ All tests passed. Ready to begin real training.")
        print("\nNext step:")
        print("  1. Place your dataset at: backend/ml/data/raw/ner_dataset.jsonl")
        print("  2. Run: cd backend && python3 -m ml.training.prepare_data")
        print("  3. Then: cd backend && python3 -m ml.training.train --model crf --epochs 200")
        return 0


if __name__ == "__main__":
    sys.exit(main())
