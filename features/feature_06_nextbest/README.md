# Feature 6 — Next-Best Investigation Engine (isolated build)

Ranks the most urgent investigative actions from case state. Honesty is the
feature: a **transparent weighted utility with disclosed weights** (asset
component, urgency decay over configurable golden hours, latency credit,
friction penalty) — explicitly *not* a calibrated Value-of-Information
estimate, because that would require a response model we do not have. The
output says so on every response.

Key behaviours (all tested):
- Asset actions (freeze/attach) score by unwithdrawn ₹; evidence-expansion
  actions score by resolution value discounted by latency.
- **Drafts are filled only from case data.** Missing required fields block the
  draft and are named (`blocked_missing_fields`) — nothing is fabricated.
- Every draft carries the banner: requires IO signature and legal verification.
- The action catalog is data (`data/action_catalog.json`): statutes per
  verified research — BNSS 106 freeze (evidentiary; 107 for attachment),
  BNSS 94 requisition (expressly electronic records), 1930/CFCFRMS referral
  (I4C triggers bank stop-payment; always present as the cheapest action),
  tower dump via judicial order, KYC fetch. Catalog completeness is validated
  at load; unknown shapes fail loudly.

Run: `D:/PROJECTS/cyber_v3/features/.venv/Scripts/python.exe -m pytest tests/ -v` — 9 passed.

Integration: `GET /nextbest/{case_id}` built from live case state (accounts at
risk from parsed bank events not yet forwarded, elapsed time from first
credit, unresolved phones from graph); executed actions recorded in
`investigation_actions` with `executed_by` + audit-chain entry; drafts never
auto-transmit.
