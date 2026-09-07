# Feature 11 — Synthetic Benchmark Generator (isolated build)

Deterministic, seeded generator of fully-labeled synthetic cyber-fraud cases:
WhatsApp transcript + bank statements (running balances) + CDR rows, with a
ground-truth file (entities, money-flow edges, planted hidden links, planted
contradictions, typology label). Typologies and entity pools are pure data
(`data/typologies.json`, `data/pools.json`) — the engine contains no case
values, no names, no templates. All values fictional (DPDP-friendly).

Honest role: this is the **evaluation harness** for the other engines, not a
scoreboard. Synthetic scores say nothing about real-case accuracy (the
template-leakage trap is documented in the project's own non-negotiables).

Cross-engine alignment test: generated ledgers must pass Feature 2's ledger
audit clean — the features are verified to compose.

Tests: determinism (same seed → identical output), seed variation, ground
truth ↔ artifact consistency, hidden-link never-co-occur contract, money
conservation at the victim hop, OCR/drop-noise recording.
`D:/PROJECTS/cyber_v3/features/.venv/Scripts/python.exe -m pytest tests/ -v` — 10 passed.

Integration: `POST /benchmark/generate {typology, seed, config}` → artifacts +
ground truth stored as a case-like package; regression harness runs parsers →
extraction → graph → hidden links → engines against it in CI.
