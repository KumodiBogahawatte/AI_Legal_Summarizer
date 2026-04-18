from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI Generated Sri Lankan Legal Case Summarizer",
    description="NLR/SLR Case Summaries, Rights Detection, Sinhala/Tamil Legal AI",
    version="1.0"
)

# IMPROVED CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://159.223.43.32",
        "http://159.223.43.32:80",
        "https://159.223.43.32",
        "http://ailegalsummarizersliit.site",
        "https://ailegalsummarizersliit.site",
        "https://lawknow.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

# Import and include all routes
from app.routes.document_routes import router as document_router
from app.routes.summary_routes import router as summary_router
from app.routes.user_routes import router as user_router

from app.routes.ner_routes import router as ner_router

# New RAG v2 and Search routes
from app.routes.rag_v2_routes import router as rag_v2_router
from app.routes.search_routes import router as search_router

app.include_router(document_router, prefix="/api")
app.include_router(summary_router, prefix="/api/analysis")
app.include_router(user_router, prefix="/api")
app.include_router(ner_router)

# RAG v2 (new chunk-level RAG pipeline)
app.include_router(rag_v2_router, prefix="/api/rag")
# Elasticsearch full-text search
app.include_router(search_router, prefix="/api/search")

from app.db import Base, engine, init_db

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    print("🚀 Starting application...")

    # Initialize database + new RAG tables
    from app.db import init_db
    init_db()
    print("✅ Database initialized")

    # We no longer pre-load BART since we migrated to OpenAI + FAISS

    # Pre-warm RAG services (non-blocking, failures are OK)
    try:
        print("📥 Initializing RAG services...")
        from app.services.rag_service_v2 import get_rag_service_v2
        get_rag_service_v2()
        print("✅ RAGServiceV2 ready")
    except Exception as e:
        print(f"⚠️ RAGServiceV2 not ready: {e}")

    try:
        from app.services.constitutional_rag_module import get_constitutional_rag
        get_constitutional_rag()
        print("✅ ConstitutionalRAGModule ready")
    except Exception as e:
        print(f"⚠️ ConstitutionalRAGModule not ready: {e}")

    # Elasticsearch is no longer used, we use FAISS instead for vector similarity

    print("✅ Application started successfully!")

@app.get("/")
def root():
    return {"message": "Sri Lankan AI Legal Summarizer API Running"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Legal Summarizer API"}