# Feature 8 — Counterfactual "What-If Freeze" Simulation (isolated build)

Replays the case's timed money flow under a hypothetical intervention —
"account X frozen at time T" — with full balance accounting:

- transfers into a frozen account **stop at the wall** (preserved),
- transfers out of a frozen account **cannot leave**; the amount counts as
  preserved only if the funds were actually there (balance tracking prevents
  double-counting money that never arrived downstream of a stop wall — other
  attempts are reported as `unfunded_attempts`),
- everything else completes.

Output is `APPROXIMATED_LOWER_BOUND` with fixed caveats: flows beyond the
uploaded statements are unobservable; this is decision-support, **"NOT
admissible proof of negligence"** — the overclaim in the original feature
sketch is explicitly refused.

Tests: 7 passed (`feature_08_counterfactual`) — mid-chain freeze preserves
exactly the post-freeze outflows; earliest freeze catches everything; late
freeze preserves nothing; out-of-order input sorted internally; unfunded
attempts never inflate the number.

Integration: `POST /counterfactual/{case_id}/simulate
{target_entity_id, freeze_time}` over bank-transfer edges from parsed
evidence; persist to `counterfactual_runs` with the full replay trace; UI
shows preserved-by-account, the blocked/attempted events, and the caveat
banner. Reuses Feature 10's replay machinery for visualization.
