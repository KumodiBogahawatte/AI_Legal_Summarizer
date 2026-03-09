"""
Hybrid Document Structure Classifier
Combines BERT model (for common sections) with rule-based detector (for rare sections)

This approach addresses the class imbalance problem where BERT fails to learn rare sections.

Usage:
------
from services.hybrid_document_classifier import HybridDocumentClassifier

# Initialize
classifier = HybridDocumentClassifier()

# Classify paragraphs
sections = classifier.classify_batch(paragraphs)
"""

import re
import torch
from pathlib import Path
from typing import List, Dict, Optional
from transformers import BertTokenizer, BertForSequenceClassification

# Section labels
SECTION_LABELS = {
    0: 'FACTS',
    1: 'ISSUES',
    2: 'LEGAL_ANALYSIS',
    3: 'REASONING',
    4: 'JUDGMENT',
    5: 'ORDERS',
}

LABEL_TO_ID = {v: k for k, v in SECTION_LABELS.items()}


class HybridDocumentClassifier:
    """
    Hybrid classifier that combines:
    1. BERT model for common sections (FACTS, LEGAL_ANALYSIS, REASONING)
    2. Rule-based patterns for rare sections (ISSUES, JUDGMENT, ORDERS)
    """
    
    def __init__(self, model_path: str = None, max_length: int = 256):
        """
        Initialize hybrid classifier
        
        Args:
            model_path: Path to trained BERT model (optional - uses rules-only if not found)
            max_length: Maximum token length for BERT
        """
        self.max_length = max_length
        self.use_bert = False
        
        # Try to load BERT model
        if model_path is None:
            backend_dir = Path(__file__).parent.parent
            model_path = backend_dir / 'models' / 'document_classifier' / 'final_model'
        
        self.model_path = Path(model_path)
        
        if self.model_path.exists():
            try:
                self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                self.tokenizer = BertTokenizer.from_pretrained(str(self.model_path))
                self.model = BertForSequenceClassification.from_pretrained(str(self.model_path))
                self.model.to(self.device)
                self.model.eval()
                self.use_bert = True
                print(f"✅ Hybrid Classifier initialized with BERT model")
                print(f"   Device: {self.device}")
            except Exception as e:
                print(f"⚠️  BERT model loading failed: {e}")
                print(f"   Using rule-based classification only")
                self.use_bert = False
        else:
            print(f"⚠️  BERT model not found at: {self.model_path}")
            print(f"   Using rule-based classification only")
        
        # Compile regex patterns for rule-based detection
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for rare sections"""
        
        # ISSUES patterns
        self.issues_patterns = [
            re.compile(r'\bissues?\s+(?:for|to\s+be|that\s+arise|raised|presented)', re.IGNORECASE),
            re.compile(r'the\s+(?:main|primary|key|central)\s+issue', re.IGNORECASE),
            re.compile(r'question\s+(?:to\s+be\s+)?(?:determined|decided|answered)', re.IGNORECASE),
            re.compile(r'whether\s+the\s+(?:petitioner|respondent|appellant)', re.IGNORECASE),
            re.compile(r'^\s*\(?[ivxIVX]+\)?\s*[.:]?\s*(?:whether|does|did|can|should)', re.IGNORECASE),
        ]
        
        # JUDGMENT patterns
        self.judgment_patterns = [
            re.compile(r'(?:we|the\s+court)\s+(?:are\s+of\s+the\s+)?(?:view|opinion|hold|find)\s+that', re.IGNORECASE),
            re.compile(r'(?:accordingly|therefore|consequently),?\s+(?:we|the\s+court)', re.IGNORECASE),
            re.compile(r'(?:petition|application|appeal)\s+is\s+(?:allowed|dismissed|granted)', re.IGNORECASE),
            re.compile(r'rights?\s+(?:have|has)\s+been\s+violated', re.IGNORECASE),
            re.compile(r'no\s+violation\s+of\s+(?:fundamental\s+)?rights?', re.IGNORECASE),
        ]
        
        # ORDERS patterns
        self.orders_patterns = [
            re.compile(r'(?:it\s+is\s+)?(?:hereby\s+)?ordered\s+that', re.IGNORECASE),
            re.compile(r'(?:we|the\s+court)\s+(?:order|direct|declare)\s+(?:that|the)', re.IGNORECASE),
            re.compile(r'respondent\s+(?:is|shall\s+be)\s+(?:directed|ordered)\s+to\s+pay', re.IGNORECASE),
            re.compile(r'damages?\s+(?:in\s+the\s+sum\s+of|of)\s+Rs\.?\s*\d', re.IGNORECASE),
            re.compile(r'costs?\s+(?:of|in\s+the\s+sum\s+of)\s+Rs\.?\s*\d', re.IGNORECASE),
            re.compile(r'(?:petition|application|appeal)\s+stands\s+(?:allowed|dismissed)', re.IGNORECASE),
        ]
    
    def _detect_section_by_rules(self, text: str) -> Optional[str]:
        """
        Apply rule-based detection for rare sections
        
        Returns:
            Section label if matched, None otherwise
        """
        # Check ISSUES
        for pattern in self.issues_patterns:
            if pattern.search(text):
                return 'ISSUES'
        
        # Check ORDERS (before JUDGMENT as orders are more specific)
        for pattern in self.orders_patterns:
            if pattern.search(text):
                return 'ORDERS'
        
        # Check JUDGMENT
        for pattern in self.judgment_patterns:
            if pattern.search(text):
                return 'JUDGMENT'
        
        return None
    
    def _classify_with_bert(self, text: str) -> str:
        """Classify using BERT model"""
        encoding = self.tokenizer(
            text,
            add_special_tokens=True,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt',
        )
        
        input_ids = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)
        
        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            predicted_id = torch.argmax(logits, dim=1).item()
        
        return SECTION_LABELS[predicted_id]
    
    def classify_paragraph(self, text: str) -> str:
        """
        Classify a single paragraph using hybrid approach
        
        Args:
            text: Paragraph text
            
        Returns:
            Section label
        """
        # Step 1: Try rule-based detection for rare sections
        rule_section = self._detect_section_by_rules(text)
        if rule_section:
            return rule_section
        
        # Step 2: Use BERT for common sections
        if self.use_bert:
            return self._classify_with_bert(text)
        
        # Step 3: Fallback to REASONING if no BERT model
        return 'REASONING'
    
    def classify_with_confidence(self, text: str) -> Dict:
        """
        Classify paragraph with confidence and method used
        
        Returns:
            Dictionary with section, confidence, and method
        """
        # Try rule-based first
        rule_section = self._detect_section_by_rules(text)
        if rule_section:
            return {
                'section': rule_section,
                'confidence': 0.90,  # High confidence for rule-based
                'method': 'rules',
            }
        
        # Use BERT
        if self.use_bert:
            encoding = self.tokenizer(
                text,
                add_special_tokens=True,
                max_length=self.max_length,
                padding='max_length',
                truncation=True,
                return_tensors='pt',
            )
            
            input_ids = encoding['input_ids'].to(self.device)
            attention_mask = encoding['attention_mask'].to(self.device)
            
            with torch.no_grad():
                outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=1)[0]
                predicted_id = torch.argmax(probs).item()
                confidence = probs[predicted_id].item()
            
            return {
                'section': SECTION_LABELS[predicted_id],
                'confidence': confidence,
                'method': 'bert',
            }
        
        # Fallback
        return {
            'section': 'REASONING',
            'confidence': 0.50,
            'method': 'fallback',
        }
    
    def classify_batch(self, texts: List[str], batch_size: int = 32) -> List[str]:
        """
        Classify multiple paragraphs efficiently
        
        Args:
            texts: List of paragraph texts
            batch_size: Batch size for BERT processing
            
        Returns:
            List of section labels
        """
        predictions = []
        
        for text in texts:
            # Rule-based first
            rule_section = self._detect_section_by_rules(text)
            if rule_section:
                predictions.append(rule_section)
            elif self.use_bert:
                # BERT classification
                predictions.append(self._classify_with_bert(text))
            else:
                # Fallback
                predictions.append('REASONING')
        
        return predictions
    
    def classify_document(self, paragraphs: List[str]) -> Dict:
        """
        Classify all paragraphs in document with statistics
        
        Returns:
            Dictionary with sections and statistics
        """
        results = []
        
        for i, para in enumerate(paragraphs):
            result = self.classify_with_confidence(para)
            results.append({
                'paragraph_index': i,
                'text': para,
                'section': result['section'],
                'confidence': result['confidence'],
                'method': result['method'],
            })
        
        # Calculate statistics
        section_counts = {}
        method_counts = {'rules': 0, 'bert': 0, 'fallback': 0}
        
        for result in results:
            section = result['section']
            method = result['method']
            section_counts[section] = section_counts.get(section, 0) + 1
            method_counts[method] += 1
        
        return {
            'sections': results,
            'statistics': {
                'total_paragraphs': len(paragraphs),
                'section_distribution': section_counts,
                'method_distribution': method_counts,
            },
        }


# Example usage
if __name__ == '__main__':
    # Initialize hybrid classifier
    classifier = HybridDocumentClassifier()
    
    # Test examples
    test_paragraphs = [
        "The petitioner filed a fundamental rights application under Article 126.",
        "The main issue to be determined is whether the arrest violated fundamental rights.",
        "According to the precedent set in Vaithilingam v. Corea (1953) 54 NLR 433...",
        "Based on the evidence and legal principles, we are satisfied that...",
        "We are of the view that the petitioner's fundamental rights have been violated.",
        "It is hereby ordered that the respondent shall pay damages of Rs. 500,000.",
    ]
    
    print("\n" + "="*70)
    print("HYBRID CLASSIFIER TEST")
    print("="*70)
    
    for para in test_paragraphs:
        result = classifier.classify_with_confidence(para)
        print(f"\n{result['section']:20} (method: {result['method']}, conf: {result['confidence']:.2f})")
        print(f"  {para[:70]}...")
    
    # Full document analysis
    doc_result = classifier.classify_document(test_paragraphs)
    
    print("\n" + "="*70)
    print("DOCUMENT STATISTICS")
    print("="*70)
    print(f"Total paragraphs: {doc_result['statistics']['total_paragraphs']}")
    print(f"\nSection distribution:")
    for section, count in doc_result['statistics']['section_distribution'].items():
        print(f"  {section:20} : {count} paragraphs")
    
    print(f"\nMethod distribution:")
    for method, count in doc_result['statistics']['method_distribution'].items():
        print(f"  {method:20} : {count} paragraphs")
    print("="*70)
