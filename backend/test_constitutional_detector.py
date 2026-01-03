"""
Test constitutional detector with the land case PDF
"""
import sys
sys.path.insert(0, r'e:\ai-legal-summarizer\backend')

import PyPDF2
from app.services.constitutional_article_detector import ConstitutionalArticleDetector

# Read PDF
print("=" * 80)
print("TESTING CONSTITUTIONAL ARTICLE DETECTOR WITH LAND CASE PDF")
print("=" * 80)

pdf_path = r'e:\ai-legal-summarizer\NLR-V-01-ALAWATUGODA-RATEMAHATMEYA-v.-KIRIWANTE.pdf'
pdf = open(pdf_path, 'rb')
reader = PyPDF2.PdfReader(pdf)
text = ''.join([page.extract_text() for page in reader.pages])
pdf.close()

print(f"\nExtracted text length: {len(text)} characters")
print("\nFirst 500 characters:")
print(text[:500])
print("...")

# Initialize detector
detector = ConstitutionalArticleDetector(semantic_threshold=0.35)

# Detect provisions
results = detector.detect(text)

print("\n" + "=" * 80)
print(f"RESULTS: {len(results)} constitutional provisions detected")
print("=" * 80)

if results:
    import json
    print(json.dumps(results, indent=2))
else:
    print("\nNo constitutional provisions detected in this case.")
    print("This is expected for old colonial-era cases that pre-date the Constitution.")
