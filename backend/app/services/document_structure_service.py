"""
Document Structure Analysis Service
Classifies paragraphs in legal documents into structural sections

Uses BERT-based model to identify:
- FACTS: Background facts of the case
- ISSUES: Legal issues to be determined
- LEGAL_ANALYSIS: Analysis of applicable law
- REASONING: Court's reasoning process
- JUDGMENT: Final decision/ruling
- ORDERS: Specific orders issued
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import torch
from transformers import BertTokenizer, BertForSequenceClassification

# Label mapping
LABEL_MAP = {
    'FACTS': 0,
    'ISSUES': 1,
    'LEGAL_ANALYSIS': 2,
    'REASONING': 3,
    'JUDGMENT': 4,
    'ORDERS': 5,
}

ID_TO_LABEL = {v: k for k, v in LABEL_MAP.items()}

# Model configuration
MAX_LENGTH = 256
MODEL_PATH = Path(__file__).parent.parent / 'models' / 'document_classifier' / 'final_model'


class DocumentStructureAnalyzer:
    """Analyzes document structure using trained BERT model"""
    
    _instance = None
    _model = None
    _tokenizer = None
    _device = None
    
    def __new__(cls):
        """Singleton pattern for model loading"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize analyzer (loads model on first call)"""
        if self._model is None:
            self._load_model()
    
    def _load_model(self):
        """Load pre-trained BERT model"""
        print(f"Loading document structure classifier from: {MODEL_PATH}")
        
        try:
            self._device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            print(f"Using device: {self._device}")
            
            self._tokenizer = BertTokenizer.from_pretrained(str(MODEL_PATH))
            self._model = BertForSequenceClassification.from_pretrained(str(MODEL_PATH))
            self._model.to(self._device)
            self._model.eval()
            
            print("✅ Document structure classifier loaded successfully")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not load trained model: {e}")
            print("Using rule-based fallback classifier")
            self._model = None
    
    def split_into_paragraphs(self, text: str) -> List[str]:
        """Split document text into paragraphs"""
        # Split by double newlines or page markers
        paragraphs = re.split(r'\n\s*\n+|---\s*Page\s+\d+\s*---', text)
        
        # Filter and clean
        cleaned = []
        for para in paragraphs:
            para = para.strip()
            if len(para) >= 20:  # Minimum length
                para = re.sub(r'\s+', ' ', para)
                cleaned.append(para)
        
        return cleaned
    
    def classify_paragraph_ml(self, text: str) -> Tuple[str, float]:
        """Classify paragraph using ML model"""
        if self._model is None:
            return self.classify_paragraph_rules(text)
        
        # Tokenize
        encoding = self._tokenizer(
            text,
            add_special_tokens=True,
            max_length=MAX_LENGTH,
            padding='max_length',
            truncation=True,
            return_tensors='pt',
        )
        
        # Move to device
        input_ids = encoding['input_ids'].to(self._device)
        attention_mask = encoding['attention_mask'].to(self._device)
        
        # Predict
        with torch.no_grad():
            outputs = self._model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=1)
            predicted_class = torch.argmax(probs, dim=1).item()
            confidence = probs[0][predicted_class].item()
        
        section = ID_TO_LABEL[predicted_class]
        return section, confidence
    
    def classify_paragraph_rules(self, text: str) -> Tuple[str, float]:
        """Fallback rule-based classification"""
        text_lower = text.lower()
        
        # Simple rule-based classification
        if any(keyword in text_lower for keyword in ['facts of', 'background', 'plaintiff', 'defendant', 'instituted action']):
            return 'FACTS', 0.7
        elif any(keyword in text_lower for keyword in ['issue', 'question', 'whether']):
            return 'ISSUES', 0.7
        elif any(keyword in text_lower for keyword in ['section', 'article', 'act', 'ordinance', 'provision']):
            return 'LEGAL_ANALYSIS', 0.7
        elif any(keyword in text_lower for keyword in ['reasoning', 'in my view', 'considered', 'accordingly']):
            return 'REASONING', 0.7
        elif any(keyword in text_lower for keyword in ['judgment', 'decision', 'held that', 'conclude']):
            return 'JUDGMENT', 0.7
        elif any(keyword in text_lower for keyword in ['order', 'directed', 'decree', 'with costs']):
            return 'ORDERS', 0.7
        
        return 'FACTS', 0.5  # Default
    
    def analyze_document(self, text: str, use_ml: bool = True) -> Dict:
        """Analyze full document and classify all paragraphs"""
        paragraphs = self.split_into_paragraphs(text)
        
        classified = []
        section_counts = {label: 0 for label in LABEL_MAP.keys()}
        
        for idx, para in enumerate(paragraphs):
            if use_ml and self._model is not None:
                section, confidence = self.classify_paragraph_ml(para)
            else:
                section, confidence = self.classify_paragraph_rules(para)
            
            classified.append({
                'paragraph_id': idx,
                'text': para,
                'section': section,
                'confidence': round(confidence, 4),
                'length': len(para),
            })
            
            section_counts[section] += 1
        
        # Create structured sections
        sections = self._group_by_section(classified)
        
        return {
            'total_paragraphs': len(paragraphs),
            'paragraphs': classified,
            'sections': sections,
            'section_summary': section_counts,
        }
    
    def _group_by_section(self, classified: List[Dict]) -> Dict[str, List[Dict]]:
        """Group classified paragraphs by section"""
        sections = {label: [] for label in LABEL_MAP.keys()}
        
        for item in classified:
            section = item['section']
            sections[section].append({
                'paragraph_id': item['paragraph_id'],
                'text': item['text'],
                'confidence': item['confidence'],
            })
        
        return sections
    
    def extract_section_text(self, text: str, section: str, use_ml: bool = True) -> str:
        """Extract all text belonging to a specific section"""
        analysis = self.analyze_document(text, use_ml=use_ml)
        section_paragraphs = analysis['sections'].get(section, [])
        
        if not section_paragraphs:
            return ""
        
        return "\n\n".join(p['text'] for p in section_paragraphs)
    
    def get_document_summary(self, text: str, use_ml: bool = True) -> Dict:
        """Get high-level summary of document structure"""
        analysis = self.analyze_document(text, use_ml=use_ml)
        
        summary = {
            'total_paragraphs': analysis['total_paragraphs'],
            'sections_found': [],
        }
        
        for section, count in analysis['section_summary'].items():
            if count > 0:
                summary['sections_found'].append({
                    'section': section,
                    'paragraph_count': count,
                    'percentage': round(count / analysis['total_paragraphs'] * 100, 2),
                })
        
        # Sort by count
        summary['sections_found'] = sorted(
            summary['sections_found'],
            key=lambda x: x['paragraph_count'],
            reverse=True
        )
        
        return summary


