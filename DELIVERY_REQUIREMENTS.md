# CyberDrishti AI / Netra 3.0 — Delivery Requirements

**What it takes to ship a fully working product where every feature works and every part coordinates as intended.**

This document is a delivery checklist, not a status report. It separates what is
already working from what is still required, and for each remaining item it states
the goal, why it matters, and how to know it is done. Items are grouped by whether
they block a *demo*, block a *production deployment*, or are *polish*.

---

## 0. Definitions used in this document

- **Working** — verified end-to-end this session (real pipeline, real data, HTTP 200 / correct output).
- **Fiction** — UI or output that presents a capability the backend does not actually perform. Must be either wired to something real or clearly badged/removed before "fully working" is honest.
- **Provenance vocabulary** (project standard): every piece of data shown must be classifiable as `REAL_EVIDENCE`, `DERIVED_ANALYSIS`, `SYNTHETIC_DEMO`, or `USER_ASSERTED`. Nothing may be silently fabricated.
- **Dual-dialect** — the app runs on PostgreSQL + asyncpg (prod) and SQLite + aiosqlite (dev/test). "Working" means working on **both**.

---

## 1. Current baseline (already working — do not re-do)

These are confirmed and should be treated as the stable foundation.

| Area | State |
|---|---|
| Auth (login, JWT, /me, role gating, unauth rejection) | ✅ Working |
| Officers (create / list / authenticate) | ✅ Working |
| Cases (create / get / list / patch / stats / delete-cascade) | ✅ Working |
| Evidence (upload, SHA-256 lock, hash-verify, background parse) | ✅ Working |
| Analytics (summary / communications / transactions) | ✅ Working |
| Timeline, Query (TF-IDF retrieval) | ✅ Working |
| Correlations (run + list flagged) | ✅ Working |
| Graph (network JSON) | ✅ Working |
| Cognitive engines (contradictions, hypotheses, next-best-actions, MO fingerprint, counterfactual freeze, network replay, cross-case collisions, verify-draft) | ✅ Working |
| Intelligence (communication + financial) | ✅ Working |
| Intel (syndicates + cross-match) | ✅ Working |
| Copilot (RAG query + status) | ✅ Working (on fallback — see §3) |
| Agent (launch, status, action ledger, sandbox rules, holds) | ✅ Working |
| Report (Section 65B PDF generation) | ✅ Working (signing is fiction — see §2) |
| Audit (tamper-evident chain verify, listing, per-case) | ✅ Working |
| Events (SSE ack + heartbeat) | ✅ Working (heartbeat-only — see §4) |
| Regression + contract test suites | ✅ Green |
| Frontend build (tsc + vite) | ✅ Green |
| Demo case (`CYB-2026-SHADOW-MULE`) | ✅ Seeded, real pipeline |

**Coverage harness:** `backend/_feature_audit.py` → 49/49 features pass.

---

## 2. BLOCKERS — features that are currently fiction

These present a capability the system does not actually perform. Until each is
either wired to a real backend or explicitly badged as a demonstration, the product
is not "fully working" in an honest sense.

### 2.1 Settings → Integrations tab (NCRP / DoT / FIU / I4C connectors)
- **Problem:** The tab shows connection status and controls for external government
  services that are not connected to anything.
- **To deliver, choose one:**
  - **(a) Real integration** — obtain API access / credentials for each service,
    implement the client, store secrets in env/secret manager, surface *actual*
    connection health.
  - **(b) Honest demo** — badge the tab "SIMULATED — not connected to live
    services" and disable the action buttons, or remove the tab.
- **Done when:** every indicator in the tab reflects a real connection state, OR the
  tab is unambiguously labelled as simulated and performs no misleading action.

### 2.2 Section 65B → PKCS#11 / HSM signing block
- **Problem:** The 65B PDF generates correctly, but the "hardware-security-module
  signed certificate" path is a stub. The legal weight it implies is not real.
- **To deliver, choose one:**
  - **(a) Real signing** — integrate a PKCS#11 provider (HSM or soft-token),
    sign the PDF hash, embed the verifiable signature + certificate chain.
  - **(b) Honest output** — state the PDF is an *analysis aid* (the code's own
    docstring already says this) and remove HSM/hardware-signing language from the
    document and UI.
