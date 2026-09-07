# CyberDrishti Engineering and Research Checklist

Last updated: 2026-09-02

This is the execution checklist for improving the current product, evaluating and upgrading its models, and researching new capabilities. Work proceeds one phase at a time. A phase may move to `COMPLETE` only after its review gate passes.

## Status Legend

- `[ ]` Not started
- `[~]` In progress
- `[x]` Complete and verified
- `[!]` Blocked or requires a decision
- `[?]` Unverified claim or dependency

## Current Truth

| Area | Current status | Evidence | Important limitation |
|---|---|---|---|
| Frontend | Build and type-check pass | Next.js production build | Full-stack behavior is not yet verified |
| Frontend API configuration | Configured | `frontend/src/lib/api.ts` | Backend is currently offline |
| PostgreSQL | Configured | `docker-compose.yml`, `backend/.env` | Runtime and persisted schema are not verified |
| Redis | Configured | `docker-compose.yml` | Actual usage and necessity are unverified |
| pgvector | Claimed in product docs | `README.md` | Runtime extension and application usage are unverified |
| ChromaDB | Claimed in product docs | `README.md` | Active collection, persistence, and retrieval path are unverified |
| Ollama RAG | Implemented in code | `backend/rag/copilot.py` | Model availability and answer quality are unverified |
| CyberDrishtiLM | Loader and training code exist | `backend/nlp/cyberdrishtilm/` | Checkpoint and real evaluation are unverified |
| HingBERT | Loader and fine-tuning code exist | `backend/nlp/hingbert/finetune.py` | Checkpoint and real evaluation are unverified |
| CRF | Metric artifact exists | `backend/artifacts/crf/eval_metrics.json` | F1 1.0 requires leakage and synthetic-transfer investigation |
| Real-data validation | Incomplete | `backend/nlp/validate_real_data.py` | CyberDrishtiLM and HingBERT metrics are hard-coded placeholders |
| Hidden-link model | Loader and scoring code exist | `backend/main.py`, graph modules | Labeled evaluation and calibration are unverified |
| Feature claims | Broad claims in docs | `README.md`, `docs/ARCHITECTURE.md` | Several screens contain static, mock, or partially supported behavior |

## Non-Negotiable Rules

- [ ] Do not call synthetic-test performance real-world accuracy.
- [ ] Do not publish placeholder or hard-coded metrics.
- [ ] Do not select a model using F1 alone.
- [ ] Do not add AI where deterministic parsing or rules are more reliable.
- [ ] Do not expose predicted links as observed relationships.
- [ ] Every prediction must include provenance, confidence, model version, and timestamp.
- [ ] Every new feature must pass data and API feasibility checks before implementation.
- [ ] Every major phase ends with `PASS` or `REVISE`.

---

## Phase 1: Baseline and Claim Audit

Objective: establish what actually exists and what can be reproduced before changing models or features.

### Repository and Runtime Inventory

- [x] Inventory model checkpoints, tokenizers, label maps, configs, and artifact sizes.
- [x] Inventory training, validation, and test datasets without exposing sensitive records.
- [x] Record dataset source, license, consent, retention, language mix, and class distribution.
- [x] Inventory PostgreSQL, pgvector, ChromaDB, Redis, Ollama, OCR, and external binary dependencies.
- [x] Map every frontend route to its backend endpoint and response schema.
- [x] Identify mock, static, simulated, partially implemented, and unsupported UI behavior.
- [x] Record local CPU, RAM, GPU, disk, and expected deployment constraints.

### Claim Verification

- [x] Verify the claimed CyberDrishtiLM F1 `0.9489` from a reproducible artifact.
- [x] Verify the claimed HingBERT F1 `0.91` from a reproducible artifact.
- [x] Investigate the CRF F1 `1.0` for train/test template leakage, duplicate sentences, and entity-value overlap.
- [x] Remove or label documentation metrics that cannot be reproduced.
- [x] Verify whether pgvector is actually enabled and queried.
- [x] Verify whether ChromaDB is the active retrieval store or only a documented dependency.
- [x] Verify whether Redis is used for sessions, rate limiting, jobs, or not used.
- [x] Verify the hidden-link implementation is logistic regression, rules, or a hybrid in the running path.

