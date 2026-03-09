"""
Evaluate trained Legal NER model
Tests model performance on test set and generates detailed metrics
"""
import sys
from pathlib import Path
import json

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import spacy
from spacy.tokens import DocBin
from spacy.scorer import Scorer
from spacy.training import Example
from collections import defaultdict

def load_test_data(test_file: Path):
    """Load test data from spaCy binary format"""
    nlp = spacy.blank("en")
    doc_bin = DocBin().from_disk(test_file)
    docs = list(doc_bin.get_docs(nlp.vocab))
    return docs

def evaluate_model(model_path: Path, test_docs: list) -> dict:
    """
    Evaluate model on test set
    
    Returns detailed metrics including:
    - Overall precision, recall, F1
    - Per-entity type metrics
    - Confusion matrix
    """
    # Load model
    nlp = spacy.load(model_path)
    
    # Create examples
    examples = []
    for gold_doc in test_docs:
        pred_doc = nlp(gold_doc.text)
        example = Example(pred_doc, gold_doc)
        examples.append(example)
    
    # Score
    scorer = Scorer()
    scores = scorer.score(examples)
    
    return scores

def generate_confusion_matrix(model_path: Path, test_docs: list) -> dict:
    """Generate confusion matrix for entity types"""
    nlp = spacy.load(model_path)
    
    confusion = defaultdict(lambda: defaultdict(int))
    
    for gold_doc in test_docs:
        pred_doc = nlp(gold_doc.text)
        
        # Create position maps
        gold_ents = {(ent.start_char, ent.end_char): ent.label_ for ent in gold_doc.ents}
        pred_ents = {(ent.start_char, ent.end_char): ent.label_ for ent in pred_doc.ents}
        
        # Track predictions
        all_positions = set(gold_ents.keys()) | set(pred_ents.keys())
        
        for pos in all_positions:
            gold_label = gold_ents.get(pos, "O")  # O = Outside (no entity)
            pred_label = pred_ents.get(pos, "O")
            confusion[gold_label][pred_label] += 1
    
    return dict(confusion)

def find_errors(model_path: Path, test_docs: list, max_errors: int = 20) -> list:
    """Find and return examples of prediction errors"""
    nlp = spacy.load(model_path)
    
    errors = []
    
    for gold_doc in test_docs:
        pred_doc = nlp(gold_doc.text)
        
        # Find false negatives (missed entities)
        for gold_ent in gold_doc.ents:
            found = False
            for pred_ent in pred_doc.ents:
                if (gold_ent.start_char == pred_ent.start_char and 
                    gold_ent.end_char == pred_ent.end_char):
                    found = True
                    break
            
            if not found:
                errors.append({
                    "type": "False Negative (Missed)",
                    "text": gold_ent.text,
                    "expected": gold_ent.label_,
                    "predicted": "O",
                    "context": gold_doc.text[max(0, gold_ent.start_char-50):min(len(gold_doc.text), gold_ent.end_char+50)]
                })
        
        # Find false positives (wrong predictions)
        for pred_ent in pred_doc.ents:
            found = False
            for gold_ent in gold_doc.ents:
                if (gold_ent.start_char == pred_ent.start_char and 
                    gold_ent.end_char == pred_ent.end_char):
                    if gold_ent.label_ != pred_ent.label_:
                        errors.append({
                            "type": "Wrong Label",
                            "text": pred_ent.text,
                            "expected": gold_ent.label_,
                            "predicted": pred_ent.label_,
                            "context": gold_doc.text[max(0, pred_ent.start_char-50):min(len(gold_doc.text), pred_ent.end_char+50)]
                        })
                    found = True
                    break
            
            if not found:
                errors.append({
                    "type": "False Positive (Hallucination)",
                    "text": pred_ent.text,
                    "expected": "O",
                    "predicted": pred_ent.label_,
                    "context": pred_doc.text[max(0, pred_ent.start_char-50):min(len(pred_doc.text), pred_ent.end_char+50)]
                })
        
        if len(errors) >= max_errors:
            break
    
    return errors[:max_errors]

