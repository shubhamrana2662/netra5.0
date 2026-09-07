# Feature 3 — Cross-Case Intelligence / Blind Index (isolated build)

Detects when the same hard identifier is active in multiple cases without
exposing identifiers or content across case boundaries.

- **Canonicalization**: `+91 X`, `0X`, bare 10-digit phone forms collide; UPI
  case-insensitive; IFSC upper-cased.
- **HMAC-SHA256 tokens** with a department-supplied key — missing key is a
  hard error, never a default. Tokens are one-way.
- **Zero-knowledge alerts**: token, entity type, case ids, score. No raw
  identifier, no case content — coordination happens through the requisition
  flow.
- **Syndicate ingress score** `S(e) = Σ_c Severity(c)·log(1+Degree_c(e))` — a
  disclosed heuristic.

Scope honesty: links cases **within one deployment**. Cross-station
federation is an institutional track — I4C already operates the national
layer (National Cybercrime Suspect Registry, CFCFRMS bank-sharing, MuleHunter
MoU with RBIH, NCRP↔CCTNS). Integrate, don't rebuild.

Tests: 9 passed (`feature_03_crosscase`), including
no-identifier-in-alerts, key-required, variant-collision, collapse of
duplicate (token, case) pairs.

Integration: post-parse hook inserts tokens into `cross_case_blind_index`;
collision check emits `syndicate_alerts`; DPDP §17 (state-agency exemption)
analysis + jurisdictional authorization required before any deployment beyond
a single office. Key from env with documented rotation policy.
