# Feature 9 — Deterministic Output Verifier (isolated build)

Intercepts every copilot draft before the officer sees it. Pure code, no model:

1. **Statutory validator** — resolves every `Section X [Act]` citation against
   `data/statutory_db.json`: unknown sections, struck-down provisions (IT Act
   66A → Shreya Singhal 2015), and pre-transition acts (IPC/CrPC/IEA after
   1 July 2024) become violations **with concrete replacement suggestions**
   (e.g., "Section 420 IPC" → "Section 318 BNS").
2. **Span grounding audit** — every ₹amount / phone / UPI in the draft must
   exist in the caller-supplied case facts; failures name the searched index.
3. **Canned-text detector** — a draft too similar to a supplied canned corpus
   (≥ `canned_similarity_threshold`) is flagged: the observable symptom of
   fallback fabrication.

Failures produce deterministic `correction_instructions` for regeneration
(negative constraints, never free-text hints).

## Honest notes

- Naming: this is **not** CRAG (arXiv 2401.15884 is a retrieval evaluator with
  web-search fallback). It is a groundedness/statutory verifier — deliberately
  deterministic and stricter.
- `statutory_db.json` is **seed data** whose entries cite their primary sources;
  production must regenerate from official MHA gazette PDFs and pass legal
  review before operational use. Unknown sections are flagged, never guessed.
- Section resolution without a named act requires uniqueness in the DB;
  ambiguity is a violation the model must fix (it must name the act).

## Tests

```
D:/PROJECTS/cyber_v3/features/.venv/Scripts/python.exe -m pytest tests/ -v
```
11 passed. (Two real bugs were caught and fixed here: a regex alternation-order
bug that read "BNSS" as "BNS", and numeric normalization leaking into
phone/UPI matching.)

## Integration plan (summary)

Wire into `rag/copilot.py` after draft generation and before the response is
returned: up to 2 regeneration rounds with `correction_instructions` appended to
the prompt; persist every critique to a `critique_results` table (draft,
violations, final text) — an auditable record that answers "did the AI
hallucinate?" with evidence.
