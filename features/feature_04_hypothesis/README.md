# Feature 4 — Hypothesis Engine (isolated build)

Competing-theory evaluation for any suspect entity: KINGPIN_ORGANIZER vs
LAYER1_MULE vs COMPROMISED_VICTIM, forced to compete against the SAME
evidence (ACH discipline: equal display + refutation focus). Log-odds
updating over hand-set likelihoods that live in `data/hypotheses.json` and
are validated at load (every row must sum to 1 — the validator caught bad
rows during development, by design).

Honesty (enforced in code, tested):
- Posteriors are `null` unless `allow_percentages=true` **and** a calibration
  object is supplied. Otherwise the output is `RULE_BASED_ASSESSMENT` with the
  display label "Ranking from hand-set likelihoods — not a calibrated
  probability. Show the matrix and refuting evidence." (Grounded in R v T
  [2010] EWCA Crim 2439: courts reject numerical Bayes without empirical
  basis; ACH's own empirical support is weak — the matrix, not the number,
  is the product.)
- Every hypothesis shows its **refuting evidence** (the indicator it explains
  worst) with the observed value and bucket.
- Missing observations are reported as unobserved, never imputed.

Tests: 9 passed (`feature_04_hypothesis`) — mule signature ranks first with
victim refuted; operator signature ranks kingpin; percentages only with
calibration; model validation rejects bad distributions.

Integration: `POST /hypothesis/{case_id}/generate {target_entity_id}`;
observations computed from parsed events (pass-through minutes from bank
rows, account age from KYC when available, inbound victim calls from CDR);
persist to `hypotheses` + `hypothesis_evidence`; UI renders the ACH matrix
with per-cell source citations. Calibration data (real labeled outcomes)
unlocks percentages later.
