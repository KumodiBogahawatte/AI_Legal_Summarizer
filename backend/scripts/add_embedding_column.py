"""
Add embedding column to legal_documents table

This migration adds a JSON column to store vector embeddings
for precedent matching functionality.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import engine
import sqlalchemy


def add_embedding_column():
    """Add embedding column to legal_documents table."""
    
    print("=" * 70)
    print("Adding embedding column to legal_documents table...")
    print("=" * 70)
    
    try:
        with engine.connect() as conn:
            # Add column if it doesn't exist
            conn.execute(sqlalchemy.text(
                "ALTER TABLE legal_documents ADD COLUMN IF NOT EXISTS embedding JSON"
            ))
            conn.commit()
            
            print("✅ Embedding column added successfully!")
            
            # Verify column exists
            result = conn.execute(sqlalchemy.text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'legal_documents' 
                AND column_name = 'embedding'
            """))
            
            row = result.fetchone()
            if row:
                print(f"✅ Verified: Column '{row[0]}' with type '{row[1]}' exists")
            else:
                print("⚠️ Warning: Could not verify column existence")
            
            print("=" * 70)
            
    except Exception as e:
        print(f"❌ Error adding embedding column: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    add_embedding_column()
