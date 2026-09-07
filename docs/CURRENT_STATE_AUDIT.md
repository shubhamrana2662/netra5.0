# CyberDrishti AI — Current State & Claim Audit (Phase 1)

**Date**: 2026-09-02  
**Audit Scope**: Repository inventory, model checkpoint verification, data leakage analysis, dependency and infrastructure validation, route-to-backend capability mapping, and truthful claim classification.  
**Roadmap Phase**: Phase 1 Baseline and Claim Audit  
**Audit Gate Decision**: **`PASS`** (All documented claims classified with reproducible evidence; ground truth established).

---

## 1. Executive Summary

This audit establishes the empirical baseline of the CyberDrishti AI platform before beginning model upgrades (Phase 2+).

Key discoveries:
1. **Model Claim Discrepancies**:
   - **CyberDrishtiLM**: Documentation claimed F1 `0.9489`. In reality, the saved checkpoint evaluation (`backend/artifacts/cyberdrishtilm/test_metrics.json`) records `ner_f1 = 0.0059` (0.59%). In `backend/nlp/validate_real_data.py`, metrics are hard-coded dummy returns (`precision: 0.75, recall: 0.72, f1: 0.73`).
   - **HingBERT**: Documentation claimed F1 `0.91`. The actual saved evaluation artifact (`backend/artifacts/hingbert/test_metrics.json`) records `eval_ner_f1_macro = 0.1454` (14.5%). In `backend/nlp/validate_real_data.py`, metrics are hard-coded dummy returns (`precision: 0.78, recall: 0.76, f1: 0.77`).
   - **CRF (Conditional Random Field)**: Claimed F1 `1.0000`. Audit confirms the model achieves 1.0 on `test.jsonl`, but reveals **100% template leakage**: every single test sample (809/809) was derived from a training template, and 125 test sentences (15.5%) are exact word-for-word duplicates of training sentences.
2. **Infrastructure Truth**:
   - **PostgreSQL 16**: Active and running on `127.0.0.1:5432` with full integrity constraints (`uq_evidence_case_sha256`, `uq_evidence_storage_path`, `ck_evidence_size`) and transaction-level advisory locks.
   - **pgvector**: Claimed in README and product documentation; in reality, pgvector is **not installed** (`0 rows` in `pg_available_extensions`) and zero database columns use vector types.
   - **ChromaDB**: Active as embedded SQLite at `backend/artifacts/chroma_db` (1.4 MB) containing 21 existing case collections. The Python dependency was absent from the local virtual environment, causing a 500 error on copilot requests until installed during this audit (`chromadb-1.5.9`).
   - **Redis**: Configured in settings and `requirements.txt`, but completely **unused** in runtime application logic.
   - **Ollama**: Local Ollama was offline. When offline, copilot queries fell back to a hardcoded synthetic case script (`_get_dedicated_case_response` in `backend/rag/copilot.py`), returning details of the "Ankita Digital Arrest Extortion Scam" even for newly created, unrelated cases.
3. **Frontend Truth**:
   - The majority of pages connect to real FastAPI endpoints.
   - However, `dashboard/transactions` falls back to `DEMO_TRANSACTION_DATA` whenever a case has no transactions, presenting fake mule accounts and transactions to investigators.
   - `dashboard/field` embeds a static WebGL prototype via `/newfront.html`.
   - `dashboard/intel/cross-match` queries entities across all cases in the database without enforcing investigator assignment or jurisdictional RBAC boundaries.

---

## 2. Hardware and Runtime Inventory

| Component | Audit Observation | Specification / Path |
|---|---|---|
| **Host Machine** | Apple Silicon | Apple M5, macOS (Darwin arm64) |
| **Unified Memory** | 16 GB RAM | 17,179,869,184 bytes |
| **Disk Storage** | APFS root volume | 460 GiB total, 286 GiB available |
| **Python Runtime** | Active Virtualenv | Python 3.12.13 (`backend/.venv`) |
| **Web Runtime** | Node.js / Next.js | Node 20+, Next.js 14.2.5 (Turbopack) |
| **PostgreSQL** | Local Service | PostgreSQL 16.15 (Homebrew) on port 5432 |
| **pgvector** | Database Extension | **Not Installed** |
| **ChromaDB** | Embedded Vector Store | Persistent Client (`backend/artifacts/chroma_db`) |
| **Redis** | In-Memory Cache | **Not Running / Unused** |
| **Ollama** | Local LLM Server | Port 11434 (Currently Offline) |
| **OCR Engine** | Tesseract | `pytesseract` library installed |

---

## 3. Model Inventory and Evaluation Audit

### 3.1 Model Checkpoint Summary

