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
        
        # STRONG indicators - Check for party names format (common in NLR)
        # Format: "NAME v. NAME" or "NAME vs NAME" or "NAME et al. v. NAME"
        party_pattern = r'\b[A-Z][A-Za-z\s]+\s+(?:v\.|vs\.|versus)\s+[A-Z][A-Za-z\s]+'
        if re.search(party_pattern, text[:1000]):  # Check first 1000 chars
            score += 15
            matched_indicators.append("Party name format (v./vs.) (+15)")
        
        # Check for "et al." which is common in NLR
        if re.search(r'\bet\s+al\.', text_upper[:1000]):
            score += 10
            matched_indicators.append("'et al.' found (+10)")
        
        # Check for "Re" citation format (e.g., "Re 38. Chanda.")
        if re.search(r'\bRe\s+\d+\.', text[:500]):
            score += 20
            matched_indicators.append("'Re' citation format (+20)")
        
        # Check for Sri Lankan Law Reports (SLR) indicators
        slr_patterns = [
            r'\bSLR\b',
            r'\bSRI\s+LANKA\s+LAW\s+REPORTS?\b',
        ]
        
        # Check for New Law Reports (NLR) indicators
        nlr_patterns = [
            r'\bNLR\b',
            r'\bNEW\s+LAW\s+REPORTS?\b',
            r'\bCEYLON\s+LAW\s+REPORTS?\b',  # Older term for SL
        ]
        
        # Check for case citation patterns
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
                score += 30
                matched_indicators.append(f"SLR/NLR citation (+30)")
                break
        
        # Check for Sri Lankan/Ceylon courts
        court_patterns = [
            r'\bSUPREME\s+COURT\b',
            r'\bCOURT\s+OF\s+APPEAL\b',
            r'\bHIGH\s+COURT\b',
            r'\bDISTRICT\s+COURT\b',
            r'\bMAGISTRATE.*COURT\b',
            r'\bPRIVY\s+COUNCIL\b',  # Historical appeals
        ]
        
        for pattern in court_patterns:
            if re.search(pattern, text_upper):
                score += 15
                matched_indicators.append(f"Court reference (+15)")
                break
        
        # Check for company/entity terms common in NLR
        entity_terms = [
            (r'\bCOMPANY\b', 5),
            (r'\bLIMITED\b', 5),
            (r'\bCORPORATION\b', 5),
            (r'\bNAVIGATION\b', 5),
            (r'\bSTEAM\b', 5),
        ]
        
        for pattern, points in entity_terms:
            if re.search(pattern, text_upper):
                score += points
                matched_indicators.append(f"Entity term ({pattern}: +{points})")
        
        # Check for case structure keywords
        case_structure_terms = [
            (r'\bPETITIONER\b', 5),
            (r'\bRESPONDENT\b', 5),
            (r'\bAPPELLANT\b', 5),
            (r'\bPLAINTIFF\b', 5),
            (r'\bDEFENDANT\b', 5),
            (r'\bACCUSED\b', 5),
            (r'\bJUDGMENT\b', 5),
            (r'\bJUDGEMENT\b', 5),
            (r'\bRULING\b', 5),
            (r'\bAPPEAL\b', 5),
            (r'\bDAMAGES\b', 5),
            (r'\bLIABILITY\b', 5),
        ]
        
        for pattern, points in case_structure_terms:
            if re.search(pattern, text_upper):
                score += points
                matched_indicators.append(f"Case structure term ({pattern}: +{points})")
        
        # Check for legal references
        legal_references = [
            (r'\bORDINANCE\b', 5),
            (r'\bACT\b', 5),
            (r'\bSECTION\s+\d+', 5),
            (r'\bCHAPTER\s+\w+', 5),
            (r'\bRULE\s+\d+', 5),
        ]
        
        for pattern, points in legal_references:
            if re.search(pattern, text_upper):
                score += points
                matched_indicators.append(f"Legal reference ({pattern}: +{points})")
        
        # LOWERED THRESHOLD: 15 points (was 20)
        # This accommodates older NLR formats which may not have all modern indicators
        
        print(f"Document validation score: {score} (minimum: 15)")
        print(f"Matched indicators: {matched_indicators}")
        
        if score < 15:
            print(f"VALIDATION FAILED: Score {score} is below threshold of 15")
            print(f"Text preview (first 500 chars): {text[:500]}")
        
        return score >= 15

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
