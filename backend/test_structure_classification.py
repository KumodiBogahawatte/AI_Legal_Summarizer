"""
Test Document Structure Classification
Simple script to verify hybrid classifier works independently
"""

from services.hybrid_document_classifier import HybridDocumentClassifier

# Sample legal document text
sample_text = """
The petitioner filed a fundamental rights application under Article 126 of the Constitution alleging that his arrest and detention violated his fundamental rights guaranteed under Articles 13(1) and 13(2) of the Constitution.

The main issues to be determined in this case are: (1) Whether the arrest of the petitioner was lawful; (2) Whether the detention exceeded a reasonable period; (3) Whether the petitioner's fundamental rights were violated.

According to the precedent established in Vaithilingam v. Corea (1953) 54 NLR 433, the arrest must comply with the procedural requirements set out in the Code of Criminal Procedure. Furthermore, in the case of Wijesekera v. Mendis (1978) 79 NLR 481, it was held that detention must not exceed a reasonable period.

Based on the evidence presented and the legal principles discussed above, we are satisfied that the arrest procedures were not properly followed. The detention period of 72 hours exceeded what would be considered reasonable under the circumstances. The conduct of the police officers demonstrates a clear disregard for the petitioner's constitutional rights.

We are of the view that the petitioner's fundamental rights guaranteed under Articles 13(1) and 13(2) of the Constitution have been violated. The respondents failed to show any justifiable reason for the extended detention period.

It is hereby ordered that: (1) The respondents shall pay damages in the sum of Rs. 500,000 to the petitioner; (2) Costs of this application are awarded to the petitioner in the sum of Rs. 50,000; (3) This order shall be implemented within 30 days from the date of this judgment.
"""

def main():
    print("="*80)
    print("TESTING HYBRID DOCUMENT CLASSIFIER")
    print("="*80)
    
    # Initialize classifier
    print("\n1. Initializing classifier...")
    try:
        classifier = HybridDocumentClassifier()
        print("   ✅ Classifier initialized successfully")
    except Exception as e:
        print(f"   ❌ Failed to initialize: {e}")
        return
    
    # Split into paragraphs
    print("\n2. Segmenting document...")
    paragraphs = [p.strip() for p in sample_text.split('\n\n') if p.strip()]
    print(f"   ✅ Found {len(paragraphs)} paragraphs")
    
    # Classify document
    print("\n3. Classifying document structure...")
    try:
        result = classifier.classify_document(paragraphs)
        print("   ✅ Classification complete")
        
        # Display results
        print("\n" + "="*80)
        print("CLASSIFICATION RESULTS")
        print("="*80)
        
        print(f"\nTotal Paragraphs: {result['statistics']['total_paragraphs']}")
        
        print(f"\nSection Distribution:")
        for section, count in sorted(result['statistics']['section_distribution'].items()):
            pct = count / result['statistics']['total_paragraphs'] * 100
            print(f"  {section:20} : {count} paragraphs ({pct:.1f}%)")
        
        print(f"\nClassification Methods:")
        for method, count in result['statistics']['method_distribution'].items():
            pct = count / result['statistics']['total_paragraphs'] * 100
            print(f"  {method:20} : {count} paragraphs ({pct:.1f}%)")
        
        print("\n" + "-"*80)
        print("DETAILED PARAGRAPH CLASSIFICATION")
        print("-"*80)
        
        for item in result['sections']:
            print(f"\nParagraph {item['paragraph_index'] + 1}: {item['section']}")
            print(f"  Method: {item['method']}, Confidence: {item['confidence']:.2f}")
            print(f"  Text: {item['text'][:100]}...")
        
        print("\n" + "="*80)
        print("✅ TEST COMPLETED SUCCESSFULLY")
        print("="*80)
        
    except Exception as e:
        print(f"   ❌ Classification failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