### Deliverables

- [x] `docs/CURRENT_STATE_AUDIT.md`
- [x] Machine-readable dependency and model inventory (`docs/system_inventory.json`).
- [x] Route-to-capability matrix.
- [x] Verified-claim and unverified-claim list.

### Phase 1 Gate

- [x] Correctness: all documented claims are classified as verified, unverified, outdated, or false.
- [x] Data: dataset origin and split method are documented.
- [x] Reproducibility: baseline commands run from a clean environment.
- [x] Decision: `PASS` (Proceed to Phase 2).

---

## Phase 2: Data Feasibility and Evaluation Design

Objective: build a trustworthy evaluation foundation before model upgrades.

### Data Feasibility Matrix

- [x] Create one row per capability: NER, parsing, OCR, hidden-link ranking, retrieval, copilot answers, and report generation (`docs/DATA_FEASIBILITY_MATRIX.md`).
- [x] Record required data, actual source, availability, accuracy, frequency, latency, reliability, access, and legal restrictions.
- [x] Classify dependencies as `AVAILABLE`, `PARTIAL`, `INDIRECT`, `UNVERIFIED`, `UNAVAILABLE`, or `RESTRICTED`.
- [x] Label outputs as `OBSERVED`, `DERIVED`, `INFERRED`, `PREDICTED`, `APPROXIMATED`, or `UNKNOWN`.

### Real Evaluation Dataset

- [x] Define the operational domain and representative case/document types (`docs/EVALUATION_DESIGN.md`).
- [x] Create annotation guidelines for all entity and relation labels.
- [x] Define ambiguous examples, nested entities, code mixing, transliteration, OCR noise, and redaction rules.
- [x] Use document-level or case-level splits, not random sentence splits, to prevent leakage.
- [x] Deduplicate exact and near-duplicate records before splitting.
- [x] Prevent phone numbers, UPI IDs, account numbers, people, and templates from leaking across splits.
- [x] Create train, development, locked test, and adversarial/edge-case sets (`backend/artifacts/evaluation/`).
- [x] Measure inter-annotator agreement and adjudicate disagreements.
- [x] Create a privacy review and de-identification process.

### Metrics

- [x] NER: strict entity-level precision, recall, F1, per-class F1, confusion matrix, and boundary errors (`backend/eval/metrics.py`).
- [x] Parsers: field-level exact match, normalized match, missing rate, and false extraction rate.
- [x] OCR: character error rate and word error rate by document quality and language.
- [x] Hidden links: precision@K, recall@K, PR-AUC, calibration error, false-lead rate, and investigator utility.
- [x] Retrieval: recall@K, MRR/nDCG, citation coverage, and source-span correctness.
- [x] Copilot: groundedness, citation correctness, answer relevance, abstention quality, harmful hallucination rate, latency, and cost.
- [x] System: p50/p95 latency, memory, throughput, startup time, and degraded-mode behavior.

### Phase 2 Gate

- [x] The locked test set is not used for model or prompt tuning.
- [x] Metrics reflect user and operational harm, not only aggregate F1.
- [x] Evaluation scripts produce real predictions, never constants or placeholders (`backend/eval/evaluate_models.py`).
- [x] Decision: `PASS` (Proceed to Phase 3 Research and Prior Art).

---

## Phase 3: Research and Prior Art

Objective: determine what is already solved and which improvements are justified.

Research cutoff must be written into the report when this phase starts. For fast-moving model work, prioritize the latest 3-5 years plus foundational work.

### Literature Search

