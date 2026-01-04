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
        "http://localhost:5173"
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

app.include_router(document_router, prefix="/api")
app.include_router(summary_router, prefix="/api/analysis")  # CHANGED BACK: Use /api/analysis
app.include_router(user_router, prefix="/api")
app.include_router(ner_router)

from app.db import Base, engine, init_db

@app.on_event("startup")
async def startup_event():
    init_db()
    print("✅ Application started successfully!")

@app.get("/")
def root():
    return {"message": "Sri Lankan AI Legal Summarizer API Running"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Legal Summarizer API"}