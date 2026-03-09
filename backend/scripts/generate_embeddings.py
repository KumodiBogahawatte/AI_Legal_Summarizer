"""
Generate Embeddings for Documents

This script generates embeddings for all documents in the database
that don't have them yet.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app.models.document_model import LegalDocument
from app.services.embedding_service import get_embedding_service
from app.services.precedent_matcher import PrecedentMatcher


def generate_embeddings():
    """Generate embeddings for all documents without them."""
    
    print("=" * 70)
    print("GENERATING EMBEDDINGS FOR DOCUMENTS")
    print("=" * 70)
    
    db = SessionLocal()
    
    try:
        # Get embedding service
        embedding_service = get_embedding_service()
        matcher = PrecedentMatcher()
        
        # Get documents without embeddings
        docs_without_embeddings = db.query(LegalDocument).filter(
            LegalDocument.embedding.is_(None)
        ).all()
        
        total = len(docs_without_embeddings)
        
        if total == 0:
            print("✅ All documents already have embeddings!")
            return
        
        print(f"\nFound {total} documents without embeddings")
        print("Generating embeddings...\n")
        
        success_count = 0
        error_count = 0
        
        for idx, doc in enumerate(docs_without_embeddings, 1):
            try:
                print(f"[{idx}/{total}] Processing: {doc.file_name}")
                
                # Prepare text
                text = matcher._prepare_text_for_embedding(doc)
                
                if not text or len(text.strip()) < 10:
                    print(f"  ⚠️  Skipping - no text content")
                    error_count += 1
                    continue
                
                # Generate embedding
                embedding = embedding_service.generate_document_embedding(text)
                
                # Save to database
                doc.embedding = embedding.tolist()
                db.commit()
                
                print(f"  ✅ Embedding generated (dim: {len(embedding)})")
                success_count += 1
                
            except Exception as e:
                print(f"  ❌ Error: {str(e)}")
                error_count += 1
                db.rollback()
                continue
        
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"✅ Successfully generated: {success_count}")
        print(f"❌ Failed: {error_count}")
        print(f"📊 Total processed: {total}")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == '__main__':
    generate_embeddings()