- **Done when:** the PDF either carries a verifiable cryptographic signature, or
  makes no claim of one.

---

## 3. BLOCKERS — production configuration & data integrity

Correct code that will misbehave or is unsafe under a real deployment.

### 3.1 Database migrations (no Alembic)
- **Problem:** Schema is created via `Base.metadata.create_all` only. There are no
  migrations. On an existing Postgres prod DB, **adding a model column will not
  reach the live database** — the new column silently won't exist.
- **To deliver:** introduce Alembic (or equivalent). Generate an initial baseline
  migration matching the current models; make every future schema change a migration.
- **Done when:** a fresh DB and an existing DB both converge to the same schema via
  `alembic upgrade head`, and CI blocks model changes that lack a migration.

### 3.2 Default admin credentials
- **Problem:** The app self-seeds `admin / admin123` (and a `rana` user). This cannot
  ship to production.
- **To deliver:** require `INITIAL_ADMIN_PASSWORD` to be set (no default) in prod;
  force a password change on first login; remove any hard-coded demo users from the
  prod seeding path.
- **Done when:** a production boot with no explicit admin secret refuses to seed a
  guessable account.

### 3.3 Secrets & environment configuration
- **Problem:** Prod depends on env vars (`DATABASE_URL`, JWT secret, `ARMORIQ_API_KEY`,
  any LLM keys). These must be real, secret, and validated at boot.
- **To deliver:** a single documented `.env`/secret-manager contract; fail-fast
  validation at startup that lists any missing required var; ensure the JWT signing
  secret is strong and not a default.
- **Done when:** the app refuses to start in prod mode with a missing/weak secret,
  and the required-var list is documented.

### 3.4 Postgres path actually exercised
- **Problem:** All 49/49 tests this session ran on SQLite. Several bugs fixed this
  cycle were Postgres-vs-SQLite dialect issues — which proves the two dialects
  diverge in practice. The Postgres path has not been run end-to-end here.
- **To deliver:** run the full `_feature_audit.py` (and regression suite) against a
  real Postgres instance.
- **Done when:** the feature audit is 49/49 on **Postgres**, not just SQLite.

---

## 4. FEATURE COMPLETION — partially-built capabilities

Real and working, but narrower than the UI implies.

