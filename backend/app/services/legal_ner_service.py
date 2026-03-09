"""
Legal NER Service
Provides entity extraction functionality for legal documents
"""
from pathlib import Path
from typing import List, Dict, Optional
import sys

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

import spacy
from spacy.language import Language

class LegalNERService:
    """Service for extracting legal entities from text"""
    
    def __init__(self, model_path: Optional[Path] = None):
        """
        Initialize the Legal NER service
        
        Args:
            model_path: Path to trained spaCy model. If None, uses default path.
        """
        if model_path is None:
            model_path = backend_dir / "models" / "legal_ner_model" / "trained_model"
        
        self.model_path = model_path
        self.nlp: Optional[Language] = None
        self._load_model()
    
    def _load_model(self):
        """Load the trained NER model"""
        if not self.model_path.exists():
            print(f"⚠️  NER model not found at: {self.model_path}")
            print("   Please train the model first with: python scripts/train_ner_model.py")
            self.nlp = None
            return
        
        try:
            self.nlp = spacy.load(self.model_path)
            print(f"✅ Legal NER model loaded from: {self.model_path}")
        except Exception as e:
            print(f"❌ Error loading NER model: {e}")
            self.nlp = None
    
    def extract_entities(self, text: str, return_positions: bool = False) -> Dict[str, List]:
        """
        Extract legal entities from text
        
        Args:
            text: Input text to process
            return_positions: If True, include start/end positions
        
        Returns:
            Dictionary mapping entity types to lists of entities
        """
        if self.nlp is None:
            return {"error": "NER model not loaded"}
        
        doc = self.nlp(text)
        
        entities_by_type = {}
        
        for ent in doc.ents:
            if ent.label_ not in entities_by_type:
                entities_by_type[ent.label_] = []
            
            if return_positions:
                entities_by_type[ent.label_].append({
                    "text": ent.text,
                    "start": ent.start_char,
                    "end": ent.end_char
                })
            else:
                entities_by_type[ent.label_].append(ent.text)
        
        return entities_by_type
    
    def extract_entities_list(self, text: str) -> List[Dict]:
        """
        Extract entities as a flat list
        
        Args:
            text: Input text to process
        
        Returns:
            List of entity dictionaries
        """
        if self.nlp is None:
            return []
        
        doc = self.nlp(text)
        
        entities = []
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char
            })
        
        return entities
    
    def extract_specific_entity_type(self, text: str, entity_type: str) -> List[str]:
        """
        Extract only specific entity type
        
        Args:
            text: Input text to process
            entity_type: Entity type to extract (e.g., "CASE_NAME", "JUDGE")
        
        Returns:
            List of entity texts
        """
        if self.nlp is None:
            return []
        
        doc = self.nlp(text)
        
        entities = []
        for ent in doc.ents:
            if ent.label_ == entity_type:
                entities.append(ent.text)
        
        return entities
    
    def annotate_document(self, text: str) -> str:
        """
        Return text with inline entity annotations
        
        Args:
            text: Input text to annotate
        
        Returns:
            Annotated text with entities marked
        """
        if self.nlp is None:
            return text
        
        doc = self.nlp(text)
        
        # Sort entities by start position (reverse)
        entities = sorted(doc.ents, key=lambda x: x.start_char, reverse=True)
        
        annotated_text = text
        for ent in entities:
            annotation = f"[{ent.text}]({ent.label_})"
            annotated_text = (
                annotated_text[:ent.start_char] + 
                annotation + 
                annotated_text[ent.end_char:]
            )
        
        return annotated_text
    
    def get_entity_summary(self, text: str) -> Dict:
        """
        Get summary statistics about entities in text
        
        Args:
            text: Input text to analyze
        
        Returns:
            Dictionary with entity counts and unique entities
        """
        if self.nlp is None:
            return {}
        
        doc = self.nlp(text)
        
        summary = {
            "total_entities": len(doc.ents),
            "entity_counts": {},
            "unique_entities": {}
        }
        
        for ent in doc.ents:
            # Count by type
            if ent.label_ not in summary["entity_counts"]:
                summary["entity_counts"][ent.label_] = 0
            summary["entity_counts"][ent.label_] += 1
            
            # Collect unique entities
            if ent.label_ not in summary["unique_entities"]:
                summary["unique_entities"][ent.label_] = set()
            summary["unique_entities"][ent.label_].add(ent.text)
        
        # Convert sets to lists for JSON serialization
        for label in summary["unique_entities"]:
            summary["unique_entities"][label] = list(summary["unique_entities"][label])
        
        return summary
    
    def extract_case_metadata(self, text: str) -> Dict:
        """
        Extract structured metadata from case text
        
        Args:
            text: Case text to analyze
        
        Returns:
            Dictionary with extracted metadata
        """
        entities = self.extract_entities(text, return_positions=False)
        
        metadata = {
            "case_names": entities.get("CASE_NAME", []),
            "courts": entities.get("COURT", []),
            "judges": entities.get("JUDGE", []),
            "statutes": entities.get("STATUTE", []),
            "articles": entities.get("ARTICLE", []),
            "legal_principles": entities.get("LEGAL_PRINCIPLE", []),
            "dates": entities.get("DATE", []),
            "citations": entities.get("CITATION", [])
        }
        
        # Get unique values
        for key in metadata:
            metadata[key] = list(set(metadata[key]))
        
        return metadata
    
    def is_model_loaded(self) -> bool:
        """Check if model is loaded"""
        return self.nlp is not None

# Singleton instance
_ner_service: Optional[LegalNERService] = None

def get_ner_service() -> LegalNERService:
    """Get or create NER service instance"""
    global _ner_service
    if _ner_service is None:
        _ner_service = LegalNERService()
    return _ner_service

# Example usage
if __name__ == "__main__":
    print("="*60)
    print("Legal NER Service Demo")
    print("="*60)
    
    # Create service
    ner_service = LegalNERService()
    
    if not ner_service.is_model_loaded():
        print("\n❌ Model not loaded. Please train the model first.")
        print("   Run: python scripts/train_ner_model.py")
        sys.exit(1)
    
    # Test text
    test_text = """
    In the case of Silva v. Fernando [2020] 1 SLR 345, the Supreme Court of 
    Sri Lanka held that Article 12(1) of the Constitution guarantees equality 
    before the law. Justice Dep P.C.J. delivered the judgment on 15th March 2019, 
    citing the Prevention of Terrorism Act No. 48 of 1979. The court applied 
    the doctrine of natural justice and dismissed the appeal.
    """
    
    print(f"\n📝 Test text:\n{test_text}")
    
    # Extract entities
    print(f"\n🔍 Extracted entities:")
    entities = ner_service.extract_entities(test_text)
    for entity_type, entity_list in entities.items():
        print(f"\n   {entity_type}:")
        for entity in entity_list:
            print(f"      - {entity}")
    
    # Get metadata
    print(f"\n📊 Case metadata:")
    metadata = ner_service.extract_case_metadata(test_text)
    for key, values in metadata.items():
        if values:
            print(f"   {key}: {values}")
    
    # Get summary
    print(f"\n📈 Entity summary:")
    summary = ner_service.get_entity_summary(test_text)
    print(f"   Total entities: {summary['total_entities']}")
    print(f"   Entity counts: {summary['entity_counts']}")
    
    print("\n" + "="*60)
    print("✅ NER Service ready!")
    print("="*60)
