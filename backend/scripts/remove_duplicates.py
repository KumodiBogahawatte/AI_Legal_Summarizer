"""
Remove Duplicate Documents

This script removes duplicate documents (keeping only the first occurrence
of each unique filename).
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app.models.document_model import LegalDocument
from sqlalchemy import func


def remove_duplicates():
    """Remove duplicate documents from database."""
    
    print("=" * 70)
    print("REMOVING DUPLICATE DOCUMENTS")
    print("=" * 70)
    
    db = SessionLocal()
    
    try:
        # Find duplicates
        duplicates = db.query(
            LegalDocument.file_name,
            func.count(LegalDocument.id).label('count')
        ).group_by(LegalDocument.file_name).having(func.count(LegalDocument.id) > 1).all()
        
        if not duplicates:
            print("✅ No duplicates found!")
            return
        
        print(f"\nFound {len(duplicates)} files with duplicates:")
        
        total_removed = 0
        
        for filename, count in duplicates:
            print(f"\n📄 {filename} ({count} copies)")
            
            # Get all documents with this filename
            docs = db.query(LegalDocument).filter(
                LegalDocument.file_name == filename
            ).order_by(LegalDocument.id).all()
            
            # Keep first, delete rest
            keep_doc = docs[0]
            remove_docs = docs[1:]
            
            print(f"  ✅ Keeping ID: {keep_doc.id}")
            
            for doc in remove_docs:
                print(f"  ❌ Removing ID: {doc.id}")
                db.delete(doc)
                total_removed += 1
            
            db.commit()
        
        print("\n" + "=" * 70)
        print(f"✅ Removed {total_removed} duplicate documents")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == '__main__':
    # Ask for confirmation
    response = input("This will permanently delete duplicate documents. Continue? (yes/no): ")
    if response.lower() == 'yes':
        remove_duplicates()
    else:
        print("Operation cancelled")
