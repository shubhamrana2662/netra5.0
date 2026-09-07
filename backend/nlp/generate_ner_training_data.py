from __future__ import annotations
"""
CyberDrishti AI — Synthetic Hinglish NER Training Data Generator (Phase 1)
Generates 8,000 BIO-tagged sentences with calibrated fraud-category sampling.

Entity types: PER, PHONE, UPI, ACCOUNT, AMOUNT, BANK, OTP, EMAIL, URL, IFSC, LOCATION, KEYWORD
Fraud categories (I4C/NCRP proportions):
  INVESTMENT 0.77 | DIGITAL_ARREST 0.08 | CARD 0.07 | SEXTORTION 0.04 | ECOMMERCE 0.03 | MALWARE 0.01
Neutral (no entities, ~15% of output)

Usage:
    python generate_ner_training_data.py --output_dir training_data --n_sentences 8000
"""
import argparse
import json
import random
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# ── Entity Pools ──────────────────────────────────────────────────────────────

FIRST_NAMES = [
    "Rahul", "Priya", "Amit", "Sunita", "Ravi", "Pooja", "Suresh", "Kavita",
    "Deepak", "Anjali", "Vijay", "Meena", "Arun", "Rekha", "Sanjay", "Nisha",
    "Manoj", "Geeta", "Rajesh", "Anita", "Vishal", "Shweta", "Rohit", "Seema",
    "Ajay", "Mala", "Nitin", "Usha", "Sachin", "Lata", "Vinod", "Chanda",
]
LAST_NAMES = [
    "Sharma", "Verma", "Singh", "Gupta", "Patel", "Joshi", "Mishra", "Yadav",
    "Kumar", "Tiwari", "Pandey", "Dubey", "Chauhan", "Rawat", "Mehta",
]

UPI_SUFFIXES = ["@upi", "@okhdfcbank", "@ybl", "@paytm", "@okaxis", "@oksbi",
                "@ibl", "@okicici", "@airtelpaymentsbank"]

BANKS = ["HDFC Bank", "SBI", "ICICI Bank", "Axis Bank", "PNB", "Kotak Bank",
         "Bank of Baroda", "Canara Bank", "Union Bank", "Yes Bank"]

FRAUD_KEYWORDS = [
    "OTP", "invest", "crypto", "cash", "transfer", "block", "verify",
    "freeze", "arrest", "FIR", "CBI", "police", "digital arrest", "loan",
    "KYC", "update", "link", "wallet", "unlock", "penalty", "doubling",
]

LOCATIONS = [
    "Delhi", "Mumbai", "Bengaluru", "Hyderabad", "Chennai", "Kolkata",
    "Pune", "Ahmedabad", "Jaipur", "Lucknow", "Bhopal", "Indore",
]

SLANG = ["bhai", "yaar", "ji", "sahab", "bhaiya", "didi", "uncle", "mam"]


def _phone() -> str:
    r"""Valid Indian mobile number (regex ^[6-9]\d{9}$)."""
    return str(random.randint(6, 9)) + "".join(str(random.randint(0, 9)) for _ in range(9))


def _upi() -> str:
    name_part = random.choice(FIRST_NAMES).lower() + str(random.randint(1, 999))
    return name_part + random.choice(UPI_SUFFIXES)


def _account() -> str:
    length = random.randint(11, 16)
    return "".join(str(random.randint(0, 9)) for _ in range(length))


def _amount() -> tuple[str, float]:
    """Returns (text representation, numeric INR value)."""
    tier = random.random()
    if tier < 0.3:
        val = random.randint(1, 99) * 1000
        return f"₹{val // 1000}k", float(val)
    elif tier < 0.6:
        val = random.uniform(0.5, 99.9)
        return f"₹{val:.1f} lakh", val * 1_00_000
    elif tier < 0.85:
        val = random.randint(100, 50000)
        return f"Rs.{val}", float(val)
    else:
        val = random.uniform(0.1, 5.0)
        return f"{val:.2f} crore", val * 1_00_00_000


