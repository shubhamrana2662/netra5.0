# 🔍 CyberDrishti AI — Autonomous Cyber Crime Intelligence & Evidence Copilot

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/FastAPI-0.109-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Next.js-14.1-black?style=for-the-badge&logo=next.js&logoColor=white" alt="Next.js 14" />
  <img src="https://img.shields.io/badge/PyTorch-2.2-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white" alt="PyTorch" />
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/Compliance-Section_65B_IT_Act-gold?style=for-the-badge" alt="Section 65B IT Act" />
</p>

> **Empowering Law Enforcement & Cyber Crime Cells** with GNN-powered Hidden Link Analysis, Multilingual Hinglish NER, Local RAG Copilot with Legal Citations, and Cryptographically Audited Section 65B Evidence Certificates.

---

## 📌 Executive Summary

**CyberDrishti AI** is an enterprise-grade, 100% on-premise cyber crime investigation copilot engineered for police departments, state cyber cells, and financial intelligence units. 

During cyber fraud investigations (such as UPI scam networks, digital arrest rackets, or mule account syndicates), investigators are inundated with thousands of pages of unstructured evidence—Call Detail Records (CDRs), IPDR logs, Hinglish WhatsApp exports, and bank statements. Manually correlating these disparate data sources takes weeks, while syndicate operators switch burner SIMs and accounts in hours.

**CyberDrishti AI automates evidence parsing, entity extraction, hidden relationship discovery, and court-admissible report generation—reducing investigation turnaround time from weeks to seconds.**

---

## 🚀 Key Innovation Highlights

### 1. 🕸️ Hidden-Link Graph Neural Engine
Traditional link analysis only shows explicit connections (e.g., A called B). CyberDrishti AI uses a **6-feature topological combinator with logistic regression** to uncover covert relationships:
- **Jaccard Similarity** (Shared contacts and entities)
- **Adamic-Adar Index** (Rare shared node weighting)
- **Temporal Proximity ($\tau=1\text{hr}$)** (Burst communication correlation)
- **Financial Velocity ($\tau=2\text{hr}$)** (Pass-through transaction timing)
- **Bridge Score & Preferential Attachment**
- *Precision-Gated Output*: Minimum $\ge 90\%$ confidence guarantee with full mathematical explainability.

### 2. 🤖 Custom Transformer (CyberDrishtiLM) & HingBERT NER
Cyber crime evidence in India frequently contains code-mixed Hinglish (*"Bhai 50k transfer kar de is UPI id par fast"*). 
- **CyberDrishtiLM**: Custom ~2.3M parameter Transformer with BPE tokenizer trained on code-mixed fraud corpus.
- **HingBERT Fine-Tune**: Fine-tuned IndicBERT model classifying 12 entity types: `PER`, `PHONE`, `UPI`, `ACCOUNT`, `AMOUNT`, `BANK`, `EMAIL`, `ORG`, `LOCATION`, `IP`, `DATE`, `DEVICE`.

### 3. 💬 Local RAG Copilot with Legal Statutory Citations
- **Zero Cloud Leakage**: Uses local Ollama LLM (`llama3.2:1b`) to ensure no sensitive case data ever leaves the department network.
- **Statutory Legal Grounding**: Built-in verification engine automatically maps findings to relevant sections of the **Information Technology Act, 2000** and **Bharatiya Nyaya Sanhita (BNS / IPC)** with citation validation to eliminate hallucinations.

### 4. 📜 Tamper-Evident SHA-256 Audit Chain & Section 65B Certificates
- **Cryptographic Custody**: Blockchain-inspired SHA-256 hash chaining tracks every evidence upload, extraction, and investigator action.
- **Instant Section 65B PDF Generation**: Generates court-ready Section 65B certificates formatted according to Indian Evidence Act standards, featuring hash verification tables and digital signature placeholders.

---

## 🏗️ System Architecture

