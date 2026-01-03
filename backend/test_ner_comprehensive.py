"""
Comprehensive Legal NER Model Test
Verifies model accuracy and entity extraction quality
"""
import spacy
from pathlib import Path
from collections import defaultdict
import json

# Configuration
PROJECT_ROOT = Path(__file__).parent
MODEL_DIR = PROJECT_ROOT / "models" / "legal_ner"

# Comprehensive test cases covering all 8 entity types
TEST_CASES = [
    {
        "name": "Full Legal Case Citation",
        "text": """
        In the landmark case of Silva vs. Fernando decided by the Supreme Court of Sri Lanka 
        on 15th March 2006, Justice S.N. Silva held that Section 175(1) of the Civil Procedure Code 
        requires filing witness lists 15 days before trial. The Court cited precedent from 
        [2005] 2 SRI L.R. 123 establishing the burden of proof principle. This case also 
        references Article 138 of the Constitution and the Maintenance Act No. 37 of 1999.
        """,
        "expected_entities": {
            "CASE_NAME": ["Silva vs. Fernando"],
            "COURT": ["Supreme Court"],
            "DATE": ["15th March 2006"],
            "JUDGE": ["Justice S.N. Silva"],
            "ARTICLE": ["Section 175(1)", "Article 138"],
            "STATUTE": ["Civil Procedure Code", "Constitution", "Maintenance Act No. 37 of 1999"],
            "CITATION": ["[2005] 2 SRI L.R. 123"],
            "LEGAL_PRINCIPLE": ["burden of proof"]
        }
    },
    {
        "name": "Court of Appeal Case",
        "text": """
        The Court of Appeal in Perera and Another vs. Bank of Ceylon (CA 450/2003) 
        examined Article 154P(3)(b) of the Constitution. Hon. Andrew Somawansa, J. 
        delivered the judgment on 21.02.2005, applying the doctrine of legitimate expectation.
        """,
        "expected_entities": {
            "COURT": ["Court of Appeal"],
            "CASE_NAME": ["Perera and Another vs. Bank of Ceylon"],
            "CITATION": ["CA 450/2003"],
            "ARTICLE": ["Article 154P(3)(b)"],
            "STATUTE": ["Constitution"],
            "JUDGE": ["Andrew Somawansa, J."],
            "DATE": ["21.02.2005"],
            "LEGAL_PRINCIPLE": ["legitimate expectation"]
        }
    },
    {
        "name": "High Court Ruling",
        "text": """
        The High Court of Colombo considered the Evidence Ordinance and fundamental rights 
        under Article 12(1). The learned District Judge applied the doctrine of res judicata 
        as per the ruling in DC Colombo 17090/L. The Prevention of Terrorism Act was also cited.
        """,
        "expected_entities": {
            "COURT": ["High Court"],
            "STATUTE": ["Evidence Ordinance", "Prevention of Terrorism Act"],
            "ARTICLE": ["Article 12(1)"],
            "LEGAL_PRINCIPLE": ["fundamental rights", "res judicata"],
            "CITATION": ["DC Colombo 17090/L"]
        }
    },
    {
        "name": "Constitutional Review",
        "text": """
        In Singarasa v. Attorney General [2006] 2 SLR 141, the Supreme Court examined 
        Article 13(4) and Article 126 of the Constitution. Chief Justice Sarath N. Silva 
        held on 15/09/2006 that the principle of natural justice applies.
        """,
        "expected_entities": {
            "CASE_NAME": ["Singarasa v. Attorney General"],
            "CITATION": ["[2006] 2 SLR 141"],
            "COURT": ["Supreme Court"],
            "ARTICLE": ["Article 13(4)", "Article 126"],
            "STATUTE": ["Constitution"],
            "JUDGE": ["Chief Justice Sarath N. Silva"],
            "DATE": ["15/09/2006"],
            "LEGAL_PRINCIPLE": ["natural justice"]
        }
    },
    {
        "name": "Labor Law Case",
        "text": """
        The Labour Tribunal applied Section 31B of the Industrial Disputes Act No. 43 of 1950
        in the matter of Workers Union v. Company Ltd. Hon. Justice Fernando ruled that the 
        audi alteram partem principle must be followed. Case reference: LT/2005/100.
        """,
        "expected_entities": {
            "COURT": ["Labour Tribunal"],
            "ARTICLE": ["Section 31B"],
            "STATUTE": ["Industrial Disputes Act No. 43 of 1950"],
            "CASE_NAME": ["Workers Union v. Company Ltd."],
            "JUDGE": ["Justice Fernando"],
            "LEGAL_PRINCIPLE": ["audi alteram partem"],
            "CITATION": ["LT/2005/100"]
        }
    }
]

def load_model(model_path: Path):
    """Load trained spaCy model"""
    if not model_path.exists():
        print(f"❌ Model not found at {model_path}")
        return None
    return spacy.load(model_path)

