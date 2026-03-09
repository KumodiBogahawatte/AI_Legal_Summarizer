# AI Legal Case Summarizer — Deployment Report

**Application:** Sri Lankan NLR/SLR Legal Case Summarizer (AI-generated summaries, constitutional analysis, related cases, RAG search)  
**Report date:** March 2026  
**Version:** 1.0

---

## 1. Overview

| Item | Description |
|------|-------------|
| **Backend** | FastAPI (Python 3.10), Uvicorn |
| **Frontend** | React + Vite, Tailwind CSS |
| **Database** | PostgreSQL (recommended) or SQLite |
| **Optional** | Redis (Celery), Elasticsearch (optional; FAISS used for vectors) |
| **Dev ports** | Backend: **8011**, Frontend: **5173** |
| **Docker** | Backend: **8000**, Frontend: **5173** |

---

## 2. Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────────────────┐
│   React (Vite)  │     │  FastAPI Backend (8011 / 8000)                    │
│   Port 5173     │────▶│  /api, /api/analysis, /api/rag, /api/search       │
└─────────────────┘     │  CORS allows localhost:5173, 3000, 3001, 5174      │
                        └───────────────┬──────────────────────────────────┘
                                        │
          ┌─────────────────────────────┼─────────────────────────────┐
          ▼                             ▼                             ▼
   ┌───────────────┐           ┌───────────────┐           ┌───────────────────┐
   │ PostgreSQL /  │           │ FAISS (RAG)   │           │ OpenAI API        │
   │ SQLite        │           │ embeddings    │           │ (summaries, etc.) │
   └───────────────┘           └───────────────┘           └───────────────────┘
```

- **API prefixes:** `/api` (documents, users), `/api/analysis` (summaries, constitutional, related cases, corpus-pdf-view), `/api/rag`, `/api/search`.
- **Startup:** DB init, RAGServiceV2 and ConstitutionalRAGModule pre-warm (non-blocking).

---

## 3. Prerequisites

- **Python:** 3.10+
- **Node.js:** LTS (for frontend build)
- **Database:** PostgreSQL 15+ (production) or SQLite (dev/single-node)
- **System (for PDF/OCR):** Tesseract, poppler-utils (backend)
- **API key:** OpenAI-compatible API key (e.g. Gemini) for summaries and constitutional analysis

---

## 4. Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_TYPE` | No | `postgresql` | `postgresql` or use SQLite (no value/other) |
| `POSTGRES_USER` | If PostgreSQL | `postgres` | DB user |
| `POSTGRES_PASSWORD` | If PostgreSQL | — | DB password (special chars URL-encoded in app) |
| `POSTGRES_HOST` | If PostgreSQL | `localhost` | DB host |
| `POSTGRES_PORT` | No | `5432` | DB port |
| `POSTGRES_DB` | No | `ai_legal_summarizer` | DB name |
| `SQLITE_DB_PATH` | If SQLite | project root `ai_legal_summarizer.db` | Path to SQLite file |
| `DATA_DIR` | No | `{PROJECT_ROOT}/data` | Base data directory (raw, processed, corpus) |
| `OPENAI_API_KEY` | Yes (for LLM) | — | API key for summaries/constitutional (e.g. Gemini) |
| `SECRET_KEY` | Production | `dev-secret-key-change-in-production` | Change in production |
| `TESSERACT_CMD` | No | `tesseract` | Tesseract executable if using OCR |
| `BACKUP_DIR` | No | `{PROJECT_ROOT}/backups` | Backup directory |
| `BACKUP_RETENTION_DAYS` | No | `30` | Backup retention |

**Docker (docker-compose):** Backend uses `DATABASE_URL`, `DATABASE_TYPE`, `REDIS_URL`, `ELASTICSEARCH_URL`, `OPENAI_API_KEY` (from host env).

---

## 5. Backend Deployment

### 5.1 Local / dev (port 8011)

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
# Set .env (especially OPENAI_API_KEY, DATABASE_TYPE, POSTGRES_* or SQLITE)
uvicorn app.main:app --host 0.0.0.0 --port 8011 --reload
```

- Health: `GET http://localhost:8011/health` → `{"status":"healthy", "service":"Legal Summarizer API"}`

