"""
Real-World Legal NER Test
Tests the model on actual Sri Lankan legal case text
"""
import spacy
from pathlib import Path
import json

MODEL_DIR = Path(__file__).parent / "models" / "legal_ner"

# Real Sri Lankan legal case text samples
REAL_CASES = [
    {
        "name": "A.R. PERERA vs CENTRAL FREIGHT BUREAU (Excerpt)",
        "text": """
        A. R. PERERA AND OTHERS vs CENTRAL FREIGHT BUREAU OF SRI LANKA AND ANOTHER
        COURT OF APPEAL
        MARSOOF J.
        
        The 1st and 2nd petitioners - the Chairman and Secretary General of the Ceylon 
        Association of Ships Agents (CASA) consisting of 113 members who are shipping agents 
        and the 3rd petitioner who is a member of the Executive Committee of CASA and a 
        director/shareholder of Malship Ltd., which company is engaged in the business of 
        a shipping agent, challenged the order made by the 1st respondent by publishing a 
        Gazette Notification on 7.04.2006 (No. 1443/9 dated 07.04.2006).
        
        In paragraph 6 of their petition, the Petitioners expressly state that they are 
        invoking the jurisdiction of this Court in terms of Article 140 of the Constitution 
        in their individual capacities as well as on behalf of the members of the CASA.
        """
    },
    {
        "name": "Fundamental Rights Case (Excerpt)",
        "text": """
        SUPREME COURT OF SRI LANKA
        
        In the matter of an application under Article 126 of the Constitution of the 
        Democratic Socialist Republic of Sri Lanka.
        
        S.N. Silva CJ, Fernando J, and Jayasinghe J.
        
        The petitioner seeks relief for violation of fundamental rights guaranteed under 
        Articles 12(1), 13(1), and 14(1)(g) of the Constitution. The petitioner filed 
        this application on 15th December 2005, as per [2005] 2 Sri LR 145.
        
        This Court has consistently held that the doctrine of legitimate expectation is 
        a recognized principle of administrative law. The principle of audi alteram partem 
        requires that parties be given a fair hearing before any adverse action is taken.
        """
    },
    {
        "name": "Employment Law Case (Excerpt)",
        "text": """
        COURT OF APPEAL OF SRI LANKA
        CA No. 234/2004
        
        Petitioner v. State Engineering Corporation
        
        Hon. A.W.A. Salam J. and Somawansa J. delivered judgment on 23.05.2006.
        
        The petitioner challenged the termination under Section 31B of the Industrial 
        Disputes Act No. 43 of 1950. The respondent cited the Prevention of Terrorism Act 
        and the Evidence Ordinance. The Court examined the principle of natural justice 
        and res judicata as established in Silva v. Fernando [2003] 1 SLR 89.
        """
    }
]

