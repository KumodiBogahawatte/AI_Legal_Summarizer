"""
Prepare training data for Legal NER model
Converts annotated JSON data to spaCy's binary format
"""
import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import random

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import spacy
from spacy.tokens import DocBin
from spacy.training import Example

def load_annotations(json_path: Path) -> List[Dict]:
    """Load annotations from JSON file"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def convert_to_spacy_format(data: List[Dict]) -> List[Tuple[str, Dict]]:
    """
    Convert annotation format to spaCy format
    
    Input format:
    {
        "text": "...",
        "entities": [[start, end, "LABEL"], ...]
    }
    
    Output format:
    [
        ("text", {"entities": [(start, end, "LABEL"), ...]}),
        ...
    ]
    """
    spacy_data = []
    for item in data:
        text = item["text"]
        entities = [tuple(ent) for ent in item["entities"]]
        spacy_data.append((text, {"entities": entities}))
    
    return spacy_data

def validate_annotations(data: List[Tuple[str, Dict]]) -> List[Tuple[str, Dict]]:
    """
    Validate and clean annotations
    - Remove overlapping entities
    - Ensure entity spans are valid
    - Check for consistency
    """
    valid_data = []
    
    for text, annotations in data:
        entities = annotations["entities"]
        
        # Sort entities by start position
        entities = sorted(entities, key=lambda x: x[0])
        
        # Remove overlapping entities
        clean_entities = []
        last_end = -1
        
        for start, end, label in entities:
            # Check if entity is within text bounds
            if start < 0 or end > len(text):
                print(f"⚠️  Skipping out-of-bounds entity: {text[max(0, start):min(len(text), end)]}")
                continue
            
            # Check for overlap with previous entity
            if start >= last_end:
                clean_entities.append((start, end, label))
                last_end = end
            else:
                print(f"⚠️  Skipping overlapping entity: {text[start:end]}")
        
        if clean_entities:
            valid_data.append((text, {"entities": clean_entities}))
    
    return valid_data

def split_data(data: List[Tuple[str, Dict]], train_ratio: float = 0.8, 
               dev_ratio: float = 0.1, test_ratio: float = 0.1) -> Tuple[List, List, List]:
    """Split data into train, dev, and test sets"""
    random.shuffle(data)
    
    n = len(data)
    train_end = int(n * train_ratio)
    dev_end = train_end + int(n * dev_ratio)
    
    train_data = data[:train_end]
    dev_data = data[train_end:dev_end]
    test_data = data[dev_end:]
    
    return train_data, dev_data, test_data

def create_docbin(nlp, data: List[Tuple[str, Dict]]) -> DocBin:
    """Create spaCy DocBin from training data"""
    db = DocBin()
    
    for text, annotations in data:
        doc = nlp.make_doc(text)
        entities = annotations["entities"]
        
        # Create entity spans
        ents = []
        for start, end, label in entities:
            span = doc.char_span(start, end, label=label, alignment_mode="contract")
            if span is not None:
                ents.append(span)
            else:
                print(f"⚠️  Could not create span for: {text[start:end]} ({label})")
        
        try:
            doc.ents = ents
            db.add(doc)
        except Exception as e:
            print(f"⚠️  Error adding doc: {e}")
            continue
    
    return db

def generate_statistics(data: List[Tuple[str, Dict]]) -> Dict:
    """Generate statistics about the training data"""
    stats = {
        "total_examples": len(data),
        "total_entities": 0,
        "entity_counts": {},
        "avg_entities_per_example": 0,
        "avg_text_length": 0
    }
    
    total_text_length = 0
    
    for text, annotations in data:
        entities = annotations["entities"]
        stats["total_entities"] += len(entities)
        total_text_length += len(text)
        
        for _, _, label in entities:
            stats["entity_counts"][label] = stats["entity_counts"].get(label, 0) + 1
    
    if len(data) > 0:
        stats["avg_entities_per_example"] = stats["total_entities"] / len(data)
        stats["avg_text_length"] = total_text_length / len(data)
    
    return stats

def main():
    """Main function to prepare training data"""
    print("="*60)
    print("Legal NER Training Data Preparation")
    print("="*60)
    
    # Paths
    project_root = backend_dir.parent
    annotations_dir = project_root / "data" / "training_data" / "ner_annotations"
    output_dir = backend_dir / "models" / "legal_ner_model" / "training_data"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load sample annotations
    sample_file = annotations_dir / "sample_annotations.json"
    
    if not sample_file.exists():
        print(f"❌ Sample annotations file not found: {sample_file}")
        print("\n📝 Please create annotated data in the following format:")
        print("""
