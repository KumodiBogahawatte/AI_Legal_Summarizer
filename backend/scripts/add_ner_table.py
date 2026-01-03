"""
Add new legal_entities table to database
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.db import engine, Base
from app.models import LegalEntity

def add_table():
    """Create the legal_entities table"""
    print("="*60)
    print("Adding legal_entities table to database")
    print("="*60)
    
    print("\n📋 Creating table schema...")
    Base.metadata.create_all(bind=engine, tables=[LegalEntity.__table__])
    
    print("✅ Table created successfully!")
    print("\n📊 Table structure:")
    print("   - id (INTEGER, PRIMARY KEY)")
    print("   - document_id (INTEGER, FOREIGN KEY)")
    print("   - entity_text (TEXT)")
    print("   - entity_type (VARCHAR)")
    print("   - start_pos (INTEGER)")
    print("   - end_pos (INTEGER)")
    print("   - context (TEXT)")
    print("   - confidence (FLOAT)")
    print("   - extracted_at (TIMESTAMP)")
    
    print("\n" + "="*60)
    print("✅ Database updated!")
    print("="*60)

if __name__ == "__main__":
    add_table()