```
                                  ┌─────────────────────────────────────────┐
                                  │       UNSTRUCTURED EVIDENCE DATA        │
                                  │  CDRs • WhatsApp Exports • Bank PDFs    │
                                  └────────────────────┬────────────────────┘
                                                       │
                                                       ▼
                                  ┌─────────────────────────────────────────┐
                                  │        PARSER & INGESTION LAYER         │
                                  │ Multi-format Parsers + Tesseract OCR    │
                                  └────────────────────┬────────────────────┘
                                                       │
                                                       ▼
                                  ┌─────────────────────────────────────────┐
                                  │       AI & CORRELATION PIPELINE         │
                                  │ ├─ CyberDrishtiLM / HingBERT NER        │
                                  │ ├─ Regex Hard-ID Extractors (11 types)  │
                                  │ ├─ 6-Metric Hidden Link Graph Engine   │
                                  │ └─ Local Ollama RAG Copilot             │
                                  └────────────────────┬────────────────────┘
                                                       │
                                                       ▼
                                  ┌─────────────────────────────────────────┐
                                  │       STORAGE & INTEGRITY LAYER         │
                                  │ PostgreSQL (pgvector) • SHA-256 Chain   │
                                  └────────────────────┬────────────────────┘
                                                       │
                                                       ▼
                                  ┌─────────────────────────────────────────┐
                                  │        INTERACTIVE FRONTEND UI          │
                                  │ Next.js 14 • React Flow Canvas • Zustand│
                                  └─────────────────────────────────────────┘
```

---

## 📦 Tech Stack

| Domain | Technologies |
| :--- | :--- |
| **Backend Framework** | Python 3.10+, FastAPI, Pydantic v2, Uvicorn |
| **Database & Cache** | PostgreSQL 16 (pgvector), SQLAlchemy ORM, Redis 7 |
| **Machine Learning** | PyTorch, HuggingFace Transformers, Scikit-Learn, NetworkX, sklearn-crfsuite |
| **Local LLM / RAG** | Ollama (`llama3.2:1b`), ChromaDB vector store |
| **Document Processing** | PyPDF2, Tabula, Tesseract OCR, Jinja2, WeasyPrint |
| **Frontend Framework** | Next.js 14 (App Router), TypeScript, React 18 |
| **UI Components** | React Flow (Interactive Canvas), Framer Motion, TailwindCSS, Lucide Icons |
| **State & API** | Zustand (Global State), Axios, TanStack Query |
| **DevOps & Container** | Docker, Docker Compose |

---

## 🛠️ Repository Structure

```
cyberdrishti-ai/
├── backend/
│   ├── main.py                     # FastAPI main entrypoint & lifespan setup
│   ├── config.py                   # Central settings & Pydantic config
│   ├── .env.example                # Sample environment variables
│   ├── db/                         # Database models, ORM & sessions
│   ├── routes/                     # API endpoint handlers (cases, graph, evidence, copilot, etc.)
│   ├── parsers/                    # Multi-format parsers (WhatsApp, CDR, Bank PDF, OCR)
│   ├── nlp/                        # CyberDrishtiLM model, tokenizer, trainer, HingBERT
│   ├── graph/                      # NetworkX graph builder & hidden link engine
│   ├── rag/                        # Ollama RAG copilot & statutory citation validator
│   └── report/                     # Section 65B PDF certificate generator
├── frontend/
│   ├── src/app/                    # Next.js App Router (14 interactive screens)
│   ├── src/components/             # UI components, layout, & React Flow graph canvas
│   ├── src/stores/                 # Zustand state management
│   ├── src/lib/                    # API client & utility functions
│   ├── .env.example                # Sample frontend env config
│   └── tailwind.config.ts          # Modern dark/glassmorphic design system
├── docs/                           # Technical documentation & architectural specs
│   ├── ARCHITECTURE.md             # Deep-dive system architecture
│   ├── GETTING_STARTED.md          # Comprehensive setup guide
│   ├── COMMANDS.md                 # CLI & API reference
│   ├── DEVELOPMENT.md              # Contributor guidelines
│   ├── PROJECT_STRUCTURE.md        # File & component breakdown
│   └── TRAINING_STATUS.md          # Model metrics & evaluation reports
├── docker-compose.yml              # One-command orchestration
└── quickstart.ps1                  # Windows PowerShell quick setup script
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python**: `3.10` or higher
- **Node.js**: `18.x` or higher
- **Docker & Docker Compose** (Recommended)
- **Ollama**: (Optional, for local AI copilot chat)

---

### Option A: Running via Docker (Recommended)

1. **Clone the Repository**
   ```bash
   git clone https://github.com/shubhamrana2662/NETRA.git
   cd NETRA
   ```

2. **Setup Environment Variables**
   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env.local
   ```