| Model | Artifact Path | Size | Real Saved Metric | Documented Claim | Audit Finding |
|---|---|---|---|---|---|
| **CRF** | `backend/artifacts/crf/crf_model.pkl` | 72 KB | F1: `1.0000` | F1: `1.0000` | **100% Template Leakage**; 125 exact duplicate sentences in test split. |
| **CyberDrishtiLM** | `backend/artifacts/cyberdrishtilm/pytorch_model.bin` | 4.7 MB | NER F1: `0.0059` | F1: `0.9489` | **Contradicted by saved metrics**; `validate_real_data.py` uses hardcoded dummy metrics (`0.73`). |
| **HingBERT** | `backend/artifacts/hingbert/model.safetensors` | 904 MB | Macro F1: `0.1454` | F1: `0.9100` | **Contradicted by saved metrics**; `validate_real_data.py` uses hardcoded dummy metrics (`0.77`). |
| **Hidden-Link Combiner** | `backend/artifacts/hidden_link_model.pkl` | 1.2 KB | Threshold: `0.8955` | Precision: `≥90%` | Pickled Logistic Regression on 7 graph features; serialized with sklearn 1.5.2 (warns on 1.9.0). Evaluated only on synthetic graphs. |
| **Copilot RAG** | `backend/rag/copilot.py` | — | Chroma Top-K | Generative RAG | Falls back to hardcoded Case 02 ("Ankita Extortion") responses when LLM is offline or case is empty. |

### 3.2 Dataset Leakage Analysis

The dataset located in `backend/artifacts/training_data/` consists of:
- `train.jsonl`: 6,396 sentences (1.6 MB)
- `val.jsonl`: 795 sentences (198 KB)
- `test.jsonl`: 809 sentences (203 KB)

**Generator Source**: `backend/nlp/generate_ner_training_data.py`  
The dataset was synthetically generated by populating fixed sentence templates from small entity pools (32 first names, 15 last names, 10 banks, 9 UPI suffixes).

**Leakage Audit Execution Results**:
- **Test Samples**: 809
- **Test Sentences Matching a Training Template**: 809 / 809 (**100.00%**)
- **Exact Identical Sentences Across Train and Test**: 125 sentences (**15.45%**)

**Conclusion on CRF F1 1.0**:  
The CRF model did not generalize; it memorized synthetic template grammar and exact token distributions. The F1 1.0 metric is an artifact of evaluation on a leaked, non-independent test split.

### 3.3 Placeholder Metrics in `validate_real_data.py`

In `backend/nlp/validate_real_data.py`, lines 46–66:
```python
def evaluate_cdlm(sentences, true_labels, model_dir):
    # Placeholder: load model checkpoint and run inference
    # For now, return dummy metrics
    return {"precision": 0.75, "recall": 0.72, "f1": 0.73}

def evaluate_hingbert(sentences, true_labels, model_dir):
    return {"precision": 0.78, "recall": 0.76, "f1": 0.77}
```
Real inference was never implemented in this evaluation script. These placeholder constants must never be reported as real-world benchmarks.

---

## 4. Frontend Route to Backend Capability Matrix

| Frontend Route | Primary Component | Backend Endpoint | Backing Architecture | Live vs Mock / Simulated |
|---|---|---|---|---|
| `/` | Landing Gateway | — | Next.js Client | Static redirect to `/login` |
| `/login` | `AuthGateway.tsx` | `POST /api/v1/auth/login`<br>`GET /api/v1/auth/me` | FastAPI + JWT + PostgreSQL (`users`) | **Live** (Cinematic unlock + bearer token storage) |
| `/dashboard` | `page.tsx`, `CitadelHUD` | `GET /api/v1/cases`<br>`GET /api/v1/copilot/status` | FastAPI + PostgreSQL | **Live** (Aggregates active cases, telemetry) |
| `/dashboard/cases` | `cases/page.tsx` | `GET /api/v1/cases`<br>`POST /api/v1/cases` | FastAPI + PostgreSQL (`cases`, `audit_log`) | **Live** (Full CRUD and case creation with audit) |
| `/dashboard/cases/[id]` | `cases/[id]/page.tsx` | `GET /api/v1/cases/{id}` | FastAPI + PostgreSQL | **Live** (Case details and access controls) |
| `/dashboard/evidence` | `evidence/page.tsx` | `POST /api/v1/evidence/upload`<br>`GET /api/v1/evidence/{case_id}` | FastAPI + File Storage + SHA-256 Check | **Live** (Deduplication, advisory lock, storage isolation) |
| `/dashboard/graph` | `graph/page.tsx` | `GET /api/v1/graph/{case_id}` | NetworkX + Topological Subgraph Builder | **Live** (Bounded node/edge limits, strictly observed links) |
| `/dashboard/timeline` | `timeline/page.tsx` | `GET /api/v1/timeline/{case_id}` | PostgreSQL (`evidence_events`) | **Live** (Chronological event sequencing) |
| `/dashboard/copilot` | `copilot/page.tsx` | `POST /api/v1/copilot/{case_id}` | ChromaDB + Ollama RAG (fallback script) | **Hybrid** (Chroma active; falls back to static Case 02 script when Ollama offline) |
| `/dashboard/reports` | `reports/page.tsx` | `GET /api/v1/report/{case_id}` | FastAPI + Report Generator | **Live** (Derived findings and Section 65B template) |
| `/dashboard/audit` | `audit/page.tsx` | `GET /api/v1/audit` | PostgreSQL (`audit_log` with SHA-256 chain) | **Live** (Tamper-evident audit chain) |
| `/dashboard/officers` | `officers/page.tsx` | `GET /api/v1/officers`<br>`POST /api/v1/officers` | PostgreSQL (`users`) | **Live** (User/Officer management with RBAC) |
| `/dashboard/intel` | `intel/page.tsx` | `GET /api/v1/intel/cross-match` | PostgreSQL (`entities`, `cases`) | **Live but Insecure** (Cross-case entity match without RBAC/jurisdiction filter) |
| `/dashboard/agent` | `agent/page.tsx` | `GET /api/v1/agent/{case_id}/status`<br>`POST /api/v1/agent/{case_id}/run` | In-memory agent registry + ArmorIQ sandbox | **Partial** (DAG stages s1-s5 partly hardcoded; in-memory sessions) |
| `/dashboard/field` | `field/page.tsx` | — | Embedded iframe `/newfront.html` | **Prototype** (Static WebGL visualization) |
| `/dashboard/transactions` | `transactions/page.tsx` | `GET /api/v1/cases/{case_id}/transactions` | FastAPI parser / analytics | **Deceptive Fallback** (Renders `DEMO_TRANSACTION_DATA` when transactions list is empty) |
| `/dashboard/communications` | `communications/page.tsx` | `GET /api/v1/cases/{case_id}/communications` | FastAPI CDR parser / analytics | **Live** (CDR call logs and chat records) |
| `/dashboard/settings` | `settings/page.tsx` | Local UI state | Client-side Zustand | **Client-only** (Theme and local preferences) |