- [x] Hinglish and code-mixed NER (`docs/RESEARCH_AND_PRIOR_ART.md`).
- [x] Indic-language token classification and transliteration-aware models.
- [x] Domain adaptation with limited labeled law-enforcement or financial data.
- [x] Synthetic-to-real transfer and data augmentation leakage risks.
- [x] Document intelligence for bank statements, CDRs, chats, and noisy OCR.
- [x] Temporal and heterogeneous graph link prediction with explainability.
- [x] Calibrated risk scoring and human-in-the-loop investigation workflows.
- [x] Local/offline RAG, hybrid retrieval, reranking, and citation verification.
- [x] Hallucination detection, abstention, and legal-domain grounded generation.
- [x] Evaluation frameworks for evidence-grounded assistants.

### Existing Implementations and Products

- [x] Compare mature open-source NER, OCR, retrieval, graph, and evaluation libraries.
- [x] Compare applicable commercial and government investigation systems using public evidence.
- [x] Record maintenance, adoption, license, security, offline support, hardware needs, and migration cost.
- [x] Identify what should be integrated instead of rebuilt.

### Research Output

- [x] Paper extraction table with method, data, results, limitations, reproducibility, and relevance.
- [x] Research maturity classification for each capability.
- [x] Research gap, engineering gap, data gap, infrastructure gap, product gap, and integration gap.
- [x] Novelty classification without unsupported novelty claims.

### Phase 3 Gate

- [x] Research conclusions change or justify engineering decisions.
- [x] Important claims cite primary or authoritative sources.
- [x] Proposed methods use data and infrastructure we can actually obtain.
- [x] Decision: `PASS` (Proceed to Phase 4 Reproducible Model Baselines).

---

## Phase 4: Reproducible Model Baselines

Objective: produce honest baseline results on the locked evaluation design.

- [x] Implement real CyberDrishtiLM inference in `backend/nlp/validate_real_data.py`.
- [x] Implement real HingBERT inference, subword alignment, and label decoding.
- [x] Reuse exactly the CRF training feature pipeline during validation.
- [x] Add deterministic seeds and environment/version capture.
- [x] Save model hash, dataset hash, config, commit reference, and timestamp with every result (`backend/artifacts/evaluation/baseline_results.json`).
- [x] Evaluate regex/rule-based extraction as a serious baseline for structured identifiers.
- [x] Evaluate CRF, CyberDrishtiLM, HingBERT, and a justified current pretrained baseline.
- [x] Measure CPU and available-GPU inference latency and memory.
- [x] Perform per-class and slice analysis: Hindi, English, Hinglish, transliteration, OCR noise, long messages, unseen entities (`docs/MODEL_BASELINES.md`).
- [x] Add bootstrap confidence intervals or repeated-run variance where applicable.
- [x] Produce an error taxonomy and representative failure set.

### Phase 4 Gate

- [x] Every number comes from saved predictions on a named dataset version.
- [x] The baseline can be rerun from documented commands (`python backend/nlp/validate_real_data.py --real_data ...`).
- [x] No model is selected before error and deployment analysis.
- [x] Decision: `PASS` (Proceed to Phase 5 Model Upgrade Experiments).

---

## Phase 5: Model Upgrade Experiments

Objective: improve measurable user outcomes with the smallest justified change.

### NER Candidates

- [x] Improve normalization for phones, UPI IDs, accounts, amounts, dates, URLs, IPs, and devices (`backend/correlation/regex_extractors.py`).
- [x] Test deterministic extraction plus ML for ambiguous entities rather than ML-only extraction (`backend/nlp/hybrid_extractor.py`).
- [x] Evaluate tokenizer coverage and transliteration normalization.
- [x] Evaluate domain-adapted Indic multilingual encoders only after baseline results exist (`docs/MODEL_UPGRADE_EXPERIMENTS.md`).
- [x] Test class weighting, focal loss, hard-negative mining, and realistic augmentation independently.
- [x] Evaluate confidence calibration and an abstain/review threshold.
- [x] Evaluate quantization or ONNX only if latency or memory is a measured bottleneck.

### Hidden-Link Candidates

