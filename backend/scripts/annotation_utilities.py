"""
Annotation utilities for Legal NER training data
Helps with manual annotation and data quality checks
"""
import json
from pathlib import Path
from typing import List, Dict, Tuple
import re

class LegalNERAnnotator:
    """Helper class for annotating legal documents"""
    
    ENTITY_PATTERNS = {
        "CASE_NAME": [
            r'\b[A-Z][a-z]+\s+v\.?\s+[A-Z][a-z]+\b',
            r'\bIn\s+re\s+[A-Z][a-z]+\b',
            r'\bEx\s+parte\s+[A-Z][a-z]+\b',
        ],
        "COURT": [
            r'\b(Supreme Court|Court of Appeal|High Court|District Court|Magistrate\'s Court)\b',
            r'\b(SC|CA|HC)\b',
        ],
        "JUDGE": [
            r'\bJustice\s+[A-Z][a-z]+(?:\s+[A-Z]\.?)+',
            r'\bChief Justice\s+[A-Z][a-z]+',
            r'\b[A-Z][a-z]+\s+J\.?\b',
        ],
        "STATUTE": [
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Act(?:\s+No\.\s+\d+\s+of\s+\d{4})?\b',
            r'\b(Constitution|Penal Code|Civil Procedure Code)\b',
        ],
        "ARTICLE": [
            r'\bArticle\s+\d+(?:\(\d+\))?(?:\([a-z]\))?\b',
            r'\bSection\s+\d+(?:\(\d+\))?(?:\([a-z]\))?\b',
        ],
        "CITATION": [
            r'\[\d{4}\]\s+\d+\s+[A-Z]{2,5}\s+\d+',
            r'\d{4}\s+[A-Z]{2,5}\s+\d+',
            r'\bNLR\s+\d+\b',
        ],
        "DATE": [
            r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b',
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{4}-\d{2}-\d{2}\b',
        ],
    }
    
    def auto_annotate(self, text: str) -> List[Tuple[int, int, str]]:
        """
        Automatically suggest annotations based on regex patterns
        Note: This is just a suggestion tool - manual review is required!
        """
        suggestions = []
        
        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    start, end = match.span()
                    suggestions.append((start, end, entity_type))
        
        # Remove overlaps - keep longer matches
        suggestions = self._remove_overlaps(suggestions)
        
        return suggestions
    
    def _remove_overlaps(self, entities: List[Tuple[int, int, str]]) -> List[Tuple[int, int, str]]:
        """Remove overlapping entities, keeping longer ones"""
        if not entities:
            return []
        
        # Sort by start position, then by length (descending)
        sorted_entities = sorted(entities, key=lambda x: (x[0], -(x[1] - x[0])))
        
        result = []
        last_end = -1
        
        for start, end, label in sorted_entities:
            if start >= last_end:
                result.append((start, end, label))
                last_end = end
        
        return result
    
    def validate_annotations(self, text: str, entities: List[Tuple[int, int, str]]) -> Dict:
        """
        Validate annotations and return quality report
        """
        issues = []
        warnings = []
        
        # Check for overlaps
        sorted_ents = sorted(entities, key=lambda x: x[0])
        for i in range(len(sorted_ents) - 1):
            _, end1, _ = sorted_ents[i]
            start2, _, _ = sorted_ents[i + 1]
            if end1 > start2:
                issues.append(f"Overlapping entities at positions {start2}-{end1}")
        
        # Check if entities are within text bounds
        text_len = len(text)
        for start, end, label in entities:
            if start < 0 or end > text_len:
                issues.append(f"Entity out of bounds: {label} at {start}-{end}")
            elif start >= end:
                issues.append(f"Invalid span: {label} at {start}-{end}")
        
        # Check for very short or long entities
        for start, end, label in entities:
            length = end - start
            if length < 2:
                warnings.append(f"Very short entity: '{text[start:end]}' ({label})")
            elif length > 200:
                warnings.append(f"Very long entity: '{text[start:end][:50]}...' ({label})")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "entity_count": len(entities)
        }
    
    def format_for_display(self, text: str, entities: List[Tuple[int, int, str]]) -> str:
        """Format annotated text for human review"""
        if not entities:
            return text
        
        # Sort entities by start position
        sorted_ents = sorted(entities, key=lambda x: x[0])
        
        result = []
        last_pos = 0
        
        for start, end, label in sorted_ents:
            # Add text before entity
            result.append(text[last_pos:start])
            # Add highlighted entity
            result.append(f"[{text[start:end]}]({label})")
            last_pos = end
        
        # Add remaining text
        result.append(text[last_pos:])
        
        return ''.join(result)
    
    def export_to_prodigy(self, annotations: List[Dict], output_file: Path):
        """Export annotations to Prodigy format"""
        prodigy_data = []
        
        for item in annotations:
            text = item["text"]
            entities = item["entities"]
            
            spans = []
            for start, end, label in entities:
                spans.append({
                    "start": start,
                    "end": end,
                    "label": label,
                    "token_start": None,
                    "token_end": None
                })
            
            prodigy_data.append({
                "text": text,
                "spans": spans,
                "answer": "accept"
            })
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in prodigy_data:
                f.write(json.dumps(item) + '\n')
        
        print(f"✅ Exported {len(prodigy_data)} annotations to Prodigy format: {output_file}")
    
    def import_from_prodigy(self, input_file: Path) -> List[Dict]:
        """Import annotations from Prodigy JSONL format"""
        annotations = []
        
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                item = json.loads(line)
                if item.get("answer") == "accept":
                    entities = []
                    for span in item.get("spans", []):
                        entities.append([span["start"], span["end"], span["label"]])
                    
                    annotations.append({
                        "text": item["text"],
                        "entities": entities
                    })
        
        print(f"✅ Imported {len(annotations)} annotations from Prodigy format")
        return annotations

