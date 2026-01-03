"""
Test sentence extraction to find where truncation occurs
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db import SessionLocal
from app.models.document_model import LegalDocument
from nltk.tokenize import sent_tokenize

def test_sentence_extraction(doc_id: int):
    db = SessionLocal()
    try:
        doc = db.query(LegalDocument).filter_by(id=doc_id).first()
        if not doc:
            print(f"❌ Document {doc_id} not found")
            return
        
        text = doc.cleaned_text or doc.raw_text
        sentences = sent_tokenize(text)
        
        print(f"Total sentences: {len(sentences)}")
        print()
        
        # Check sentences that contain "Marso'of" (the truncation point we saw)
        print("Searching for sentences containing 'Marso':")
        for i, sent in enumerate(sentences):
            if 'Marso' in sent or 'marsoof' in sent.lower():
                print(f"\nSentence {i}:")
                print("-" * 80)
                print(sent)
                print("-" * 80)
                print(f"Length: {len(sent)} chars, {len(sent.split())} words")
        
        # Check last few sentences
        print("\n\nLast 3 sentences:")
        for i, sent in enumerate(sentences[-3:]):
            print(f"\nSentence {len(sentences) - 3 + i}:")
            print("-" * 80)
            print(sent)
            print("-" * 80)
            
    finally:
        db.close()

if __name__ == "__main__":
    doc_id = int(sys.argv[1]) if len(sys.argv) > 1 else 31
    test_sentence_extraction(doc_id)