def _ifsc() -> str:
    bank_prefix = random.choice(["HDFC", "ICIC", "SBIN", "UTIB", "PUNB", "BARB"])
    return bank_prefix + "0" + "".join(random.choice("ABCDEFGH0123456789") for _ in range(6))


def _email() -> str:
    name = random.choice(FIRST_NAMES).lower() + str(random.randint(10, 9999))
    domain = random.choice(["gmail.com", "yahoo.co.in", "outlook.com", "hotmail.com"])
    return f"{name}@{domain}"


def _otp() -> str:
    return str(random.randint(100000, 999999))


def _name() -> str:
    return random.choice(FIRST_NAMES) + " " + random.choice(LAST_NAMES)


# ── BIO Tagging ───────────────────────────────────────────────────────────────

@dataclass
class TaggedSpan:
    text: str
    label: str  # entity type like PER, PHONE — or "" for O


def _bio_tag_sentence(spans: list[TaggedSpan]) -> tuple[list[str], list[str]]:
    """
    Tokenise (whitespace split) a sequence of TaggedSpans and assign BIO tags.
    Returns (tokens, bio_tags).
    """
    tokens: list[str] = []
    tags: list[str] = []

    for span in spans:
        words = span.text.split()
        if not words:
            continue
        if span.label == "":
            tokens.extend(words)
            tags.extend(["O"] * len(words))
        else:
            tokens.append(words[0])
            tags.append(f"B-{span.label}")
            for w in words[1:]:
                tokens.append(w)
                tags.append(f"I-{span.label}")

    return tokens, tags


# ── Sentence Templates by Fraud Category ─────────────────────────────────────

def _make_investment(rng) -> list[TaggedSpan]:
    name = _name(); phone = _phone(); upi = _upi(); amount, _ = _amount()
    templates = [
        [TaggedSpan(name, "PER"), TaggedSpan("ne bola invest karo", ""), TaggedSpan(amount, "AMOUNT"),
         TaggedSpan("aur double milega", ""), TaggedSpan(upi, "UPI"), TaggedSpan("pe bhejo", "")],
        [TaggedSpan("Aapka account", ""), TaggedSpan(phone, "PHONE"),
         TaggedSpan("par blocked hai, abhi", ""), TaggedSpan(amount, "AMOUNT"),
         TaggedSpan("transfer karo nahi toh penalty lagegi", "")],
        [TaggedSpan("Crypto invest karo", ""), TaggedSpan(amount, "AMOUNT"),
         TaggedSpan("ka guaranteed return milega,", ""), TaggedSpan(name, "PER"),
         TaggedSpan("contact karo", ""), TaggedSpan(phone, "PHONE")],
        [TaggedSpan("Rs", ""), TaggedSpan(amount, "AMOUNT"),
         TaggedSpan("invest karo account", ""), TaggedSpan(_account(), "ACCOUNT"),
         TaggedSpan("mein — 300% returns guaranteed", "")],
    ]
    return rng.choice(templates)


def _make_digital_arrest(rng) -> list[TaggedSpan]:
    name = _name(); phone = _phone(); amount, _ = _amount()
    templates = [
        [TaggedSpan("CBI officer", ""), TaggedSpan(name, "PER"),
         TaggedSpan("bol rahe hain apka", ""), TaggedSpan("FIR", "KEYWORD"),
         TaggedSpan("hua hai, call karo", ""), TaggedSpan(phone, "PHONE")],
        [TaggedSpan("Digital arrest ho jayega agar", ""), TaggedSpan(amount, "AMOUNT"),
         TaggedSpan("abhi", ""), TaggedSpan(_upi(), "UPI"), TaggedSpan("pe nahi bheja", "")],
        [TaggedSpan("Police", ""), TaggedSpan("ne aapka", ""),
         TaggedSpan("warrant", "KEYWORD"), TaggedSpan("nikala hai,", ""),
         TaggedSpan(name, "PER"), TaggedSpan("se sampark karo", ""),
         TaggedSpan(phone, "PHONE")],
    ]
    return rng.choice(templates)


