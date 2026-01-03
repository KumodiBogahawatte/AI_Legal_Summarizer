"""
SQLite to PostgreSQL Migration Script

This script migrates data from SQLite to PostgreSQL for the AI Legal Summarizer project.

Usage:
    python migrate_to_postgresql.py

Requirements:
    - PostgreSQL database created and accessible
    - .env file configured with PostgreSQL connection details
    - SQLite database file exists
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL, PROJECT_ROOT
from app.db import Base
from app.models import *
import json
from datetime import datetime

# SQLite source
SQLITE_DB_PATH = PROJECT_ROOT / "ai_legal_summarizer.db"
SQLITE_URL = f"sqlite:///{SQLITE_DB_PATH}"

def migrate_data():
    """Migrate data from SQLite to PostgreSQL"""
    
    print("=" * 60)
    print("SQLite to PostgreSQL Migration")
    print("=" * 60)
    
    # Check if SQLite database exists
    if not SQLITE_DB_PATH.exists():
        print(f"❌ SQLite database not found at: {SQLITE_DB_PATH}")
        print("Nothing to migrate. Creating fresh PostgreSQL database...")
        create_fresh_database()
        return
    
    print(f"\n📂 Source (SQLite): {SQLITE_DB_PATH}")
    print(f"📂 Target (PostgreSQL): {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")
    
    # Create engines
    print("\n🔌 Connecting to databases...")
    sqlite_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
    postgres_engine = create_engine(DATABASE_URL)
    
    # Create sessions
    SqliteSession = sessionmaker(bind=sqlite_engine)
    PostgresSession = sessionmaker(bind=postgres_engine)
    
    sqlite_session = SqliteSession()
    postgres_session = PostgresSession()
    
    # Create all tables in PostgreSQL
    print("\n🏗️  Creating tables in PostgreSQL...")
    Base.metadata.create_all(bind=postgres_engine)
    print("✅ Tables created successfully")
    
    # Get list of tables from SQLite
    inspector = inspect(sqlite_engine)
    tables = inspector.get_table_names()
    
    print(f"\n📋 Found {len(tables)} tables in SQLite database")
    
    # Migration statistics
    stats = {}
    
    try:
        # Migrate each table
        for table_name in tables:
            print(f"\n📦 Migrating table: {table_name}")
            
            # Get model class
            model_class = get_model_class(table_name)
            if not model_class:
                print(f"⚠️  Skipping {table_name} - no model class found")
                continue
            
            # Get all records from SQLite
            sqlite_records = sqlite_session.query(model_class).all()
            record_count = len(sqlite_records)
            
            if record_count == 0:
                print(f"   ℹ️  No records to migrate")
                stats[table_name] = 0
                continue
            
            # Insert into PostgreSQL
            migrated = 0
            for record in sqlite_records:
                # Create new instance with same data
                record_dict = {c.name: getattr(record, c.name) 
                              for c in record.__table__.columns}
                new_record = model_class(**record_dict)
                postgres_session.add(new_record)
                migrated += 1
            
            # Commit this table's data
            postgres_session.commit()
            stats[table_name] = migrated
            print(f"   ✅ Migrated {migrated} records")
        
        print("\n" + "=" * 60)
        print("Migration Summary:")
        print("=" * 60)
        for table, count in stats.items():
            print(f"  {table}: {count} records")
        print(f"\nTotal records migrated: {sum(stats.values())}")
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        postgres_session.rollback()
        raise
    finally:
        sqlite_session.close()
        postgres_session.close()

def get_model_class(table_name):
    """Get SQLAlchemy model class by table name"""
    model_map = {
        'legal_documents': LegalDocument,
        'detected_rights': DetectedRight,
        'sl_citations': SLCitation,
        'rights_violations': RightsViolation,
        'user_preferences': UserPreference,
        'user_accounts': UserAccount,
        'bookmarks': Bookmark,
        'search_history': SearchHistory,
        'processing_logs': ProcessingLog,
        'case_similarities': CaseSimilarity,
        'document_versions': DocumentVersion,
        'audit_logs': AuditLog,
    }
    return model_map.get(table_name)

def create_fresh_database():
    """Create fresh PostgreSQL database with empty tables"""
    print("\n🏗️  Creating fresh PostgreSQL database...")
    postgres_engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=postgres_engine)
    print("✅ PostgreSQL database created with all tables")

def verify_migration():
    """Verify the migration by checking record counts"""
    print("\n🔍 Verifying migration...")
    
    if not SQLITE_DB_PATH.exists():
        print("⚠️  No SQLite database to verify against")
        return
    
    sqlite_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
    postgres_engine = create_engine(DATABASE_URL)
    
    SqliteSession = sessionmaker(bind=sqlite_engine)
    PostgresSession = sessionmaker(bind=postgres_engine)
    
    sqlite_session = SqliteSession()
    postgres_session = PostgresSession()
    
    print("\nRecord count comparison:")
    print("-" * 60)
    print(f"{'Table':<30} {'SQLite':<15} {'PostgreSQL':<15} {'Status':<10}")
    print("-" * 60)
    
    all_match = True
    tables_to_check = [
        ('legal_documents', LegalDocument),
        ('detected_rights', DetectedRight),
        ('sl_citations', SLCitation),
        ('rights_violations', RightsViolation),
        ('user_preferences', UserPreference),
    ]
    
    for table_name, model_class in tables_to_check:
        try:
            sqlite_count = sqlite_session.query(model_class).count()
            postgres_count = postgres_session.query(model_class).count()
            status = "✅ OK" if sqlite_count == postgres_count else "❌ MISMATCH"
            if sqlite_count != postgres_count:
                all_match = False
            print(f"{table_name:<30} {sqlite_count:<15} {postgres_count:<15} {status:<10}")
        except Exception as e:
            print(f"{table_name:<30} {'ERROR':<15} {'ERROR':<15} {'❌ ERROR':<10}")
            all_match = False
    
    print("-" * 60)
    
    if all_match:
        print("\n✅ Verification successful - all record counts match!")
    else:
        print("\n⚠️  Verification found mismatches - please review migration")
    
    sqlite_session.close()
    postgres_session.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate SQLite data to PostgreSQL")
    parser.add_argument('--verify-only', action='store_true', 
                       help='Only verify existing migration, do not migrate')
    args = parser.parse_args()
    
    if args.verify_only:
        verify_migration()
    else:
        migrate_data()
        print("\n" + "=" * 60)
        verify_migration()
