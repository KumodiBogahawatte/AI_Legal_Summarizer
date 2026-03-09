"""
Test the NER API endpoint
"""
import requests
import json

# Test text with multiple entity types
test_text = """
In the landmark case of Silva vs. Fernando decided by the Supreme Court on 15th March 2006,
Justice S.N. Silva held that Section 175(1) of the Civil Procedure Code requires filing 
witness lists 15 days before trial. The Court cited precedent from [2005] 2 SRI L.R. 123 
establishing the burden of proof principle. This case also references Article 138 of the 
Constitution and the Maintenance Act No. 37 of 1999.
"""

print("=" * 70)
print("Testing Legal NER API Endpoint")
print("=" * 70)

# Test the POST endpoint for direct text
print("\n📝 Testing POST /api/analysis/extract-entities")
print("-" * 70)

try:
    response = requests.post(
        "http://localhost:8000/api/analysis/extract-entities",
        params={"text": test_text}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"\n📊 Results:")
        print(f"   Total entities: {data['total_entities']}")
        print(f"   Entity types: {', '.join(data['entity_types'])}")
        print(f"   Text length: {data['text_length']} characters")
        
        print(f"\n🏷️  Entities by Type:")
        for entity_type, entities in data['entities_by_type'].items():
            print(f"\n   {entity_type} ({len(entities)} found):")
            for ent in entities:
                print(f"      • {ent['text']}")
        
        print("\n" + "=" * 70)
        print("✅ NER API TEST SUCCESSFUL!")
        print("=" * 70)
    else:
        print(f"❌ Error: Status {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ Request failed: {e}")
    print("\n⚠️  Make sure the FastAPI server is running on port 8000")
