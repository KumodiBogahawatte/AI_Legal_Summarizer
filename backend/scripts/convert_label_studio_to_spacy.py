"""
Convert Label Studio annotations to spaCy format.

This script converts annotated data exported from Label Studio
into the spaCy format required for NER model training.
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple
import spacy
from spacy.tokens import DocBin


def load_label_studio_export(filepath: Path) -> List[Dict]:
    """Load annotations exported from Label Studio."""
    print(f"📂 Loading Label Studio export from: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✅ Loaded {len(data)} annotated tasks")
    return data


def convert_to_spacy_format(label_studio_data: List[Dict]) -> List[Tuple[str, Dict]]:
    """
    Convert Label Studio annotations to spaCy format.
    
    Label Studio format:
    {
      "data": {"text": "..."},
      "annotations": [{
        "result": [{
          "value": {
            "start": 0,
            "end": 10,
            "text": "...",
            "labels": ["CASE_NAME"]
          }
        }]
      }]
    }
    
    spaCy format:
    [
      ("text...", {"entities": [(0, 10, "CASE_NAME"), ...]})
    ]
    """
    spacy_data = []
    skipped = 0
    
    for task in label_studio_data:
        text = task.get('data', {}).get('text', '')
        if not text:
            skipped += 1
            continue
        
        # Get annotations (Label Studio may have multiple annotators)
        annotations = task.get('annotations', [])
        if not annotations:
            # No annotations for this task
            spacy_data.append((text, {"entities": []}))
            continue
        
        # Use the first annotation (or merge if multiple)
        annotation = annotations[0]
        results = annotation.get('result', [])
        
        entities = []
        for result in results:
            if result.get('type') == 'labels':
                value = result.get('value', {})
                start = value.get('start')
                end = value.get('end')
                labels = value.get('labels', [])
                
                if start is not None and end is not None and labels:
                    label = labels[0]  # Take first label if multiple
                    entities.append((start, end, label))
        
        # Sort entities by start position
        entities.sort(key=lambda x: x[0])
        
        spacy_data.append((text, {"entities": entities}))
    
    if skipped > 0:
        print(f"⚠️  Skipped {skipped} tasks with no text")
    
    print(f"✅ Converted {len(spacy_data)} tasks to spaCy format")
    return spacy_data


def validate_annotations(spacy_data: List[Tuple[str, Dict]]) -> List[Tuple[str, Dict]]:
    """Validate and clean annotations."""
    valid_data = []
    invalid_count = 0
    
    for text, annotations in spacy_data:
        entities = annotations.get('entities', [])
        valid_entities = []
        
        for start, end, label in entities:
            # Check bounds
            if start < 0 or end > len(text) or start >= end:
                print(f"⚠️  Invalid entity bounds: [{start}:{end}] in text of length {len(text)}")
                invalid_count += 1
                continue
            
            # Check if entity text exists
            entity_text = text[start:end]
            if not entity_text.strip():
                print(f"⚠️  Empty entity text: [{start}:{end}]")
                invalid_count += 1
                continue
            
            valid_entities.append((start, end, label))
        
        # Check for overlapping entities
        for i, (start1, end1, label1) in enumerate(valid_entities):
            for start2, end2, label2 in valid_entities[i+1:]:
                if start1 < end2 and start2 < end1:
                    print(f"⚠️  Overlapping entities: [{start1}:{end1}] and [{start2}:{end2}]")
                    invalid_count += 1
        
        if valid_entities or not entities:  # Keep texts with valid entities or no entities
            valid_data.append((text, {"entities": valid_entities}))
    
    if invalid_count > 0:
        print(f"⚠️  Found {invalid_count} invalid entities (cleaned)")
    
    print(f"✅ Validated {len(valid_data)} examples")
    return valid_data


def save_as_json(data: List[Tuple[str, Dict]], output_file: Path):
    """Save in JSON format for inspection."""
    json_data = []
    for text, annotations in data:
        json_data.append({
            "text": text,
            "entities": [[start, end, label] for start, end, label in annotations["entities"]]
        })
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved JSON to: {output_file}")


def save_as_spacy(data: List[Tuple[str, Dict]], output_file: Path):
    """Save in spaCy binary format."""
    nlp = spacy.blank("en")
    doc_bin = DocBin()
    
    for text, annotations in data:
        doc = nlp.make_doc(text)
        entities = annotations.get('entities', [])
        
        if entities:
            ents = []
            for start, end, label in entities:
                span = doc.char_span(start, end, label=label, alignment_mode="expand")
                if span:
                    ents.append(span)
            
            doc.ents = ents
        
        doc_bin.add(doc)
    
    doc_bin.to_disk(output_file)
    print(f"✅ Saved spaCy binary to: {output_file}")


def generate_statistics(data: List[Tuple[str, Dict]]) -> Dict:
    """Generate statistics about the annotations."""
    total_examples = len(data)
    total_entities = 0
    entity_counts = {}
    examples_with_entities = 0
    
    for text, annotations in data:
        entities = annotations.get('entities', [])
        if entities:
            examples_with_entities += 1
            total_entities += len(entities)
            
            for start, end, label in entities:
                entity_counts[label] = entity_counts.get(label, 0) + 1
    
    stats = {
        "total_examples": total_examples,
        "examples_with_entities": examples_with_entities,
        "examples_without_entities": total_examples - examples_with_entities,
        "total_entities": total_entities,
        "avg_entities_per_example": total_entities / total_examples if total_examples > 0 else 0,
        "entity_distribution": entity_counts
    }
    
    return stats


def print_statistics(stats: Dict):
    """Print annotation statistics."""
    print("\n" + "=" * 70)
    print("ANNOTATION STATISTICS")
    print("=" * 70)
    print(f"Total examples: {stats['total_examples']}")
    print(f"Examples with entities: {stats['examples_with_entities']}")
    print(f"Examples without entities: {stats['examples_without_entities']}")
    print(f"Total entities: {stats['total_entities']}")
    print(f"Avg entities per example: {stats['avg_entities_per_example']:.2f}")
    print()
    print("Entity distribution:")
    for label, count in sorted(stats['entity_distribution'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / stats['total_entities']) * 100
        print(f"  {label:20s}: {count:5d} ({percentage:5.1f}%)")
    print("=" * 70)


def main():
    """Main conversion function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert Label Studio export to spaCy format")
    parser.add_argument("input_file", help="Path to Label Studio JSON export file")
    parser.add_argument("--output-dir", default="data/training_data/ner_annotations/converted",
                       help="Output directory for converted files")
    
    args = parser.parse_args()
    
    # Setup paths
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    input_file = Path(args.input_file)
    output_dir = PROJECT_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("Converting Label Studio Annotations to spaCy Format")
    print("=" * 70)
    print()
    
    # Load Label Studio export
    label_studio_data = load_label_studio_export(input_file)
    
    # Convert to spaCy format
    print("\n🔄 Converting to spaCy format...")
    spacy_data = convert_to_spacy_format(label_studio_data)
    
    # Validate annotations
    print("\n✅ Validating annotations...")
    valid_data = validate_annotations(spacy_data)
    
    # Generate output filename
    base_name = input_file.stem
    json_output = output_dir / f"{base_name}_converted.json"
    spacy_output = output_dir / f"{base_name}_converted.spacy"
    stats_output = output_dir / f"{base_name}_stats.json"
    
    # Save in both formats
    print(f"\n💾 Saving converted data...")
    save_as_json(valid_data, json_output)
    save_as_spacy(valid_data, spacy_output)
    
    # Generate and save statistics
    print(f"\n📊 Generating statistics...")
    stats = generate_statistics(valid_data)
    print_statistics(stats)
    
    with open(stats_output, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"✅ Saved statistics to: {stats_output}")
    
    print("\n" + "=" * 70)
    print("CONVERSION COMPLETE!")
    print("=" * 70)
    print(f"📁 Output files:")
    print(f"   - {json_output.name}")
    print(f"   - {spacy_output.name}")
    print(f"   - {stats_output.name}")
    print()
    print("Next step: Combine all converted files with existing training data:")
    print("  python scripts/prepare_ner_training_data.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
