"""
Auto-annotate legal documents using rule-based NER.

This script uses spaCy's Matcher and patterns to automatically detect legal entities,
then generates Label Studio compatible annotations for manual review.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Tuple

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent
BATCH_DIR = PROJECT_ROOT / "data" / "training_data" / "ner_annotations" / "annotation_batches"
OUTPUT_DIR = PROJECT_ROOT / "data" / "training_data" / "ner_annotations" / "auto_annotated"


# Entity patterns
PATTERNS = {
    "CASE_NAME": [
        r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+v[s]?\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',
        r'\b[A-Z][a-z]+\s+and\s+(?:Another|Others)\s+v[s]?\.?\s+[A-Z][a-z]+',
    ],
    "COURT": [
        r'Supreme\s+Court(?:\s+of\s+Sri\s+Lanka)?',
        r'Court\s+of\s+Appeal',
        r'High\s+Court(?:\s+of\s+(?:the\s+)?Provinces?)?',
        r'District\s+Court(?:\s+of\s+\w+)?',
        r'Magistrate(?:\'s|\s+)Court(?:\s+of\s+\w+)?',
        r'Provincial\s+High\s+Court',
    ],
    "JUDGE": [
        r'(?:HON\.\s+)?[A-Z]\.(?:\s*[A-Z]\.)*\s+[A-Z][a-z]+,?\s+(?:C\.J\.|J\.|P/CA|President)',
        r'(?:Justice|Chief\s+Justice)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?',
        r'\b[A-Z][A-Z\s]+,\s+(?:J\.|C\.J\.)',
    ],
    "STATUTE": [
        r'(?:Civil\s+)?Procedure\s+Code',
        r'Evidence\s+Ordinance',
        r'Maintenance\s+(?:Act|Ordinance)(?:\s+No\.\s+\d+\s+of\s+\d{4})?',
        r'Constitution(?:\s+of\s+(?:the\s+)?Democratic\s+Socialist\s+Republic\s+of\s+Sri\s+Lanka)?',
        r'Debt\s+Conciliation\s+Ordinance',
        r'Penal\s+Code',
        r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Act\s+No\.\s+\d+\s+of\s+\d{4}',
        r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Ordinance(?:\s+No\.\s+\d+\s+of\s+\d{4})?',
    ],
    "ARTICLE": [
        r'Article\s+\d+[A-Z]?(?:\([a-z0-9]+\))*',
        r'Section\s+\d+[A-Z]?(?:\([a-z0-9]+\))*',
        r'Rule\s+\d+[A-Z]?(?:\([a-z0-9]+\))*',
        r'section\s+\d+[A-Z]?(?:\([a-z0-9]+\))*(?:\s+of\s+(?:the\s+)?[A-Z])',
    ],
    "CITATION": [
        r'\[\d{4}\]\s+\d+\s+SRI\s+L\.?\s*R\.?(?:\s+\d+)?',
        r'\[\d{4}\]\s+\d+\s+S\.?L\.?R\.?(?:\s+\d+)?',
        r'\d+\s+NLR\s+\d+',
        r'CA\s+\d+/\d+(?:\s+\([A-Z]+\))?',
        r'SC\s+\d+/\d+',
        r'HC\s+[A-Z]+\s+(?:NO\.\s+)?\d+/\d+',
        r'DC\s+[A-Z]+\s+\d+/[A-Z]',
    ],
    "DATE": [
        r'\d{1,2}\.\d{1,2}\.\d{4}',
        r'\d{1,2}/\d{1,2}/\d{4}',
        r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
        r'\d{1,2}(?:st|nd|rd|th)\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',
    ],
    "LEGAL_PRINCIPLE": [
        r'burden\s+of\s+proof',
        r'natural\s+justice',
        r'res\s+judicata',
        r'stare\s+decisis',
        r'ultra\s+vires',
        r'locus\s+standi',
        r'prima\s+facie',
        r'mens\s+rea',
        r'actus\s+reus',
        r'fundamental\s+right[s]?',
    ]
}


def compile_patterns():
    """Compile regex patterns for each entity type."""
    compiled = {}
    for entity_type, patterns in PATTERNS.items():
        compiled[entity_type] = [re.compile(p, re.IGNORECASE) for p in patterns]
    return compiled


def find_entities(text: str, compiled_patterns: Dict) -> List[Dict]:
    """Find all entities in text using regex patterns."""
    entities = []
    
    for entity_type, patterns in compiled_patterns.items():
        for pattern in patterns:
            for match in pattern.finditer(text):
                start, end = match.span()
                entities.append({
                    "start": start,
                    "end": end,
                    "text": match.group(),
                    "label": entity_type
                })
    
    # Sort by start position
    entities.sort(key=lambda x: x['start'])
    
    # Remove overlapping entities (keep first occurrence)
    non_overlapping = []
    last_end = -1
    
    for entity in entities:
        if entity['start'] >= last_end:
            non_overlapping.append(entity)
            last_end = entity['end']
    
    return non_overlapping


def create_label_studio_annotation(text: str, entities: List[Dict]) -> Dict:
    """Convert entities to Label Studio annotation format."""
    # Label Studio expects annotations with results
    results = []
    
    for entity in entities:
        result = {
            "value": {
                "start": entity['start'],
                "end": entity['end'],
                "text": entity['text'],
                "labels": [entity['label']]
            },
            "from_name": "label",
            "to_name": "text",
            "type": "labels"
        }
        results.append(result)
    
    return results


def process_batch(batch_file: Path, output_file: Path, compiled_patterns: Dict):
    """Process a batch file and generate auto-annotations."""
    with open(batch_file, 'r', encoding='utf-8') as f:
        tasks = json.load(f)
    
    annotated_tasks = []
    total_entities = 0
    
    for task in tasks:
        text = task['data']['text']
        
        # Find entities
        entities = find_entities(text, compiled_patterns)
        total_entities += len(entities)
        
        # Create Label Studio annotation format
        results = create_label_studio_annotation(text, entities)
        
        # Add annotations to task
        annotated_task = {
            "data": task['data'],
            "annotations": [{
                "result": results,
                "was_cancelled": False,
                "ground_truth": False
            }]
        }
        
        if 'meta' in task:
            annotated_task['meta'] = task['meta']
        
        annotated_tasks.append(annotated_task)
    
    # Save annotated batch
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(annotated_tasks, f, indent=2, ensure_ascii=False)
    
    return len(tasks), total_entities


def main():
    """Main execution function."""
    print("=" * 70)
    print("Auto-Annotating Legal Documents for NER")
    print("=" * 70)
    print()
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Compile patterns
    print("📝 Compiling entity patterns...")
    compiled_patterns = compile_patterns()
    print(f"✅ Loaded {sum(len(p) for p in PATTERNS.values())} patterns for {len(PATTERNS)} entity types")
    
    # Process all batch files
    batch_files = sorted(BATCH_DIR.glob("batch_*.json"))
    
    if not batch_files:
        print(f"❌ No batch files found in {BATCH_DIR}")
        return
    
    print(f"\n📦 Found {len(batch_files)} batch files to process")
    print()
    
    total_tasks = 0
    total_entities = 0
    
    for batch_file in batch_files:
        output_file = OUTPUT_DIR / f"auto_{batch_file.name}"
        
        print(f"Processing {batch_file.name}...", end=" ")
        tasks, entities = process_batch(batch_file, output_file, compiled_patterns)
        total_tasks += tasks
        total_entities += entities
        print(f"✅ {tasks} tasks, {entities} entities")
    
    print()
    print("=" * 70)
    print("AUTO-ANNOTATION COMPLETE!")
    print("=" * 70)
    print(f"📊 Total tasks processed: {total_tasks}")
    print(f"🏷️  Total entities found: {total_entities}")
    print(f"📈 Average entities per task: {total_entities/total_tasks:.1f}")
    print(f"\n📁 Auto-annotated files saved to:")
    print(f"   {OUTPUT_DIR}")
    print()
    print("=" * 70)
    print("NEXT STEPS:")
    print("=" * 70)
    print("1. Import auto-annotated files to Label Studio:")
    print(f"   - Files: {OUTPUT_DIR}/auto_batch_*.json")
    print("2. Review and correct the annotations")
    print("3. The auto-annotations are PRE-FILLED, just fix any errors!")
    print("4. Export corrected annotations when done")
    print()
    print("⚠️  Remember: Auto-annotations may have errors!")
    print("   - False positives (wrong entities)")
    print("   - False negatives (missed entities)")
    print("   - Always review before accepting!")
    print("=" * 70)


if __name__ == "__main__":
    main()