def _make_card_fraud(rng) -> list[TaggedSpan]:
    otp = _otp(); phone = _phone(); bank = rng.choice(BANKS)
    templates = [
        [TaggedSpan(bank, "BANK"), TaggedSpan("ka account block ho raha hai,", ""),
         TaggedSpan("OTP", "KEYWORD"), TaggedSpan("share karo:", ""),
         TaggedSpan(otp, "OTP")],
        [TaggedSpan("Aapka", ""), TaggedSpan("KYC", "KEYWORD"),
         TaggedSpan("update karna hai", ""), TaggedSpan(bank, "BANK"),
         TaggedSpan("ke liye call karo", ""), TaggedSpan(phone, "PHONE")],
        [TaggedSpan("Card", ""), TaggedSpan("verify", "KEYWORD"),
         TaggedSpan("karne ke liye", ""), TaggedSpan(otp, "OTP"),
         TaggedSpan("batao,", ""), TaggedSpan(bank, "BANK"), TaggedSpan("officer bol rahe hain", "")],
    ]
    return rng.choice(templates)


def _make_sextortion(rng) -> list[TaggedSpan]:
    amount, _ = _amount(); upi = _upi()
    templates = [
        [TaggedSpan("Teri video viral kar dunga agar", ""),
         TaggedSpan(amount, "AMOUNT"), TaggedSpan("nahi bheja", ""),
         TaggedSpan(upi, "UPI"), TaggedSpan("pe", "")],
        [TaggedSpan("Private video leak hogi, abhi", ""),
         TaggedSpan(amount, "AMOUNT"), TaggedSpan("transfer karo", ""),
         TaggedSpan(_phone(), "PHONE"), TaggedSpan("pe", "")],
    ]
    return rng.choice(templates)


def _make_ecommerce(rng) -> list[TaggedSpan]:
    amount, _ = _amount(); phone = _phone(); name = _name()
    templates = [
        [TaggedSpan("Order", ""), TaggedSpan("cancel hua,", ""),
         TaggedSpan(amount, "AMOUNT"), TaggedSpan("refund ke liye call karo", ""),
         TaggedSpan(phone, "PHONE")],
        [TaggedSpan(name, "PER"), TaggedSpan("ne product bheja nahi, upi hai", ""),
         TaggedSpan(_upi(), "UPI")],
    ]
    return rng.choice(templates)


def _make_malware(rng) -> list[TaggedSpan]:
    url = f"http://{''.join(rng.choice('abcdefghijklmnop') for _ in range(8))}.com/install"
    templates = [
        [TaggedSpan("Ye app install karo banking ke liye:", ""),
         TaggedSpan(url, "URL")],
        [TaggedSpan("Link pe click karo account verify karne ke liye:", ""),
         TaggedSpan(url, "URL"), TaggedSpan("—", ""),
         TaggedSpan(_phone(), "PHONE"), TaggedSpan("pe call karo", "")],
    ]
    return rng.choice(templates)


def _make_neutral(rng) -> list[TaggedSpan]:
    """Noise sentences — no fraud entities."""
    neutrals = [
        "Aaj mausam bahut accha hai",
        "Kal market band rahega",
        "Meeting 3 baje hai office mein",
        "Khana kha liya?",
        "Bhai aaj cricket match dekhna hai",
        "Festival ki bahut bahut badhai",
        "Kya haal hai yaar",
        "Ghar ka kaam ho gaya",
        "Train late ho gayi",
        "Aaj school mein holiday hai",
    ]
    return [TaggedSpan(rng.choice(neutrals), "")]


# ── Category sampler ──────────────────────────────────────────────────────────

_CATEGORY_WEIGHTS = {
    "investment":     0.77,
    "digital_arrest": 0.08,
    "card":           0.07,
    "sextortion":     0.04,
    "ecommerce":      0.03,
    "malware":        0.01,
}
_FRAUD_BUILDERS: dict[str, Callable] = {
    "investment":     _make_investment,
    "digital_arrest": _make_digital_arrest,
    "card":           _make_card_fraud,
    "sextortion":     _make_sextortion,
    "ecommerce":      _make_ecommerce,
    "malware":        _make_malware,
}


