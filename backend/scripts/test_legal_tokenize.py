"""Test the new legal_sent_tokenize function"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db import SessionLocal
from app.models.document_model import LegalDocument
from app.services.advanced_summarizer import legal_sent_tokenize

db = SessionLocal()
try:
    doc = db.query(LegalDocument).filter_by(id=31).first()
    text = doc.cleaned_text
    
    # Find the Premadasa sentence
    idx = text.find('For instance, in Premadasa')
    snippet = text[idx:idx+800]
    
    sentences = legal_sent_tokenize(snippet)
    
    print(f"Found {len(sentences)} sentences in snippet")
    for i, sent in enumerate(sentences):
        print(f"\nSentence {i+1} ({len(sent.split())} words):")
        print("-" * 80)
        print(sent)
        print("-" * 80)
        
finally:
    db.close()
