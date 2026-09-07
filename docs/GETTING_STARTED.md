# 🚀 Getting Started with CyberDrishti AI

Welcome to CyberDrishti AI! This guide will help you set up and run the platform in **under 30 minutes**.

---

## 📋 Prerequisites Checklist

Before you begin, ensure you have:

- [ ] **Python 3.10 or higher** → [Download](https://www.python.org/downloads/)
- [ ] **Node.js 18 or higher** → [Download](https://nodejs.org/)
- [ ] **Docker Desktop** → [Download](https://www.docker.com/products/docker-desktop)
- [ ] **Git** → [Download](https://git-scm.com/downloads)
- [ ] **(Optional) NVIDIA GPU with CUDA** for model training
- [ ] **(Optional) Ollama** → [Download](https://ollama.ai/) for AI Copilot

**Check your versions:**
```powershell
python --version    # Should be 3.10+
node --version      # Should be 18+
docker --version    # Should be 20+
git --version
```

---

## ⚡ Quick Start (5 Minutes)

### **Option 1: Automated Setup (Recommended)**

1. **Clone the repository:**
   ```powershell
   git clone <your-repo-url>
   cd cyberdrishti-ai
   ```

2. **Run the quick start script:**
   ```powershell
   .\quickstart.ps1
   ```

3. **Open 2 terminals and start services:**

   **Terminal 1 (Backend):**
   ```powershell
   cd backend
   .\venv\Scripts\Activate.ps1
   uvicorn main:app --reload
   ```

   **Terminal 2 (Frontend):**
   ```powershell
   cd frontend
   npm run dev
   ```

4. **Open your browser:**
   - Frontend: http://localhost:3000
   - Backend API Docs: http://localhost:8000/docs

---

### **Option 2: Manual Setup**

If you prefer manual control, follow these steps:

#### **1. Start Infrastructure**
```powershell
docker-compose up -d
```

This starts:
- PostgreSQL 16 (port 5432)
- Redis 7 (port 6379)
- Adminer (port 8080)

#### **2. Setup Backend**
```powershell
cd backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Create .env file
@"
DATABASE_URL=postgresql://cd_user:cd_secure_password@localhost:5432/cyberdrishti
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=dev-secret-key-change-in-production
"@ | Out-File -FilePath ".env" -Encoding utf8

# Initialize database
python database/init_db.py
```

#### **3. Setup Frontend**
```powershell
cd frontend

# Install dependencies
npm install

# Create .env.local file
"NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" | Out-File -FilePath ".env.local" -Encoding utf8
```

#### **4. Start Services**

**Terminal 1 (Backend):**
```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload
```

**Terminal 2 (Frontend):**
```powershell
cd frontend
npm run dev
```

---

## 👤 Create Your First User

The system doesn't have a default user. Create one via the API:

1. **Open Swagger UI:** http://localhost:8000/docs

2. **Navigate to `/auth/register`** (if implemented) or create directly via POST:

   ```powershell
   # Using PowerShell
   $body = @{
       username = "admin"
       password = "admin123"
       full_name = "Administrator"
       email = "admin@cyberdrishti.ai"
       role = "admin"
   } | ConvertTo-Json

   Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/v1/officers" -Body $body -ContentType "application/json"
   ```

3. **Login at:** http://localhost:3000/login
   - Username: `admin`
   - Password: `admin123`

---

## 📝 Your First Investigation Case

### **1. Create a Case**

**Via UI:**
1. Click "New Case" button in the sidebar
2. Fill in case details
3. Click "Create Case"

**Via API:**
```powershell
# First, login to get token
$response = Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/v1/auth/login" -ContentType "multipart/form-data" -Form @{username="admin"; password="admin123"}
$token = $response.access_token

# Create case
$headers = @{Authorization = "Bearer $token"}
$body = @{
    case_number = "FIR/2025/001"
    title = "UPI Fraud Investigation"
    priority = "high"
    status = "in_progress"
    crime_type = "UPI Fraud"
    description = "Victim reported unauthorized UPI transactions from their account."
} | ConvertTo-Json

$case = Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/v1/cases" -Headers $headers -Body $body -ContentType "application/json"
$caseId = $case.id
```

### **2. Upload Evidence**

Navigate to **Evidence Upload** screen and drag-drop files:
- WhatsApp chat exports (.txt)
- Bank statements (.pdf)
- Call logs (.csv)
- Screenshots (.png, .jpg)

Or via API:
```powershell
$form = @{
    case_id = $caseId
    source_type = "whatsapp"
    files = Get-Item "path/to/whatsapp_chat.txt"
}

Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/v1/evidence/upload" -Headers $headers -Form $form
```

### **3. View Extracted Data**

After upload, the system automatically:
- ✅ Parses evidence files
- ✅ Extracts entities (PHONE, UPI, ACCOUNT, etc.)
- ✅ Builds entity graph
- ✅ Generates timeline
- ✅ Detects hidden links

Navigate to:
- **Entity Graph** to see relationships
- **Timeline** to see chronological events
- **Communications** to see parsed messages
- **Transactions** to see financial movements

### **4. Ask the AI Copilot**

1. Navigate to **AI Copilot** screen
2. Ask questions like:
   - "What transactions involved +91 9876543210?"
   - "Summarize the WhatsApp messages from May 4th"
   - "What's the legal section for electronic evidence?"

3. The copilot will:
   - Search your case evidence
   - Provide grounded answers
   - Show source citations

### **5. Generate Section 65B Report**

1. Navigate to **Reports** screen
2. Click "Generate Certificate"
3. Download the PDF with:
   - SHA-256 hash table for all evidence
   - Extracted entities
   - Hidden links with explainability
   - Timeline snapshot
   - Audit chain

---

## 🧪 Train Your Own Models (Optional)

If you want to train custom NER models on your own data:

### **1. Generate Synthetic Training Data**
```powershell
cd backend
python nlp/generate_ner_training_data.py --output_dir training_data --n_sentences 8000
```

This creates:
- `training_data/train.json` (6,400 sentences)
- `training_data/val.json` (800 sentences)
- `training_data/test.json` (800 sentences)

### **2. Train All Models**
```powershell
# With GPU (recommended, 1-2 hours)
python train_all.py --synthetic 8000 --epochs 10 --gpu

# Without GPU (CPU only, 4-6 hours)
python train_all.py --synthetic 8000 --epochs 5
```

This will:
- Train CyberDrishtiLM (custom transformer)
- Fine-tune HingBERT (ai4bharat/indic-bert)
- Train CRF baseline
- Generate comparison report

### **3. View Results**
```powershell
# View comparison table
Get-Content artifacts/model_comparison_table.txt

# View metrics
Get-Content artifacts/cyberdrishtilm/eval_metrics.json
Get-Content artifacts/hingbert/eval_metrics.json
Get-Content artifacts/crf/eval_metrics.json
```

### **4. Validate on Real Data (if available)**
```powershell
python nlp/validate_real_data.py \
    --real_data ./your_real_data/test.txt \
    --cdlm_model artifacts/cyberdrishtilm \
    --hingbert_model artifacts/hingbert \
    --crf_model artifacts/crf/crf_model.pkl \
    --output_report artifacts/real_validation.json
```

---

## 🤖 Setup AI Copilot (Optional)

To enable the RAG-powered AI assistant:

1. **Install Ollama:**
   - Download from https://ollama.ai
   - Install and run

2. **Pull llama3.2:1b model:**
   ```powershell
   ollama pull llama3.2:1b
   ```

3. **Start Ollama server:**
   ```powershell
   ollama serve
   ```

4. **Restart backend:**
   The backend will auto-detect Ollama and enable RAG mode

---

## 🎓 Learning Path

### **Day 1: Get Familiar**
- ✅ Setup and run the platform
- ✅ Create your first case
- ✅ Upload sample evidence
- ✅ Explore all 14 screens

### **Day 2: Deep Dive**
- ✅ Read ARCHITECTURE.md
- ✅ Explore API docs at http://localhost:8000/docs
- ✅ Try different evidence parsers
- ✅ Generate a Section 65B report

### **Day 3: Customize**
- ✅ Train models on synthetic data
- ✅ Experiment with AI Copilot
- ✅ Test hidden-link detection
- ✅ Review audit logs

### **Week 1: Production Ready**
- ✅ Validate models on real labeled data
- ✅ Add unit tests
- ✅ Configure for production deployment
- ✅ Set up monitoring

---

## 🐛 Troubleshooting

### **Problem: Docker containers won't start**
**Solution:**
```powershell
# Check if ports are already in use
netstat -ano | findstr :5432
netstat -ano | findstr :6379

# Stop conflicting processes or change ports in docker-compose.yml
```

### **Problem: Backend won't connect to database**
**Solution:**
```powershell
# Check if database is running
docker ps

# Check database logs
docker-compose logs postgres

# Reinitialize database
cd backend
python database/init_db.py
```

### **Problem: Frontend shows "Network Error"**
**Solution:**
1. Check if backend is running: http://localhost:8000/docs
2. Verify `NEXT_PUBLIC_API_URL` in `frontend/.env.local`
3. Check CORS configuration in `backend/main.py`

### **Problem: Model training fails with CUDA error**
**Solution:**
```powershell
# Train without GPU
python train_all.py --synthetic 8000 --epochs 5

# Or install CUDA-compatible PyTorch:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### **Problem: Ollama not detected**
**Solution:**
1. Check if Ollama is running: http://localhost:11434
2. Pull the model: `ollama pull llama3.2:1b`
3. Restart backend to auto-detect

### **Problem: PDF generation fails**
**Solution:**
```powershell
# Install WeasyPrint dependencies
pip install --upgrade weasyprint

# On Windows, you may need GTK3 runtime
# Download from: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer
```

---

## 📚 Documentation Guide

- **README.md** — Comprehensive overview + setup
- **ARCHITECTURE.md** — System architecture diagram
- **DEVELOPMENT.md** — Dev workflow + debugging
- **COMMANDS.md** — Quick command reference
- **PROJECT_STRUCTURE.md** — File organization
- **BUILD_SUMMARY.md** — What's been built
- **This file (GETTING_STARTED.md)** — First-time user guide

---

## 🆘 Getting Help

1. **Check the docs** — Most questions are answered in the docs above
2. **API Documentation** — http://localhost:8000/docs for live API reference
3. **GitHub Issues** — Open an issue for bugs or feature requests
4. **Code Comments** — Most complex functions have inline explanations

---

## 🎯 Next Steps

After getting the basic setup working:

1. **Explore all 14 screens** to understand the full feature set
2. **Read ARCHITECTURE.md** to understand data flow
3. **Train models** on synthetic data to see the ML pipeline
4. **Try the AI Copilot** to see RAG in action
5. **Generate reports** to see Section 65B certificates
6. **Review DEVELOPMENT.md** to start customizing

---

## ⚡ Pro Tips

1. **Use Adminer for database inspection** — http://localhost:8080
2. **Swagger UI is your friend** — Test all API endpoints interactively
3. **Keep Docker Desktop running** — Backend needs Postgres + Redis
4. **Check logs first** — Most errors are self-explanatory in terminal output
5. **Use the quickstart script** — It handles 90% of setup automatically
6. **Train with GPU** — Model training is 10x faster with CUDA
7. **Start with synthetic data** — Don't wait for real data to test models
8. **Bookmark COMMANDS.md** — Quick reference for daily development

---

## 🎉 You're Ready!

You now have a production-grade AI investigation platform running locally. Experiment, break things, and learn!

**Welcome to CyberDrishti AI — See Beyond the Evidence** 🔍

---

**Questions?** Open an issue on GitHub or check the documentation links above.

**Happy Investigating!** 🚀
