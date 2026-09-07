# 🏗️ CyberDrishti AI — System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         🌐 FRONTEND (Next.js 14)                            │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │  Dashboard  │  │    Cases    │  │    Graph    │  │  Timeline   │      │
│  │  (Screen 1) │  │ (Screen 2,3)│  │  (Screen 4) │  │  (Screen 5) │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │   Comms     │  │Transactions │  │  Evidence   │  │  Analytics  │      │
│  │  (Screen 6) │  │  (Screen 7) │  │  (Screen 8) │  │  (Screen 9) │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │   Copilot   │  │   Reports   │  │    Audit    │  │   Officers  │      │
│  │ (Screen 10) │  │ (Screen 11) │  │ (Screen 12) │  │ (Screen 13) │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
│                                                                             │
│  ┌─────────────┐          ┌──────────────────────────────────┐            │
│  │   Settings  │          │   Zustand Stores (4)             │            │
│  │ (Screen 14) │          │   - investigation  - copilot     │            │
│  └─────────────┘          │   - selection      - ui          │            │
│                           └──────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Axios API Client (JWT)
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                         🔧 BACKEND (FastAPI)                                │
│                                                                             │
│  ┌────────────────────── API Routes (9) ──────────────────────┐            │
│  │  /auth     │ JWT login, me                                 │            │
│  │  /cases    │ CRUD, stats                                   │            │
│  │  /evidence │ Upload, extraction                            │            │
│  │  /graph    │ Entity graph, hidden links                    │            │
│  │  /timeline │ Chronological events                          │            │
│  │  /copilot  │ Ollama RAG chat                               │            │
│  │  /report   │ Section 65B PDF                               │            │
│  │  /audit    │ Audit logs, verification                      │            │
│  │  /officers │ User management                               │            │
│  └──────────────────────────────────────────────────────────────┘          │
│                                      │                                      │
│  ┌───────────────── Evidence Parsers (4) ────────────────┐                 │
│  │  WhatsApp Parser  │  Bank PDF Parser                  │                 │
│  │  CDR Parser       │  OCR Parser (Tesseract+Paddle)    │                 │
│  └─────────────────────────────────────────────────────────┘               │
│                                      │                                      │
│  ┌───────────────── NLP/ML Pipeline ─────────────────────┐                 │
│  │                                                        │                 │
│  │  ┌──────────────────────────────────────────────┐    │                 │
│  │  │  Synthetic Data Generator                    │    │                 │
│  │  │  (8,000 Hinglish sentences, 12 entity types) │    │                 │
│  │  └──────────────────────────────────────────────┘    │                 │
│  │                          │                            │                 │
│  │         ┌────────────────┼────────────────┐           │                 │
│  │         │                │                │           │                 │
│  │  ┌──────▼──────┐  ┌──────▼──────┐  ┌─────▼─────┐    │                 │
│  │  │CyberDrishtiLM│  │   HingBERT  │  │    CRF    │    │                 │
│  │  │(Custom 2.3M) │  │ Fine-tuned  │  │  Baseline │    │                 │
│  │  │              │  │             │  │           │    │                 │
│  │  │ F1: 0.9489   │  │  F1: 0.91   │  │ F1: 0.76  │    │                 │
│  │  └──────────────┘  └─────────────┘  └───────────┘    │                 │
│  │                          │                            │                 │
│  │  ┌─────────────────────────────────────────────┐     │                 │
│  │  │  Model Comparison & Selection               │     │                 │
│  │  └─────────────────────────────────────────────┘     │                 │
│  │                          │                            │                 │
│  │  ┌─────────────────────────────────────────────┐     │                 │
│  │  │  Hidden-Link Graph Engine                   │     │                 │
│  │  │  • 6 features (Jaccard, AA, Temporal, etc.) │     │                 │
│  │  │  • Logistic regression combiner             │     │                 │
│  │  │  • Explainability (component scores)        │     │                 │
│  │  └─────────────────────────────────────────────┘     │                 │
│  │                          │                            │                 │
│  │  ┌─────────────────────────────────────────────┐     │                 │
│  │  │  Ollama RAG Copilot                         │     │                 │
│  │  │  • llama3.2:1b local inference              │     │                 │
│  │  │  • Statutory citation lookup                │     │                 │
│  │  │  • Citation validator                       │     │                 │
│  │  └─────────────────────────────────────────────┘     │                 │
│  │                                                        │                 │
│  └────────────────────────────────────────────────────────┘                │
│                                      │                                      │
│  ┌─────────────────── Utilities ──────────────────────┐                    │
│  │  Regex Extractors (11 types)  │  Audit Chain      │                    │
│  │  Section 65B PDF Generator     │  Hash Utilities   │                    │
│  └────────────────────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                        ┌─────────────┴─────────────┐
                        │                           │
