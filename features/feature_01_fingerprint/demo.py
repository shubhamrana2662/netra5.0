"""Live demo — Feature 1: Resilient Document Fingerprinting.

Walks through the four real-world upload scenarios:
  1. First upload                      -> NEW
  2. Same file, renamed                -> EXACT_DUPLICATE (SHA-256; name irrelevant)
  3. Bank adds 5 rows, re-issues PDF   -> VARIANT + exact row diff (the core fix)
  4. Forged/tampered variant           -> VARIANT showing what changed
  5. Different account, similar layout -> DISTINCT (shared-key guardrail)

Run:  D:/PROJECTS/cyber_v3/features/.venv/Scripts/python.exe demo.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import FingerprintEngine

engine = FingerprintEngine(require_shared_key=True, key_field="account")


def statement_rows(rows, account="482910111222"):
    return [
        {"event_type": "bank_txn", "timestamp": ts, "amount": amt,
         "reference": ref, "account": account}
        for ts, amt, ref in rows
    ]


def pdf(name, extra=""):
    # stand-in for raw statement bytes; deterministic per-document filler so
    # different documents carry genuinely different binary content (same-name
    # variants stay binary-similar, unrelated documents stay binary-distant)
    seed = sum(ord(c) * (i + 7) for i, c in enumerate(name + extra))
    filler = " ".join(f"row{i}:{(i * 7919 + seed) % 9973:04d}" for i in range(600))
    return f"%PDF-1.7 {name} {extra} {filler}".encode()


def show(step, title, result):
    print(f"\n{'='*70}\nSTEP {step}: {title}\n{'='*70}")
    print(f"  verdict          : {result['verdict']}")
    print(f"  jaccard estimate : {result['jaccard_estimate']}")
    if result.get("containment") is not None:
        print(f"  containment      : {result['containment']}")
    if result.get("tlsh_distance") is not None:
        print(f"  tlsh distance    : {result['tlsh_distance']}  (<=30 very similar, >100 distinct)")
    if result.get("matched_evidence_id"):
        print(f"  linked to        : {result['matched_evidence_id']}")
    if "diff" in result:
        d = result["diff"]
        print(f"  diff             : +{d['added_rows']} added, "
              f"-{d['removed_rows']} removed, ={d['unchanged_rows']} unchanged")
    if result.get("reason"):
        print(f"  reason           : {result['reason']}")


# ── the evidence (fictional bank statement rows) ──────────────────────────────
ROWS_V1 = statement_rows([
    ("2026-04-22T11:24:00", "68000.00", "UPI/719462"),
    ("2026-04-22T11:27:00", "68000.00", "UPI/881201"),
    ("2026-04-22T10:02:00", "12500.00", "IMPS/553209"),
])

# v2: the same 3 rows + 5 new ones (bank re-issued the statement)
ROWS_V2 = ROWS_V1 + statement_rows([
    ("2026-04-23T09:10:00", "30000.00", "UPI/900112"),
    ("2026-04-23T09:15:00", "30000.00", "UPI/900113"),
    ("2026-04-23T09:22:00", "15000.00", "UPI/900114"),
    ("2026-04-23T09:30:00", "7000.00", "ATM/DEL-005"),
    ("2026-04-23T09:31:00", "7000.00", "ATM/BLR-011"),
])

# v2 stored under a completely different filename
raw_v1 = pdf("SBI_statement_Apr2026.pdf")
raw_v2_renamed = pdf("download(3).pdf", "reissued with appended rows")

# prior evidence already ingested in this case
prior = [("EV-001", engine.compute(raw_v1, ROWS_V1), ROWS_V1)]

print("=" * 70)
print("FEATURE 1 — RESILIENT DOCUMENT FINGERPRINTING (LIVE DEMO)")
print("case evidence already ingested: EV-001 (3 transactions)")
print("=" * 70)

# Step 1: fresh document
r = engine.classify_upload(pdf("new_case_doc.pdf"), statement_rows([
    ("2026-05-01T08:00:00", "999.00", "UPI/111111"),
]), prior)
show(1, "Brand-new statement from another case file", r)

# Step 2: same bytes, renamed
r = engine.classify_upload(raw_v1, ROWS_V1, prior)
show(2, 'Same file re-uploaded as "download(3).pdf" (renamed only)', r)

# Step 3: bank appends 5 rows, PDF re-issued under a new name
r = engine.classify_upload(raw_v2_renamed, ROWS_V2, prior)
show(3, "Bank re-issued statement: +5 new rows, renamed, re-saved", r)
if r["verdict"] == "VARIANT":
    diff = engine.structural_diff(ROWS_V1, ROWS_V2)
    print("  -> ingest plan   : link as v2 of EV-001; ingest ONLY these rows:")
    for t in diff.added:
        print(f"       {t[1]:<22} {t[2]:<14} {t[3]}")

# Step 4: tampered amount
TAMPERED = [dict(r) for r in ROWS_V1]
TAMPERED[0]["amount"] = "6000.00"  # was 68000.00 — forged
r = engine.classify_upload(pdf("sbi_stmt_edit.pdf", "tampered"), TAMPERED, prior)
show(4, "Forged copy: the ₹68,000 row edited to ₹6,000", r)
if "diff" in r:
    diff = engine.structural_diff(ROWS_V1, TAMPERED)
    print("  -> what changed  :")
    for t in diff.removed:
        print(f"       REMOVED: {t[1]:<22} {t[2]}")
    for t in diff.added:
        print(f"       ADDED  : {t[1]:<22} {t[2]}")

# Step 5: different account, same layout (the false-merge trap)
OTHER = statement_rows(ROWS_V1 and [
    (ts, amt, ref) for ts, amt, ref in [
        ("2026-04-22T11:24:00", "68000.00", "UPI/719462"),
        ("2026-04-22T11:27:00", "68000.00", "UPI/881201"),
        ("2026-04-22T10:02:00", "12500.00", "IMPS/553209"),
    ]
], account="771122334455")
r = engine.classify_upload(pdf("other_bank_stmt.pdf", "different account"), OTHER, prior)
show(5, "Look-alike rows but a DIFFERENT account number", r)

print("\n" + "=" * 70)
print("SHA-256 note: raw-byte hashes are still computed and preserved for")
print("chain-of-custody (Section 63 BSA); the fingerprint tiers ADD")
print("semantic duplicate detection without touching that record.")
print("=" * 70)
