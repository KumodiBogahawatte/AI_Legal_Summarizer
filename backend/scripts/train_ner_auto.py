"""
Fully automated NER training pipeline.
Converts auto-annotations directly to spaCy format and trains the model.
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Tuple
import spacy
from spacy.training import Example
from spacy.util import minibatch, compounding

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent
AUTO_ANNOTATED_DIR = PROJECT_ROOT / "data" / "training_data" / "ner_annotations" / "auto_annotated"
OUTPUT_DIR = PROJECT_ROOT / "backend" / "models" / "legal_ner"
TRAINING_DATA_FILE = PROJECT_ROOT / "data" / "training_data" / "ner_annotations" / "training_data.json"

# Entity labels
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


def convert_label_studio_to_spacy(auto_annotated_files: List[Path]) -> List[Tuple[str, Dict]]:
    """Convert auto-annotated Label Studio format to spaCy training format."""
    training_data = []
    
    for file_path in auto_annotated_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            tasks = json.load(f)
        
        for task in tasks:
            text = task['data']['text']
            
            if 'annotations' not in task or not task['annotations']:
                continue
            
            # Get the first annotation
            annotation = task['annotations'][0]
            
            if 'result' not in annotation:
                continue
            
            # Convert to spaCy format
            entities = []
            for result in annotation['result']:
                if result['type'] != 'labels':
                    continue
                
                start = result['value']['start']
                end = result['value']['end']
                label = result['value']['labels'][0]
                
                entities.append((start, end, label))
            
            # Sort entities by start position
            entities.sort(key=lambda x: x[0])
            
            training_data.append((text, {"entities": entities}))
    
    return training_data


def split_dataset(data: List[Tuple], train_ratio=0.8):
    """Split data into train and evaluation sets."""
    random.shuffle(data)
    split_idx = int(len(data) * train_ratio)
    return data[:split_idx], data[split_idx:]


def train_ner_model(train_data: List[Tuple], eval_data: List[Tuple], n_iter=30):
    """Train spaCy NER model."""
    
    # Create blank English model
    nlp = spacy.blank("en")
    
    # Add NER pipeline
    if "ner" not in nlp.pipe_names:
        ner = nlp.add_pipe("ner")
    else:
        ner = nlp.get_pipe("ner")
    
    # Add entity labels
    for label in ENTITY_LABELS:
        ner.add_label(label)
    
    # Prepare training examples
    train_examples = []
    for text, annotations in train_data:
        doc = nlp.make_doc(text)
        example = Example.from_dict(doc, annotations)
        train_examples.append(example)
    
    # Training configuration
    optimizer = nlp.begin_training()
    
    print(f"\n🎯 Starting training with {len(train_examples)} examples...")
    print(f"📊 Evaluation set: {len(eval_data)} examples")
    print(f"🔄 Iterations: {n_iter}")
    print()
    
    # Training loop
    losses_history = []
    
    for iteration in range(n_iter):
        random.shuffle(train_examples)
        losses = {}
        
        # Batch training
        batches = minibatch(train_examples, size=compounding(4.0, 32.0, 1.001))
        
        for batch in batches:
            nlp.update(batch, drop=0.5, losses=losses)
        
        losses_history.append(losses['ner'])
        
        # Print progress
        if (iteration + 1) % 5 == 0:
            print(f"Iteration {iteration + 1}/{n_iter} - Loss: {losses['ner']:.4f}")
    
    print(f"\n✅ Training complete!")
    print(f"📉 Final loss: {losses['ner']:.4f}")
    
    return nlp, losses_history


def evaluate_model(nlp, eval_data: List[Tuple]):
    """Evaluate model on test data."""
    correct = 0
    total = 0
    
    for text, annotations in eval_data:
        doc = nlp(text)
        predicted = set((ent.start_char, ent.end_char, ent.label_) for ent in doc.ents)
        
        gold = set()
        for start, end, label in annotations['entities']:
            gold.add((start, end, label))
        
        correct += len(predicted & gold)
        total += len(gold)
    
    precision = correct / len([e for _, a in eval_data for e in a['entities']]) if eval_data else 0
    recall = correct / total if total > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'correct': correct,
        'total': total
    }


def save_model(nlp, output_dir: Path):
    """Save trained model to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    nlp.to_disk(output_dir)