def evaluate_entity_extraction(nlp, test_cases):
    """
    Evaluate model on test cases
    Returns accuracy metrics
    """
    results = {
        "total_expected": 0,
        "total_found": 0,
        "correct": 0,
        "per_entity_type": defaultdict(lambda: {"expected": 0, "found": 0, "correct": 0}),
        "test_results": []
    }
    
    for test_case in test_cases:
        text = test_case["text"]
        expected = test_case["expected_entities"]
        
        # Process text
        doc = nlp(text)
        
        # Extract entities by type
        found_entities = defaultdict(list)
        for ent in doc.ents:
            found_entities[ent.label_].append(ent.text.strip())
        
        # Compare with expected
        case_result = {
            "name": test_case["name"],
            "entity_matches": {}
        }
        
        for entity_type, expected_list in expected.items():
            found_list = found_entities.get(entity_type, [])
            
            # Normalize for comparison (case-insensitive, strip whitespace)
            expected_normalized = [e.lower().strip() for e in expected_list]
            found_normalized = [f.lower().strip() for f in found_list]
            
            # Count matches
            matches = 0
            for exp in expected_normalized:
                if any(exp in found or found in exp for found in found_normalized):
                    matches += 1
            
            # Update results
            results["total_expected"] += len(expected_list)
            results["total_found"] += len(found_list)
            results["correct"] += matches
            
            results["per_entity_type"][entity_type]["expected"] += len(expected_list)
            results["per_entity_type"][entity_type]["found"] += len(found_list)
            results["per_entity_type"][entity_type]["correct"] += matches
            
            case_result["entity_matches"][entity_type] = {
                "expected": expected_list,
                "found": found_list,
                "matches": matches,
                "total": len(expected_list)
            }
        
        results["test_results"].append(case_result)
    
    # Calculate metrics
    precision = results["correct"] / results["total_found"] if results["total_found"] > 0 else 0
    recall = results["correct"] / results["total_expected"] if results["total_expected"] > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    results["metrics"] = {
        "precision": precision,
        "recall": recall,
        "f1_score": f1
    }
    
    return results

def print_results(results):
    """Print evaluation results in a readable format"""
    print("\n" + "="*80)
    print("COMPREHENSIVE NER MODEL EVALUATION RESULTS")
    print("="*80)
    
    # Overall metrics
    metrics = results["metrics"]
    print(f"\n📊 OVERALL PERFORMANCE:")
    print(f"   Precision: {metrics['precision']:.2%}")
    print(f"   Recall:    {metrics['recall']:.2%}")
    print(f"   F1-Score:  {metrics['f1_score']:.2%}")
    print(f"\n   Total Expected: {results['total_expected']}")
    print(f"   Total Found:    {results['total_found']}")
    print(f"   Correct:        {results['correct']}")
    
    # Per-entity type metrics
    print(f"\n{'='*80}")
    print("PER-ENTITY TYPE PERFORMANCE:")
    print("="*80)
    
    for entity_type in sorted(results["per_entity_type"].keys()):
        stats = results["per_entity_type"][entity_type]
        precision = stats["correct"] / stats["found"] if stats["found"] > 0 else 0
        recall = stats["correct"] / stats["expected"] if stats["expected"] > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        print(f"\n   {entity_type}:")
        print(f"      Expected: {stats['expected']}")
        print(f"      Found:    {stats['found']}")
        print(f"      Correct:  {stats['correct']}")
        print(f"      Precision: {precision:.2%}")
        print(f"      Recall:    {recall:.2%}")
        print(f"      F1-Score:  {f1:.2%}")
    
    # Test case details
    print(f"\n{'='*80}")
    print("TEST CASE DETAILS:")
    print("="*80)
    
    for test_result in results["test_results"]:
        print(f"\n   ✓ {test_result['name']}")
        for entity_type, match_info in test_result["entity_matches"].items():
            accuracy = match_info["matches"] / match_info["total"] if match_info["total"] > 0 else 0
            status = "✅" if accuracy >= 0.8 else "⚠️" if accuracy >= 0.5 else "❌"
            print(f"      {status} {entity_type}: {match_info['matches']}/{match_info['total']} ({accuracy:.0%})")
            
            # Show misses
            if match_info["matches"] < match_info["total"]:
                missing = set(match_info["expected"]) - set(match_info["found"])
                if missing:
                    print(f"         Missing: {', '.join(missing)}")
    
    # Quality assessment
    print(f"\n{'='*80}")
    print("QUALITY ASSESSMENT:")
    print("="*80)
    
    f1 = metrics['f1_score']
    if f1 >= 0.85:
        print("   ✅ EXCELLENT: Model meets production quality standards (F1 ≥ 85%)")
        print("      Ready for deployment and PP1 submission")
    elif f1 >= 0.70:
        print("   ⚠️  GOOD: Model is functional but could be improved (F1 ≥ 70%)")
        print("      Consider adding more training data")
    else:
        print("   ❌ NEEDS IMPROVEMENT: Model below acceptable threshold (F1 < 70%)")
        print("      Requires retraining with better data")
    
    print("\n" + "="*80)

def main():
    """Main execution function"""
    print("\n" + "="*80)
    print("COMPREHENSIVE LEGAL NER MODEL TEST")
    print("="*80)
    print(f"\n📍 Model Path: {MODEL_DIR}")
    
    # Load model
    print("\n🔍 Loading model...")
    nlp = load_model(MODEL_DIR)
    
    if nlp is None:
        print("\n❌ Test failed: Model not available")
        return
    
    print("✅ Model loaded successfully")
    print(f"📊 Entity types: {', '.join(nlp.get_pipe('ner').labels)}")
    
    # Run evaluation
    print(f"\n🧪 Running {len(TEST_CASES)} comprehensive test cases...")
    results = evaluate_entity_extraction(nlp, TEST_CASES)
    
    # Print results
    print_results(results)
    
    # Save results
    output_file = PROJECT_ROOT / "ner_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        # Convert defaultdict to dict for JSON serialization
        results_serializable = {
            "total_expected": results["total_expected"],
            "total_found": results["total_found"],
            "correct": results["correct"],
            "metrics": results["metrics"],
            "per_entity_type": dict(results["per_entity_type"]),
            "test_results": results["test_results"]
        }
        json.dump(results_serializable, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    print("\n✅ COMPREHENSIVE TEST COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
