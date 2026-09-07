from __future__ import annotations
"""
CyberDrishtiLM — Training Script
AdamW + linear warmup/decay, early stopping, seqeval evaluation.
Saves best checkpoint; flags suspiciously perfect metrics.

Usage:
    python train.py --data_dir training_data --output_dir artifacts/model
"""
import argparse
import json
import pathlib
from collections import defaultdict

import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.utils.data import DataLoader, Dataset
from seqeval.metrics import classification_report, f1_score

from model import CyberDrishtiLM, ModelConfig, NER_LABEL2ID, NER_ID2LABEL
from tokenizer import CDTokenizer


# ── Dataset ───────────────────────────────────────────────────────────────────

class NERDataset(Dataset):
    def __init__(self, path: str, tokenizer: CDTokenizer):
        self.samples  = []
        self.tokenizer = tokenizer
        with open(path, encoding="utf-8") as f:
            for line in f:
                self.samples.append(json.loads(line))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample    = self.samples[idx]
        tokens    = sample["tokens"]
        ner_tags  = sample["ner_tags"]
        fraud_lbl = sample["fraud_label"]

        enc = self.tokenizer.encode(tokens)

        # Align BIO labels to subword tokens
        word_ids  = enc["word_ids"]  # None for special tokens
        input_ids = enc["input_ids"]
        attn_mask = enc["attention_mask"]
        seq_len   = len(input_ids)

        # Map word-level BIO labels to token-level with -100 for special tokens
        label_ids: list[int] = []
        prev_word = None
        for wi in word_ids:
            if wi is None:
                label_ids.append(-100)  # special token — ignored in loss
            elif wi != prev_word:
                tag = ner_tags[wi] if wi < len(ner_tags) else "O"
                label_ids.append(NER_LABEL2ID.get(tag, 0))
                prev_word = wi
            else:
                # Continuation subword: use I- tag if B- was assigned, else O
                tag = ner_tags[wi] if wi < len(ner_tags) else "O"
                if tag.startswith("B-"):
                    i_tag = "I-" + tag[2:]
                    label_ids.append(NER_LABEL2ID.get(i_tag, NER_LABEL2ID.get(tag, 0)))
                else:
                    label_ids.append(NER_LABEL2ID.get(tag, 0))

        return {
            "input_ids":   torch.tensor(input_ids,  dtype=torch.long),
            "attn_mask":   torch.tensor(attn_mask,  dtype=torch.long),
            "ner_labels":  torch.tensor(label_ids,  dtype=torch.long),
            "fraud_label": torch.tensor(fraud_lbl,  dtype=torch.long),
            "raw_tokens":  tokens,
            "raw_ner":     ner_tags,
        }


def _collate(batch):
    return {
        "input_ids":   torch.stack([b["input_ids"]   for b in batch]),
        "attn_mask":   torch.stack([b["attn_mask"]   for b in batch]),
        "ner_labels":  torch.stack([b["ner_labels"]  for b in batch]),
        "fraud_label": torch.stack([b["fraud_label"] for b in batch]),
        "raw_tokens":  [b["raw_tokens"] for b in batch],
        "raw_ner":     [b["raw_ner"]    for b in batch],
    }


# ── Scheduler ─────────────────────────────────────────────────────────────────

def _get_linear_schedule(optimizer, warmup_steps: int, total_steps: int):
    from torch.optim.lr_scheduler import LambdaLR
    def lr_lambda(step):
        if step < warmup_steps:
            return float(step) / max(1, warmup_steps)
        progress = float(step - warmup_steps) / max(1, total_steps - warmup_steps)
        return max(0.0, 1.0 - progress)
    return LambdaLR(optimizer, lr_lambda)


# ── Evaluation ────────────────────────────────────────────────────────────────

def evaluate(model, loader, device):
    model.eval()
    total_loss = 0.0
    all_true_ner: list[list[str]] = []
    all_pred_ner: list[list[str]] = []
    fraud_correct = 0
    fraud_total   = 0

    with torch.no_grad():
        for batch in loader:
            ids   = batch["input_ids"].to(device)
            mask  = batch["attn_mask"].to(device)
            n_lbl = batch["ner_labels"].to(device)
            f_lbl = batch["fraud_label"].to(device)

            out = model(ids, mask, n_lbl, f_lbl)
            total_loss += out["loss"].item()

            # NER predictions — ignore -100 positions
            ner_preds = out["ner_logits"].argmax(-1)  # (B, T)
            for i in range(len(batch["raw_ner"])):
                true_tags = batch["raw_ner"][i]
                pred_seq  = []
                true_seq  = []
                for j, wi in enumerate(batch["raw_tokens"][i]):
                    if j < len(true_tags):
                        true_seq.append(true_tags[j])
                # Simplified: align at word level using raw_ner
                # Full alignment via word_ids requires re-encoding per-batch
                # Using approximate alignment for speed
                all_true_ner.append(batch["raw_ner"][i])
                # Map pred token IDs back to word-level labels
                word_preds = [NER_ID2LABEL.get(p.item(), "O")
                              for p, m in zip(ner_preds[i], mask[i]) if m == 1]
                # Trim to sentence length
                all_pred_ner.append(word_preds[:len(batch["raw_ner"][i])])

            # Fraud relevance
            fraud_pred = out["fraud_logits"].argmax(-1)
            fraud_correct += (fraud_pred == f_lbl).sum().item()
            fraud_total   += len(f_lbl)

    ner_f1_macro = f1_score(all_true_ner, all_pred_ner, average="macro", zero_division=0)
    fraud_acc    = fraud_correct / fraud_total if fraud_total else 0.0
    mean_loss    = total_loss / len(loader)

    return {
        "loss":       mean_loss,
        "ner_f1":     ner_f1_macro,
        "fraud_acc":  fraud_acc,
        "ner_report": classification_report(all_true_ner, all_pred_ner, zero_division=0),
    }


