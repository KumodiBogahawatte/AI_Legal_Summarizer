import os
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Get base paths without imports
BASE_DIR = Path(__file__).resolve().parent.parent  # backend/app -> backend
PROJECT_ROOT = BASE_DIR.parent  # backend -> project root

# Load environment variables from backend directory
load_dotenv(BASE_DIR / ".env")

# Database Configuration
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "postgresql")  # Default to PostgreSQL

# PostgreSQL Configuration
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "ai_legal_summarizer")

# Construct DATABASE_URL based on type
if DATABASE_TYPE == "postgresql":
    # URL-encode password to handle special characters
    encoded_password = quote_plus(POSTGRES_PASSWORD)
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"postgresql://{POSTGRES_USER}:{encoded_password}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
else:  # SQLite fallback
    SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", str(PROJECT_ROOT / "ai_legal_summarizer.db"))
    DATABASE_URL = f"sqlite:///{SQLITE_DB_PATH}"

# Data directories (point to project data)
DATA_DIR = os.getenv("DATA_DIR", str(PROJECT_ROOT / "data"))
RAW_DIR = os.path.join(DATA_DIR, "raw_documents")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
CORPUS_DIR = os.path.join(DATA_DIR, "sri_lanka_legal_corpus")

# Tesseract cmd (if needed)
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "tesseract")

# Security settings
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Backup settings
BACKUP_DIR = os.getenv("BACKUP_DIR", str(PROJECT_ROOT / "backups"))
BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))

# Ingestion: skip LLM summaries + constitutional RAG + plain-language on upload (saves minutes).
# CaseAnalysis still calls /summarize/with-local-context (BART) after upload. Set to 0 for full pipeline.
INGESTION_SKIP_POST_CHUNK_LLM = os.getenv("INGESTION_SKIP_POST_CHUNK_LLM", "0").lower() in (
    "1",
    "true",
    "yes",
)