# backend/create_tables.py
from app.db import engine, Base
from app.models import LegalDocument, DetectedRight, SLCitation, RightsViolation, UserPreference

def create_tables():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    # List all created tables
    tables = list(Base.metadata.tables.keys())
    print(f"✅ Created tables: {tables}")

if __name__ == "__main__":
    create_tables()