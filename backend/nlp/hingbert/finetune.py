from __future__ import annotations
"""
CyberDrishtiLM — HingBERT Fine-Tune Script (Phase 3)
Fine-tunes L3Cube-Pune/hindi-bert-v2 on the same labeled corpus used in Phase 2.
Produces a side-by-side comparison table: CyberDrishtiLM vs HingBERT.

Usage:
    python finetune.py --data_dir training_data --output_dir artifacts/hingbert_model
"""
import argparse
import json
import pathlib

import torch
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    DataCollatorForTokenClassification,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback,
)
from seqeval.metrics import classification_report, f1_score
import numpy as np


# Same label set as CyberDrishtiLM Phase 2
NER_LABEL2ID: dict[str, int] = {
    "O":          0,
    "B-PER":      1,  "I-PER":      2,
    "B-PHONE":    3,
    "B-UPI":      4,
    "B-ACCOUNT":  5,
    "B-AMOUNT":   6,
    "B-BANK":     7,  "I-BANK":     8,
    "B-OTP":      9,
    "B-EMAIL":   10,
    "B-URL":     11,  "I-URL":     12,
    "B-IFSC":    13,
    "B-LOCATION":14,  "I-LOCATION":15,
    "B-KEYWORD": 16,  "I-KEYWORD": 17,
}
NER_ID2LABEL = {v: k for k, v in NER_LABEL2ID.items()}
NUM_LABELS   = len(NER_LABEL2ID)

HINGBERT_CHECKPOINT = "l3cube-pune/hindi-bert-v2"


# ── Dataset ───────────────────────────────────────────────────────────────────

class HingBERTDataset(Dataset):
    def __init__(self, path: str, tokenizer, max_length: int = 128):
        self.samples    = []
        self.tokenizer  = tokenizer
        self.max_length = max_length
        with open(path, encoding="utf-8") as f:
            for line in f:
                self.samples.append(json.loads(line))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s          = self.samples[idx]
        tokens     = s["tokens"]
        word_labels = [NER_LABEL2ID.get(t, 0) for t in s["ner_tags"]]
        fraud_lbl  = s["fraud_label"]

        enc = self.tokenizer(
            tokens,
            is_split_into_words=True,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
        )
        word_ids    = enc.word_ids()
        label_ids   = []
        prev_word   = None
        for wi in word_ids:
            if wi is None:
                label_ids.append(-100)
            elif wi != prev_word:
                label_ids.append(word_labels[wi] if wi < len(word_labels) else 0)
                prev_word = wi
            else:
                # Continuation token — set to I- variant or -100
                tag = s["ner_tags"][wi] if wi < len(s["ner_tags"]) else "O"
                if tag.startswith("B-"):
                    i_tag = "I-" + tag[2:]
                    label_ids.append(NER_LABEL2ID.get(i_tag, NER_LABEL2ID.get(tag, 0)))
                else:
                    label_ids.append(-100)

        return {
            "input_ids":       enc["input_ids"],
            "attention_mask":  enc["attention_mask"],
            "labels":          label_ids,
            "fraud_label":     fraud_lbl,
            "raw_ner":         s["ner_tags"],
        }


# ── Metrics ────────────────────────────────────────────────────────────────────

def make_compute_metrics(eval_dataset):
    """Closure so we can access raw NER labels."""
    def _compute(p):
        predictions, labels = p
        preds = np.argmax(predictions, axis=2)

        true_seqs, pred_seqs = [], []
        for pred_row, lbl_row, sample in zip(preds, labels, eval_dataset.samples):
            true_seq, pred_seq = [], []
            raw_ner = sample["ner_tags"]
            wi_ptr  = 0
            for pred_id, lbl_id in zip(pred_row, lbl_row):
                if lbl_id == -100:
                    continue
                true_seq.append(raw_ner[wi_ptr] if wi_ptr < len(raw_ner) else "O")
                pred_seq.append(NER_ID2LABEL.get(int(pred_id), "O"))
                wi_ptr += 1
            true_seqs.append(true_seq)
            pred_seqs.append(pred_seq)

        return {
            "ner_f1_macro": f1_score(true_seqs, pred_seqs, average="macro", zero_division=0),
        }
    return _compute