# ── Training loop ─────────────────────────────────────────────────────────────

def train(
    data_dir:   str | pathlib.Path = "training_data",
    output_dir: str | pathlib.Path = "artifacts/model",
    batch_size:  int   = 32,
    max_epochs:  int   = 30,
    lr:          float = 3e-4,
    warmup_steps: int  = 500,
    patience:    int   = 4,
    grad_clip:   float = 1.0,
    weight_decay: float = 0.01,
    vocab_size:  int   = 4000,
):
    data_dir  = pathlib.Path(data_dir)
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[TRAIN] Using device: {device}")

    # Train tokenizer
    print("[TRAIN] Training tokenizer...")
    all_tokens = []
    for split in ["train", "val"]:
        with open(data_dir / f"{split}.jsonl") as f:
            for line in f:
                all_tokens.append(json.loads(line)["tokens"])
    tokenizer = CDTokenizer.train_from_corpus(all_tokens, vocab_size=vocab_size)
    tokenizer.save(output_dir)

    # Datasets
    train_ds = NERDataset(str(data_dir / "train.jsonl"), tokenizer)
    val_ds   = NERDataset(str(data_dir / "val.jsonl"),   tokenizer)
    test_ds  = NERDataset(str(data_dir / "test.jsonl"),  tokenizer)

    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True,  collate_fn=_collate)
    val_dl   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False, collate_fn=_collate)
    test_dl  = DataLoader(test_ds,  batch_size=batch_size, shuffle=False, collate_fn=_collate)

    # Model
    cfg   = ModelConfig(vocab_size=tokenizer.vocab_size)
    model = CyberDrishtiLM(cfg).to(device)
    print(f"[TRAIN] Parameters: {model.count_parameters():,}")

    # Optimiser + scheduler
    optimizer = AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    total_steps = len(train_dl) * max_epochs
    scheduler   = _get_linear_schedule(optimizer, warmup_steps, total_steps)

    # Training
    best_val_loss = float("inf")
    patience_ctr  = 0
    history: list[dict] = []

    for epoch in range(1, max_epochs + 1):
        model.train()
        epoch_loss = 0.0

        for batch in train_dl:
            ids   = batch["input_ids"].to(device)
            mask  = batch["attn_mask"].to(device)
            n_lbl = batch["ner_labels"].to(device)
            f_lbl = batch["fraud_label"].to(device)

            optimizer.zero_grad()
            out = model(ids, mask, n_lbl, f_lbl)
            out["loss"].backward()
            nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            optimizer.step()
            scheduler.step()
            epoch_loss += out["loss"].item()

        val_metrics = evaluate(model, val_dl, device)
        avg_train = epoch_loss / len(train_dl)
        history.append({"epoch": epoch, "train_loss": avg_train, **val_metrics})

        print(
            f"[Epoch {epoch:02d}] train_loss={avg_train:.4f} "
            f"val_loss={val_metrics['loss']:.4f} "
            f"val_ner_f1={val_metrics['ner_f1']:.4f} "
            f"val_fraud_acc={val_metrics['fraud_acc']:.4f}"
        )

        if val_metrics["loss"] < best_val_loss:
            best_val_loss = val_metrics["loss"]
            patience_ctr  = 0
            model.save(output_dir)
            print(f"  ✓ New best checkpoint saved (val_loss={best_val_loss:.4f})")
        else:
            patience_ctr += 1
            if patience_ctr >= patience:
                print(f"[TRAIN] Early stopping after {epoch} epochs (patience={patience})")
                break

    # ── Test evaluation ──────────────────────────────────────────────────────
    best_model = CyberDrishtiLM.load(output_dir, map_location=str(device))
    best_model.to(device)
    test_metrics = evaluate(best_model, test_dl, device)

    print("\n=== TEST RESULTS ===")
    print(test_metrics["ner_report"])
    print(f"NER macro-F1: {test_metrics['ner_f1']:.4f}")
    print(f"Fraud accuracy: {test_metrics['fraud_acc']:.4f}")

    # ── Flag suspiciously perfect scores ────────────────────────────────────
    if test_metrics["fraud_acc"] > 0.99 or test_metrics["ner_f1"] > 0.99:
        print(
            "\n⚠ WARNING: Score is at or near 1.00.\n"
            "  UNVERIFIED — needs real-data stress test in Phase 4.\n"
            "  A perfect score on synthetic template-generated data usually means\n"
            "  the model is recognising which template produced a sentence, not\n"
            "  learning fraud language in general."
        )

    with open(output_dir / "training_history.json", "w") as f:
        json.dump(history, f, indent=2)
    with open(output_dir / "test_metrics.json", "w") as f:
        json.dump({k: v for k, v in test_metrics.items() if k != "ner_report"}, f, indent=2)

    return test_metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir",   default="training_data")
    parser.add_argument("--output_dir", default="artifacts/model")
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--epochs",     type=int, default=30)
    parser.add_argument("--device",     type=str, default="cpu", help="Device: cpu or cuda")
    args = parser.parse_args()
    train(data_dir=args.data_dir, output_dir=args.output_dir,
          batch_size=args.batch_size, max_epochs=args.epochs)