# Global instance
_analyzer = None

def get_analyzer() -> DocumentStructureAnalyzer:
    """Get global analyzer instance"""
    global _analyzer
    if _analyzer is None:
        _analyzer = DocumentStructureAnalyzer()
    return _analyzer


def analyze_document_structure(text: str, use_ml: bool = True) -> Dict:
    """
    Main function to analyze document structure
    
    Args:
        text: Document text to analyze
        use_ml: Whether to use ML model (True) or rule-based (False)
    
    Returns:
        Dictionary containing classified paragraphs and sections
    """
    analyzer = get_analyzer()
    return analyzer.analyze_document(text, use_ml=use_ml)


def extract_section(text: str, section: str, use_ml: bool = True) -> str:
    """
    Extract specific section from document
    
    Args:
        text: Document text
        section: Section to extract (FACTS, ISSUES, etc.)
        use_ml: Whether to use ML model
    
    Returns:
        Extracted section text
    """
    analyzer = get_analyzer()
    return analyzer.extract_section_text(text, section, use_ml=use_ml)


if __name__ == '__main__':
    # Test the analyzer
    sample_text = """
    SUPREME COURT.
    S.N. SILVA, C.J.
    FERNANDO, J.
    
    The applicant instituted action No. 13390 in the Magistrate's Court 
    claiming maintenance from the Respondent for the child born out of wedlock.
    
    The learned Magistrate by his order dated 17.12.2002 ordered the Respondent 
    to pay a sum of Rs. 750 per month as maintenance for the child.
    
    HELD:
    
    (1) The 13th amendment to the Constitution which came into force on 14.11.1987 
    by Article 154P(3)(b) vested the High Court of the Provinces with jurisdiction 
    in respect of orders made by the Magistrates.
    
    In my view, the appellant has failed to comply with the Rules and hence the 
    preliminary objection raised by the Respondent must succeed.
    
    Accordingly this appeal of the Appellant is rejected. The Respondent is entitled 
    to the costs of this application.
    """
    
    print("Testing Document Structure Analyzer")
    print("=" * 70)
    
    analyzer = get_analyzer()
    result = analyzer.analyze_document(sample_text, use_ml=False)
    
    print(f"\nTotal paragraphs: {result['total_paragraphs']}")
    print("\nSection Summary:")
    for section, count in result['section_summary'].items():
        if count > 0:
            print(f"  {section}: {count}")
    
    print("\nClassified Paragraphs:")
    for p in result['paragraphs']:
        print(f"\n[{p['section']}] (confidence: {p['confidence']:.2f})")
        print(f"{p['text'][:100]}...")
