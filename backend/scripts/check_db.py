#!/usr/bin/env python3
"""
Quick script to verify database usage. Run from backend: python scripts/check_db.py
Shows row counts for each table so you can confirm data is being saved after uploads.
"""
import sys
from pathlib import Path

# Add backend to path
backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend))

from app.db import SessionLocal
from app.models import (
    LegalDocument,
    DetectedRight,
    SLCitation,
    LegalEntity,
    DocumentChunk,
    RAGJob,
    RightsViolation,
    Bookmark,
    SearchHistory,
    UserPreference,
    UserAccount,
    ProcessingLog,
    CaseSimilarity,
    DocumentVersion,
    AuditLog,
)

def main():
    db = SessionLocal()
    try:
        tables = [
            ("legal_documents", LegalDocument),
            ("document_chunks", DocumentChunk),
            ("rag_jobs", RAGJob),
            ("detected_rights", DetectedRight),
            ("sl_citations", SLCitation),
            ("legal_entities", LegalEntity),
            ("rights_violations", RightsViolation),
            ("bookmarks", Bookmark),
            ("search_history", SearchHistory),
            ("user_preferences", UserPreference),
            ("user_accounts", UserAccount),
            ("processing_logs", ProcessingLog),
            ("case_similarities", CaseSimilarity),
            ("document_versions", DocumentVersion),
            ("audit_logs", AuditLog),
        ]
        print("Table row counts:")
        print("-" * 40)
        for name, model in tables:
            try:
                n = db.query(model).count()
                print(f"  {name}: {n}")
            except Exception as e:
                print(f"  {name}: (error: {e})")
        print("-" * 40)
        docs = db.query(LegalDocument).order_by(LegalDocument.id.desc()).limit(5).all()
        if docs:
            print("Recent documents (newest first):")
            for d in docs:
                print(f"  id={d.id}  file={d.file_name!r}  court={d.court}  year={d.year}")
        else:
            print("No documents in DB. Upload a PDF via the app (Upload & Analyze) to populate.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