┌───────────────────────▼──────┐   ┌────────────────▼──────────┐
│    PostgreSQL 16 (DB)        │   │      Redis 7 (Cache)      │
│                              │   │                           │
│  Tables (8):                 │   │  • Session storage        │
│  • users                     │   │  • Rate limiting          │
│  • cases                     │   │  • Job queue              │
│  • evidence_files            │   │                           │
│  • evidence_events           │   └───────────────────────────┘
│  • entities                  │
│  • entity_mentions           │   ┌───────────────────────────┐
│  • correlations              │   │     Ollama (Optional)     │
│  • audit_log                 │   │                           │
│                              │   │  • llama3.2:1b            │
│  SQLAlchemy ORM              │   │  • Local inference        │
│  Tamper-evident audit chain  │   │  • No cloud costs         │
└──────────────────────────────┘   └───────────────────────────┘


════════════════════════════════════════════════════════════════════════════════
                            🔄 DATA FLOW
════════════════════════════════════════════════════════════════════════════════

1. USER UPLOADS EVIDENCE
   ↓
2. PARSER EXTRACTS EVENTS → evidence_events table
   ↓
3. NER MODEL EXTRACTS ENTITIES → entities + entity_mentions tables
   ↓
4. HIDDEN-LINK ENGINE BUILDS GRAPH → correlations table
   ↓
5. TIMELINE GENERATED → Sorted events with timestamps
   ↓
6. USER ASKS COPILOT QUESTION
   ↓
7. RAG RETRIEVES RELEVANT EVIDENCE + GENERATES ANSWER
   ↓
8. SECTION 65B REPORT GENERATED → PDF with hash table + audit chain


════════════════════════════════════════════════════════════════════════════════
                            🎯 KEY FEATURES
════════════════════════════════════════════════════════════════════════════════

✅ Custom Hinglish NER (CyberDrishtiLM, HingBERT, CRF)
✅ 12 entity types (PHONE, UPI, ACCOUNT, AMOUNT, EMAIL, PER, ORG, LOC, etc.)
✅ Hidden-link detection with explainability
✅ Ollama RAG copilot with statutory citations
✅ Tamper-evident audit chain (SHA-256 blockchain-style)
✅ Section 65B evidence certificate (PDF)
✅ 4 evidence parsers (WhatsApp, Bank, CDR, OCR)
✅ 14 production-ready UI screens
✅ Glassmorphic design system
✅ JWT authentication + RBAC
✅ Full CRUD for cases, evidence, officers


════════════════════════════════════════════════════════════════════════════════
                            📊 TECH STACK
════════════════════════════════════════════════════════════════════════════════

Backend:    FastAPI 0.115.0, PostgreSQL 16, Redis 7, PyTorch 2.5.0
Frontend:   Next.js 14.2.5, React 18.3.1, Tailwind CSS 3.4.10, Zustand 4.5.4
ML:         Transformers 4.46.0, sklearn-crfsuite 0.5.0, Ollama
Infra:      Docker Compose, WeasyPrint (PDF), Tesseract + PaddleOCR


════════════════════════════════════════════════════════════════════════════════
                    🚀 DEPLOYMENT ARCHITECTURE (Production)
════════════════════════════════════════════════════════════════════════════════

┌──────────────────────┐
│   Vercel / Netlify   │  Frontend (Next.js static export)
└──────────┬───────────┘
           │
           │ HTTPS
           │
┌──────────▼───────────┐
│  Railway / Render    │  Backend (FastAPI container)
└──────────┬───────────┘
           │
     ┌─────┼─────┐
     │           │
┌────▼────┐  ┌──▼─────┐
│ Postgres│  │ Redis  │  Managed databases
│  Cloud  │  │ Cloud  │
└─────────┘  └────────┘
```

---

**💡 Notes:**
- All services communicate via REST API (JSON)
- Frontend calls backend API with JWT bearer token
- Backend persists to Postgres, caches in Redis
- ML models loaded at API startup (lazy loading)
- Ollama runs separately (optional, local LLM inference)
