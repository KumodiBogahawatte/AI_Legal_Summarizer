"""
bulk_process_all_data.py
────────────────────────
Completely wipes the SQLite database, recreates it, and runs the FULL DocumentProcessor
pipeline (including OpenAI-powered CaseBriefGenerator and NER) on all PDFs and ZIP
files found in `data/raw_documents`.
"""

import os
import sys
import zipfile
import tempfile
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load OpenAI key and DB config
load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(BACKEND_DIR))

# Ensure SQLite is used
os.environ["DATABASE_TYPE"] = "sqlite"
os.environ["SQLITE_DB_PATH"] = str(BACKEND_DIR.parent / "ai_legal_summarizer.db")

from app.db import SessionLocal, engine, Base
from app.services.document_processor import DocumentProcessor

DATA_DIR = BACKEND_DIR.parent / "data" / "raw_documents"

def recreate_database():
    """Wipe and recreate all tables in SQLite."""
    logger.info("🗑️ Wiping existing database tables...")
    Base.metadata.drop_all(bind=engine)
    logger.info("✨ Recreating database schema...")
    Base.metadata.create_all(bind=engine)

def process_pdf(pdf_path: Path, db):
    """Run full pipeline on a single PDF."""
    logger.info(f"📄 Processing: {pdf_path.name}")
    try:
        with open(pdf_path, "rb") as f:
            file_bytes = f.read()
        
        # This orchestrates cleaning, NER, structure analysis, FAISS chunking,
        # and case brief generation (which will use OpenAI if available).
        doc = DocumentProcessor.process_and_save(
            db=db,
            file_name=pdf_path.name,
            file_path=str(pdf_path),
            file_bytes=file_bytes
        )
        logger.info(f"✅ Success: {doc.file_name} (ID: {doc.id})")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to process {pdf_path.name}: {e}")
        db.rollback()
        return False

def main():
    if not DATA_DIR.exists():
        logger.error(f"❌ Directory not found: {DATA_DIR}")
        sys.exit(1)

    # 1. Recreate DB
    recreate_database()
    
    # 2. Collect all PDFs (direct or inside ZIPs)
    temp_dir = tempfile.mkdtemp()
    pdf_files_to_process = []
    
    # Direct PDFs
    for pdf_file in DATA_DIR.glob("*.pdf"):
        pdf_files_to_process.append(pdf_file)
        
    # Extracted from ZIPs
    for zip_file in DATA_DIR.glob("*.zip"):
        logger.info(f"📦 Unzipping: {zip_file.name}")
        try:
            with zipfile.ZipFile(zip_file, 'r') as zf:
                zf.extractall(temp_dir)
        except zipfile.BadZipFile:
            logger.error(f"❌ Bad ZIP file: {zip_file.name}")
            continue
            
    # Add extracted PDFs
    for root, _, files in os.walk(temp_dir):
        for f in files:
            if f.lower().endswith(".pdf"):
                pdf_files_to_process.append(Path(root) / f)

    logger.info(f"🚀 Found {len(pdf_files_to_process)} PDFs to process.")
    
    # 3. Process each PDF Document
    db = SessionLocal()
    success_count = 0
    fail_count = 0
    
    # To prevent overwhelming the OpenAI API rate limits and to track progress:
    for i, pdf_path in enumerate(pdf_files_to_process, 1):
        logger.info(f"[{i}/{len(pdf_files_to_process)}] Starting...")
        if process_pdf(pdf_path, db):
            success_count += 1
        else:
            fail_count += 1
            
    db.close()
    
    logger.info(f"🎉 Bulk Processing Complete!")
    logger.info(f"📊 Successfully Ingested: {success_count} documents.")
    logger.info(f"❌ Failed: {fail_count} documents.")

if __name__ == "__main__":
    main()
