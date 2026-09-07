#!/usr/bin/env python3
"""
CyberDrishti AI — CRF Baseline Model Training
Trains a Conditional Random Field (CRF) model for NER as a baseline comparison.

Usage:
    python train_crf.py --data_dir training_data --output_path artifacts/crf/crf_model.pkl
"""

import argparse
import pickle
import json
from pathlib import Path
from typing import List, Tuple
from sklearn_crfsuite import CRF
from sklearn_crfsuite.metrics import flat_classification_report
import re


def word_features(sent: List[str], i: int) -> dict:
    """Extract hand-crafted features for CRF from a word at position i."""
    word = sent[i]

    features = {
        'bias': 1.0,
        'word.lower()': word.lower(),
        'word[-3:]': word[-3:],
        'word[-2:]': word[-2:],
        'word.isupper()': word.isupper(),
        'word.istitle()': word.istitle(),
        'word.isdigit()': word.isdigit(),
        'word.isalpha()': word.isalpha(),
        'word.isalnum()': word.isalnum(),
        'word.length': len(word),
    }

    # Pattern features
    features['has.digit'] = bool(re.search(r'\d', word))
    features['has.hyphen'] = '-' in word
    features['has.dot'] = '.' in word
    features['has.@'] = '@' in word
    features['has.+91'] = word.startswith('+91')
    features['has.rupee'] = '₹' in word or word.lower() in ['rs', 'inr']

    # Position features
    if i > 0:
        word_prev = sent[i-1]
        features.update({
            '-1:word.lower()': word_prev.lower(),
            '-1:word.istitle()': word_prev.istitle(),
            '-1:word.isupper()': word_prev.isupper(),
            '-1:word.isdigit()': word_prev.isdigit(),
        })
    else:
        features['BOS'] = True  # Beginning of sentence

    if i < len(sent) - 1:
        word_next = sent[i+1]
        features.update({
            '+1:word.lower()': word_next.lower(),
            '+1:word.istitle()': word_next.istitle(),
            '+1:word.isupper()': word_next.isupper(),
            '+1:word.isdigit()': word_next.isdigit(),
        })
    else:
        features['EOS'] = True  # End of sentence

    return features


def sent2features(sent: List[str]) -> List[dict]:
    """Convert a sentence to feature dictionaries for each word."""
    return [word_features(sent, i) for i in range(len(sent))]


def sent2labels(tags: List[str]) -> List[str]:
    """Extract labels from BIO tags."""
    return tags


def load_conll_data(file_path: Path) -> Tuple[List[List[str]], List[List[str]]]:
    """Load training data — supports .jsonl (tokens/ner_tags) or CoNLL tab-separated .txt."""
    sentences = []
    labels = []

    # Try jsonl first (primary format used by generate_ner_training_data.py)
    jsonl_path = file_path.with_suffix('.jsonl') if file_path.suffix == '.txt' else file_path
    if jsonl_path.exists():
        import json
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                tokens = record.get('tokens', [])
                tags = record.get('ner_tags', ['O'] * len(tokens))
                if tokens:
                    sentences.append(tokens)
                    labels.append(tags)
        return sentences, labels

    # Fallback: CoNLL tab-separated format
    current_sent = []
    current_labels = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                if current_sent:
                    sentences.append(current_sent)
                    labels.append(current_labels)
                    current_sent = []
                    current_labels = []
            else:
                parts = line.split('\t')
                if len(parts) == 2:
                    word, tag = parts
                    current_sent.append(word)
                    current_labels.append(tag)

        # Handle last sentence
        if current_sent:
            sentences.append(current_sent)
            labels.append(current_labels)

    return sentences, labels


def main():
    parser = argparse.ArgumentParser(description="Train CRF baseline model")
    parser.add_argument("--data_dir", type=str, required=True, help="Directory containing train.txt and test.txt")
    parser.add_argument("--output_path", type=str, required=True, help="Path to save trained CRF model (.pkl)")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("="*60)
    print("🧠 CyberDrishti AI — CRF Baseline Training")
    print("="*60)

    # Load training data
    print(f"\n📂 Loading training data from {data_dir / 'train.txt'}...")
    train_sents, train_labels = load_conll_data(data_dir / 'train.txt')
    print(f"✅ Loaded {len(train_sents)} training sentences")

    # Load test data
    print(f"\n📂 Loading test data from {data_dir / 'test.txt'}...")
    test_sents, test_labels = load_conll_data(data_dir / 'test.txt')
    print(f"✅ Loaded {len(test_sents)} test sentences")

    # Extract features
    print("\n🔧 Extracting hand-crafted features...")
    X_train = [sent2features(s) for s in train_sents]
    y_train = [sent2labels(l) for l in train_labels]

    X_test = [sent2features(s) for s in test_sents]
    y_test = [sent2labels(l) for l in test_labels]

    print(f"✅ Feature extraction complete")
    print(f"   Training samples: {len(X_train)}")
    print(f"   Test samples: {len(X_test)}")

    # Train CRF model
    print("\n🚀 Training CRF model...")
    crf = CRF(
        algorithm='lbfgs',
        c1=0.1,
        c2=0.1,
        max_iterations=100,
        all_possible_transitions=True,
        verbose=True
    )

    crf.fit(X_train, y_train)
    print("\n✅ Training complete!")

    # Evaluate on test set
    print("\n📊 Evaluating on test set...")
    y_pred = crf.predict(X_test)

    # Calculate metrics
    report = flat_classification_report(y_test, y_pred, digits=4)
    print("\n" + report)

    # Parse report to extract overall metrics
    lines = report.strip().split('\n')
    metrics = {}
    for line in lines:
        if 'micro avg' in line or 'weighted avg' in line:
            parts = line.split()
            if len(parts) >= 5:
                avg_type = parts[0] + ' ' + parts[1]
                metrics[avg_type] = {
                    'precision': float(parts[2]),
                    'recall': float(parts[3]),
                    'f1': float(parts[4]),
                    'support': int(parts[5]) if len(parts) > 5 else 0
                }

    # Save model
    print(f"\n💾 Saving model to {output_path}...")
    with open(output_path, 'wb') as f:
        pickle.dump(crf, f)
    print("✅ Model saved!")

    # Save evaluation metrics
    metrics_path = output_path.parent / 'eval_metrics.json'
    eval_metrics = {
        'model': 'CRF',
        'test_samples': len(test_sents),
        'precision': metrics.get('weighted avg', {}).get('precision', 0.0),
        'recall': metrics.get('weighted avg', {}).get('recall', 0.0),
        'f1': metrics.get('weighted avg', {}).get('f1', 0.0),
        'full_report': report
    }

    with open(metrics_path, 'w') as f:
        json.dump(eval_metrics, f, indent=2)
    print(f"✅ Metrics saved to {metrics_path}")

    print("\n" + "="*60)
    print("🎉 CRF Training Complete!")
    print("="*60)
    print(f"\n📁 Model: {output_path}")
    print(f"📊 Metrics: {metrics_path}")
    print(f"\n🎯 Test F1 Score: {eval_metrics['f1']:.4f}")
    print()


if __name__ == "__main__":
    main()