3. **Launch All Services**
   ```bash
   docker-compose up --build
   ```
   - **Frontend**: Access at `http://localhost:3000`
   - **Backend API Docs**: Access Swagger UI at `http://localhost:8000/docs`

---

### Option B: Local Manual Setup

#### 1. Backend Setup
```bash
cd backend

# Create & activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run FastAPI backend
uvicorn main:app --reload --port 8000
```

#### 2. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local

# Start Next.js development server
npm run dev
```

---

## 🖥️ Screen & Module Overview

| Module / Screen | Description & Capability |
| :--- | :--- |
| **1. Executive Dashboard** | Real-time case metrics, active threats, suspicious link alerts, and operational stats. |
| **2. Case Management** | Case creation, officer assignment, priority tracking, and evidence summary. |
| **3. Entity Link Graph** | Interactive React Flow network canvas showcasing suspect relationships & hidden link predictions. |
| **4. Case Timeline** | Multi-source chronological event reconstruction with temporal filtering. |
| **5. Communications** | Parsed call logs, SMS, and Hinglish WhatsApp chat analysis with NER entity highlighting. |
| **6. Financial Transactions**| Bank statement analysis, mule account velocity tracking, and high-value flow detection. |
| **7. Evidence Ingestion** | Drag-and-drop file uploader supporting WhatsApp TXT, Bank PDFs, CDR CSVs, and images. |
| **8. RAG AI Copilot** | Contextual natural language assistant with grounded legal statutory citations. |
| **9. Section 65B Reports** | Automated court-admissible PDF certificate generation with cryptographic verification tables. |
| **10. Audit Chain** | Tamper-evident SHA-256 hash log inspector for chain-of-custody compliance. |

---

## 🔐 Security & Legal Compliance

- 🔒 **100% Air-Gapped & On-Premise Support**: CyberDrishti AI executes completely on local hardware. Sensitive law enforcement evidence never hits commercial cloud APIs.
- ⚖️ **Section 65B Admissibility**: Conforms with Section 65B of the Indian Evidence Act (and Section 63 of Bharatiya Sakshya Adhiniyam, 2023) by certifying computer output integrity via SHA-256 hash logs.
- 🔑 **Role-Based Access Control (RBAC)**: JWT authentication ensures only authorized investigating officers access assigned case files.

---

## 📑 Additional Documentation

For detailed technical specifications, explore the guides in the [`docs/`](./docs/) directory:
- [🏗️ System Architecture Specs](./docs/ARCHITECTURE.md)
- [🏁 Detailed Getting Started Guide](./docs/GETTING_STARTED.md)
- [💻 Command & API Reference](./docs/COMMANDS.md)
- [📊 Model Performance & Training Status](./docs/TRAINING_STATUS.md)

---

<p align="center">
  <b>Built for Hackathons & Future Law Enforcement Innovation</b><br/>
  <i>CyberDrishti AI — Illuminating Hidden Links in Cyber Crime Intelligence</i>
</p>