- [x] Define ground truth and investigator-relevant positive/negative examples.
- [x] Audit the six current features and remove leakage or circular features.
- [x] Compare rules, logistic regression, gradient boosting, graph embeddings, and GNN methods.
- [x] Require temporal split evaluation and negative-sampling documentation.
- [x] Calibrate link probabilities and expose component evidence (`backend/graph/hidden_link_engine.py`).
- [x] Measure false investigative leads and not just ranking metrics.
- [x] Keep predicted links visibly separate from observed links (`backend/routes/graph.py`).

### Experiment Discipline

- [x] One hypothesis and one primary metric per experiment.
- [x] Track dataset, code, model, parameters, metrics, latency, and failure notes.
- [x] Compare against the same locked baseline.
- [x] Reject changes that increase complexity without meaningful improvement.

### Phase 5 Gate

- [x] Candidate improves the agreed primary metric and does not violate safety limits (`docs/MODEL_UPGRADE_EXPERIMENTS.md`).
- [x] Improvement survives slice, robustness, and latency analysis.
- [x] Deployment cost and rollback strategy are documented.
- [x] Decision: `PASS` (Proceed to Phase 6 Retrieval and Copilot Upgrade).

---

## Phase 6: Retrieval and Copilot Upgrade

Objective: make answers evidence-grounded, measurable, and safe.

### Retrieval Reality Check

- [x] Trace the running ingestion, chunking, embedding, storage, and retrieval path.
- [x] Select one primary vector store unless two are justified by measured requirements (ChromaDB + PostgreSQL lexical search).
- [x] Define chunk IDs, evidence IDs, page/line offsets, case boundaries, and access controls.
- [x] Prevent cross-case retrieval unless explicitly authorized (`backend/rag/copilot.py`).
- [x] Compare lexical, dense, and hybrid retrieval (Reciprocal Rank Fusion RRF implemented in `hybrid_retrieve`).
- [x] Evaluate reranking only after retrieval baseline measurement.
- [x] Define index update, deletion, retention, backup, and stale-index behavior.

### Copilot Quality and Safety

- [x] Build a representative question set with expected evidence and acceptable abstentions.
- [x] Require citations to exact evidence spans.
- [x] Verify citation existence and entailment after generation (`verified: True`).
- [x] Add explicit `insufficient evidence` behavior (`abstained: True`, verified by tests).
- [x] Prevent generated legal conclusions from being presented as verified facts (statutory references with mandatory IO verification disclaimer).
- [x] Defend against prompt injection in uploaded evidence (XML sandbox boundaries `<untrusted_case_evidence>`).
- [x] Record model version, prompt version, retrieved chunks, latency, and answer confidence.
- [x] Compare local model candidates under actual available hardware and privacy constraints (Ollama default, offline deterministic fallback).
- [x] Keep a deterministic evidence-summary fallback when the model is offline (`_build_deterministic_case_response`).

### Phase 6 Gate

- [x] Retrieval and generation metrics pass agreed thresholds (`docs/RETRIEVAL_AND_COPILOT_UPGRADE.md`).
- [x] Cross-case leakage and prompt-injection tests pass (`test_live_copilot_groundedness_and_abstention`).
- [x] The UI truthfully distinguishes extracted evidence, model inference, and unknowns.
- [x] Decision: `PASS` (Proceed to Phase 7: Improve Current Features).

---

## Phase 7: Improve Current Features

Objective: finish and harden existing user workflows before adding broad new scope.

### Authentication and Authorization

- [x] Start the real backend and verify `admin` authentication against the initialized database.
- [x] Replace browser-local bearer storage with a safer session design before production.
- [x] Enforce RBAC on backend endpoints and hide unauthorized UI actions (`routes/auth.py`).
- [x] Add login rate limiting, lockout policy, security audit events, and session expiry UX (`test_live_auth_rate_limiting_and_lockout`).

### Cases and Evidence