[
  {
    "text": "Your legal text here...",
    "entities": [[start_pos, end_pos, "ENTITY_LABEL"], ...]
  },
  ...
]
        """)
        return
    
    print(f"\n📂 Loading annotations from: {sample_file}")
    raw_data = load_annotations(sample_file)
    print(f"✅ Loaded {len(raw_data)} annotations")
    
    # Convert to spaCy format
    print("\n🔄 Converting to spaCy format...")
    spacy_data = convert_to_spacy_format(raw_data)
    
    # Validate
    print("\n🔍 Validating annotations...")
    valid_data = validate_annotations(spacy_data)
    print(f"✅ Valid examples: {len(valid_data)}/{len(spacy_data)}")
    
    if len(valid_data) == 0:
        print("❌ No valid training examples found!")
        return
    
    # Generate statistics
    print("\n📊 Training Data Statistics:")
    stats = generate_statistics(valid_data)
    print(f"   Total examples: {stats['total_examples']}")
    print(f"   Total entities: {stats['total_entities']}")
    print(f"   Avg entities per example: {stats['avg_entities_per_example']:.2f}")
    print(f"   Avg text length: {stats['avg_text_length']:.0f} characters")
    print(f"\n   Entity Distribution:")
    for label, count in sorted(stats['entity_counts'].items(), key=lambda x: x[1], reverse=True):
        print(f"      {label}: {count} ({count/stats['total_entities']*100:.1f}%)")
    
    # Split data
    print("\n✂️  Splitting data (80% train, 10% dev, 10% test)...")
    train_data, dev_data, test_data = split_data(valid_data, 0.8, 0.1, 0.1)
    print(f"   Train: {len(train_data)} examples")
    print(f"   Dev: {len(dev_data)} examples")
    print(f"   Test: {len(test_data)} examples")
    
    # Create blank spaCy model
    print("\n🏗️  Creating spaCy DocBin files...")
    nlp = spacy.blank("en")
    
    # Create DocBins
    train_db = create_docbin(nlp, train_data)
    dev_db = create_docbin(nlp, dev_data)
    test_db = create_docbin(nlp, test_data)
    
    # Save DocBins
    train_db.to_disk(output_dir / "train.spacy")
    dev_db.to_disk(output_dir / "dev.spacy")
    test_db.to_disk(output_dir / "test.spacy")
    
    print(f"\n✅ Training data saved to: {output_dir}")
    print(f"   - train.spacy ({len(train_data)} examples)")
    print(f"   - dev.spacy ({len(dev_data)} examples)")
    print(f"   - test.spacy ({len(test_data)} examples)")
    
    # Save statistics
    stats_file = output_dir / "statistics.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)
    print(f"\n📈 Statistics saved to: {stats_file}")
    
    print("\n" + "="*60)
    print("✅ Data preparation complete!")
    print("="*60)
    print("\n📝 Next steps:")
    print("   1. Add more annotations to ner_annotations/")
    print("   2. Run this script again to regenerate training data")
    print("   3. Train the model with: python scripts/train_ner_model.py")
    print("\n⚠️  Note: 10 examples is too small for production.")
    print("   Recommended: 1,000+ annotated examples for good performance")

if __name__ == "__main__":
    main()
