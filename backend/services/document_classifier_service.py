"""
Document Structure Classifier Service
Uses trained BERT model to classify legal document sections

Usage in your application:
--------------------------
from services.document_classifier_service import DocumentClassifierService

# Initialize once (loads model)
classifier = DocumentClassifierService()

# Classify a single paragraph
section = classifier.classify_paragraph("The petitioner filed a motion...")
print(section)  # Output: "FACTS"

# Classify multiple paragraphs
paragraphs = [
    "The petitioner filed a motion...",
    "The court considered the following issues...",
    "Based on the precedent set in...",
]
sections = classifier.classify_batch(paragraphs)
print(sections)  # Output: ["FACTS", "ISSUES", "LEGAL_ANALYSIS"]

# Get confidence scores
result = classifier.classify_with_confidence("The court hereby orders...")
print(result)  
# Output: {"section": "ORDERS", "confidence": 0.95, "all_scores": {...}}
"""

import torch
import numpy as np
from pathlib import Path
from typing import Dict, List, Union, Tuple
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


class DocumentClassifierService:
    """Service for classifying legal document sections using trained BERT model"""
    
    def __init__(self, model_path: str = None, max_length: int = 256):
        """
        Initialize the classifier service
        
        Args:
            model_path: Path to trained model directory (default: backend/models/document_classifier/final_model)
            max_length: Maximum token length for BERT (default: 256)
        """
        if model_path is None:
            # Default path
            backend_dir = Path(__file__).parent.parent
            model_path = backend_dir / 'models' / 'document_classifier' / 'final_model'
        
        self.model_path = Path(model_path)
        self.max_length = max_length
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Load model and tokenizer
        self._load_model()
        
        print(f"✅ Document Classifier loaded")
        print(f"   Model: {self.model_path}")
        print(f"   Device: {self.device}")
    
    def _load_model(self):
        """Load trained model and tokenizer"""
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model not found at: {self.model_path}\n"
                f"Please train the model first or download the trained model from Google Drive."
            )
        
        # Load tokenizer and model
        self.tokenizer = BertTokenizer.from_pretrained(str(self.model_path))
        self.model = BertForSequenceClassification.from_pretrained(str(self.model_path))
        self.model.to(self.device)
        self.model.eval()  # Set to evaluation mode
    
    def classify_paragraph(self, text: str) -> str:
        """
        Classify a single paragraph into a document section
        
        Args:
            text: Paragraph text to classify
            
        Returns:
            Section label (e.g., "FACTS", "ISSUES", "LEGAL_ANALYSIS")
        """
        # Tokenize
        encoding = self.tokenizer(
            text,
            add_special_tokens=True,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt',
        )
        
        # Move to device
        input_ids = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)
        
        # Predict
        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            predicted_id = torch.argmax(logits, dim=1).item()
        
        return SECTION_LABELS[predicted_id]
    
    def classify_with_confidence(self, text: str) -> Dict:
        """
        Classify paragraph and return confidence scores
        
        Args:
            text: Paragraph text to classify
            
        Returns:
            Dictionary with:
                - section: Predicted section label
                - confidence: Confidence score (0-1)
                - all_scores: Scores for all sections
        """
        # Tokenize
        encoding = self.tokenizer(
            text,
            add_special_tokens=True,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt',
        )
        
        # Move to device
        input_ids = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)
        
        # Predict
        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            
            # Apply softmax to get probabilities
            probs = torch.softmax(logits, dim=1)[0]
            predicted_id = torch.argmax(probs).item()
            confidence = probs[predicted_id].item()
            
            # Get all scores
            all_scores = {
                SECTION_LABELS[i]: float(probs[i])
                for i in range(len(SECTION_LABELS))
            }
        
        return {
            'section': SECTION_LABELS[predicted_id],
            'confidence': confidence,
            'all_scores': all_scores,
        }
    
    def classify_batch(self, texts: List[str], batch_size: int = 32) -> List[str]:
        """
        Classify multiple paragraphs efficiently
        
        Args:
            texts: List of paragraph texts
            batch_size: Batch size for processing
            
        Returns:
            List of section labels
        """
        if not texts:
            return []
        
        predictions = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            # Tokenize batch
            encodings = self.tokenizer(
                batch_texts,
                add_special_tokens=True,
                max_length=self.max_length,
                padding='max_length',
                truncation=True,
                return_tensors='pt',
            )
            
            # Move to device
            input_ids = encodings['input_ids'].to(self.device)
            attention_mask = encodings['attention_mask'].to(self.device)
            
            # Predict
            with torch.no_grad():
                outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
                logits = outputs.logits
                predicted_ids = torch.argmax(logits, dim=1).cpu().numpy()
            
            # Convert to labels
            batch_predictions = [SECTION_LABELS[pred_id] for pred_id in predicted_ids]
            predictions.extend(batch_predictions)
        
        return predictions
    
    def classify_batch_with_confidence(
        self, 
        texts: List[str], 
        batch_size: int = 32
    ) -> List[Dict]:
        """
        Classify multiple paragraphs with confidence scores
        
        Args:
            texts: List of paragraph texts
            batch_size: Batch size for processing
            
        Returns:
            List of dictionaries with section, confidence, and all_scores
        """
        if not texts:
            return []
        
        results = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            # Tokenize batch
            encodings = self.tokenizer(
                batch_texts,
                add_special_tokens=True,
                max_length=self.max_length,
                padding='max_length',
                truncation=True,
                return_tensors='pt',
            )
            
            # Move to device
            input_ids = encodings['input_ids'].to(self.device)
            attention_mask = encodings['attention_mask'].to(self.device)
            
            # Predict
            with torch.no_grad():
                outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
                logits = outputs.logits
                
                # Apply softmax
                probs = torch.softmax(logits, dim=1)
                predicted_ids = torch.argmax(probs, dim=1).cpu().numpy()
                confidences = probs[range(len(probs)), predicted_ids].cpu().numpy()
                all_probs = probs.cpu().numpy()
            
            # Build results
            for pred_id, conf, prob_row in zip(predicted_ids, confidences, all_probs):
                results.append({
                    'section': SECTION_LABELS[pred_id],
                    'confidence': float(conf),
                    'all_scores': {
                        SECTION_LABELS[i]: float(prob_row[i])
                        for i in range(len(SECTION_LABELS))
                    },
                })
        
        return results
    
    def classify_document(self, paragraphs: List[str]) -> Dict:
        """
        Classify all paragraphs in a document and return structured output
        
        Args:
            paragraphs: List of paragraph texts from document
            
        Returns:
            Dictionary with:
                - sections: List of classified paragraphs with metadata
                - statistics: Section distribution counts
        """
        # Classify all paragraphs
        results = self.classify_batch_with_confidence(paragraphs)
        
        # Structure output
        sections = []
        for i, (para, result) in enumerate(zip(paragraphs, results)):
            sections.append({
                'paragraph_index': i,
                'text': para,
                'section': result['section'],
                'confidence': result['confidence'],
            })
        
        # Calculate statistics
        section_counts = {}
        for result in results:
            section = result['section']
            section_counts[section] = section_counts.get(section, 0) + 1
        
        return {
            'sections': sections,
            'statistics': {
                'total_paragraphs': len(paragraphs),
                'section_distribution': section_counts,
            },
        }