def create_annotation_template(output_file: Path, sample_texts: List[str]):
    """Create a template JSON file for manual annotation"""
    template = []
    
    for text in sample_texts:
        template.append({
            "text": text,
            "entities": [],
            "notes": "Add entities in format: [start_pos, end_pos, 'LABEL']"
        })
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created annotation template: {output_file}")
    print(f"   Contains {len(template)} texts to annotate")

def main():
    """Demo/testing of annotation utilities"""
    print("="*60)
    print("Legal NER Annotation Utilities")
    print("="*60)
    
    annotator = LegalNERAnnotator()
    
    # Test text
    test_text = """
    In the case of Silva v. Fernando [2020] 1 SLR 345, the Supreme Court 
    held that Article 12(1) of the Constitution guarantees equality before 
    the law. Justice Dep P.C.J. delivered the judgment on 15th March 2019.
    """
    
    print(f"\n📝 Test text:\n{test_text}")
    
    # Auto-suggest annotations
    print(f"\n🤖 Auto-suggested annotations:")
    suggestions = annotator.auto_annotate(test_text)
    for start, end, label in suggestions:
        print(f"   [{start}-{end}] {test_text[start:end]} ({label})")
    
    # Validate
    print(f"\n✅ Validation:")
    validation = annotator.validate_annotations(test_text, suggestions)
    print(f"   Valid: {validation['valid']}")
    print(f"   Entity count: {validation['entity_count']}")
    if validation['issues']:
        print(f"   Issues: {validation['issues']}")
    if validation['warnings']:
        print(f"   Warnings: {validation['warnings']}")
    
    # Format for display
    print(f"\n📋 Formatted text:")
    formatted = annotator.format_for_display(test_text, suggestions)
    print(f"   {formatted}")
    
    print("\n" + "="*60)
    print("✅ Annotation utilities ready!")
    print("="*60)

if __name__ == "__main__":
    main()
