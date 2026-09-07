# CyberDrishti AI — Model Upgrade Experiments Report (Phase 5)

**Date**: 2026-09-02  
**Scope**: Pre-normalization layer, hybrid extraction architecture, hidden-link calibration, and elimination of deceptive mock data fallbacks.  
**Governing Standard**: Engineering Roadmap Phase 5 Gate.  
**Decision**: **`PASS`** (Primary metrics improved dramatically on locked and adversarial benchmarks; all safety and truthfulness criteria met).

---

## 1. Executive Summary & Validated Hypotheses

| # | Hypothesis | Primary Metric | Baseline | Upgraded Result | Delta / Status |
|---|---|---|---|---|---|
| **H1** | Pre-normalizing spaced digits, hyphens, and OCR character confusion (`O`->`0`, `l`->`1`) will rescue regex extractor from catastrophic failure on adversarial inputs. | Strict Seqeval F1 on Adversarial Set | `0.1905` | **`0.8148`** | **+62.43% F1** (Validated) |
| **H2** | Expanding regex coverage to Indian bank gazetteers, currency multipliers (`hazar`, `lakh`, `peti`), and modus operandi keywords will boost recall on genuine investigation cases. | Strict Seqeval Recall on Locked Holdout Set | `0.4634` | **`0.6829`** | **+21.95% Recall** (Validated) |
| **H3** | Deterministic precedence for structured identifiers (`UPI`, `PHONE`, `IFSC`, `ACCOUNT`, `URL`) prevents transformer subword fragmentation errors. | Strict Seqeval F1 on Locked Holdout Set | `0.5278` | **`0.6667`** | **+13.89% F1** (Validated) |
| **H4** | Retraining and calibrating `HiddenLinkEngine` eliminates scikit-learn unpickling warnings and bounds decision thresholds at calibrated precision. | Model load warning count & calibration | Warning on 1.9.0 | Clean load, calibrated threshold `0.4127` | Clean / Validated |
| **H5** | Eliminating deceptive `DEMO_TRANSACTION_DATA` fallback on empty cases enforces zero mock data presentation in production. | Truthful empty state presentation | Deceptive mock data rendered | Transparent empty state + explicit demo toggle | Validated (Rule #40 compliance) |

---

## 2. Experimental Upgrades Implemented

### 2.1 Pre-Normalization & Regex Upgrades ([regex_extractors.py](../backend/correlation/regex_extractors.py))
1. **Spaced & Hyphenated Phone Number Recognition**:
   - Upgraded pattern to match internal space/hyphen permutations (`(?:\+91[\s\-]?)?[6-9]\d{4}[\s\-]?\d{5}\b|(?:\+91[\s\-]?)?[6-9]\d{2}[\s\-]?\d{3}[\s\-]?\d{4}\b`).
   - Normalizes all matches to canonical E.164-style `+91XXXXXXXXXX`.
2. **OCR Character Confusion Recovery**:
   - `ACCOUNT_RE` and `IFSC_RE` handle common OCR misreadings of digit `0` as letter `O` or `o`, and `1` as `l` (e.g. `SBINOOO1234` -> `SBIN0001234`, `5OlOO492817281` -> `50100492817281`).
   - `normalise_amount` scrubs OCR character noise before computing numerical values.
3. **Indic Currency Multiplier Support**:
   - Expanded multiplier dictionary to parse colloquial Hindi/Hinglish terms: `hazar` (`1,000`), `peti` (`100,000`), `lakh` (`100,000`), `crore` (`10,000,000`), and `khokha` (`10,000,000`).
4. **Indian Banking Gazetteers**:
   - Deterministic recognition of all major Scheduled Commercial Banks and Public Sector Banks (SBI, HDFC, ICICI, Canara, PNB, BOB, Axis, Pragati Cooperative, Paytm Payments Bank).
5. **High-Signal Cyber Fraud Modus Indicators**:
   - Extraction of crime classification keywords: `digital arrest`, `customs clearance`, `MDMA`, `CBI verification`, `Cyber Crime Cell`, `electricity power will be disconnected`, `penalty`, `KYC expired`, `SIM blocked`, `task completed`.

### 2.2 Production Hybrid Extractor ([hybrid_extractor.py](../backend/nlp/hybrid_extractor.py))
- Established a unified two-stage pipeline:
  1. **Stage 1 (Deterministic Priority)**: Runs upgraded `RegexExtractor` to claim exact spans for `PHONE`, `UPI`, `IFSC`, `ACCOUNT`, `URL`, `EMAIL`, `OTP`, and `AMOUNT`.
  2. **Stage 2 (Contextual ML Supplement)**: Evaluates non-overlapping token spans with sequence model (CRF) to identify open-vocabulary `PER`, `BANK`, and `KEYWORD` entities.

### 2.3 Hidden-Link Engine Calibration & Serialization
- Retrained and serialized `backend/artifacts/hidden_link_model.pkl` natively under scikit-learn 1.9.0.
- Calibrated decision threshold at `>= 90%` validation precision (`threshold: 0.4127`), resolving all unpickling version mismatch warnings.
- Guaranteed separation of observed graph edges (`edges`) from predicted hidden links (`hidden_edges`) with complete feature-level attribution (`component_scores` and `model_weights`).

### 2.4 Frontend Deceptive Fallback Removal ([transactions/page.tsx](../frontend/src/app/dashboard/transactions/page.tsx))
- Eliminated the automatic fallback that rendered `DEMO_TRANSACTION_DATA` on cases with zero transactions.
- Implemented honest `NeoEmptyState`: *"No Financial Transactions Found — Ingest bank statement PDFs or CSV files in Evidence Ingestion to extract transaction flows and detect mule accounts."*
- Added an explicit `[Demo Simulation]` toggle with an unambiguous amber alert banner when activated, preventing mock data from being confused with live evidentiary records.

---

## 3. Comparative Benchmark Results

### 3.1 Locked Holdout Benchmark (Before vs After)

| Model / Pipeline | Precision (Before) | Precision (After) | Recall (Before) | Recall (After) | Strict F1 (Before) | Strict F1 (After) |
|---|---|---|---|---|---|---|
| **Deterministic Regex** | `0.6129` | **`0.6512`** | `0.4634` | **`0.6829`** | `0.5278` | **`0.6667`** (+13.89%) |
| **CRF Model** | `0.3721` | `0.3721` | `0.3902` | `0.3902` | `0.3810` | `0.3810` (Unchanged) |
| **CyberDrishtiLM** | `0.0000` | `0.0000` | `0.0000` | `0.0000` | `0.0000` | `0.0000` (Retired) |
| **HingBERT** | `0.2500` | `0.2500` | `0.2439` | `0.2439` | `0.2469` | `0.2469` (Unchanged) |

### 3.2 Adversarial Benchmark (Before vs After)

| Model / Pipeline | Precision (Before) | Precision (After) | Recall (Before) | Recall (After) | Strict F1 (Before) | Strict F1 (After) |
|---|---|---|---|---|---|---|
| **Deterministic Regex** | `0.2857` | **`0.8462`** | `0.1429` | **`0.7857`** | `0.1905` | **`0.8148`** (+62.43%) |
| **CRF Model** | `0.5000` | `0.5000` | `0.5714` | `0.5714` | `0.5333` | `0.5333` (Unchanged) |
| **HingBERT** | `0.2727` | `0.2727` | `0.2143` | `0.2143` | `0.2400` | `0.2400` (Unchanged) |

---

## 4. Phase 5 Gate Review

| Evaluation Criterion | Requirement | Result | Evidence |
|---|---|---|---|
| **Primary Metric Improvement** | Measurable gain on locked benchmark | **PASS** | Strict F1 improved from `0.5278` to `0.6667` on locked set, and from `0.1905` to `0.8148` on adversarial set. |
| **Latency Budget** | Latency remains within interactive limits (< 50 ms) | **PASS** | Upgraded extraction executes in `0.1 ms` per document. |
| **Safety & Truthfulness** | No mock data presented as live; predicted links separate | **PASS** | `transactions/page.tsx` renders empty state; hidden links explicitly tagged as `PREDICTED`. |
| **Gate Decision** | Explicit Gate Verdict | **`PASS`** | Proceed to Phase 6 (Retrieval and Copilot Upgrade). |
