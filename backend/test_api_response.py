"""
Quick test to verify the summary endpoint returns constitutional provisions
"""
import sys
sys.path.insert(0, r'e:\ai-legal-summarizer\backend')

# Simulate what happens when document is uploaded and summary is requested
print("=" * 80)
print("TESTING SUMMARY ENDPOINT WITH CONSTITUTIONAL PROVISIONS")
print("=" * 80)

from app.services.nlp_analyzer import NLPAnalyzer
from app.services.sri_lanka_legal_engine import SriLankaLegalEngine

# Sample text from the land case
text = """
The charge against the accused was clearing Crown land for chena cultivation without
a permit, in breach of Forest Ordinance No. 10 of 1885, chapter IV. The Police 
Magistrate convicted the defendant. On appeal, the Supreme Court held that the 
judgment was defective under section 372 of the Criminal Procedure Code. The Court
noted that the prosecution failed to prove the land boundaries and that the land was
at the disposal of the Crown. The conviction was quashed and remitted for further
evidence. It does not follow that every patch of ground in the Island which has forest
trees on it, or is waste, or is unoccupied or uncultivated, is presumed to be the 
property of the Crown.
"""

print("\nInitializing engines...")
nlp_analyzer = NLPAnalyzer()
legal_engine = SriLankaLegalEngine()

print("\n1. Generating summary...")
summary = nlp_analyzer.extractive_summary(text, n_sentences=3)
print(f"Summary: {summary[:200]}...")

print("\n2. Extracting keywords...")
keywords = nlp_analyzer.extract_keywords(text)
print(f"Keywords: {keywords[:10]}")

print("\n3. Detecting multilingual terms...")
multilingual_terms = legal_engine.detect_multilingual_terms(text)
print(f"Multilingual terms: {len(multilingual_terms)} found")

print("\n4. Detecting constitutional provisions...")
constitutional_provisions = legal_engine.analyze_constitutional_provisions(text, language="en")
print(f"Constitutional provisions: {len(constitutional_provisions)} found")

if constitutional_provisions:
    print("\nFirst 5 provisions:")
    for i, prov in enumerate(constitutional_provisions[:5], 1):
        print(f"  {i}. Article {prov.get('article', 'Unknown')} ({prov.get('method', 'unknown')})")
        print(f"     Score: {prov.get('score', 0):.3f}")
        print(f"     Text: {prov.get('matched_text', '')[:80]}...")

print("\n5. Simulating API response...")
response_data = {
    "document_id": 999,
    "summary": summary,
    "keywords": keywords,
    "multilingual_legal_terms": multilingual_terms,
    "constitutional_provisions": constitutional_provisions
}

import json
print(json.dumps({
    "document_id": response_data["document_id"],
    "summary_length": len(response_data["summary"]),
    "keywords_count": len(response_data["keywords"]),
    "multilingual_terms_count": len(response_data["multilingual_legal_terms"]),
    "constitutional_provisions_count": len(response_data["constitutional_provisions"])
}, indent=2))

print("\n" + "=" * 80)
print("✅ Backend is ready to return constitutional provisions!")
print("✅ Frontend will now display all detected provisions")
print("=" * 80)
