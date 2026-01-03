"""
Create PostgreSQL database if it doesn't exist
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_database():
    """Create the database if it doesn't exist"""
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = os.getenv('POSTGRES_PORT', '5432')
    user = os.getenv('POSTGRES_USER', 'postgres')
    password = os.getenv('POSTGRES_PASSWORD', '')
    db_name = os.getenv('POSTGRES_DB', 'ai_legal_summarizer')
    
    print(f"Connecting to PostgreSQL at {host}:{port} as user '{user}'...")
    
    try:
        # Connect to PostgreSQL server (default postgres database)
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database='postgres'  # Connect to default database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,)
        )
        exists = cursor.fetchone()
        
        if exists:
            print(f"✅ Database '{db_name}' already exists")
        else:
            # Create database
            cursor.execute(f'CREATE DATABASE {db_name}')
            print(f"✅ Database '{db_name}' created successfully")
        
        cursor.close()
        conn.close()
        
        # Now create the pgvector extension
        print(f"\nConnecting to '{db_name}' to enable pgvector extension...")
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=db_name
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            print("✅ pgvector extension enabled")
        except Exception as e:
            print(f"⚠️  Could not enable pgvector extension: {e}")
            print("   (This is optional and won't prevent basic functionality)")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*60)
        print("✅ Database setup complete!")
        print("="*60)
        print(f"\nYou can now run the migration script:")
        print("  python scripts/migrate_to_postgresql.py")
        
        return True
        
    except psycopg2.OperationalError as e:
        print(f"\n❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure PostgreSQL is running")
        print("2. Check your .env file has correct credentials:")
        print(f"   POSTGRES_HOST={host}")
        print(f"   POSTGRES_PORT={port}")
        print(f"   POSTGRES_USER={user}")
        print(f"   POSTGRES_PASSWORD=***")
        print("3. Try connecting with pgAdmin to verify credentials")
        return False
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == "__main__":
    create_database()