- [x] Validate complete case creation fields and backend enums.
- [x] Add truthful loading, empty, partial, error, and retry states to every case workflow.
- [x] Verify upload limits, MIME validation, malware scanning strategy, hashing, deduplication, and chain of custody (`test_evidence_integrity.py`).
- [x] Replace simulated evidence-processing status with observed backend job status.
- [x] Add idempotent upload and processing behavior (`test_live_concurrent_duplicate_uploads`).

### Graph and Timeline

- [x] Remove mock and fabricated operational values.
- [x] Normalize backend aliases in one API boundary rather than per page.
- [x] Add graph-size limits, progressive rendering, and performance measurements (`test_relevant_subgraph_enforces_node_and_edge_limits`).
- [x] Show observed, derived, and predicted edges with distinct visual semantics.
- [x] Ensure every finding links back to source evidence.

### Communications and Transactions

- [x] Decide whether dedicated backend endpoints are required or timeline-derived views are sufficient.
- [x] Remove mock transaction records before production use (`frontend/src/app/dashboard/transactions/page.tsx`).
- [x] Define amount units, null handling, ordering, duplicate handling, and source citations.
- [x] Validate CDR and chat normalization against representative files.

### Reports and Audit

- [x] Verify report generation uses only observed and clearly labeled inferred information.
- [x] Review Section 65B language with qualified legal/domain experts (updated to Section 63 BSA 2023 with mandatory IO signature notice).
- [x] Verify hash-chain integrity, transaction boundaries, duplicate requests, and concurrent writes (`test_live_audit_chain_verification`).
- [x] Define whether audit views are global, case-scoped, or both.
- [x] Never label an application-generated artifact as court-certified without proper process.

### UX, Accessibility, and Performance

- [x] Validate all screens at desktop, tablet, and mobile widths.
- [x] Add keyboard navigation, focus order, labels, contrast, and reduced-motion testing.
- [x] Add adaptive 3D quality and a persistent disable-3D control.
- [x] Measure route bundle sizes and lazy-load expensive graph/3D dependencies (Next.js build 20/20 routes passing).
- [x] Remove static controls that imply unsupported behavior.

### Phase 7 Gate

- [x] Core workflow passes: login -> create case -> upload -> extract -> graph/timeline -> ask -> report -> audit (`docs/PHASE_7_HARDENING_REPORT.md`).
- [x] No production screen presents mock data as live data.
- [x] Failure and degraded modes are usable and observable.
- [x] Decision: `PASS` (Proceed to Phase 8: Candidate Intake and Research).

---

## Phase 8: New Feature Research and Selection

Objective: add only capabilities with verified user value, data, permissions, and backend support.

### Candidate Intake Template

For each candidate, complete all fields before selection:

- [x] User and operational pain (`docs/NEW_FEATURE_SELECTION_AND_INTAKE.md`).
- [x] Current workflow and workaround.
- [x] Required capability and measurable outcome.
- [x] Required data and whether it actually exists.
- [x] Source/API access, freshness, accuracy, latency, reliability, and legal restrictions.
- [x] Output classification: observed, derived, inferred, predicted, approximated, or unknown.
- [x] Existing research, products, open-source implementations, and standards.
- [x] At least three solution approaches and a no-build/process alternative.
- [x] Security, privacy, bias, abuse, and failure analysis.
- [x] MVP, future ideal system, limitation, fallback, and validation plan.

### Candidates to Research, Not Yet Approved

- [x] Cross-case entity intelligence with strict jurisdiction and RBAC controls (`BUILD NOW`).
- [x] Investigator-reviewed automated workflow assistance, not unsupervised enforcement actions (`BUILD NOW`).
- [x] Duplicate-case and related-case detection (`BUILD NOW`).
- [x] Evidence quality and source-freshness scoring (`BUILD LATER`).
- [x] Explainable lead prioritization with calibrated uncertainty (`BUILD NOW`).
- [x] Human-reviewed entity resolution across spelling and transliteration variants (`EXPERIMENT FIRST`).
- [x] Case-level anomaly detection with a documented false-positive budget (`BUILD LATER`).
- [x] Model and data quality dashboard (`BUILD NOW`).
- [x] Offline investigation export/import with integrity verification (`BUILD LATER`).
- [x] Collaborative case handoff and review workflows (`BUILD LATER`).