# ── Fine-tuning ────────────────────────────────────────────────────────────────

def finetune(
    data_dir:   str | pathlib.Path = "training_data",
    output_dir: str | pathlib.Path = "artifacts/hingbert_model",
    cyberdrishti_metrics_path: str | None = None,
    max_length: int   = 128,
    batch_size: int   = 16,
    num_epochs: int   = 5,
    lr:         float = 2e-5,
    weight_decay: float = 0.01,
):
    data_dir   = pathlib.Path(data_dir)
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[HingBERT] Loading tokenizer from {HINGBERT_CHECKPOINT}")
    tokenizer = AutoTokenizer.from_pretrained(HINGBERT_CHECKPOINT)

    train_ds = HingBERTDataset(str(data_dir / "train.jsonl"), tokenizer, max_length)
    val_ds   = HingBERTDataset(str(data_dir / "val.jsonl"),   tokenizer, max_length)
    test_ds  = HingBERTDataset(str(data_dir / "test.jsonl"),  tokenizer, max_length)

    model = AutoModelForTokenClassification.from_pretrained(
        HINGBERT_CHECKPOINT,
        num_labels=NUM_LABELS,
        id2label=NER_ID2LABEL,
        label2id=NER_LABEL2ID,
        ignore_mismatched_sizes=True,
    )

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=lr,
        weight_decay=weight_decay,
        warmup_ratio=0.1,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="ner_f1_macro",
        greater_is_better=True,
        logging_steps=50,
        report_to="none",
        fp16=torch.cuda.is_available(),
    )

    data_collator = DataCollatorForTokenClassification(tokenizer, pad_to_multiple_of=8)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=data_collator,
        compute_metrics=make_compute_metrics(val_ds),
        callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
    )

    print("[HingBERT] Starting fine-tuning...")
    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    # ── Test evaluation ───────────────────────────────────────────────────────
    test_results = trainer.evaluate(test_ds)
    ner_f1 = test_results.get("eval_ner_f1_macro", 0.0)
    print(f"\n[HingBERT] Test NER macro-F1: {ner_f1:.4f}")
    with open(output_dir / "test_metrics.json", "w") as f:
        json.dump(test_results, f, indent=2)

    # ── Comparison table ──────────────────────────────────────────────────────
    if cyberdrishti_metrics_path and pathlib.Path(cyberdrishti_metrics_path).exists():
        with open(cyberdrishti_metrics_path) as f:
            cd_metrics = json.load(f)
        print("\n=== MODEL COMPARISON (Phase 3) ===")
        print(f"{'Metric':<30} {'CyberDrishtiLM':>18} {'HingBERT fine-tune':>20}")
        print("-" * 70)
        print(f"{'NER macro-F1 (test)':<30} {cd_metrics.get('ner_f1', 'N/A'):>18} {ner_f1:>20.4f}")
        fraud_acc_cd = cd_metrics.get('fraud_acc', 'N/A')
        print(f"{'Fraud relevance acc.':<30} {str(fraud_acc_cd):>18} {'N/A (head not trained)':>20}")
        print("(Both evaluated on identical synthetic test split)")

    return test_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir",              default="training_data")
    parser.add_argument("--output_dir",            default="artifacts/hingbert_model")
    parser.add_argument("--cyberdrishti_metrics",  default="artifacts/model/test_metrics.json")
    parser.add_argument("--epochs", type=int,      default=5)
    parser.add_argument("--batch_size", type=int,  default=16, help="Batch size (ignored, using Trainer defaults)")
    parser.add_argument("--device", type=str,      default="cpu", help="Device: cpu or cuda (ignored, Trainer auto-detects)")
    args = parser.parse_args()
    finetune(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        cyberdrishti_metrics_path=args.cyberdrishti_metrics,
        num_epochs=args.epochs,
    )
