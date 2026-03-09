"""
Train Legal NER Model using spaCy
Trains a custom Named Entity Recognition model for Sri Lankan legal documents
"""
import sys
from pathlib import Path
import json
from typing import Dict, List
import random

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import spacy
from spacy.training import Example
from spacy.util import minibatch, compounding
from spacy.tokens import DocBin
import warnings
warnings.filterwarnings("ignore")

# Entity labels for legal NER
ENTITY_LABELS = [
    "CASE_NAME",
    "COURT",
    "JUDGE",
    "STATUTE",
    "ARTICLE",
    "LEGAL_PRINCIPLE",
    "DATE",
    "CITATION"
]

def load_training_data(data_path: Path):
    """Load training data from spaCy binary format"""
    nlp = spacy.blank("en")
    doc_bin = DocBin().from_disk(data_path)
    docs = list(doc_bin.get_docs(nlp.vocab))
    
    examples = []
    for doc in docs:
        examples.append(doc)
    
    return examples

def create_model(labels: List[str]):
    """Create a blank spaCy model with NER pipeline"""
    nlp = spacy.blank("en")
    
    # Add NER pipeline
    if "ner" not in nlp.pipe_names:
        ner = nlp.add_pipe("ner", last=True)
    else:
        ner = nlp.get_pipe("ner")
    
    # Add labels
    for label in labels:
        ner.add_label(label)
    
    return nlp

def evaluate_model(nlp, examples: List):
    """Evaluate model performance"""
    from spacy.scorer import Scorer
    
    scorer = Scorer()
    test_examples = []
    
    for doc in examples:
        pred_doc = nlp(doc.text)
        test_examples.append(Example(pred_doc, doc))
    
    scores = scorer.score(test_examples)
    
    return scores

def train_model(nlp, train_examples: List, n_iter: int = 30, dropout: float = 0.2):
    """
    Train the NER model
    
    Args:
        nlp: spaCy model
        train_examples: List of training examples
        n_iter: Number of training iterations
        dropout: Dropout rate
    """
    print(f"\n🏋️  Training model for {n_iter} iterations...")
    print(f"   Training examples: {len(train_examples)}")
    print(f"   Dropout: {dropout}")
    
    # Get NER pipeline
    ner = nlp.get_pipe("ner")
    
    # Initialize optimizer
    optimizer = nlp.initialize()
    
    # Training loop
    losses = {}
    best_loss = float('inf')
    
    for iteration in range(n_iter):
        random.shuffle(train_examples)
        losses = {}
        
        # Create batches
        batches = minibatch(train_examples, size=compounding(4.0, 32.0, 1.001))
        
        for batch in batches:
            examples = []
            for doc in batch:
                pred_doc = nlp.make_doc(doc.text)
                example = Example(pred_doc, doc)
                examples.append(example)
            
            nlp.update(examples, drop=dropout, losses=losses)
        
        # Print progress
        if (iteration + 1) % 5 == 0:
            loss_value = losses.get("ner", 0)
            print(f"   Iteration {iteration + 1}/{n_iter} - Loss: {loss_value:.4f}")
            
            if loss_value < best_loss:
                best_loss = loss_value
    
    return losses

def main():
    """Main training function"""
    print("="*60)
    print("Legal NER Model Training")
    print("="*60)
    
    # Paths
    model_dir = backend_dir / "models" / "legal_ner_model"
    training_data_dir = model_dir / "training_data"
    output_dir = model_dir / "trained_model"
    
    # Check if training data exists
    train_file = training_data_dir / "train.spacy"
    dev_file = training_data_dir / "dev.spacy"
    test_file = training_data_dir / "test.spacy"
    
    if not train_file.exists():
        print(f"\n❌ Training data not found: {train_file}")
        print("\n📝 Please run prepare_ner_training_data.py first:")
        print("   python scripts/prepare_ner_training_data.py")
        return
    
    # Load training data
    print(f"\n📂 Loading training data...")
    train_examples = load_training_data(train_file)
    print(f"✅ Loaded {len(train_examples)} training examples")
    
    if dev_file.exists():
        dev_examples = load_training_data(dev_file)
        print(f"✅ Loaded {len(dev_examples)} dev examples")
    else:
        dev_examples = []
        print("⚠️  No dev data found")
    
    if test_file.exists():
        test_examples = load_training_data(test_file)
        print(f"✅ Loaded {len(test_examples)} test examples")
    else:
        test_examples = []
        print("⚠️  No test data found")
    
    # Create model
    print(f"\n🏗️  Creating blank model with {len(ENTITY_LABELS)} entity types...")
    nlp = create_model(ENTITY_LABELS)
    print(f"✅ Model created with entities: {', '.join(ENTITY_LABELS)}")
    
    # Train model
    losses = train_model(nlp, train_examples, n_iter=30, dropout=0.2)
    
    # Evaluate on dev set
    if dev_examples:
        print(f"\n📊 Evaluating on dev set...")
        dev_scores = evaluate_model(nlp, dev_examples)
        print(f"   Precision: {dev_scores['ents_p']:.2%}")
        print(f"   Recall: {dev_scores['ents_r']:.2%}")
        print(f"   F1-Score: {dev_scores['ents_f']:.2%}")
        
        # Per-entity scores
        if 'ents_per_type' in dev_scores:
            print(f"\n   Per-Entity Scores:")
            for entity_type, scores in dev_scores['ents_per_type'].items():
                print(f"      {entity_type}:")
                print(f"         P: {scores['p']:.2%} | R: {scores['r']:.2%} | F1: {scores['f']:.2%}")
    
    # Evaluate on test set
    if test_examples:
        print(f"\n📊 Evaluating on test set...")
        test_scores = evaluate_model(nlp, test_examples)
        print(f"   Precision: {test_scores['ents_p']:.2%}")
        print(f"   Recall: {test_scores['ents_r']:.2%}")
        print(f"   F1-Score: {test_scores['ents_f']:.2%}")
    
    # Save model
    output_dir.mkdir(parents=True, exist_ok=True)
    nlp.to_disk(output_dir)
    print(f"\n💾 Model saved to: {output_dir}")
    
    # Save metadata
    metadata = {
        "entity_labels": ENTITY_LABELS,
        "training_examples": len(train_examples),
        "dev_examples": len(dev_examples),
        "test_examples": len(test_examples),
        "final_loss": losses.get("ner", 0),
        "dev_scores": dev_scores if dev_examples else None,
        "test_scores": test_scores if test_examples else None
    }
    
    metadata_file = output_dir / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    print(f"📄 Metadata saved to: {metadata_file}")
    
    # Test the model
    print(f"\n🧪 Testing model with sample text...")
    test_text = "In Silva v. Fernando, the Supreme Court held that Article 12(1) guarantees equality."
    doc = nlp(test_text)
    
    print(f"\n   Text: {test_text}")
    print(f"   Entities found:")
    for ent in doc.ents:
        print(f"      - {ent.text} ({ent.label_})")
    
    print("\n" + "="*60)
    print("✅ Training complete!")
    print("="*60)
    print("\n📝 Next steps:")
    print("   1. Test the model with: python scripts/test_ner_model.py")
    print("   2. Integrate into services: legal_ner_service.py")
    print("   3. Add more training data to improve accuracy")
    print(f"\n⚠️  Current model trained on {len(train_examples)} examples")
    print("   Recommended: 1,000+ examples for production use")

if __name__ == "__main__":
    main()
