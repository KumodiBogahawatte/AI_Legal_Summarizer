"""
Database Status Check Script

Verifies:
1. How many documents are in the database
2. How many have embeddings
3. Lists all documents with their metadata
4. Checks for duplicates
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app.models.document_model import LegalDocument
from sqlalchemy import func


def check_database_status():
    """Check database status and document embeddings."""
    
    print("=" * 70)
    print("DATABASE STATUS CHECK")
    print("=" * 70)
    
    db = SessionLocal()
    
    try:
        # Total documents
        total_docs = db.query(LegalDocument).count()
        print(f"\n📊 Total Documents: {total_docs}")
        
        # Documents with embeddings
        docs_with_embeddings = db.query(LegalDocument).filter(
            LegalDocument.embedding.isnot(None)
        ).count()
        print(f"✅ Documents with Embeddings: {docs_with_embeddings}")
        print(f"❌ Documents without Embeddings: {total_docs - docs_with_embeddings}")
        
        # Check for duplicate filenames
        print("\n" + "=" * 70)
        print("CHECKING FOR DUPLICATES")
        print("=" * 70)
        
        duplicates = db.query(
            LegalDocument.file_name,
            func.count(LegalDocument.id).label('count')
        ).group_by(LegalDocument.file_name).having(func.count(LegalDocument.id) > 1).all()
        
        if duplicates:
            print(f"⚠️  Found {len(duplicates)} duplicate filenames:")
            for filename, count in duplicates:
                print(f"   - {filename}: {count} copies")
                # Show IDs of duplicates
                dup_docs = db.query(LegalDocument).filter(
                    LegalDocument.file_name == filename
                ).all()
                print(f"     IDs: {[d.id for d in dup_docs]}")
        else:
            print("✅ No duplicate filenames found")
        
        # List all documents
        print("\n" + "=" * 70)
        print("ALL DOCUMENTS IN DATABASE")
        print("=" * 70)
        
        all_docs = db.query(LegalDocument).order_by(LegalDocument.id).all()
        
        for doc in all_docs:
            has_embedding = "✅" if doc.embedding and len(doc.embedding) > 0 else "❌"
            embedding_dim = len(doc.embedding) if doc.embedding else 0
            
            print(f"\nID: {doc.id}")
            print(f"  File: {doc.file_name}")
            print(f"  Court: {doc.court or 'N/A'}")
            print(f"  Year: {doc.year or 'N/A'}")
            print(f"  Case Number: {doc.case_number or 'N/A'}")
            print(f"  Has Text: {'✅' if doc.cleaned_text or doc.raw_text else '❌'}")
            print(f"  Embedding: {has_embedding} (dim: {embedding_dim})")
        
        # Summary statistics
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        
        if total_docs == 0:
            print("⚠️  No documents in database!")
            print("   Run upload script or use the upload API endpoint")
        elif docs_with_embeddings == 0:
            print("⚠️  No embeddings generated!")
            print("   Run: python scripts/generate_embeddings.py")
        elif docs_with_embeddings < total_docs:
            print(f"⚠️  {total_docs - docs_with_embeddings} documents missing embeddings")
            print("   Run: python scripts/generate_embeddings.py")
        else:
            print("✅ All documents have embeddings!")
        
        if duplicates:
            print(f"\n⚠️  {len(duplicates)} duplicate filenames need cleanup")
            print("   Consider running a deduplication script")
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"❌ Error checking database: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == '__main__':
    check_database_status()
