# CyberDrishti AI — Development Guide

## 🎯 Development Workflow

### **Daily Development Loop**

1. **Start Infrastructure:**
   ```powershell
   docker-compose up -d
   ```

2. **Terminal 1 — Backend:**
   ```powershell
   cd backend
   .\venv\Scripts\Activate.ps1
   uvicorn main:app --reload --log-level debug
   ```

3. **Terminal 2 — Frontend:**
   ```powershell
   cd frontend
   npm run dev
   ```

4. **Terminal 3 — ML Experiments (optional):**
   ```powershell
   cd backend
   .\venv\Scripts\Activate.ps1
   python nlp/generate_ner_training_data.py --output_dir training_data --n_sentences 1000
   ```

---

## 🧪 Testing Workflow

### **Backend API Testing**

**Using FastAPI Swagger UI:**
1. Navigate to http://localhost:8000/docs
2. Test `/auth/login` first to get JWT token
3. Click "Authorize" and paste token
4. Test other endpoints

**Using curl:**
```powershell
# Login
$token = (curl -X POST http://localhost:8000/api/v1/auth/login `
    -F "username=admin" `
    -F "password=admin123" | ConvertFrom-Json).access_token

# Get cases
curl -H "Authorization: Bearer $token" http://localhost:8000/api/v1/cases
```

### **Frontend Component Testing**

**Manual Testing Checklist:**
- [ ] Login page (valid + invalid credentials)
- [ ] Dashboard KPI cards render
- [ ] Cases list pagination works
- [ ] Case detail tabs switch correctly
- [ ] Evidence upload drag-and-drop
- [ ] Graph visualization renders
- [ ] Timeline events display
- [ ] AI Copilot sends messages
- [ ] Section 65B PDF downloads
- [ ] Audit logs load and verify
- [ ] Officers CRUD operations
- [ ] Settings tabs switch

---

## 🔧 Common Development Tasks

### **Add a New API Route**

1. Create route file in `backend/api/routes/`:
   ```python
   from fastapi import APIRouter, Depends
   from sqlalchemy.orm import Session
   from database.session import get_db
   
   router = APIRouter(prefix="/my-feature", tags=["My Feature"])
   
   @router.get("/")
   def list_items(db: Session = Depends(get_db)):
       return {"items": []}
   ```

2. Register in `backend/main.py`:
   ```python
   from api.routes import my_feature
   app.include_router(my_feature.router, prefix="/api/v1")
   ```

### **Add a New Database Table**

1. Define model in `backend/database/models.py`:
   ```python
   class MyTable(Base):
       __tablename__ = "my_table"
       id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
       name = Column(String, nullable=False)
       created_at = Column(DateTime(timezone=True), server_default=func.now())
   ```

2. Run database init:
   ```powershell
   python database/init_db.py
   ```

### **Add a New Frontend Screen**

1. Create page in `frontend/src/app/dashboard/my-screen/page.tsx`:
   ```tsx
   "use client";
   export default function MyScreenPage() {
       return <div>My Screen</div>;
   }
   ```

2. Add route to sidebar in `frontend/src/components/layout/Sidebar.tsx`:
   ```tsx
   { icon: MyIcon, label: "My Screen", href: "/dashboard/my-screen" }
   ```

### **Add a New Entity Type**

1. Update synthetic data generator in `backend/nlp/generate_ner_training_data.py`:
   ```python
   ENTITY_TYPES.append("MYENTITY")
   ```

2. Add patterns/examples for the new entity type

3. Retrain models:
   ```powershell
   python train_all.py --synthetic 8000 --epochs 10
   ```

---

## 🐛 Debugging

### **Backend Debugging**

**Enable Debug Logs:**
```powershell
uvicorn main:app --reload --log-level debug
```

**PostgreSQL Query Logs:**
```python
# In database/session.py, add:
engine = create_engine(DATABASE_URL, echo=True)  # Logs all SQL queries
```

**Redis Commands:**
```powershell
docker exec -it cyberdrishti-redis redis-cli
> KEYS *
> GET <key>
```

### **Frontend Debugging**

**React DevTools:**
1. Install React DevTools browser extension
2. Inspect component tree and state

**Zustand State Debugging:**
```tsx
// Add to any component:
const store = useInvestigationStore();
console.log("Store state:", store);
```

**API Call Debugging:**
```tsx
// In src/lib/api.ts, add:
api.interceptors.response.use(
  (res) => {
    console.log("API Response:", res);
    return res;
  }
);
```

---

## 📦 Building for Production

### **Backend**

```powershell
# 1. Generate requirements (if changed)
pip freeze > requirements.txt

# 2. Build Docker image
docker build -t cyberdrishti-backend:latest ./backend

# 3. Run container
docker run -p 8000:8000 cyberdrishti-backend:latest
```

### **Frontend**

```powershell
# 1. Build production bundle
cd frontend
npm run build

# 2. Test production build locally
npm start

# 3. Deploy to Vercel/Netlify
vercel --prod
```

---

## 🔐 Security Checklist

Before deploying to production:

- [ ] Change `JWT_SECRET` in `.env`
- [ ] Update database credentials
- [ ] Enable HTTPS (SSL/TLS certificates)
- [ ] Configure CORS for production frontend URL only
- [ ] Review and harden PostgreSQL permissions
- [ ] Enable rate limiting on API endpoints
- [ ] Add API key authentication for external services
- [ ] Review all environment variables
- [ ] Enable audit logging
- [ ] Set up backup strategy for database

---

## 📊 Performance Optimization

### **Backend**

- [ ] Add Redis caching for frequently accessed data
- [ ] Use database connection pooling
- [ ] Add pagination to all list endpoints
- [ ] Optimize SQL queries (add indexes)
- [ ] Use async database operations where possible
- [ ] Compress large responses with gzip

### **Frontend**

- [ ] Enable Next.js Image optimization
- [ ] Add React.memo() to expensive components
- [ ] Lazy-load non-critical components
- [ ] Implement virtual scrolling for long lists
- [ ] Add debouncing to search inputs
- [ ] Use SWR or React Query for data fetching

---

## 🎓 Learning Resources

**FastAPI:**
- Official Docs: https://fastapi.tiangolo.com
- Tutorial: https://fastapi.tiangolo.com/tutorial/

**Next.js 14:**
- Official Docs: https://nextjs.org/docs
- App Router: https://nextjs.org/docs/app

**SQLAlchemy 2.0:**
- Official Docs: https://docs.sqlalchemy.org/en/20/

**PyTorch:**
- Official Tutorial: https://pytorch.org/tutorials/

**Transformers:**
- HuggingFace Docs: https://huggingface.co/docs/transformers/

---

## 💡 Tips & Best Practices

1. **Always activate virtual environment before running Python commands**
2. **Use `git commit` frequently with descriptive messages**
3. **Test API endpoints with Swagger UI before integrating frontend**
4. **Keep synthetic data generation separate from model training**
5. **Use TypeScript's type system — don't use `any`**
6. **Follow the existing code style and naming conventions**
7. **Add JSDoc comments to complex functions**
8. **Use Tailwind utility classes instead of custom CSS**
9. **Keep components under 300 lines — split if larger**
10. **Run linters before committing: `npm run lint` / `black .`**

---

## 🤝 Getting Help

- **GitHub Issues:** Open an issue for bugs or feature requests
- **Documentation:** Check README.md and PROJECT_STRUCTURE.md
- **API Docs:** http://localhost:8000/docs for live API reference
- **Code Comments:** Most complex functions have inline comments

---

**Happy Coding! 🚀**