### 4.1 Live event streaming (SSE)
- **Current:** `GET /events/cases/{id}` emits a connection ack + 5-second heartbeats
  only. It does **not** stream real ingestion progress, agent actions, or alerts.
  (This is stated in the endpoint's own docstring as a later-sprint concern.)
- **To deliver:** publish real domain events (evidence processed, correlation flagged,
  agent action, hold created) onto the stream so the UI updates live.
- **Done when:** uploading evidence or running the agent produces visible, real-time
  events in a connected client — with no fabricated activity.

### 4.2 Autonomous agent — full run to completion
- **Current:** The agent launches, persists its actions (fixed this session), and is
  correctly blocked by the ArmorIQ governance layer when it proposes an undeclared
  action (`modify_network_control_config`). That block is **by design**. But it means
  a default run ends in `failed` rather than a clean completion.
- **To deliver (decide intent):** either (a) add the network-control action to the
  declared authorization plan if it is genuinely in scope, so approved runs complete;
  or (b) keep it out of scope and make the UI present the governance block as the
  *intended, successful* outcome (control fired) rather than a failure.
- **Done when:** the demo agent run reaches a state the UI frames as success, and the
  human approve/reject hold flow is exercised end-to-end.

### 4.3 ArmorIQ governance on the real SDK
- **Current:** Runs on a local stub because `ARMORIQ_API_KEY` is unset. The
  governance semantics work against the stub.
- **To deliver:** provision the key and run against the real ArmorIQ SDK.
- **Done when:** the intent-verification and audit behaviour is confirmed against the
  real service, not the stub.

### 4.4 ML models (HingBERT NER, CyberDrishtiLM)
- **Current:** Model directories are absent; the pipeline uses deterministic
  extraction fallback. Correct and honest, but not ML-backed.
- **To deliver (if "full" requires ML):** provision the model artifacts to
  `backend/artifacts/…`; confirm the loader picks them up; measure extraction quality
  vs. the fallback.
- **Done when:** NER/classification runs on the real models where present, and
  cleanly falls back (as now) where they are not.

### 4.5 Copilot / RAG LLM backend
- **Current:** Works; needs confirmation of whether prod points at a real LLM or a
  fallback.
- **To deliver:** configure the intended LLM provider + key for prod; confirm the
  CRAG "verify-draft" firewall behaves against the real model.
- **Done when:** copilot answers are generated by the intended prod LLM and the
  hallucination-firewall is validated end-to-end.

---

## 5. CROSS-CUTTING — "coordinating as intended"

The user's phrase "every option working and coordinating as intended" implies the
parts must work *together*, not just individually.

### 5.1 End-to-end investigator journey
- **To deliver:** one scripted walkthrough that a real user can follow —
  login → create case → upload evidence → watch it process (live) → review timeline
  & graph → run cognitive analysis → run agent → approve/reject a hold → generate
  the 65B report → verify the audit chain — with every step reflecting the previous
  step's real output.
- **Done when:** the journey runs start-to-finish with no dead ends, no fiction, and
  each screen shows data derived from the actual prior action.

### 5.2 Frontend ↔ backend contract integrity
- **To deliver:** confirm every screen consumes a real endpoint (no mocked API
  responses left in the frontend), and error/loading/empty states are handled.
- **Done when:** disconnecting the backend produces graceful UI errors, not blank
  screens or fabricated data.

### 5.3 Role-based access across the whole surface
- **To deliver:** verify IO / FIU-analyst / admin each see and can do exactly what
  their role permits across *every* screen (not just the auth endpoint), including
  IDOR protection on case-scoped resources.
- **Done when:** a non-owner IO cannot read or mutate another officer's case through
  any endpoint or screen.

### 5.4 Deployment topology
- **Current:** `vercel.json` describes multi-service routing (frontend + backend).
- **To deliver:** confirm the deployed topology actually serves the SPA and proxies
  `/api/v1` to the backend, with the DB reachable from the deployed backend.
- **Done when:** the app works from the deployed URL exactly as it does locally.

---

## 6. QUALITY GATES — before calling it done

- [ ] `_feature_audit.py` 49/49 on **Postgres**
- [ ] Regression + contract suites green on **both** dialects
- [ ] Frontend build green + no console errors on the core journey
- [ ] No fiction reachable without a "SIMULATED/DEMO" badge (§2)
- [ ] Migrations exist and apply cleanly to a fresh and an existing DB (§3.1)
- [ ] No default/guessable credentials in prod (§3.2)
- [ ] Required secrets validated at boot (§3.3)
- [ ] End-to-end investigator journey passes manually (§5.1)
- [ ] Role/IDOR checks pass across the full surface (§5.3)
- [ ] Deployed URL behaves as local (§5.4)

---

## 7. Suggested delivery order

1. **Decide the fiction question (§2).** Everything else assumes you know whether
   integrations/HSM are being built or badged. This is a product decision, not a
   coding task.
2. **Production safety (§3.1–3.3):** migrations, credentials, secrets. Cheap, high-risk-if-skipped.
3. **Verify on Postgres (§3.4).** Proves the dual-dialect fixes hold where it counts.
4. **Feature completion (§4):** streaming, agent completion, real SDK/LLM/models — in
   whatever order matches the demo's priorities.
5. **Cross-cutting coordination (§5)** and the **quality gates (§6).**

---

## 8. Honesty note on this document

Items in §1 are verified. Items in §2 are known from the project's own standard
(they were deliberately left as fiction). Items in §3–§5 are a mix of verified facts
(no Alembic, default admin, SSE heartbeat-only, agent governance block, ML fallback,
SQLite-only test runs) and areas that need confirmation on a real prod configuration
(LLM provider, deployment topology, frontend mock residue). Where confirmation is
needed it is stated as such rather than asserted as done.
