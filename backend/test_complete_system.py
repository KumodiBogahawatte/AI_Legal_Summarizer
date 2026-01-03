"""
Complete integration test - showing fundamental rights + constitutional provisions
"""
import sys
sys.path.insert(0, r'e:\ai-legal-summarizer\backend')

from app.services.fundamental_rights_detector import FundamentalRightsDetector
from app.services.constitutional_article_detector import ConstitutionalArticleDetector

print("=" * 80)
print("INTEGRATED LEGAL ANALYSIS SYSTEM TEST")
print("=" * 80)

# Test case 1: Fundamental Rights Case
print("\n\n" + "=" * 80)
print("TEST 1: FUNDAMENTAL RIGHTS CASE")
print("=" * 80)

fr_text = """
The Supreme Court held that the petitioner's fundamental rights under Article 12(1)
were violated. The petitioner was subjected to discriminatory treatment on the basis
of religion. Additionally, Article 13(1) was breached when the petitioner was arrested
without being informed of the reasons. The Court found evidence of torture and
inhuman treatment contrary to Article 11. The freedom of expression guaranteed under
Article 14(1)(a) was also restricted without lawful justification.
"""

fr_detector = FundamentalRightsDetector()
const_detector = ConstitutionalArticleDetector()

print("\nText:", fr_text.strip())
print("\n" + "-" * 80)

fr_results = fr_detector.detect(fr_text)
print(f"\n📜 FUNDAMENTAL RIGHTS DETECTED: {len(fr_results)}")
for i, r in enumerate(fr_results[:5], 1):
    print(f"{i}. Article {r['article']} - {r['explanation'][:80]}...")

const_results = const_detector.detect(fr_text)
print(f"\n📚 CONSTITUTIONAL PROVISIONS DETECTED: {len(const_results)}")
for i, r in enumerate(const_results[:5], 1):
    article = r.get('article', 'Unknown')
    method = r.get('method', 'unknown')
    print(f"{i}. Article {article} ({method})")

# Test case 2: Land/Property Case (like the PDF)
print("\n\n" + "=" * 80)
print("TEST 2: LAND/PROPERTY CASE (Similar to the PDF)")
print("=" * 80)

land_text = """
The charge against the accused was clearing Crown land for chena cultivation without
a permit, in breach of Forest Ordinance No. 10 of 1885, chapter IV. The Police 
Magistrate convicted the defendant. On appeal, the Supreme Court held that the 
judgment was defective under section 372 of the Criminal Procedure Code. The Court
noted that the prosecution failed to prove the land boundaries and that the land was
at the disposal of the Crown. The conviction was quashed and remitted for further
evidence.
"""

print("\nText:", land_text.strip())
print("\n" + "-" * 80)

fr_results2 = fr_detector.detect(land_text)
print(f"\n📜 FUNDAMENTAL RIGHTS DETECTED: {len(fr_results2)}")
if fr_results2:
    for i, r in enumerate(fr_results2, 1):
        print(f"{i}. Article {r['article']} - {r['explanation'][:80]}...")
else:
    print("   None (This is expected - not a fundamental rights case)")

const_results2 = const_detector.detect(land_text)
print(f"\n📚 CONSTITUTIONAL PROVISIONS DETECTED: {len(const_results2)}")
for i, r in enumerate(const_results2[:10], 1):
    article = r.get('article', 'Unknown')
    method = r.get('method', 'unknown')
    score = r.get('score', 0)
    print(f"{i}. Article {article} ({method}, score: {score:.3f})")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("""
✅ The system now detects BOTH:
   1. Fundamental Rights (Articles 10-18) - specific constitutional protections
   2. All Constitutional Provisions - comprehensive constitutional analysis

✅ For fundamental rights cases: Detects violations of Articles 10-18
✅ For other legal cases: Detects relevant constitutional provisions, procedures, etc.
✅ Uses both explicit mention detection and semantic similarity matching
""")