def save_training_data(data: List[Tuple], output_file: Path):
    """Save training data in spaCy format."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    formatted_data = [
        {
            "text": text,
            "entities": [(start, end, label) for start, end, label in annotations['entities']]
        }
        for text, annotations in data
    ]
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(formatted_data, f, indent=2, ensure_ascii=False)


def main():
    """Main execution function."""
    print("=" * 70)
    print("Automated Legal NER Training Pipeline")
    print("=" * 70)
    print()
    
    # Load auto-annotated files
    print("📂 Loading auto-annotated files...")
    auto_files = sorted(AUTO_ANNOTATED_DIR.glob("auto_batch_*.json"))
    
    if not auto_files:
        print(f"❌ No auto-annotated files found in {AUTO_ANNOTATED_DIR}")
        return
    
    print(f"✅ Found {len(auto_files)} auto-annotated files")
    
    # Convert to spaCy format
    print("\n🔄 Converting to spaCy format...")
    training_data = convert_label_studio_to_spacy(auto_files)
    print(f"✅ Converted {len(training_data)} training examples")
    
    # Calculate statistics
    total_entities = sum(len(annotations['entities']) for _, annotations in training_data)
    print(f"🏷️  Total entities: {total_entities}")
    print(f"📈 Average entities per text: {total_entities/len(training_data):.1f}")
    
    # Entity distribution
    entity_counts = {}
    for _, annotations in training_data:
        for _, _, label in annotations['entities']:
            entity_counts[label] = entity_counts.get(label, 0) + 1
    
    print("\n📊 Entity distribution:")
    for label, count in sorted(entity_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"   {label}: {count} ({count/total_entities*100:.1f}%)")
    
    # Save training data
    print(f"\n💾 Saving training data to {TRAINING_DATA_FILE}...")
    save_training_data(training_data, TRAINING_DATA_FILE)
    
    # Split dataset
    print("\n✂️  Splitting dataset (80% train, 20% eval)...")
    train_data, eval_data = split_dataset(training_data, train_ratio=0.8)
    print(f"   Training: {len(train_data)} examples")
    print(f"   Evaluation: {len(eval_data)} examples")
    
    # Train model
    print("\n" + "=" * 70)
    print("TRAINING MODEL")
    print("=" * 70)
    
    nlp, losses = train_ner_model(train_data, eval_data, n_iter=30)
    
    # Evaluate model
    print("\n" + "=" * 70)
    print("EVALUATING MODEL")
    print("=" * 70)
    
    metrics = evaluate_model(nlp, eval_data)
    print(f"\n📊 Evaluation Results:")
    print(f"   Precision: {metrics['precision']:.2%}")
    print(f"   Recall: {metrics['recall']:.2%}")
    print(f"   F1 Score: {metrics['f1']:.2%}")
    print(f"   Correct: {metrics['correct']}/{metrics['total']}")
    
    # Save model
    print(f"\n💾 Saving model to {OUTPUT_DIR}...")
    save_model(nlp, OUTPUT_DIR)
    
    print("\n" + "=" * 70)
    print("TRAINING COMPLETE!")
    print("=" * 70)
    print(f"✅ Model saved to: {OUTPUT_DIR}")
    print(f"✅ Training data saved to: {TRAINING_DATA_FILE}")
    print()
    print("🚀 Next steps:")
    print("   1. Test the model: python scripts/test_ner_model.py")
    print("   2. Integrate with API: Update backend/app/services/nlp_analyzer.py")
    print("   3. Deploy to production")
    print("=" * 70)


if __name__ == "__main__":
    main()