def _generate_one(rng: random.Random, neutral_prob: float = 0.15) -> dict:
    if rng.random() < neutral_prob:
        spans = _make_neutral(rng)
        label = "neutral"
        fraud_relevant = 0
    else:
        cat = rng.choices(
            list(_CATEGORY_WEIGHTS.keys()),
            weights=list(_CATEGORY_WEIGHTS.values()),
        )[0]
        spans = _FRAUD_BUILDERS[cat](rng)
        label = cat
        fraud_relevant = 1

    tokens, bio_tags = _bio_tag_sentence(spans)
    return {
        "tokens": tokens,
        "ner_tags": bio_tags,
        "fraud_label": fraud_relevant,
        "category": label,
    }


# ── Dataset generation & splitting ───────────────────────────────────────────

def generate_dataset(
    n_sentences: int = 8000,
    seed: int = 42,
    output_dir: str | Path = "training_data",
) -> dict[str, list[dict]]:
    rng = random.Random(seed)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    all_samples = [_generate_one(rng) for _ in range(n_sentences)]

    # Stratified split 80/10/10 by (fraud_label, dominant entity type)
    train, val, test = [], [], []
    by_group: dict[str, list[dict]] = {}
    for s in all_samples:
        entity_types = sorted(set(t.split("-")[1] for t in s["ner_tags"] if t != "O"))
        key = f"{s['fraud_label']}_{','.join(entity_types)}"
        by_group.setdefault(key, []).append(s)

    for group_samples in by_group.values():
        rng.shuffle(group_samples)
        n = len(group_samples)
        n_train = max(1, int(n * 0.8))
        n_val   = max(0, int(n * 0.1))
        train.extend(group_samples[:n_train])
        val.extend(group_samples[n_train:n_train + n_val])
        test.extend(group_samples[n_train + n_val:])

    splits = {"train": train, "val": val, "test": test}

    for split_name, samples in splits.items():
        out_path = Path(output_dir) / f"{split_name}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for s in samples:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")

    # ── Status report ──────────────────────────────────────────────────────
    entity_counts: Counter = Counter()
    for s in all_samples:
        for tag in s["ner_tags"]:
            if tag.startswith("B-"):
                entity_counts[tag[2:]] += 1

    print("\n=== CyberDrishti NER Training Data — Status Report ===")
    print(f"Total sentences generated: {n_sentences}")
    print(f"Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")
    print("\nEntity counts (B- tags):")
    for etype in ["PER","PHONE","UPI","ACCOUNT","AMOUNT","BANK","OTP","EMAIL","URL","IFSC","LOCATION","KEYWORD"]:
        count = entity_counts.get(etype, 0)
        flag  = " ✓" if count >= 60 else " ⚠ BELOW 60 MINIMUM"
        print(f"  {etype:12s}: {count:5d}{flag}")
    print("\nFraud label distribution:")
    for cat, weight in _CATEGORY_WEIGHTS.items():
        cat_count = sum(1 for s in all_samples if s["category"] == cat)
        print(f"  {cat:20s}: {cat_count:5d} ({cat_count/n_sentences:.2%}, target {weight:.2%})")
    neutral_count = sum(1 for s in all_samples if s["category"] == "neutral")
    print(f"  {'neutral':20s}: {neutral_count:5d} ({neutral_count/n_sentences:.2%})")
    print(f"\nOutput directory: {output_dir}")

    return splits


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic Hinglish NER training data")
    parser.add_argument("--output_dir",  default="training_data", help="Output directory")
    parser.add_argument("--n_sentences", type=int, default=8000,  help="Number of sentences")
    parser.add_argument("--seed",        type=int, default=42,    help="Random seed")
    args = parser.parse_args()

    generate_dataset(n_sentences=args.n_sentences, seed=args.seed, output_dir=args.output_dir)
