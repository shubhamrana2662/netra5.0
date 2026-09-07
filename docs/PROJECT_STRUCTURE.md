# CyberDrishti AI — Project Structure

```
cyberdrishti-ai/
├── backend/                                 # FastAPI backend
│   ├── main.py                             # FastAPI app entry point
│   ├── requirements.txt                    # Python dependencies
│   ├── train_all.py                        # Master ML training orchestrator
│   │
│   ├── database/                           # Database layer
│   │   ├── __init__.py
│   │   ├── models.py                       # SQLAlchemy ORM models (8 tables)
│   │   ├── session.py                      # Session handler
│   │   └── init_db.py                      # Database initialization script
│   │
│   ├── api/                                # API routes
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── auth.py                     # JWT authentication
│   │       ├── cases.py                    # Case CRUD + stats
│   │       ├── evidence.py                 # Evidence upload + extraction
│   │       ├── graph.py                    # Entity graph + hidden links
│   │       ├── timeline.py                 # Timeline generation
│   │       ├── copilot.py                  # Ollama RAG copilot
│   │       ├── report.py                   # Section 65B PDF generator
│   │       ├── audit.py                    # Audit logs + verification
│   │       └── officers.py                 # User management
│   │
│   ├── parsers/                            # Evidence parsers
│   │   ├── __init__.py
│   │   ├── whatsapp_parser.py             # WhatsApp export → events
│   │   ├── bank_pdf_parser.py             # Bank PDF → transactions
│   │   ├── cdr_parser.py                  # Call Detail Record → logs
│   │   └── ocr_parser.py                  # Tesseract + PaddleOCR
│   │
│   ├── nlp/                                # ML/NLP pipeline
│   │   ├── __init__.py
│   │   ├── generate_ner_training_data.py  # Synthetic Hinglish data generator
│   │   ├── validate_real_data.py          # Real data validator
│   │   ├── compare_models.py              # Model comparison utility
│   │   │
│   │   ├── cyberdrishtilm/                # Custom transformer
│   │   │   ├── __init__.py
│   │   │   ├── model.py                   # CyberDrishtiLM architecture
│   │   │   └── train.py                   # Training script
│   │   │
│   │   ├── hingbert_finetune.py           # HingBERT fine-tuning
│   │   ├── train_crf.py                   # CRF baseline training
│   │   ├── hidden_link_engine.py          # 6-feature graph scorer
│   │   └── ollama_rag.py                  # RAG copilot with citations
│   │
│   └── utils/                              # Utilities
│       ├── __init__.py
│       ├── regex_extractors.py            # Hard-ID extraction (PHONE, UPI, etc.)
│       └── audit_chain.py                 # Tamper-evident hash chain
│
├── frontend/                               # Next.js frontend
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts                 # Design tokens
│   ├── tsconfig.json
│   ├── postcss.config.js
│   │
│   └── src/
│       ├── app/                            # Next.js App Router
│       │   ├── layout.tsx                 # Root layout
│       │   ├── page.tsx                   # Root page (redirect)
│       │   ├── globals.css                # Global styles
│       │   │
│       │   ├── login/
│       │   │   └── page.tsx               # Login page
│       │   │
│       │   └── dashboard/
│       │       ├── layout.tsx             # Dashboard layout (Sidebar + Header)
│       │       ├── page.tsx               # Screen 1: Dashboard
│       │       │
│       │       ├── cases/
│       │       │   ├── page.tsx           # Screen 2: Cases list
│       │       │   └── [id]/
│       │       │       └── page.tsx       # Screen 3: Case detail
│       │       │
│       │       ├── graph/
│       │       │   └── page.tsx           # Screen 4: Entity graph
│       │       │
│       │       ├── timeline/
│       │       │   └── page.tsx           # Screen 5: Timeline
│       │       │
│       │       ├── communications/
│       │       │   └── page.tsx           # Screen 6: Communications
│       │       │
│       │       ├── transactions/
│       │       │   └── page.tsx           # Screen 7: Transactions
│       │       │
│       │       ├── evidence/
│       │       │   └── page.tsx           # Screen 8: Evidence upload
│       │       │
│       │       ├── analytics/
│       │       │   └── page.tsx           # Screen 9: Analytics
│       │       │
│       │       ├── copilot/
│       │       │   └── page.tsx           # Screen 10: AI copilot
│       │       │
│       │       ├── reports/
│       │       │   └── page.tsx           # Screen 11: Reports
│       │       │
│       │       ├── audit/
│       │       │   └── page.tsx           # Screen 12: Audit logs
│       │       │
│       │       ├── officers/
│       │       │   └── page.tsx           # Screen 13: Officers
│       │       │
│       │       └── settings/
│       │           └── page.tsx           # Screen 14: Settings
│       │
│       ├── components/
│       │   └── layout/
│       │       ├── Sidebar.tsx            # Collapsible navigation
│       │       └── TopHeader.tsx          # Search + notifications
│       │
│       ├── stores/
│       │   └── index.ts                   # Zustand stores (4 stores)
│       │
│       └── lib/
│           ├── api.ts                     # Axios client + typed helpers
│           └── utils.ts                   # cn() utility
│
├── docker-compose.yml                      # Postgres + Redis + Adminer
├── README.md                              # Comprehensive documentation
└── .gitignore
```

---

## 📊 Key Metrics

**Backend:**
- 9 API route modules
- 8 SQLAlchemy tables
- 4 evidence parsers
- 3 ML models (CyberDrishtiLM, HingBERT, CRF)
- 1 hidden-link graph engine
- 1 Ollama RAG copilot

**Frontend:**
- 14 screens (Dashboard + 13 feature screens)
- 4 Zustand stores
- 2 layout components (Sidebar, TopHeader)
- Glassmorphic light-mode design system

**Total Lines of Code (estimated):**
- Backend: ~8,500 lines
- Frontend: ~4,200 lines
- Total: ~12,700 lines

---

## 🎯 Coverage

**Phase 1-7 (MVP — Backend + ML):** ✅ Complete
- Infrastructure (Docker Compose)
- Synthetic data generation
- CyberDrishtiLM training
- HingBERT fine-tuning
- CRF baseline
- 4 parsers (WhatsApp, Bank, CDR, OCR)
- Hidden-link graph engine
- Ollama RAG copilot
- Section 65B PDF generator
- Tamper-evident audit chain
- 9 FastAPI routes

**Phase 8-10 (Product — Frontend):** ✅ Complete
- 14 production-ready screens
- Glassmorphic design system
- Zustand state management
- API integration layer
- Framer Motion animations
- React Flow graph visualization
- Authentication flow

---

## 🚀 Next Steps

1. **Start Infrastructure:**
   ```powershell
   docker-compose up -d
   ```

2. **Generate Training Data:**
   ```powershell
   cd backend
   python nlp/generate_ner_training_data.py --output_dir training_data --n_sentences 8000
   ```

3. **Train Models:**
   ```powershell
   python train_all.py --synthetic 8000 --epochs 10 --gpu
   ```

4. **Start Backend:**
   ```powershell
   uvicorn main:app --reload
   ```

5. **Start Frontend:**
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

6. **Open Browser:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/docs
