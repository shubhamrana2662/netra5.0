# Feature 1 — Resilient Document Fingerprinting (isolated build)

Detects near-duplicate evidence (bank statements, CDRs, chat exports) even when
renamed, re-saved, or appended-to, and computes the row-level diff so only
genuinely new rows enter the pipeline as new evidence. SHA-256 is preserved
untouched — it remains the chain-of-custody mechanism, not the dedup mechanism.

## What it does

| Tier | Mechanism | Catches | Verdict role |
|---|---|---|---|
| 1 | SHA-256 of raw bytes | byte-identical re-uploads (any filename) | EXACT_DUPLICATE |
| 2 | TLSH (optional import) | near-identical binary streams | advisory distance only |
| 3 | MinHash + containment over canonical transaction tuples | renamed/re-issued/appended documents | VARIANT / REVIEW_SIMILAR / DISTINCT (deciding tier) |

Three content verdicts, each tested: **VARIANT** (≥85% Jaccard or ≥90% containment with a shared key — safe to auto-link as a version), **REVIEW_SIMILAR** (partially similar — e.g. a doctored row, or identical rows on a *different* account, the same-template forgery signature — surfaced for human comparison, never auto-linked), **DISTINCT** (genuinely unrelated). `strict_guardrail: true` hard-blocks guardrail failures to DISTINCT instead.

Key design decisions (validated in tests):
- **Containment (overlap coefficient), not just symmetric Jaccard.** Appending 5
  rows to a 3-row statement gives Jaccard 0.375 but containment 1.0 — the
  "v2 re-upload" pattern is a containment pattern. Both thresholds configurable.
- **Shared-key guardrail.** With `require_shared_key: true`, two documents with
  similar rows but *no shared account/reference value* are DISTINCT — protects
  against merging two different accounts' statements.
- **Format-insensitive normalization.** `₹1,23,456.50` == `123456.50`; references
  case-folded. Normalizer is injectable.
- **`classify_upload` never deletes anything.** It returns a verdict, the best
  match id, and `{added, removed, unchanged}` row counts. The caller (main
  backend) decides version linking (`parent_file_id`, `version_number`) and
  ingests only `added` rows.

## Honest limits

- **TLSH tier is ACTIVE in this sandbox** (test `test_tlsh_tier_when_available` runs for real).
  Windows install notes (no compiler on this machine, so we built one):
  1. conda-forge `gcc` + `gxx` 16.2.0 (native mingw-w64) via micromamba at
     `tools/mmamba/gcc-env` — real g++, no Visual Studio needed.
  2. Built official `py-tlsh 5.0.0` sdist with `--compiler=mingw32`
     (CRT objects `crt2.o`/`dllcrt2.o`/`default-manifest.o` copied from the
     sysroot into the driver's search path).
  3. `tlsh.cp311-win_amd64.pyd` + `libstdc++-6.dll`/`libgcc_s_seh-1.dll`
     installed into the venv (DLLs sit NEXT TO the pyd — uv venvs use a
     trampoline exe, so the application dir is not the venv).
  4. Engine guards against TLSH's `"TNULL..."` sentinel (degenerate
     low-entropy inputs) — such files simply skip Tier 2.
  Production Linux: plain `pip install py-tlsh` (Apache-2.0/BSD-3).
- MinHash is an *estimate* (±~4.4% at 128 permutations) — reported as
  `jaccard_estimate`, never as exact similarity.
- Canonical tuples assume the upstream parser produced the fields listed in
  `tuple_fields` (default: event_type, timestamp, amount, reference). Map your
  parser output accordingly or override `tuple_fields`.

## Config (all thresholds are data, not code)

```json
{
  "num_perm": 128, "seed": 0,
  "tlsh_distance_threshold": 30,
  "jaccard_threshold": 0.85, "overlap_threshold": 0.90, "overlap_min_tuples": 2,
  "require_shared_key": false, "key_field": "account",
  "tuple_fields": ["event_type", "timestamp", "amount", "reference"]
}
```
Unknown keys are rejected (`load_config` raises) — config drift fails loudly.

## Run tests

```
D:/PROJECTS/cyber_v3/features/.venv/Scripts/python.exe -m pytest tests/ -v
```
(14 passed, 1 skipped — the skip is the TLSH tier when the library is absent.)

## Integration plan (summary — full plan at integration phase)

1. Add `evidence_fingerprints` table (see research report schema).
2. Hook `compute` + `classify_upload` into `routes/evidence.py::_process_evidence_file`
   after parsing, before event insertion; on VARIANT link as new version and
   ingest only `diff.added`.
3. Return `near_dup_match` + `version` fields in the upload response.
4. Production deps: `py-tlsh` (Apache-2.0/BSD-3), optionally `datasketch` for
   LSH bucketing at scale; the stdlib MinHash here is correct but O(n·perm) per
   compare — fine for per-case volumes.
