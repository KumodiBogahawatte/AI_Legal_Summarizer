import os
import sys
import logging

# Add the current directory to sys.path to allow imports from app
sys.path.append(os.getcwd())

from app.db import engine, Base
from sqlalchemy import inspect

def check_models():
    logging.basicConfig(level=logging.INFO)
    print("Checking SQLAlchemy models...")
    
    # Import all models to register them
    from app.models import (
        LegalDocument,
        DetectedRight,
        SLCitation,
        RightsViolation,
        UserPreference,
        DocumentChunk,
        RAGJob
    )
    
    # Force mapper configuration
    from sqlalchemy.orm import configure_mappers
    try:
        configure_mappers()
        print("✅ Mappers configured successfully.")
    except Exception as e:
        print(f"❌ Mapper configuration failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Inspect SLCitation
    print("\nInspecting SLCitation mapper...")
    mapper = inspect(SLCitation)
    print(f"Relationships: {[r.key for r in mapper.relationships]}")
    if 'document' in [r.key for r in mapper.relationships]:
        print("✅ SLCitation has 'document' relationship.")
    else:
        print("❌ SLCitation MISSING 'document' relationship!")

    # Inspect LegalDocument
    print("\nInspecting LegalDocument mapper...")
    mapper = inspect(LegalDocument)
    print(f"Relationships: {[r.key for r in mapper.relationships]}")
    if 'citations' in [r.key for r in mapper.relationships]:
        print("✅ LegalDocument has 'citations' relationship.")
    else:
        print("❌ LegalDocument MISSING 'citations' relationship!")

if __name__ == "__main__":
    check_models()