### 5.2 Production (single process)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8011 --workers 2
```

- Use a process manager (systemd, supervisord) or reverse proxy (Nginx) in front.  
- For production, set `SECRET_KEY` and restrict CORS (see Section 8).

### 5.3 Docker

- **Dockerfile:** `backend/Dockerfile` — Python 3.10-slim, tesseract, poppler, exposes **8000**.
- **Run:** `docker build -t legal-backend ./backend` then  
  `docker run -p 8000:8000 -e OPENAI_API_KEY=your_key -e DATABASE_TYPE=sqlite -v $(pwd)/data:/app/data legal-backend`  
  (or use `docker-compose` for full stack).

---

## 6. Frontend Deployment

### 6.1 Dev (Vite, port 5173)

```bash
cd Frontend-main/Frontend
npm install
npm run dev
```

- API proxy: Vite proxies `/api` to `http://localhost:8011` (see `vite.config.ts`).  
- Backend must be on **8011** for this proxy; or change `api.ts` and `vite.config.ts` to match backend port.

### 6.2 Production build

```bash
cd Frontend-main/Frontend
npm install
npm run build
```

- Output: `dist/`. Serve with Nginx/Apache/any static host.  
- **API base URL:** Edit `Frontend-main/Frontend/src/config/api.ts`: set `BACKEND_HOST` and `BACKEND_PORT` to your deployed backend (e.g. `https://api.yourdomain.com` and omit port if 443), or use build-time env (e.g. `import.meta.env.VITE_API_BASE`) and point it to the production API.

---

## 7. Database

- **Init:** On startup, `init_db()` creates all tables (including RAG-related). No separate migration required for initial deploy.
- **SQLite:** Set `DATABASE_TYPE=sqlite` (or leave unset and use SQLite path). WAL mode and timeouts are set in code. Good for single-node/dev.
- **PostgreSQL:** Set `DATABASE_TYPE=postgresql` and `POSTGRES_*` (or `DATABASE_URL`). Recommended for production and multi-worker.

---

## 8. CORS and Production

- **Current origins:** `localhost:3000`, `127.0.0.1:3000`, `localhost:3001`, `localhost:5173`, `localhost:5174`, `127.0.0.1:5173`, `127.0.0.1:5174`.
- **Production:** In `backend/app/main.py`, add your frontend origin(s), e.g. `https://yourdomain.com`, and remove or restrict dev origins as needed.

---

## 9. Optional Services (Docker Compose)

- **PostgreSQL:** Used when `DATABASE_TYPE=postgresql` and `DATABASE_URL` points to `postgres:5432`.
- **Redis:** For Celery (async ingestion). Not required for core summarizer/analysis.
- **Elasticsearch:** Present in compose; app uses FAISS for vector search. Can be disabled if not used.

---

## 10. Data and Uploads

- **Data directories:** Under `DATA_DIR`: `raw_documents`, `processed`, `sri_lanka_legal_corpus`.  
- **Uploads:** Stored under backend (e.g. `backend/uploads` or `uploaded_docs`); Docker compose mounts `uploaded_docs`.  
- **Corpus PDF view:** `GET /api/analysis/corpus-pdf-view?file_name=...&title=...` serves HTML with embedded PDF; ensure corpus files are reachable by the backend.

---

## 11. Deployment Checklist

- [ ] Backend `.env` set: `OPENAI_API_KEY`, `DATABASE_TYPE`, DB credentials or SQLite path, `DATA_DIR` if needed.
- [ ] Production: `SECRET_KEY` changed.
- [ ] Backend port consistent: 8011 (dev) or 8000 (Docker); frontend proxy and `api.ts` match.
- [ ] Frontend production: `api.ts` (or env) points to production API URL.
- [ ] CORS: Production frontend origin added in `main.py`.
- [ ] Health check: `GET /health` returns 200.
- [ ] DB: Tables created on first run (`init_db()`).
- [ ] Optional: Tesseract/poppler installed if using OCR; Redis/Elasticsearch only if using those features.

---

## 12. Quick Reference — Ports and URLs

| Context | Backend | Frontend |
|---------|---------|----------|
| Local dev | `http://localhost:8011` | `http://localhost:5173` |
| Docker (compose) | `http://localhost:8000` | `http://localhost:5173` |
| Production | Your API host (e.g. `https://api.example.com`) | Your app host (e.g. `https://app.example.com`) |

**Key endpoints:**  
- `GET /health` — health check  
- `GET /api/analysis/...` — summaries, constitutional, related cases, corpus-pdf-view  
- `GET/POST /api/documents/...` — document upload/list  
- `GET/POST /api/rag/...` — RAG  
- `GET/POST /api/search/...` — search  

This report is intended for deployment and handover; keep `.env` and API keys out of version control.
