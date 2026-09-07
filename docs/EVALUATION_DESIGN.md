# CyberDrishti AI — Evaluation Design & Annotation Guidelines (Phase 2)

**Last Updated**: 2026-09-02  
**Purpose**: Define trustworthy, reproducible, non-leaked evaluation benchmarks and metrics for CyberDrishti AI models and parsers.  
**Governing Standard**: Engineering Roadmap Phase 2 Gate.

---

## 1. Why the Legacy Evaluation Failed

The Phase 1 baseline audit proved that legacy model evaluations were compromised:
- **100% Template Leakage**: All 809 test sentences in `test.jsonl` were generated from the exact same synthetic grammar templates as the training set.
- **15.45% Exact Duplicates**: 125 sentences in `test.jsonl` were identical word-for-word copies of sentences in `train.jsonl`.
- **Inflated Metrics**: This produced an artificial CRF F1 score of `1.0000`, while real transformer models (CyberDrishtiLM and HingBERT) scored `0.0059` and `0.1454` respectively.
- **Hard-coded Dummies**: The validation script `backend/nlp/validate_real_data.py` returned hard-coded dictionary constants (`0.73` and `0.77`) instead of running real inference.

**Core Rule**: No model shall be evaluated on random sentence splits of template-generated text. Evaluation must use case-level and document-level splits with zero entity and template overlap.

---

## 2. Evaluation Split Architecture

Evaluation assets are split into three strictly isolated sets:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        EVALUATION CORPUS                               │
├──────────────────────────────────┬─────────────────────────────────────┤
│  1. Locked Test Benchmark        │  2. Adversarial & Robustness Set    │
│  - Case-level holdout            │  - OCR noise & character confusion  │
│  - Real investigation documents  │  - Disguised/spaced phone numbers   │
│  - Zero entity/template leakage  │  - Non-standard Hinglish slang      │
│  - Document-level coherence      │  - Ambiguous & nested entities      │
└──────────────────────────────────┴─────────────────────────────────────┘
```

### 2.1 Split Guardrails
1. **Case-Level Isolation**: All evidence from an investigation (FIR, chat export, bank statement, CDR) belongs exclusively to one split.
2. **Entity Value Disjointness**: A phone number, UPI ID, account number, or person name appearing in Train/Val MUST NEVER appear in the Locked Test set.
3. **No Prompt or Hyperparameter Tuning on Locked Test**: The locked test set is evaluated strictly as a final gate. If a model is tuned on it, the test set is considered burned.

---

## 3. Indic Hinglish Entity Annotation Guidelines

### 3.1 Entity Types & Definitions

| Entity Tag | Category | Definition | In-Scope Examples | Out-of-Scope Examples |
|---|---|---|---|---|
| `PER` | Person Name | Individual human suspect, victim, officer, or decoy. | `Ankita`, `Suresh Sharma`, `Deepak Patil`, `Dr. V. K. Rao` | Company names, bank names (`HDFC`), bot usernames. |
| `PHONE` | Phone Number | 10-digit Indian mobile numbers with or without country code, spaces, hyphens. | `+919876543210`, `9876543210`, `098765-43210`, `98765 43210` | Account numbers, transaction reference IDs, landlines with STD (unless tagged `PHONE_LANDLINE`). |
| `UPI` | UPI VPA | Virtual Payment Address handle. | `sanjeev.kumar@okhdfc`, `9876543210@ybl`, `fraudster@paytm` | Standard email addresses (`test@gmail.com`). |
| `ACCOUNT` | Bank Account | 9 to 18-digit bank account number. | `50100234567891`, `918273645019` | Phone numbers (10 digits starting with 6-9), UPI reference numbers. |
| `AMOUNT` | Monetary Value | Indian Rupee currency representations. | `₹68,000`, `Rs. 45000`, `2.5 lakh`, `50k`, `1.2 crore` | Generic numbers without monetary context (e.g. `68000 units`). |
| `BANK` | Banking Institution | Indian Scheduled Commercial Bank, Cooperative, Payment Bank, or SFB. | `HDFC Bank`, `SBI`, `Pragati Cooperative Bank`, `Paytm Payments Bank` | Merchant names, non-bank fintech apps (`PhonePe` without bank). |
| `OTP` | Security Code | 4 to 8-digit One-Time Password mentioned in chats/SMS. | `719462`, `OTP 482913`, `code is 9912` | Year numbers (`2024`), amounts, PIN codes with postal context. |
| `EMAIL` | Email Address | Standard electronic mail address. | `cyber.cell@delhipolice.gov.in`, `investor99@gmail.com` | UPI handles (`name@okhdfcbank`). |
| `URL` | Web Link | Malicious phishing link, fake APK download link, or portal domain. | `https://sbi-kyc-update.top`, `t.me/crypto_doubling`, `bit.ly/claim-tax` | Standard non-incriminating references unless evidence-linked. |
| `IFSC` | Bank Branch Code | 11-character Indian Financial System Code (`^[A-Z]{4}0[A-Z0-9]{6}$`). | `HDFC0001234`, `SBIN0004567`, `PUNB0123400` | Account numbers, random alphanumeric strings. |
| `LOCATION` | Geographical Point | Indian city, state, telecom tower sector, or address. | `Delhi`, `Mewat`, `Cyberabad`, `DEL-TWR-021`, `Sector 62 Noida` | Country-wide generalities ("India"). |
| `KEYWORD` | Cyber Fraud Indicator | High-signal modus operandi terms used for extortion and scamming. | `digital arrest`, `customs clearance`, `drugs in parcel`, `KYC expired`, `CBI notice`, `SIM block` | Everyday neutral words ("hello", "payment"). |

