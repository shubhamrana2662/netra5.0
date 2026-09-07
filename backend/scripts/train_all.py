#!/usr/bin/env python3
"""
CyberDrishti AI — Master Training Orchestrator
Runs the full ML pipeline: synthetic data → train all 3 models → compare → select best.

Usage:
    python train_all.py --synthetic 8000 --real_data ./real_labeled_data --epochs 10
"""

import argparse
import subprocess
import sys
from pathlib import Path
import json
import time

def run_command(cmd: list[str], description: str):
    """Run a subprocess command with nice logging."""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}\n")

    start = time.time()
    result = subprocess.run(cmd, capture_output=False)
    elapsed = time.time() - start

    if result.returncode != 0:
        print(f"\n❌ Failed after {elapsed:.1f}s. Exit code: {result.returncode}")
        sys.exit(1)
    else:
        print(f"\n✅ Completed in {elapsed:.1f}s")
    return result

def main():
    parser = argparse.ArgumentParser(description="CyberDrishti AI — Full Training Pipeline")
    parser.add_argument("--synthetic", type=int, default=8000, help="Number of synthetic sentences to generate")
    parser.add_argument("--real_data", type=str, default=None, help="Path to real labeled data directory (optional)")
    parser.add_argument("--epochs", type=int, default=10, help="Training epochs for transformer models")
    parser.add_argument("--batch_size", type=int, default=16, help="Batch size")
    parser.add_argument("--output_dir", type=str, default="artifacts", help="Output directory for all models")
    parser.add_argument("--skip_synthetic", action="store_true", help="Skip synthetic data generation")
    parser.add_argument("--gpu", action="store_true", help="Enable GPU training (requires CUDA)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    training_data_dir = output_dir / "training_data"
    training_data_dir.mkdir(exist_ok=True)

    # ── PHASE 1: Generate Synthetic Data ──────────────────────────────────────
    if not args.skip_synthetic:
        run_command([
            sys.executable,
            "nlp/generate_ner_training_data.py",
            "--output_dir", str(training_data_dir),
            "--n_sentences", str(args.synthetic),
        ], f"Generating {args.synthetic} synthetic Hinglish NER sentences")
    else:
        print("\n⏭️  Skipping synthetic data generation")

    # ── PHASE 2: Train CyberDrishtiLM ─────────────────────────────────────────
    cdlm_output = output_dir / "cyberdrishtilm"
    run_command([
        sys.executable,
        "nlp/cyberdrishtilm/train.py",
        "--data_dir", str(training_data_dir),
        "--output_dir", str(cdlm_output),
        "--epochs", str(args.epochs),
        "--batch_size", str(args.batch_size),
        "--device", "cuda" if args.gpu else "cpu",
    ], "Training CyberDrishtiLM (custom transformer)")

    # ── PHASE 3: Fine-tune HingBERT ───────────────────────────────────────────
    hingbert_output = output_dir / "hingbert"
    run_command([
        sys.executable,
        "nlp/hingbert/finetune.py",
        "--data_dir", str(training_data_dir),
        "--output_dir", str(hingbert_output),
        "--epochs", str(args.epochs),
        "--batch_size", str(args.batch_size),
        "--device", "cuda" if args.gpu else "cpu",
    ], "Fine-tuning HingBERT on CyberDrishti NER task")

    # ── PHASE 4: Train CRF Baseline ───────────────────────────────────────────
    crf_output = output_dir / "crf"
    crf_output.mkdir(exist_ok=True)
    run_command([
        sys.executable,
        "nlp/train_crf.py",
        "--data_dir", str(training_data_dir),
        "--output_path", str(crf_output / "crf_model.pkl"),
    ], "Training CRF baseline model")

    # ── PHASE 5: Real-data Validation (if provided) ───────────────────────────
    if args.real_data:
        real_data_path = Path(args.real_data)
        if not real_data_path.exists():
            print(f"\n⚠️  Real data path {args.real_data} not found, skipping validation")
        else:
            run_command([
                sys.executable,
                "nlp/validate_real_data.py",
                "--real_data", str(real_data_path),
                "--cdlm_model", str(cdlm_output),
                "--hingbert_model", str(hingbert_output),
                "--crf_model", str(crf_output / "crf_model.pkl"),
                "--output_report", str(output_dir / "real_data_validation.json"),
            ], "Validating all models on real labeled data")
    else:
        print("\n⏭️  No real data provided, skipping validation")

    # ── PHASE 6: Model Comparison Report ──────────────────────────────────────
    run_command([
        sys.executable,
        "nlp/compare_models.py",
        "--cdlm_metrics", str(cdlm_output / "eval_metrics.json"),
        "--hingbert_metrics", str(hingbert_output / "eval_metrics.json"),
        "--crf_metrics", str(crf_output / "eval_metrics.json"),
        "--output_report", str(output_dir / "model_comparison.json"),
        "--output_table", str(output_dir / "model_comparison_table.txt"),
    ], "Generating model comparison report")

    # ── Final Summary ─────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("🎉 TRAINING PIPELINE COMPLETE")
    print("="*60)
    print(f"\n📁 All artifacts saved to: {output_dir.absolute()}")
    print(f"\n📊 Model Comparison Report: {output_dir / 'model_comparison_table.txt'}")
    print(f"📈 Real Data Validation: {output_dir / 'real_data_validation.json'}")
    print("\n✅ Next steps:")
    print("   1. Review model_comparison_table.txt to select the best model")
    print("   2. Deploy the winning model to api/routes/evidence.py")
    print("   3. Start the FastAPI backend: uvicorn main:app --reload")
    print("   4. Launch the Next.js frontend: cd frontend && npm run dev")
    print("\n🚀 CyberDrishti AI is ready for investigation!\n")

if __name__ == "__main__":
    main()
