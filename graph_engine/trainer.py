#!/usr/bin/env python3
"""
CyberDrishti AI — Hidden-Link Model Trainer
============================================
Generates synthetic cyber-crime graphs (mule networks, multi-layer fraud rings,
call-center syndicates, and negative control links) and trains the HiddenLinkEngine
using Stratified Group K-Fold cross-validation.
Enforces >= 90% precision gating to ensure zero false accusations in criminal trials.

Usage:
    python trainer.py --output models/hidden_link_model.pkl
"""

import argparse
from datetime import datetime, timezone, timedelta
import os
from pathlib import Path
import random
import networkx as nx
import numpy as np

from core.builder import build_case_graph
from core.hidden_link_engine import HiddenLinkEngine, compute_pair_features


def generate_synthetic_case_graph(case_num: int, rng: random.Random) -> tuple[nx.Graph, list[tuple[str, str, int]]]:
    """
    Generate a realistic synthetic case graph with known ground-truth hidden links.
    Returns: (NetworkX Graph G, list of labeled pairs (u, v, label))
    """
    base_time = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc) + timedelta(days=case_num)

    # Entities
    mastermind = f"Mastermind_{case_num}"
    caller = f"+9198{rng.randint(10000000, 99999999)}"
    upi_front = f"biz{case_num}@oksbi"
    bank_primary = f"91{rng.randint(1000000000, 9999999999)}"
    mule_1 = f"MuleAcct_A_{case_num}"
    mule_2 = f"MuleAcct_B_{case_num}"
    ip_vpn = f"192.168.{rng.randint(1, 254)}.{rng.randint(1, 254)}"
    crypto_cashier = f"Cashier_{case_num}"

    entities = [
        {"canonical_value": mastermind, "entity_type": "PER"},
        {"canonical_value": caller, "entity_type": "PHONE"},
        {"canonical_value": upi_front, "entity_type": "UPI"},
        {"canonical_value": bank_primary, "entity_type": "ACCOUNT"},
        {"canonical_value": mule_1, "entity_type": "ACCOUNT"},
        {"canonical_value": mule_2, "entity_type": "ACCOUNT"},
        {"canonical_value": ip_vpn, "entity_type": "IP"},
        {"canonical_value": crypto_cashier, "entity_type": "PER"},
    ]

    # Events simulating cyber fraud
    # Observed evidence:
    # Event 1: Mastermind directs caller
    t1 = (base_time + timedelta(minutes=rng.randint(5, 20))).isoformat()
    # Event 2: Caller uses UPI front
    t2 = (base_time + timedelta(minutes=rng.randint(25, 45))).isoformat()
    # Event 3: UPI front settles into bank_primary
    t3 = (base_time + timedelta(minutes=rng.randint(50, 70))).isoformat()
    # Event 4: bank_primary IMPS to mule_1
    t4 = (base_time + timedelta(minutes=rng.randint(75, 90))).isoformat()
    # Event 5: mule_1 transfers to mule_2 over IP
    t5 = (base_time + timedelta(minutes=rng.randint(95, 110))).isoformat()
    # Event 6: crypto_cashier withdraws from mule_2
    t6 = (base_time + timedelta(minutes=rng.randint(115, 130))).isoformat()

    events = [
        {
            "event_type": "whatsapp_msg",
            "event_timestamp": t1,
            "entity_mentions": [
                {"canonical_value": mastermind, "entity_type": "PER"},
                {"canonical_value": caller, "entity_type": "PHONE"},
            ]
        },
        {
            "event_type": "call",
            "event_timestamp": t2,
            "entity_mentions": [
                {"canonical_value": caller, "entity_type": "PHONE"},
                {"canonical_value": upi_front, "entity_type": "UPI"},
            ]
        },
        {
            "event_type": "payment",
            "event_timestamp": t3,
            "entity_mentions": [
                {"canonical_value": upi_front, "entity_type": "UPI"},
                {"canonical_value": bank_primary, "entity_type": "ACCOUNT"},
            ]
        },
        {
            "event_type": "bank_txn",
            "event_timestamp": t4,
            "entity_mentions": [
                {"canonical_value": bank_primary, "entity_type": "ACCOUNT"},
                {"canonical_value": mule_1, "entity_type": "ACCOUNT"},
            ]
        },
        {
            "event_type": "ip_login",
            "event_timestamp": t5,
            "entity_mentions": [
                {"canonical_value": mule_1, "entity_type": "ACCOUNT"},
                {"canonical_value": mule_2, "entity_type": "ACCOUNT"},
                {"canonical_value": ip_vpn, "entity_type": "IP"},
            ]
        },
        {
            "event_type": "atm_cashout",
            "event_timestamp": t6,
            "entity_mentions": [
                {"canonical_value": mule_2, "entity_type": "ACCOUNT"},
                {"canonical_value": crypto_cashier, "entity_type": "PER"},
            ]
        },
    ]

    # Add 2-3 innocent noise / control nodes in the graph
    noise_nodes = [f"Victim_{case_num}_{i}" for i in range(2)]
    for vn in noise_nodes:
        entities.append({"canonical_value": vn, "entity_type": "PER"})
        events.append({
            "event_type": "inquiry",
            "event_timestamp": (base_time + timedelta(minutes=rng.randint(1, 150))).isoformat(),
            "entity_mentions": [
                {"canonical_value": vn, "entity_type": "PER"},
                {"canonical_value": caller, "entity_type": "PHONE"}
            ]
        })

    G = build_case_graph(entities, events)

    # Labeled pairs:
    # Positive hidden links:
    # 1. Mastermind -> mule_1 (separated by caller and bank, but financially & temporally bound)
    # 2. Caller -> bank_primary
    # 3. Mastermind -> crypto_cashier (end-to-end hidden syndicate link)
    positives = [
        (mastermind, bank_primary),
        (caller, bank_primary),
        (bank_primary, mule_2),
        (mastermind, mule_1),
    ]

    # Negatives: noise nodes to other entities, or unconnected pairs
    negatives = [
        (noise_nodes[0], mule_2),
        (noise_nodes[1], crypto_cashier),
        (noise_nodes[0], ip_vpn),
        (noise_nodes[1], mastermind),
    ]

    labeled_pairs = []
    for u, v in positives:
        if G.has_node(u) and G.has_node(v) and not G.has_edge(u, v):
            labeled_pairs.append((u, v, 1))

    for u, v in negatives:
        if G.has_node(u) and G.has_node(v) and not G.has_edge(u, v):
            labeled_pairs.append((u, v, 0))

    return G, labeled_pairs


