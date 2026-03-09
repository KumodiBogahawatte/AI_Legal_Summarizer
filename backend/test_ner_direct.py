"""
Direct test of NER functionality without API
"""
import sys
sys.path.insert(0, 'e:\\ai-legal-summarizer\\backend')

from app.services.nlp_analyzer import NLPAnalyzer

# Test text with multiple entity types
test_text = """
In the landmark case of Silva vs. Fernando decided by the Supreme Court on 15th March 2006,
Justice S.N. Silva held that Section 175(1) of the Civil Procedure Code requires filing 
witness lists 15 days before trial. The Court cited precedent from [2005] 2 SRI L.R. 123 
establishing the burden of proof principle. This case also references Article 138 of the 
Constitution and the Maintenance Act No. 37 of 1999.
"""

print("=" * 70)
print("Testing Legal NER Model Integration")
print("=" * 70)

print("\n📝 Input Text:")
print(test_text.strip())

print("\n🔍 Extracting entities...")
entities = NLPAnalyzer.extract_legal_entities(test_text)

if "error" in entities:
    print(f"❌ Error: {entities['error']}")
else:
    total = sum(len(ents) for ents in entities.values())
    print(f"\n✅ Found {total} entities across {len(entities)} types\n")
    
    for entity_type, ent_list in sorted(entities.items()):
        print(f"🏷️  {entity_type} ({len(ent_list)} found):")
        for ent in ent_list:
            print(f"   • {ent['text']}")
        print()

print("=" * 70)
print("✅ NER INTEGRATION TEST COMPLETE")
print("=" * 70)