def main():
    """Main evaluation function"""
    print("="*60)
    print("Legal NER Model Evaluation")
    print("="*60)
    
    # Paths
    model_dir = backend_dir / "models" / "legal_ner_model"
    model_path = model_dir / "trained_model"
    test_file = model_dir / "training_data" / "test.spacy"
    output_dir = model_dir / "evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if model exists
    if not model_path.exists():
        print(f"\n❌ Trained model not found: {model_path}")
        print("   Please train the model first with: python scripts/train_ner_model.py")
        return
    
    # Check if test data exists
    if not test_file.exists():
        print(f"\n❌ Test data not found: {test_file}")
        print("   Please prepare data first with: python scripts/prepare_ner_training_data.py")
        return
    
    # Load test data
    print(f"\n📂 Loading test data from: {test_file}")
    test_docs = load_test_data(test_file)
    print(f"✅ Loaded {len(test_docs)} test documents")
    
    # Evaluate model
    print(f"\n📊 Evaluating model...")
    scores = evaluate_model(model_path, test_docs)
    
    # Print overall scores
    print(f"\n{'='*60}")
    print("OVERALL SCORES")
    print("="*60)
    print(f"   Precision: {scores.get('ents_p', 0):.2%}")
    print(f"   Recall:    {scores.get('ents_r', 0):.2%}")
    print(f"   F1-Score:  {scores.get('ents_f', 0):.2%}")
    
    # Print per-entity scores
    if 'ents_per_type' in scores:
        print(f"\n{'='*60}")
        print("PER-ENTITY TYPE SCORES")
        print("="*60)
        for entity_type, type_scores in sorted(scores['ents_per_type'].items()):
            print(f"\n   {entity_type}:")
            print(f"      Precision: {type_scores.get('p', 0):.2%}")
            print(f"      Recall:    {type_scores.get('r', 0):.2%}")
            print(f"      F1-Score:  {type_scores.get('f', 0):.2%}")
    
    # Generate confusion matrix
    print(f"\n📊 Generating confusion matrix...")
    confusion = generate_confusion_matrix(model_path, test_docs)
    
    print(f"\n{'='*60}")
    print("CONFUSION MATRIX")
    print("="*60)
    for true_label, predictions in sorted(confusion.items()):
        print(f"\n   True: {true_label}")
        for pred_label, count in sorted(predictions.items()):
            if count > 0:
                print(f"      Predicted as {pred_label}: {count}")
    
    # Find errors
    print(f"\n🔍 Finding prediction errors...")
    errors = find_errors(model_path, test_docs, max_errors=10)
    
    if errors:
        print(f"\n{'='*60}")
        print(f"SAMPLE ERRORS (showing {len(errors)})")
        print("="*60)
        for i, error in enumerate(errors, 1):
            print(f"\n   Error {i}: {error['type']}")
            print(f"      Text: '{error['text']}'")
            print(f"      Expected: {error['expected']}")
            print(f"      Predicted: {error['predicted']}")
            print(f"      Context: ...{error['context']}...")
    
    # Save evaluation results
    eval_results = {
        "overall_scores": {
            "precision": scores.get('ents_p', 0),
            "recall": scores.get('ents_r', 0),
            "f1_score": scores.get('ents_f', 0)
        },
        "per_entity_scores": scores.get('ents_per_type', {}),
        "confusion_matrix": confusion,
        "sample_errors": errors,
        "test_set_size": len(test_docs)
    }
    
    eval_file = output_dir / "evaluation_results.json"
    with open(eval_file, 'w', encoding='utf-8') as f:
        json.dump(eval_results, f, indent=2)
    print(f"\n💾 Evaluation results saved to: {eval_file}")
    
    # Generate recommendations
    print(f"\n{'='*60}")
    print("RECOMMENDATIONS")
    print("="*60)
    
    f1_score = scores.get('ents_f', 0)
    if f1_score < 0.7:
        print("   ⚠️  F1-score is below 70%. Consider:")
        print("      - Adding more training data")
        print("      - Balancing entity types in training set")
        print("      - Reviewing annotation quality")
    elif f1_score < 0.85:
        print("   ⚠️  F1-score is below 85%. Consider:")
        print("      - Adding more diverse examples")
        print("      - Fine-tuning hyperparameters")
    else:
        print("   ✅ Model performance is good!")
        print("      - Continue monitoring on real data")
        print("      - Consider deploying to production")
    
    print("\n" + "="*60)
    print("✅ Evaluation complete!")
    print("="*60)

if __name__ == "__main__":
    main()
