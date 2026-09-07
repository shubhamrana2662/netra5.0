# Feature 7 — MO Fingerprinting (isolated build)

Represents a case as an ordered **crime script** (stage tokens: LURE →
ISOLATION → EXTRACTION → LAYERING → DISPOSAL family) and matches it against a
playbook library with normalized Levenshtein edit distance on the stage
sequence. DTW was deliberately rejected (it is for numeric series, not
categorical scripts); mining (`prefixspan`) is unnecessary at cold-start —
matching a curated library is the whole job.

Architecture decisions the tests forced:
- **Per-playbook tracing**: each playbook is traced against its OWN detectors,
  so stages from unrelated playbooks never pollute a sequence and shared
  vocabulary ("arrest" inside a fake notice vs a real threat) is scored in the
  right context.
- **Detector specificity lives in data** (`data/playbooks.json`): generic words
  belong to the stage that actually exhibits them. The library ships with
  sources (I4C Digital Arrest advisory Mar 2025; NITI Aayog Apr 2025; NCRP
  investment/task typology).
- Output is a **SIMILARITY in [0,1] with per-stage alignment and message-line
  citations, `epistemic_status: PREDICTED`** — never "96% match with Syndicate
  #11" (no verified national syndicate registry exists). Below threshold →
  "NO_CONFIDENT_MATCH", not a best guess.

Run: `D:/PROJECTS/cyber_v3/features/.venv/Scripts/python.exe -m pytest tests/ -v` — 8 passed.

Integration: `POST /mo/{case_id}/classify` runs over parsed WhatsApp messages;
results to `mo_profiles`; UI shows the alignment drawer (observed stage →
playbook position, with the triggering chat lines). Extend the library by
editing the JSON only — from I4C advisories and the NCRP Daily Digest.