### 3.2 Boundary and Code-Mixing Rules
1. **Currency Symbols & Units**:
   - Currency symbol is included in the span if attached: `[₹68,000]` or `[Rs. 45000]`.
   - Multipliers are included: `[2.5 lakh]`, `[50k]`, `[1.2 crore]`.
2. **Country Codes & Formatting**:
   - Phone prefixes `+91`, `0`, or `91` must be included in the `B-PHONE` / `I-PHONE` span.
3. **Transliterated Hinglish**:
   - Hindi words in Latin script are annotated identically:
     - *"Bhai [sanjeev.kumar@okhdfc](UPI) pe [68000](AMOUNT) bhej de, [Ankita](PER) ne bola hai."*
4. **Disambiguation Principles**:
   - When a 10-digit number is ambiguous (Phone vs Account vs UTR):
     - If preceded by `+91`, `call`, `WhatsApp`, `dial`: tag as `PHONE`.
     - If preceded by `A/C`, `account`, `credited to`: tag as `ACCOUNT`.
     - If preceded by `Ref`, `UTR`, `Txn`: tag as `KEYWORD` or parser metadata.

---

## 4. Capability Metric Formulations

### 4.1 Named Entity Recognition (NER)
- **Strict Entity-Level Precision / Recall / F1**: Evaluated via Seqeval under IOB2 scheme. Partial boundary matches are counted as errors.
- **Per-Class Breakdown**: Separate F1 computed for each of the 12 entity types. Macro-averaged and weighted-averaged F1 reported.
- **Boundary Error Rate**: Count of predicted spans overlapping a ground-truth entity with incorrect token boundaries.

### 4.2 Parsers (CDR, Bank Statements, WhatsApp)
- **Field-Level Exact Match Rate (EMR)**: Percentage of parsed rows where all critical fields (Date, Amount, Sender, Recipient, Ref) match ground truth exactly.
- **Normalized Match Rate (NMR)**: Percentage of fields matching after standard normalization (e.g. phone numbers stripped of spaces/dashes, dates in ISO 8601).
- **Missing Field Rate (MFR)**: Percentage of expected ground-truth fields left empty by the parser.
- **False Extraction Rate (FER)**: Non-existent records synthesized by parser misinterpretation.

### 4.3 Hidden-Link Combiner
- **Precision@5 / Precision@10**: Proportion of top-ranked hidden links that represent true undisclosed conspirators or shared infrastructure.
- **PR-AUC (Precision-Recall Area Under Curve)**: Area under precision-recall curve across all thresholds.
- **False Lead Rate (FLR)**: Proportion of flagged links with zero corroborating financial, telecom, or physical overlap.
- **Brier Score / Calibration Error**: Mean squared difference between predicted probability and observed edge existence.

### 4.4 RAG & Copilot Answers
- **Citation Precision**: Proportion of generated statements with an attached citation where the cited excerpt actually contains the factual claim.
- **Span Existence Rate**: Proportion of cited file/line/page spans that exist verbatim in the case evidence.
- **Abstention Quality**: Model's ability to respond with *"Insufficient evidence in case record"* when queried on unrecorded facts, rather than hallucinating plausible details.
- **Harmful Hallucination Rate**: Generation of fabricated suspects, fake confession quotes, or false bank accounts. Target: **`0.00%`**.

---

## 5. Phase 2 Gate Criteria

To pass Phase 2, the project must fulfill:
1. **Dataset Integrity**: Locked test set created with zero template leakage and zero entity overlap.
2. **Adversarial Set**: Explicit edge-case evaluation set provided with perturbed and noisy inputs.
3. **Real Inference Runner**: Automated evaluation script executing real inference (no constants/placeholders).
4. **Baseline Metrics Recorded**: Honest baseline numbers established on the locked dataset.
