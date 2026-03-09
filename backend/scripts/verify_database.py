"""
Verify PostgreSQL database setup
"""
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import inspect, text
from app.db import engine

def verify_database():
    """Check database tables and structure"""
    inspector = inspect(engine)
    
    print("=" * 60)
    print("PostgreSQL Database Verification")
    print("=" * 60)
    
    # Get all tables
    tables = inspector.get_table_names()
    print(f"\n✅ Found {len(tables)} tables:")
    for table in sorted(tables):
        print(f"   - {table}")
    
    # Check each table's columns
    print(f"\n{'='*60}")
    print("Table Details:")
    print("=" * 60)
    
    for table in sorted(tables):
        columns = inspector.get_columns(table)
        print(f"\n📋 {table} ({len(columns)} columns):")
        for col in columns:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            print(f"   - {col['name']}: {col['type']} {nullable}")
    
    # Test connection
    print(f"\n{'='*60}")
    print("Connection Test:")
    print("=" * 60)
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print(f"✅ Connected to PostgreSQL")
        print(f"   Version: {version[:50]}...")
        
        result = conn.execute(text("SELECT current_database()"))
        db_name = result.fetchone()[0]
        print(f"   Database: {db_name}")
    
    print(f"\n{'='*60}")
    print("✅ Database setup verified successfully!")
    print("=" * 60)

if __name__ == "__main__":
    verify_database()
