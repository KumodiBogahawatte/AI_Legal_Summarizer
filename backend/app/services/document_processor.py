# backend/app/services/document_processor.py

import pdfplumber
import pytesseract
from PIL import Image
import io
import re
from sqlalchemy.orm import Session
from ..models.document_model import LegalDocument
from ..utils.sri_lanka_legal_utils import extract_case_year, extract_case_number, extract_court

# Import hybrid document classifier for structure analysis
try:
    import sys
    from pathlib import Path
    # Add backend directory to path if needed
    backend_dir = Path(__file__).parent.parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    
    from services.hybrid_document_classifier import HybridDocumentClassifier
    CLASSIFIER_AVAILABLE = True
    print("✅ Hybrid Document Classifier loaded for structure analysis")
except ImportError as e:
    CLASSIFIER_AVAILABLE = False
    print(f"ℹ️  Document structure classifier not installed: {e}")
except Exception as e:
    CLASSIFIER_AVAILABLE = False
    # Don't show DLL errors in production - these are expected if PyTorch isn't fully set up
    if "DLL" in str(e) or "torch" in str(e).lower():
        print(f"ℹ️  Document structure classifier disabled (PyTorch dependencies not fully configured)")
    else:
        print(f"⚠️  Document structure classifier error: {e}")

class DocumentProcessor:
    
    # Class-level classifier instance (singleton pattern)
    _classifier = None
    
    @classmethod
    def get_classifier(cls):
        """Get or initialize the document structure classifier"""
        if cls._classifier is None and CLASSIFIER_AVAILABLE:
            try:
                cls._classifier = HybridDocumentClassifier()
            except Exception as e:
                print(f"Failed to initialize classifier: {e}")
                cls._classifier = None
        return cls._classifier

    @staticmethod
    def extract_text_from_pdf(file_bytes: bytes) -> str:
        """
        Extracts text using pdfplumber.
        If no text found -> fallback to OCR (Tesseract).
        """
        text = ""

        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"

        except Exception as e:
            print("PDFPlumber extraction failed:", e)

        # Fallback: OCR
        if len(text.strip()) < 50:
            print("Fallback to OCR...")
            images = DocumentProcessor.convert_pdf_to_images(file_bytes)
            for img in images:
                text += pytesseract.image_to_string(img)

        return text

    @staticmethod
    def convert_pdf_to_images(file_bytes: bytes):
        """Convert PDF to images for OCR"""
        try:
            from pdf2image import convert_from_bytes
            return convert_from_bytes(file_bytes)
        except:
            return []

    @staticmethod
    def clean_text(text: str) -> str:
        """Remove line breaks, special chars, normalize spacing."""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @staticmethod
    def is_sri_lanka_legal_document(text: str) -> bool:
        """Validate if document is a Sri Lankan legal case (SLR or NLR)."""
        if not text or len(text.strip()) < 100:
            print("Validation failed: Text too short or empty")
            return False
            
        text_upper = text.upper()
        score = 0
        matched_indicators = []
        
        # STRONG indicators (must have at least one)
        # Check for Sri Lankan Law Reports (SLR) indicators
        slr_patterns = [
            r'\bSLR\b',
            r'\bSRI\s+LANKA\s+LAW\s+REPORTS?\b',
        ]
        
        # Check for New Law Reports (NLR) indicators
        nlr_patterns = [
            r'\bNLR\b',
            r'\bNEW\s+LAW\s+REPORTS?\b'
        ]
        
        # Check for case citation patterns (e.g., "2015 1 SLR 123", "2020 NLR 45")
        citation_patterns = [
            r'\d{4}\s+\d+\s+SLR\s+\d+',
            r'\d{4}\s+NLR\s+\d+',
            r'\(\d{4}\)\s+\d+\s+SLR\s+\d+',
            r'\(\d{4}\)\s+NLR\s+\d+',
            r'\[\d{4}\]\s+\d+\s+SLR\s+\d+',
            r'\[\d{4}\]\s+NLR\s+\d+'
        ]
        
        # Strong match: SLR/NLR citation or report name
        strong_patterns = slr_patterns + nlr_patterns + citation_patterns
        for pattern in strong_patterns:
            if re.search(pattern, text_upper):
                score += 50
                matched_indicators.append(f"SLR/NLR citation (+50)")
                break
        
        # Check for Sri Lankan courts (MUST have specific Sri Lanka court)
        court_patterns = [
            r'\bSUPREME\s+COURT\s+OF\s+SRI\s+LAN?KA\b',
            r'\bCOURT\s+OF\s+APPEAL\s+OF\s+SRI\s+LAN?KA\b',
            r'\bHIGH\s+COURT\s+OF\s+SRI\s+LAN?KA\b',
            r'\bDISTRICT\s+COURT.*SRI\s+LAN?KA\b',
            r'\bMAGISTRATE.*COURT.*SRI\s+LAN?KA\b',
        ]
        
        for pattern in court_patterns:
            if re.search(pattern, text_upper):
                score += 30
                matched_indicators.append(f"Sri Lankan court (+30)")
                break
        
        # Check for legal case structure keywords (must have multiple)
        case_structure_terms = [
            (r'\bPETITIONER\b', 10),
            (r'\bRESPONDENT\b', 10),
            (r'\bAPPELLANT\b', 10),
            (r'\bPLAINTIFF\b', 10),
            (r'\bDEFENDANT\b', 10),
            (r'\bACCUSED\b', 10),
            (r'\bJUDGMENT\b', 5),
            (r'\bJUDGEMENT\b', 5),
            (r'\bRULING\b', 5),
            (r'\bCONVICTION\b', 5),
            (r'\bAPPEAL\b', 5),
            (r'\bS\.\s*C\.\s*APPLICATION\b', 15),
            (r'\bC\.\s*A\.\s*APPLICATION\b', 15),
            (r'\bH\.\?C\.\s*APPLICATION\b', 15),
        ]
        
        for pattern, points in case_structure_terms:
            if re.search(pattern, text_upper):
                score += points
                matched_indicators.append(f"Case structure term ({pattern}: +{points})")
        
        # Check for legal citations and references
        legal_references = [
            (r'\bORDINANCE\s+NO\.\s+\d+', 10),
            (r'\bACT\s+NO\.\s+\d+', 10),
            (r'\bSECTION\s+\d+', 5),
            (r'\bCHAPTER\s+\w+', 5),
            (r'\bP\.\s*C[,\.]', 10),  # Police Court
            (r'\bD\.\s*C[,\.]', 10),  # District Court
            (r'\bCRIMINAL\s+PROCEDURE\s+CODE', 10),
            (r'\bCIVIL\s+PROCEDURE\s+CODE', 10),
        ]
        
        for pattern, points in legal_references:
            if re.search(pattern, text_upper):
                score += points
                matched_indicators.append(f"Legal reference ({pattern}: +{points})")
        
        # Must have score of at least 20 to pass validation (lowered from 30)
        # This is more lenient for various types of Sri Lankan legal documents
        # Minimum requirements:
        # - At least some legal structure terms (20 points) OR
        # - Court name (30 points) OR  
        # - SLR/NLR citation (50 points)
        
        print(f"Document validation score: {score} (minimum: 20)")
        print(f"Matched indicators: {matched_indicators}")
        
        if score < 20:
            print(f"VALIDATION FAILED: Score {score} is below threshold of 20")
            print(f"Text preview (first 500 chars): {text[:500]}")
        
        return score >= 20

    @staticmethod
    def segment_into_paragraphs(text: str) -> list:
        """Split text into paragraphs for structure analysis"""
        # Split by double newlines or paragraph markers
        paragraphs = re.split(r'\n\s*\n', text)
        # Filter out very short segments
        paragraphs = [p.strip() for p in paragraphs if len(p.strip()) > 50]
        return paragraphs
    
    @classmethod
    def analyze_document_structure(cls, text: str) -> dict:
        """
        Analyze document structure using hybrid classifier
        
        Returns:
            Dictionary with structure analysis results or None if classifier unavailable
        """
        classifier = cls.get_classifier()
        if not classifier:
            return None
        
        try:
            # Segment document
            paragraphs = cls.segment_into_paragraphs(text)
            
            if not paragraphs:
                return None
            
            # Classify using hybrid approach
            result = classifier.classify_document(paragraphs)
            
            return {
                'total_paragraphs': result['statistics']['total_paragraphs'],
                'section_distribution': result['statistics']['section_distribution'],
                'method_distribution': result['statistics']['method_distribution'],
                'sections': result['sections']  # Full paragraph-level classification
            }
        except Exception as e:
            print(f"Structure analysis failed: {e}")
            return None

    @staticmethod
    def process_and_save(db: Session, file_name: str, file_path: str, file_bytes: bytes):
        """Full pipeline: extract, clean, parse metadata, analyze structure, save to DB."""

        raw_text = DocumentProcessor.extract_text_from_pdf(file_bytes)
        cleaned = DocumentProcessor.clean_text(raw_text)
        
        # Validate that this is actually a Sri Lankan legal document
        if not DocumentProcessor.is_sri_lanka_legal_document(cleaned):
            raise ValueError(
                "This document does not appear to be a Sri Lankan legal case (SLR or NLR). "
                "Please upload only Sri Lankan Law Reports (SLR) or New Law Reports (NLR) documents."
            )

        year = extract_case_year(cleaned)
        case_no = extract_case_number(cleaned)
        court = extract_court(cleaned)
        
        # Analyze document structure (Section 1.3)
        structure_analysis = DocumentProcessor.analyze_document_structure(cleaned)

        document = LegalDocument(
            file_name=file_name,
            file_path=file_path,
            raw_text=raw_text,
            cleaned_text=cleaned,
            year=year,
            case_number=case_no,
            court=court
        )

        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Attach structure analysis to document object (not saved to DB, just returned)
        if structure_analysis:
            document.structure_analysis = structure_analysis
            print(f"✅ Document structure analyzed: {structure_analysis['total_paragraphs']} paragraphs")
            print(f"   Sections: {structure_analysis['section_distribution']}")

        return document
