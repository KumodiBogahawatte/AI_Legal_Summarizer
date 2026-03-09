"""
Test Precedent Matching Similarity
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app.services.precedent_matcher import get_precedent_matcher


def test_similarity(document_id=1, top_k=5):
    """Test similarity search for a document."""
    
    print("=" * 70)
    print(f"TESTING SIMILARITY SEARCH FOR DOCUMENT {document_id}")
    print("=" * 70)
    
    db = SessionLocal()
    matcher = get_precedent_matcher()
    
    try:
        results = matcher.find_similar_cases(
            document_id=document_id,
            top_k=top_k,
            db=db
        )
        
        if not results:
            print("\n⚠️  No similar cases found!")
            return
        
        print(f"\n✅ Found {len(results)} similar cases:\n")
        
        for i, case in enumerate(results, 1):
            print(f"{i}. {case['file_name']}")
            print(f"   Similarity: {case['similarity_score']}%")
            print(f"   Weighted Score: {case['weighted_score']}%")
            print(f"   Court: {case['court']} (Weight: {case['court_weight']}%)")
            print(f"   Year: {case['year']}")
            print(f"   Recency: {case['recency']}%" if case['recency'] is not None else "   Recency: N/A")
            print(f"   Binding: {'Yes' if case['binding'] else 'No'}")
            print()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == '__main__':
    import sys
    doc_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    test_similarity(doc_id)