---

## 5. Verified Claims vs Unverified / False Claims

### 5.1 Verified Claims
- [x] **Case-Scoped Access Boundaries**: Non-admin, unassigned users receive 404 on protected case endpoints without leaking case existence.
- [x] **SHA-256 Evidence Deduplication**: Duplicate uploads with identical byte payloads (under the same or different filenames) are flagged as duplicates (`duplicate_count: 1`) and recorded in the audit log.
- [x] **Non-Overwriting Storage Isolation**: Submitting different bytes under an identical original filename assigns a unique server storage UUID, preventing evidence overwrite.
- [x] **Concurrent Ingestion Safety**: Concurrent upload tasks on identical bytes serialize safely under PostgreSQL advisory locks without unique constraint crashes.
- [x] **Bounded Graph Responses**: Case graphs enforce node limits (default 40), edge limits (default 100), and return truthful empty graphs (`nodes: [], edges: []`) for unpopulated cases rather than fabricated samples.
- [x] **Tamper-Evident Audit Chain**: Audit entries compute SHA-256 hash chains over prior entries with advisory transaction serialization.

### 5.2 False / Contradicted Claims
- [ ] **CyberDrishtiLM F1 0.9489**: False. Checkpoint test metric is `0.0059`.
- [ ] **HingBERT F1 0.91**: False. Checkpoint test metric is `0.1454`.
- [ ] **CRF Real-World F1 1.0**: False. Result of 100% template leakage and 15.5% identical training sentences in the test set.
- [ ] **pgvector Active Vector Database**: False. pgvector extension is not installed in PostgreSQL, and no vector columns exist.
- [ ] **Redis Durable Queue/Cache**: False. Redis is not used anywhere in running backend code.
- [ ] **Zero-Hallucination Arbitrary Copilot**: False. When Ollama is offline, copilot returns the pre-written script for Case 02 regardless of the case queried.

### 5.3 Unverified Claims / Gaps Requiring Phase 2+ Action
- [ ] **Hidden-Link Real Precision**: Scikit-learn model trained only on synthetic graph co-occurrences; precision in real investigations is unmeasured.
- [ ] **Cross-Case Entity Intelligence Governance**: Endpoint `/api/v1/intel/cross-match` exposes all department cases to any authenticated officer without case assignment checks.
- [ ] **Durable Background Tasks**: Ingested files are currently parsed in FastAPI background threads rather than durable worker queues (e.g. Celery / RQ / Arq).

---

## 6. Phase 1 Review Gate

| Evaluation Criterion | Standard | Result | Evidence |
|---|---|---|---|
| **Correctness** | All claims classified as verified, unverified, outdated, or false | **PASS** | Section 5 classifications backed by runtime inspection. |
| **Data Integrity** | Dataset origin and split methods documented | **PASS** | Section 3.2 documents synthetic generator, 100% template overlap, and duplicate sentences. |
| **Reproducibility** | Baseline commands run from clean environment | **PASS** | 8/8 automated backend integration tests pass; machine-readable inventory produced in `docs/system_inventory.json`. |
| **Decision** | Explicit gate verdict | **`PASS`** | Ground truth established. Proceed to Phase 2 (Data Feasibility and Evaluation Design). |
