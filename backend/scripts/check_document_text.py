"""
Quick diagnostic script to check document text completeness
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db import SessionLocal
from app.models.document_model import LegalDocument

def check_document(doc_id: int):
    db = SessionLocal()
    try:
        doc = db.query(LegalDocument).filter_by(id=doc_id).first()
        if not doc:
            print(f"❌ Document {doc_id} not found")
            return
        
        print(f"📄 Document: {doc.file_name}")
        print("=" * 80)
        print(f"Raw text length: {len(doc.raw_text) if doc.raw_text else 0:,} characters")
        print(f"Cleaned text length: {len(doc.cleaned_text) if doc.cleaned_text else 0:,} characters")
        print()
        
        if doc.cleaned_text:
            print("Last 500 characters of cleaned text:")
            print("-" * 80)
            print(doc.cleaned_text[-500:])
            print("-" * 80)
            print(f"\nEnds with: '{doc.cleaned_text[-1]}'")
            print(f"Ends properly: {doc.cleaned_text[-1] in '.!?'}")
        
        if doc.raw_text:
            print("\n\nLast 500 characters of raw text:")
            print("-" * 80)
            print(doc.raw_text[-500:])
            print("-" * 80)
            print(f"\nEnds with: '{doc.raw_text[-1]}'")
            
    finally:
        db.close()

if __name__ == "__main__":
    doc_id = int(sys.argv[1]) if len(sys.argv) > 1 else 31
    check_document(doc_id)