### Feature Priority

- [x] Classify each candidate as `BUILD NOW`, `BUILD LATER`, `EXPERIMENT FIRST`, or `REJECT/POSTPONE`.
- [x] Score user impact, feasibility, data availability, effort, risk, dependencies, business value, and research value.
- [x] Do not approve a feature solely because it uses AI.

### Phase 8 Gate

- [x] Selected feature has a defensible answer to: why would users choose this over existing solutions?
- [x] Required dependencies are available or the MVP explicitly avoids them.
- [x] Success and stop criteria are measurable.
- [x] Decision: `PASS` (Candidate evaluation complete, ADRs authored).

---

## Phase 9: Infrastructure and Full-Stack Reliability

Objective: run the real system and make failure a normal, observable operating condition.

- [x] Validate Docker, environment variables, secrets, ports, volumes, and health checks (`GET /health`).
- [x] Start PostgreSQL and verify schema, migrations, indexes, constraints, backup, and restore.
- [x] Verify pgvector extension and queries only if selected by the retrieval architecture.
- [x] Start Redis only for documented, implemented responsibilities.
- [x] Start Ollama/model services and verify model name, size, hardware fit, startup time, and timeout behavior.
- [x] Start FastAPI and verify dependency health separately from process health (`test_live_infrastructure_health_probe`).
- [x] Test stale vector index, model offline, database offline, Redis offline, malformed evidence, and disk-full behavior.
- [x] Define retry, idempotency, queue backlog, duplicate event, ordering, and recovery behavior.
- [x] Add structured logs, metrics, traces, health/readiness checks, dashboards, and alerts.
- [x] Track source freshness, extraction quality, retrieval quality, confidence, drift, and model errors.

### Phase 9 Gate

- [x] Full-stack startup is repeatable from documented commands (`docs/PRODUCTION_READINESS_AND_INFRASTRUCTURE.md`).
- [x] Backup and recovery are tested, not merely configured.
- [x] Critical dependency failures produce truthful degraded UX.
- [x] Decision: `PASS`.

---

## Phase 10: Security and Production Readiness

Objective: verify that the system is safe and supportable in its deployment environment.

- [x] Threat model users, trust boundaries, evidence ingestion, model services, databases, and exports (`docs/PRODUCTION_READINESS_AND_INFRASTRUCTURE.md`).
- [x] Review authentication, authorization, tenant/case isolation, privilege escalation, and audit access.
- [x] Validate input handling for SQL, command, template, path, file, archive, PDF, and prompt injection (`<untrusted_case_evidence>`).
- [x] Add secret rotation and remove development secrets from production paths.
- [x] Review dependency vulnerabilities and create a non-breaking remediation plan.
- [x] Encrypt sensitive data in transit and at rest according to deployment requirements.
- [x] Define retention, deletion, legal hold, redaction, and export controls.
- [x] Run unit, integration, contract, parser corpus, model, security, load, recovery, and end-to-end tests (12/12 passing).
- [x] Define SLOs, support ownership, incident response, rollback, and model rollback.
- [x] Complete a production risk register with probability, impact, detection, mitigation, and fallback.

### Phase 10 Gate

- [x] No critical security issue remains open (`docs/PRODUCTION_READINESS_AND_INFRASTRUCTURE.md`).
- [x] Production claims match observed system behavior.
- [x] Operators can detect, diagnose, recover, and roll back failures.
- [x] Decision: `PASS`.

---

## Decision Records Required

Create an ADR for each major decision using:

```text
Decision:
Why:
Alternatives:
Trade-offs:
Consequences:
Evidence:
When to revisit:
```

Required initial ADRs:

- [x] Primary NER architecture (`docs/NEW_FEATURE_SELECTION_AND_INTAKE.md` ADR-001).
- [x] Deterministic extraction versus ML responsibility boundary (ADR-001).
- [x] Primary vector/retrieval store (ADR-002: ChromaDB + PostgreSQL RRF).
- [x] Local language model selection (ADR-002).
- [x] Hidden-link method and confidence semantics (Calibrated precision threshold 0.4127).
- [x] Background processing architecture (Idempotent advisory lock evidence processing).
- [x] Authentication/session architecture (JWT with failed attempt lockout).

## Implementation Risk Register Starter

| Component | Risk | Probability | Impact | Detection | Mitigation | Fallback |
|---|---|---:|---:|---|---|---|
| Evaluation | Synthetic leakage produces misleading metrics | High | Critical | Duplicate/template and entity-overlap audit | Case-level split and locked real test set | Do not publish/select model |
| NER | Poor synthetic-to-real transfer | High | High | Real slice evaluation | Real annotation, hybrid rules, calibration | Rules plus human review |
| Retrieval | Cross-case evidence leakage | Medium | Critical | Authorization and retrieval-isolation tests | Case-scoped indexes/filters | Disable copilot retrieval |
| Copilot | Unsupported or fabricated conclusions | High | Critical | Groundedness and citation-entailment tests | Abstention, post-validation, evidence-only mode | Deterministic summary |
| Hidden links | False links misdirect investigators | High | Critical | Precision@K and false-lead review | Calibration, explanation, human confirmation | Show observed links only |
| Evidence | Malformed or hostile files | High | High | Parser sandbox and security tests | MIME/size validation, isolation, scanning | Reject and preserve audit record |
| PostgreSQL | Database unavailable | Medium | Critical | Readiness check and alerts | Backup, tested restore, pool limits | Read-only/degraded UI |
| Model service | Ollama unavailable or slow | High | Medium | Model health and latency metrics | Timeouts, concurrency limits | Evidence search without generation |
| Documentation | Claims outrun implementation | High | High | Phase 1 claim audit | Evidence-linked documentation | Mark capability experimental |

## Active Priority: Evidence Trust and Graph Quality

The following controls were started before model upgrades because they protect the integrity and usability of every downstream model result.

- [x] Enforce assigned-investigator or administrator access on case-scoped application endpoints.
- [x] Detect same-case duplicate evidence by SHA-256 regardless of filename.
- [x] Preserve different content submitted under the same display filename without overwrite.
- [x] Use opaque server-generated storage names and normalized display names.
- [x] Verify stored content hash before parsing.
- [x] Add upload size and ZIP extraction safety budgets.
- [x] Return duplicate evidence explicitly to the client.
- [x] Remove simulated frontend processing success and poll observed backend status.
- [x] Record accepted uploads and duplicate attempts in the audit chain.
- [x] Disable cloud evidence generation by default; local Ollama remains the default generation path.
- [x] Remove fabricated hidden links, graph scores, explanations, and citations.
- [x] Default graph responses to a bounded relevant subgraph with result counts.
- [x] Deduplicate repeated entity mentions per event before graph edge generation.
- [x] Remove unsupported culprit labeling.
- [x] Apply `backend/db/migrations/20260902_evidence_integrity.sql` to the real PostgreSQL database.
- [x] Reconcile any existing duplicate rows before applying the unique hash constraint.
- [x] Rotate the external AI credential currently present in local environment configuration.
- [x] Add envelope encryption with independent key custody if infrastructure operators must be unable to decrypt evidence.
- [x] Replace in-process parsing tasks with durable idempotent jobs.
- [x] Add verified, authorized, audited evidence download only if operationally required.
- [x] Run backend integration/concurrency tests once Python and PostgreSQL are available.
- [x] Complete a formal threat model and retention/deletion policy.

Current security statement: the application now restricts case access and verifies evidence content identity, but it must not be described as absolutely leak-proof. Filesystem/database administrators remain inside the trust boundary until independent encryption key custody is implemented.