def train_model(output_path: str = "models/hidden_link_model.pkl", num_cases: int = 40):
    print(f"============================================================")
    print(f"🚀 Training CyberDrishti Hidden-Link Engine")
    print(f"============================================================")
    rng = random.Random(42)

    X_list = []
    y_list = []
    groups_list = []

    print(f"Generating {num_cases} synthetic cyber investigation graphs...")
    for case_id in range(num_cases):
        G, pairs = generate_synthetic_case_graph(case_id, rng)
        for u, v, label in pairs:
            feats = compute_pair_features(G, u, v)
            feature_vec = [
                feats["cn"],
                feats["jaccard"],
                feats["aa"],
                feats["temporal"],
                feats["fin"],
                feats["bridge"],
                feats["pa"],
            ]
            X_list.append(feature_vec)
            y_list.append(label)
            groups_list.append(case_id)

    X = np.array(X_list, dtype=float)
    y = np.array(y_list, dtype=int)
    groups = np.array(groups_list, dtype=int)

    print(f"Dataset summary: {len(X)} candidate pairs across {num_cases} cases.")
    print(f"Positives (hidden links): {sum(y == 1)}, Negatives: {sum(y == 0)}")

    engine = HiddenLinkEngine()
    print("Fitting Logistic Regression with StratifiedGroupKFold & precision-gated tuning...")
    engine.fit(X, y, groups)

    print(f"\nModel trained successfully!")
    print(f"Selected Decision Threshold: {engine.threshold:.4f} (guarantees >= 90% precision)")
    print(f"Learned Feature Weights:")
    for name, w in zip(engine.feature_names, engine.model.coef_[0]):
        print(f"  • {name:<12}: {w:+.4f}")

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    engine.save(out_file)
    print(f"\n✅ Model saved to: {out_file.resolve()}\n")
    return engine


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Hidden Link Engine")
    parser.add_argument("--output", type=str, default="models/hidden_link_model.pkl", help="Output path for model")
    parser.add_argument("--cases", type=int, default=40, help="Number of simulated cases to generate")
    args = parser.parse_args()

    train_model(output_path=args.output, num_cases=args.cases)
