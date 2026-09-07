# Feature 5 — Split-Conformal Uncertainty (isolated build)

Replaces naked model confidence with **prediction sets** carrying a
distribution-free marginal guarantee: P(Y ∈ C(X)) ≥ 1−ε under exchangeability
(Vovk et al. 2005; Angelopoulos & Bates, arXiv:2107.07511).

- `calibrate(scores, epsilon, source)`: q̂ = ⌈(n+1)(1−ε)⌉-th smallest
  non-conformity score; ∞ when the rank exceeds the sample (a small
  calibration set cannot certify abstention — the engine, not folklore,
  decides).
- `predict_set`: single label → confident; multiple → "the data cannot
  distinguish between: …; more evidence required"; empty →
  `OUT_OF_DISTRIBUTION` abstention.
- **Synthetic calibration is flagged `valid_for_real_data: false`** — the
  guarantee must not be quietly claimed from synthetic coverage. Real labeled
  outcomes (currently a data gap, RESTRICTED) unlock it.

Tests: 7 passed (`feature_05_uncertainty`) — exact quantile order statistics,
empirical coverage ≥ 1−ε over 1000 seeded trials on exchangeable data,
abstention, ambiguous-set honesty, invalid-input rejection.

Integration: wraps the hidden-link scorer and hypothesis posteriors; store
calibrations in `conformal_calibrations` (model name, ε, q̂, n, source,
model hash); UI renders prediction sets as chips ("Mule OR Merchant — ATM
CCTV needed") instead of fake percentages.