def test_real_cases():
    """Test on real case excerpts"""
    print("="*80)
    print("REAL-WORLD LEGAL NER TEST")
    print("Testing on actual Sri Lankan legal case text")
    print("="*80)
    
    # Load model
    print(f"\n🔍 Loading model from: {MODEL_DIR}")
    try:
        nlp = spacy.load(str(MODEL_DIR))
        print("✅ Model loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        return
    
    print(f"📊 Entity types: {', '.join(nlp.get_pipe('ner').labels)}\n")
    
    all_results = []
    total_entities = 0
    
    for i, case in enumerate(REAL_CASES, 1):
        print(f"\n{'='*80}")
        print(f"TEST CASE {i}: {case['name']}")
        print(f"{'='*80}")
        
        doc = nlp(case['text'])
        
        # Group entities by type
        entities_by_type = {}
        for ent in doc.ents:
            if ent.label_ not in entities_by_type:
                entities_by_type[ent.label_] = []
            entities_by_type[ent.label_].append(ent.text)
        
        # Display results
        if entities_by_type:
            print(f"\n✅ Found {len(doc.ents)} entities:\n")
            for entity_type in sorted(entities_by_type.keys()):
                entities = entities_by_type[entity_type]
                print(f"   {entity_type} ({len(entities)}):")
                for entity in entities:
                    print(f"      • {entity}")
                total_entities += len(entities)
        else:
            print("\n⚠️  No entities found")
        
        all_results.append({
            "case": case['name'],
            "total_entities": len(doc.ents),
            "entities_by_type": entities_by_type
        })
    
    # Summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print("="*80)
    print(f"\n📊 Total entities extracted: {total_entities}")
    print(f"📄 Cases processed: {len(REAL_CASES)}")
    print(f"📈 Average per case: {total_entities / len(REAL_CASES):.1f}")
    
    # Quality checks
    print(f"\n{'='*80}")
    print("QUALITY CHECKS")
    print("="*80)
    
    checks_passed = 0
    total_checks = 3
    
    # Check 1: At least 5 entities per case on average
    avg_entities = total_entities / len(REAL_CASES)
    if avg_entities >= 5:
        print(f"   ✅ Average entities per case: {avg_entities:.1f} (target: ≥5)")
        checks_passed += 1
    else:
        print(f"   ❌ Average entities per case: {avg_entities:.1f} (target: ≥5)")
    
    # Check 2: All entity types present
    all_types = set()
    for result in all_results:
        all_types.update(result['entities_by_type'].keys())
    
    expected_types = {'CASE_NAME', 'COURT', 'JUDGE', 'STATUTE', 'ARTICLE', 
                     'LEGAL_PRINCIPLE', 'DATE', 'CITATION'}
    missing_types = expected_types - all_types
    
    if len(missing_types) <= 2:  # Allow 2 types to be missing
        print(f"   ✅ Entity type coverage: {len(all_types)}/8 types found")
        checks_passed += 1
    else:
        print(f"   ❌ Entity type coverage: {len(all_types)}/8 types found")
        print(f"      Missing: {', '.join(missing_types)}")
    
    # Check 3: Critical entities detected
    critical_entities = []
    for result in all_results:
        if 'COURT' in result['entities_by_type']:
            critical_entities.append('COURT')
        if 'ARTICLE' in result['entities_by_type']:
            critical_entities.append('ARTICLE')
    
    if len(critical_entities) >= 3:
        print(f"   ✅ Critical entities detected: {len(critical_entities)} instances")
        checks_passed += 1
    else:
        print(f"   ❌ Critical entities detected: {len(critical_entities)} instances")
    
    # Final verdict
    print(f"\n{'='*80}")
    print("FINAL VERDICT FOR PP1")
    print("="*80)
    
    success_rate = (checks_passed / total_checks) * 100
    
    if checks_passed == total_checks:
        print(f"\n   ✅ ALL CHECKS PASSED ({checks_passed}/{total_checks})")
        print("   ✅ Model is PRODUCTION READY")
        print("   ✅ SUITABLE FOR PP1 SUBMISSION")
    elif checks_passed >= 2:
        print(f"\n   ⚠️  MOST CHECKS PASSED ({checks_passed}/{total_checks})")
        print("   ⚠️  Model is FUNCTIONAL but could be improved")
        print("   ✅ ACCEPTABLE FOR PP1 SUBMISSION")
    else:
        print(f"\n   ❌ CHECKS FAILED ({checks_passed}/{total_checks})")
        print("   ❌ Model needs improvement")
        print("   ⚠️  NOT RECOMMENDED FOR PP1")
    
    print(f"\n{'='*80}")
    
    # Save results
    output_file = Path(__file__).parent / "ner_real_world_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "test_results": all_results,
            "summary": {
                "total_entities": total_entities,
                "cases_processed": len(REAL_CASES),
                "average_per_case": avg_entities,
                "checks_passed": checks_passed,
                "total_checks": total_checks,
                "success_rate": success_rate
            }
        }, f, indent=2)
    
    print(f"💾 Results saved to: {output_file}\n")

if __name__ == "__main__":
    test_real_cases()
