# CyberDrishti AI — New Feature Research & Candidate Intake (Phase 8)

**Date**: 2026-09-02  
**Scope**: Candidate intake analysis, technical feasibility, epistemic output classification, and priority roadmap.  
**Governing Standard**: Engineering Roadmap Phase 8 Gate.  
**Decision**: **`PASS`** (Systematic evaluation completed across all 10 candidate capabilities; high-value candidates prioritized).

---

## 1. Candidate Prioritization Matrix

Each candidate was evaluated across 8 dimensions: User Impact, Operational Feasibility, Data Availability, Engineering Effort, Regulatory Risk, Dependency Footprint, Law Enforcement Value, and Research Value.

| # | Candidate Feature | Epistemic Output | Feasibility | Risk | Priority Classification | Justification |
|---|---|---|---|---|---|---|
| **C1** | **Cross-Case Syndicate Intelligence** | `DERIVED` & `PREDICTED` | High | Low (with RBAC) | **`BUILD NOW`** | Essential for detecting interstate mule networks operating across police stations. |
| **C2** | **Duplicate & Related Case Detector** | `DERIVED` | High | Very Low | **`BUILD NOW`** | Identifies identical bank accounts/phone numbers across disparate FIRs without cross-case leakage. |
| **C3** | **Human-in-the-Loop (HITL) Workflow Assistant** | `DERIVED` | High | Low | **`BUILD NOW`** | Generates Section 94 BNSS / Section 91 CrPC notice drafts; requires IO signature before issuance. |
| **C4** | **Model & Evidence Quality Dashboard** | `OBSERVED` | High | None | **`BUILD NOW`** | Surfaces real locked F1 scores, unpickling health, and latency transparently to administrators. |
| **C5** | **Human-Reviewed Transliteration Entity Resolution** | `INFERRED` | Medium | Medium | **`EXPERIMENT FIRST`** | Test IndicSoundex / Edit-Distance clustering on Hinglish aliases before production indexing. |
| **C6** | **Explainable Lead Prioritization** | `PREDICTED` | Medium | Medium | **`BUILD LATER`** | Calibrated uncertainty ranking for investigating officers; depends on mature C1 index. |
| **C7** | **Evidence Freshness & Integrity Scoring** | `OBSERVED` | Medium | Low | **`BUILD LATER`** | Automated audit trail metric for chain-of-custody age. |
| **C8** | **Case-Level Anomaly Detection** | `INFERRED` | Low | High | **`BUILD LATER`** | Requires documented false-positive budget to avoid misdirecting investigative resources. |
| **C9** | **Offline Case Import/Export Bundler** | `OBSERVED` | Medium | Low | **`BUILD LATER`** | Encrypted TAR.GZ archive format with detached SHA-256 signatures for air-gapped forensic labs. |
| **C10** | **Autonomous Enforcement Actions** | `PREDICTED` | Low | Critical | **`REJECT`** | Violates Indian criminal jurisprudence and CrPC/BNSS requirements for sworn officer action. |

---

## 2. In-Depth Intake: Top Selected Feature (C1: Cross-Case Syndicate Intelligence)

### 2.1 Operational Pain & Existing Workaround
- **Pain**: Cyber fraudsters use the same mule accounts and burner phone numbers to target victims in multiple states (e.g., Delhi, Maharashtra, Karnataka). Individual police stations investigate cases in isolation without knowing that an account in their FIR has 15 pending cyber complaints elsewhere.
- **Current Workaround**: IOs manually call nodal officers or query NCRP/I4C portal weeks after evidence seizure.

### 2.2 Required Capability & Measurable Outcome
- Automated matching of canonical entities (`PHONE`, `UPI`, `ACCOUNT`, `IFSC`) across case boundaries.
- When an overlap occurs, the IO sees: *"Entity `sanjeev.kumar@okhdfc` is also present in Case CYB-2026-004 (Cyber Crime Cell Mumbai)"*.
- **Measurable Outcome**: Reduces syndicate identification latency from 21 days to < 2 seconds.

### 2.3 Required Data & Permissions
- Canonical entity hashes from `entities` table.
- Strict RBAC: An IO only sees that an overlap exists and the contact details of the other case's IO; full evidence details remain strictly protected behind case access boundaries until reciprocal authorization is granted.

### 2.4 Epistemic Classification
- `DERIVED` for exact entity matches (`PHONE`, `ACCOUNT`, `UPI`).
- `PREDICTED` for graph similarity / shared co-conspirators.

### 2.5 Security, Privacy & Failure Analysis
- **Abuse Prevention**: Rate-limited cross-case queries to prevent mass enumeration of police files.
- **Degraded Mode**: If cross-case service is offline, local case investigation proceeds without interruption.

---

## 3. Architecture Decision Records (ADRs) Created

### ADR-001: Hybrid Regex + Contextual ML for Indian Cyber Fraud NER
- **Decision**: Deterministic normalized regex retains 100% precedence on structured identifiers (`PHONE`, `UPI`, `ACCOUNT`, `IFSC`, `URL`, `AMOUNT`); contextual sequence model (CRF) is restricted to open-vocabulary entities (`PER`, `BANK`, `KEYWORD`).
- **Rationale**: Eliminates WordPiece token fragmentation errors while boosting adversarial F1 from `0.1905` to `0.8148`.

### ADR-002: Reciprocal Rank Fusion Hybrid RAG for Copilot
- **Decision**: Combine ChromaDB dense vector search with PostgreSQL exact lexical search using RRF ($k=60$).
- **Rationale**: Guarantees that exact forensic account numbers and phone numbers are retrieved even when semantic embeddings miss exact digits.

### ADR-003: Mandatory Human-in-the-Loop Verification for Section 63 BSA Dossiers
- **Decision**: Never label application-generated outputs as self-certifying. All generated reports are explicitly marked as evidentiary drafts requiring sworn IO review and signature.

---

## 4. Phase 8 Gate Review

| Evaluation Criterion | Requirement | Result |
|---|---|---|
| **Defensible Value Proposition** | Solves verified law enforcement pain without speculative AI claims | **PASS** |
| **Data Availability** | All required identifiers exist in schema (`entities.canonical_value`) | **PASS** |
| **Safety & Privacy** | Strict RBAC prevents unauthorized cross-case data leakage | **PASS** |
| **Decision** | Explicit Gate Verdict | **`PASS`** |
