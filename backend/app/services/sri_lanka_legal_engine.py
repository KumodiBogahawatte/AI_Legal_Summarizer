# backend/app/services/sri_lanka_legal_engine.py

import re
from sqlalchemy.orm import Session
from ..models.rights_model import DetectedRight
from ..models.citation_model import SLCitation
from .fundamental_rights_detector import FundamentalRightsDetector
from .constitutional_article_detector import ConstitutionalArticleDetector
from ..utils.sri_lanka_legal_utils import (
    FUNDAMENTAL_RIGHTS_PATTERNS,
    PROCESSED_CONSTITUTIONS,
    GLOSSARY_SI_EN_TA,
    CITATION_PATTERN_NLR,
    CITATION_PATTERN_SLR
)

detector = FundamentalRightsDetector(semantic_threshold=0.45)
constitutional_detector = ConstitutionalArticleDetector(semantic_threshold=0.35)

class SriLankaLegalEngine:
    
    def __init__(self):
        pass

    def analyze_constitutional_provisions(self, text: str, language: str = "en"):
        """
        Detect all constitutional provisions (articles, sections, chapters) in text.
        Returns list of detected provisions with constitutional references.
        """
        return constitutional_detector.detect(text, language=language)

    def analyze_rights(self, db: Session, document_id: int, text: str, language: str = "en"):
        """
        Detect fundamental rights and save them to database.
        Returns list of detected rights as dictionaries.
        """
        # Get detections from the detector
        detections = detector.detect(text, language=language)
        
        # Save to database if document_id is provided
        if document_id:
            for detection in detections:
                # Extract article number (handle both string and int)
                article_str = str(detection.get("article", "0"))
                try:
                    article_num = int(article_str)
                except ValueError:
                    # If article is "unknown" or non-numeric, skip
                    continue
                
                # Create database record
                new_right = DetectedRight(
                    document_id=document_id,
                    article_number=article_num,
                    matched_text=detection.get("matched_text", ""),
                    explanation_en=detection.get("explanation", "")
                )
                db.add(new_right)
            
            try:
                db.commit()
            except Exception as e:
                print(f"Error saving rights to database: {e}")
                db.rollback()
        
        # Return detections as list of dicts for immediate use
        return detections

    @staticmethod
    def detect_fundamental_rights(db, doc_id, text):
        detected = []

        for article, pattern in FUNDAMENTAL_RIGHTS_PATTERNS.items():
            # Handle pattern as string (compile it first)
            if isinstance(pattern, str):
                try:
                    compiled_pattern = re.compile(pattern, re.IGNORECASE)
                    matches = compiled_pattern.findall(text)
                except Exception as e:
                    print(f"Error compiling pattern for article {article}: {e}")
                    continue
            else:
                # Pattern is already compiled
                matches = pattern.findall(text)
            
            for match in matches:
                # Ensure match is a string (handle tuples from capture groups)
                if isinstance(match, tuple):
                    match_text = ' '.join(str(m) for m in match if m)
                else:
                    match_text = str(match)
                
                # Find nearest constitution explanation
                related_sentences = []
                for const in PROCESSED_CONSTITUTIONS.values():
                    for s in const["sentences"]:
                        if str(article) in s or match_text.lower() in s.lower():
                            related_sentences.append(s)

                explanation = " ".join(related_sentences[:3])  # first 3 relevant sentences

                new_right = DetectedRight(
                    document_id=doc_id,
                    article_number=article,
                    matched_text=match_text,
                    explanation_en=explanation
                )
                db.add(new_right)
                detected.append(new_right)

        db.commit()
        return detected

    @staticmethod
    def extract_citations(db: Session, doc_id: int, text: str):
        citations_found = []

        patterns = [CITATION_PATTERN_NLR, CITATION_PATTERN_SLR]

        for pattern in patterns:
            # Handle pattern as string (compile it first)
            if isinstance(pattern, str):
                try:
                    compiled_pattern = re.compile(pattern)
                    matches = compiled_pattern.findall(text)
                except Exception as e:
                    print(f"Error compiling citation pattern: {e}")
                    continue
            else:
                # Pattern is already compiled
                matches = pattern.findall(text)
                
            for match in matches:
                # Ensure match is a string (handle tuples from capture groups)
                if isinstance(match, tuple):
                    citation_text = ' '.join(str(m) for m in match if m)
                else:
                    citation_text = str(match)
                    
                cite = SLCitation(
                    document_id=doc_id,
                    citation_text=citation_text,
                )
                db.add(cite)
                citations_found.append(cite)

        db.commit()
        return citations_found

    @staticmethod
    def detect_multilingual_terms(text: str):
        found_terms = {}
        # FIXED: Use GLOSSARY_SI_EN_TA directly
        for term, meanings in GLOSSARY_SI_EN_TA.items():
            if term.lower() in text.lower():
                found_terms[term] = meanings
        return found_terms