# Example usage
if __name__ == '__main__':
    # Initialize classifier
    classifier = DocumentClassifierService()
    
    # Example 1: Single paragraph
    text = "The petitioner filed a fundamental rights application under Article 126 of the Constitution."
    section = classifier.classify_paragraph(text)
    print(f"\nExample 1 - Single paragraph:")
    print(f"Text: {text}")
    print(f"Section: {section}")
    
    # Example 2: With confidence
    result = classifier.classify_with_confidence(text)
    print(f"\nExample 2 - With confidence:")
    print(f"Section: {result['section']}")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"All scores: {result['all_scores']}")
    
    # Example 3: Batch classification
    paragraphs = [
        "The petitioner filed a motion on January 15, 2020.",
        "The main issue is whether the arrest violated fundamental rights.",
        "According to the precedent set in Vaithilingam v. Corea, the court must consider...",
        "Based on the evidence and legal principles, we find that...",
        "The court is of the view that the petitioner's rights were violated.",
        "It is hereby ordered that the respondent shall pay damages of Rs. 500,000.",
    ]
    
    sections = classifier.classify_batch(paragraphs)
    print(f"\nExample 3 - Batch classification:")
    for para, section in zip(paragraphs, sections):
        print(f"{section:20} | {para[:60]}...")
    
    # Example 4: Full document classification
    doc_result = classifier.classify_document(paragraphs)
    print(f"\nExample 4 - Document statistics:")
    print(f"Total paragraphs: {doc_result['statistics']['total_paragraphs']}")
    print(f"Section distribution:")
    for section, count in doc_result['statistics']['section_distribution'].items():
        print(f"  {section:20} : {count} paragraphs")
