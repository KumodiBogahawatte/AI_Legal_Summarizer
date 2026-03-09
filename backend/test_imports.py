#!/usr/bin/env python3
"""
Test script to check if all imports work correctly
"""

def test_imports():
    print("Testing imports...")
    
    try:
        # Test database
        from app.db import engine, Base
        print("✅ Database imports work")
        
        # Test models
        from app.models import LegalDocument, DetectedRight, SLCitation, RightsViolation, UserPreference
        print("✅ Model imports work")
        
        # Test routes
        from app.routes.document_routes import router as document_router
        from app.routes.summary_routes import router as summary_router
        print("✅ Route imports work")
        
        # Test services
        from app.services.document_processor import DocumentProcessor
        from app.services.sri_lanka_legal_engine import SriLankaLegalEngine
        from app.services.nlp_analyzer import NLPAnalyzer
        print("✅ Service imports work")
        
        # Test utils
        from app.utils.sri_lanka_legal_utils import GLOSSARY_SI_EN_TA
        print("✅ Util imports work")
        
        print("\n🎉 All imports successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Other error: {e}")
        return False

if __name__ == "__main__":
    test_imports()