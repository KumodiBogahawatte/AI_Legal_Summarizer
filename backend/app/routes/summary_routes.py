from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models.document_model import LegalDocument
from ..services.nlp_analyzer import NLPAnalyzer
from ..services.sri_lanka_legal_engine import SriLankaLegalEngine
from ..services.document_structure_service import analyze_document_structure, extract_section
from ..utils.sri_lanka_legal_utils import GLOSSARY_SI_EN_TA

# NO PREFIX - let main.py handle the /api/analysis prefix
router = APIRouter(prefix="", tags=["Analysis & Summaries"])

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/constitutional-rights")
def analyze_rights(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(LegalDocument).filter_by(id=document_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")

    # Get actual rights data from database
    from ..models.rights_model import DetectedRight
    rights = db.query(DetectedRight).filter_by(document_id=document_id).all()

    # Convert to response format
    rights_data = []
    for right in rights:
        rights_data.append({
            "id": right.id,
            "article_number": right.article_number,
            "matched_text": right.matched_text,
            "explanation_en": right.explanation_en,
            "explanation_si": right.explanation_si,
            "explanation_ta": right.explanation_ta
        })

    return {
        "document_id": document_id,
        "rights_detected": len(rights),
        "rights": rights_data
    }

@router.post("/summarize/with-local-context")
def summarize_document(document_id: int, db: Session = Depends(get_db)):
    try:
        doc = db.query(LegalDocument).filter_by(id=document_id).first()
        if not doc:
            raise HTTPException(404, "Document not found")

        if not doc.cleaned_text:
            raise HTTPException(400, "No text available for summarization")

        print(f"Processing document {document_id} with text length: {len(doc.cleaned_text)}")
        
        # Validate if document is a Sri Lankan legal case (SLR or NLR)
        from ..services.document_processor import DocumentProcessor
        if not DocumentProcessor.is_sri_lanka_legal_document(doc.cleaned_text):
            raise HTTPException(
                400, 
                "This document does not appear to be a Sri Lankan legal case (SLR or NLR). "
                "Please upload only Sri Lankan Law Reports (SLR) or New Law Reports (NLR) documents."
            )

        # Initialize engines
        nlp_analyzer = NLPAnalyzer()
        legal_engine = SriLankaLegalEngine()

        # Test each step individually to find which one fails
        try:
            summary = nlp_analyzer.extractive_summary(doc.cleaned_text or "", n_sentences=5)
            print("Summary generated successfully")
        except Exception as e:
            print(f"Summary generation failed: {str(e)}")
            raise

        try:
            multilingual_terms = legal_engine.detect_multilingual_terms(doc.cleaned_text or "")
            print("Multilingual terms detected successfully")
        except Exception as e:
            print(f"Multilingual terms detection failed: {str(e)}")
            raise

        # NEW: Detect constitutional rights using the legal engine
        try:
            # analyze_rights returns a list of detected rights as dictionaries
            rights = legal_engine.analyze_rights(
                db=db,
                document_id=document_id,
                text=doc.cleaned_text or "",
                language="en"  # Default to English, or extract from document
            )
            print(f"Constitutional rights detected successfully: {len(rights)} rights found")
            
            # Filter to only Fundamental Rights (Articles 10-18, 14A) for the rights section
            fundamental_rights = [
                r for r in rights 
                if r.get("article", "0") in ["10", "11", "12", "13", "14", "14A", "15", "16", "17", "18"]
            ]
            print(f"Fundamental Rights filtered: {len(fundamental_rights)} rights (Articles 10-18)")
        except Exception as e:
            print(f"Constitutional rights detection failed: {str(e)}")
            import traceback
            traceback.print_exc()
            # Don't fail the whole request if rights detection fails
            rights = []
            fundamental_rights = []

        # NEW: Detect all constitutional provisions
        try:
            constitutional_provisions = legal_engine.analyze_constitutional_provisions(
                text=doc.cleaned_text or "",
                language="en"
            )
            print(f"Constitutional provisions detected: {len(constitutional_provisions)} provisions found")
        except Exception as e:
            print(f"Constitutional provisions detection failed: {str(e)}")
            import traceback
            traceback.print_exc()
            constitutional_provisions = []

        return {
            "document_id": document_id,
            "summary": summary,
            "keywords": nlp_analyzer.extract_keywords(doc.cleaned_text or ""),
            "multilingual_legal_terms": multilingual_terms,
            "fundamental_rights": fundamental_rights,  # Filtered to Articles 10-18 only
            "constitutional_provisions": constitutional_provisions  # All constitutional articles
        }
    except Exception as e:
        print(f"Summary error: {str(e)}")
        raise HTTPException(500, f"Summary generation failed: {str(e)}")

# Alternative endpoint that accepts text directly (like in the example)
from pydantic import BaseModel

class SummarizeReq(BaseModel):
    text: str
    language: str = "en"
    document_id: int | None = None

@router.post("/summarize/with-local-context/text")
def summarize_text(req: SummarizeReq, db: Session = Depends(get_db)):
    """Alternative endpoint that accepts text directly instead of document_id"""
    try:
        if not req.text:
            raise HTTPException(400, "Text cannot be empty")
        
        # Validate if text is from a Sri Lankan legal case
        from ..services.document_processor import DocumentProcessor
        if not DocumentProcessor.is_sri_lanka_legal_document(req.text):
            raise HTTPException(
                400,
                "This document does not appear to be a Sri Lankan legal case (SLR or NLR). "
                "Please provide text from Sri Lankan Law Reports (SLR) or New Law Reports (NLR) documents."
            )

        # Initialize engines
        nlp_analyzer = NLPAnalyzer()
        legal_engine = SriLankaLegalEngine()

        # Generate summary
        summary = nlp_analyzer.extractive_summary(req.text, n_sentences=5)
        
        # Detect multilingual terms
        multilingual_terms = legal_engine.detect_multilingual_terms(req.text)
        
        # Detect constitutional rights
        try:
            rights = legal_engine.analyze_rights(
                db=db,
                document_id=req.document_id,  # Can be None
                text=req.text,
                language=req.language
            )
            print(f"Constitutional rights detected: {len(rights)} rights found")
        except Exception as e:
            print(f"Rights detection failed: {str(e)}")
            import traceback
            traceback.print_exc()
            rights = []
        
        # Detect all constitutional provisions
        try:
            constitutional_provisions = legal_engine.analyze_constitutional_provisions(
                text=req.text,
                language=req.language
            )
            print(f"Constitutional provisions detected: {len(constitutional_provisions)} provisions found")
        except Exception as e:
            print(f"Constitutional provisions detection failed: {str(e)}")
            import traceback
            traceback.print_exc()
            constitutional_provisions = []
        
        # Optionally extract citations if available
        # citations = legal_engine.extract_citations(req.text)

        return {
            "summary": summary,
            "keywords": nlp_analyzer.extract_keywords(req.text),
            "multilingual_legal_terms": multilingual_terms,
            "rights": rights,
            "constitutional_provisions": constitutional_provisions,
            # "citations": citations  # Uncomment if you implement citation extraction
        }
    except Exception as e:
        print(f"Text summarization error: {str(e)}")
        raise HTTPException(500, f"Text summarization failed: {str(e)}")

@router.get("/legal-terms/explain/{language}")
def explain_legal_terms(language: str):
    if language not in ["en", "si", "ta"]:
        raise HTTPException(400, "Invalid language code")

    result = {}
    # FIXED: Use GLOSSARY_SI_EN_TA directly
    for term, meanings in GLOSSARY_SI_EN_TA.items():
        if language in meanings:
            result[term] = meanings[language]

    return {"language": language, "terms": result}

@router.post("/extract-entities")
def extract_legal_entities_from_text(text: str):
    """
    Extract legal entities (case names, courts, judges, statutes, etc.) from text.
    
    Request body:
    - text: The legal text to analyze
    
    Returns:
    - entities_by_type: Dictionary grouped by entity type
    - total_entities: Total number of entities found
    - entity_types: List of entity types found
    """
    try:
        if not text or len(text.strip()) == 0:
            raise HTTPException(400, "Text cannot be empty")
        
        # Extract entities using the trained NER model
        entities = NLPAnalyzer.extract_legal_entities(text)
        
        if "error" in entities:
            raise HTTPException(500, f"Entity extraction failed: {entities['error']}")
        
        # Calculate statistics
        total_entities = sum(len(ents) for ents in entities.values())
        entity_types = list(entities.keys())
        
        return {
            "entities_by_type": entities,
            "total_entities": total_entities,
            "entity_types": entity_types,
            "text_length": len(text)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Entity extraction error: {str(e)}")
        raise HTTPException(500, f"Entity extraction failed: {str(e)}")

@router.get("/extract-entities/{document_id}")
def extract_legal_entities_from_document(document_id: int, db: Session = Depends(get_db)):
    """
    Extract legal entities from a stored document.
    
    Returns entities grouped by type with their positions in the text.
    """
    try:
        doc = db.query(LegalDocument).filter_by(id=document_id).first()
        if not doc:
            raise HTTPException(404, "Document not found")
        
        # Use cleaned_text (preferred) or raw_text as fallback
        text = doc.cleaned_text or doc.raw_text
        
        if not text or len(text.strip()) == 0:
            raise HTTPException(400, "Document has no text content")
        
        # Extract entities
        entities = NLPAnalyzer.extract_legal_entities(text)
        
        if "error" in entities:
            raise HTTPException(500, f"Entity extraction failed: {entities['error']}")
        
        # Calculate statistics
        total_entities = sum(len(ents) for ents in entities.values())
        entity_types = list(entities.keys())
        
        return {
            "document_id": document_id,
            "file_name": doc.file_name,
            "entities_by_type": entities,
            "total_entities": total_entities,
            "entity_types": entity_types,
            "content_length": len(text)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Entity extraction error: {str(e)}")
        raise HTTPException(500, f"Entity extraction failed: {str(e)}")


@router.post("/analyze-structure")
def analyze_structure(text: str = None, use_ml: bool = False):
    """
    Analyze document structure from raw text
    
    Args:
        text: Document text to analyze
        use_ml: Whether to use ML model (default: False, uses rule-based)
    
    Returns:
        Structured analysis with classified paragraphs
    """
    try:
        if not text:
            raise HTTPException(400, "No text provided")
        
        # Analyze structure
        analysis = analyze_document_structure(text, use_ml=use_ml)
        
        return {
            "analysis": analysis,
            "method": "ml" if use_ml else "rule-based"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Structure analysis error: {str(e)}")
        raise HTTPException(500, f"Structure analysis failed: {str(e)}")


@router.get("/analyze-structure/{document_id}")
def analyze_document_structure_by_id(document_id: int, use_ml: bool = False, db: Session = Depends(get_db)):
    """
    Analyze structure of a stored document
    
    Args:
        document_id: ID of document to analyze
        use_ml: Whether to use ML model
        db: Database session
    
    Returns:
        Document structure analysis
    """
    try:
        # Get document
        doc = db.query(LegalDocument).filter_by(id=document_id).first()
        if not doc:
            raise HTTPException(404, "Document not found")
        
        # Get text
        text = doc.cleaned_text or doc.raw_text
        if not text:
            raise HTTPException(400, "Document has no text content")
        
        # Analyze structure
        analysis = analyze_document_structure(text, use_ml=use_ml)
        
        return {
            "document_id": document_id,
            "file_name": doc.file_name,
            "analysis": analysis,
            "method": "ml" if use_ml else "rule-based"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Structure analysis error: {str(e)}")
        raise HTTPException(500, f"Structure analysis failed: {str(e)}")


@router.get("/extract-section/{document_id}")
def extract_document_section(
    document_id: int,
    section: str,
    use_ml: bool = False,
    db: Session = Depends(get_db)
):
    """
    Extract a specific section from document
    
    Args:
        document_id: ID of document
        section: Section to extract (FACTS, ISSUES, LEGAL_ANALYSIS, REASONING, JUDGMENT, ORDERS)
        use_ml: Whether to use ML model
        db: Database session
    
    Returns:
        Extracted section text
    """
    try:
        # Validate section
        valid_sections = ['FACTS', 'ISSUES', 'LEGAL_ANALYSIS', 'REASONING', 'JUDGMENT', 'ORDERS']
        if section.upper() not in valid_sections:
            raise HTTPException(400, f"Invalid section. Must be one of: {', '.join(valid_sections)}")
        
        # Get document
        doc = db.query(LegalDocument).filter_by(id=document_id).first()
        if not doc:
            raise HTTPException(404, "Document not found")
        
        # Get text
        text = doc.cleaned_text or doc.raw_text
        if not text:
            raise HTTPException(400, "Document has no text content")
        
        # Extract section
        section_text = extract_section(text, section.upper(), use_ml=use_ml)
        
        return {
            "document_id": document_id,
            "file_name": doc.file_name,
            "section": section.upper(),
            "text": section_text,
            "length": len(section_text),
            "method": "ml" if use_ml else "rule-based"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Section extraction error: {str(e)}")
        raise HTTPException(500, f"Section extraction failed: {str(e)}")


# ============================================================================
# MULTI-LEVEL SUMMARIZATION ENDPOINTS (NEW)
# ============================================================================

@router.get("/summarize/multi-level/{document_id}")
def generate_multi_level_summary(
    document_id: int,
    include_plain_language: bool = False,
    db: Session = Depends(get_db)
):
    """
    Generate all three levels of summaries for a document:
    - Executive Summary (150-200 words)
    - Detailed Summary (600-1000 words)
    - Section-Specific Summaries
    
    Optionally includes plain language versions.
    """
    try:
        from ..services.advanced_summarizer import AdvancedLegalSummarizer
        from ..services.plain_language_converter import PlainLanguageConverter
        
        # Get document
        doc = db.query(LegalDocument).filter_by(id=document_id).first()
        if not doc:
            raise HTTPException(404, "Document not found")
        
        text = doc.cleaned_text or doc.raw_text
        if not text:
            raise HTTPException(400, "Document has no text content")
        
        # Try to get structured content (from document structure classification)
        structured_content = None
        try:
            structure_result = analyze_document_structure(text, use_ml=True)
            if structure_result and 'sections' in structure_result:
                structured_content = {}
                for section, paragraphs in structure_result['sections'].items():
                    if paragraphs:  # paragraphs is a list of dicts
                        paragraph_texts = [p['text'] for p in paragraphs]
                        structured_content[section] = "\n\n".join(paragraph_texts)
        except Exception as e:
            print(f"Could not get structured content: {e}")
        
        # Generate summaries
        summarizer = AdvancedLegalSummarizer()
        summaries = summarizer.generate_all_summaries(text, structured_content)
        
        # Add plain language versions if requested
        if include_plain_language:
            converter = PlainLanguageConverter()
            plain_versions = converter.convert_summary_to_plain(summaries)
            summaries['plain_language'] = plain_versions
        
        return {
            "document_id": document_id,
            "file_name": doc.file_name,
            "summaries": summaries,
            "structure_aware": structured_content is not None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Multi-level summarization error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Summarization failed: {str(e)}")


@router.get("/summarize/executive/{document_id}")
def generate_executive_summary(document_id: int, db: Session = Depends(get_db)):
    """Generate only executive summary (150-200 words)."""
    try:
        from ..services.advanced_summarizer import AdvancedLegalSummarizer
        
        doc = db.query(LegalDocument).filter_by(id=document_id).first()
        if not doc:
            raise HTTPException(404, "Document not found")
        
        text = doc.cleaned_text or doc.raw_text
        if not text:
            raise HTTPException(400, "Document has no text content")
        
        # Try to get structured content
        structured_content = None
        try:
            structure_result = analyze_document_structure(text, use_ml=True)
            if structure_result and 'sections' in structure_result:
                structured_content = {}
                for section, paragraphs in structure_result['sections'].items():
                    if paragraphs:  # paragraphs is a list of dicts
                        paragraph_texts = [p['text'] for p in paragraphs]
                        structured_content[section] = "\n\n".join(paragraph_texts)
        except:
            pass
        
        summarizer = AdvancedLegalSummarizer()
        summary = summarizer.generate_executive_summary(text, structured_content)
        
        return {
            "document_id": document_id,
            "file_name": doc.file_name,
            **summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Executive summary error: {str(e)}")
        raise HTTPException(500, f"Executive summary failed: {str(e)}")


@router.get("/summarize/detailed/{document_id}")
def generate_detailed_summary(document_id: int, db: Session = Depends(get_db)):
    """Generate only detailed summary (600-1000 words)."""
    try:
        from ..services.advanced_summarizer import AdvancedLegalSummarizer
        
        doc = db.query(LegalDocument).filter_by(id=document_id).first()
        if not doc:
            raise HTTPException(404, "Document not found")
        
        text = doc.cleaned_text or doc.raw_text
        if not text:
            raise HTTPException(400, "Document has no text content")
        
        # Try to get structured content
        structured_content = None
        try:
            structure_result = analyze_document_structure(text, use_ml=True)
            if structure_result and 'sections' in structure_result:
                structured_content = {}
                for section, paragraphs in structure_result['sections'].items():
                    if paragraphs:  # paragraphs is a list of dicts
                        paragraph_texts = [p['text'] for p in paragraphs]
                        structured_content[section] = "\n\n".join(paragraph_texts)
        except:
            pass
        
        summarizer = AdvancedLegalSummarizer()
        summary = summarizer.generate_detailed_summary(text, structured_content)
        
        return {
            "document_id": document_id,
            "file_name": doc.file_name,
            **summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Detailed summary error: {str(e)}")
        raise HTTPException(500, f"Detailed summary failed: {str(e)}")


@router.post("/convert-to-plain-language")
def convert_text_to_plain_language(req: SummarizeReq):
    """Convert legal text to plain language."""
    try:
        from ..services.plain_language_converter import PlainLanguageConverter
        
        if not req.text:
            raise HTTPException(400, "Text cannot be empty")
        
        converter = PlainLanguageConverter()
        result = converter.convert_to_plain_language(req.text)
        
        # Generate glossary
        glossary = converter.generate_glossary(req.text)
        
        return {
            **result,
            'glossary': glossary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Plain language conversion error: {str(e)}")
        raise HTTPException(500, f"Conversion failed: {str(e)}")


# ==================== PRECEDENT MATCHING ROUTES ====================

from ..services.precedent_matcher import get_precedent_matcher
from pydantic import BaseModel
from typing import Optional

class PrecedentQuery(BaseModel):
    """Request model for text-based precedent search"""
    query_text: str
    top_k: int = 5
    court_filter: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None


@router.get("/similar-cases/{document_id}")
def get_similar_cases(
    document_id: int,
    top_k: int = 5,
    min_similarity: float = 0.3,
    db: Session = Depends(get_db)
):
    """
    Find similar cases to a given document.
    
    Args:
        document_id: ID of the source document
        top_k: Number of similar cases to return (default: 5)
        min_similarity: Minimum similarity threshold (default: 0.3)
    
    Returns:
        List of similar cases with similarity scores and metadata
    """
    try:
        # Verify document exists
        doc = db.query(LegalDocument).filter_by(id=document_id).first()
        if not doc:
            raise HTTPException(404, f"Document {document_id} not found")
        
        # Get precedent matcher
        matcher = get_precedent_matcher()
        
        # Find similar cases
        similar_cases = matcher.find_similar_cases(
            document_id=document_id,
            top_k=top_k,
            min_similarity=min_similarity,
            db=db
        )
        
        return {
            'document_id': document_id,
            'source_document': {
                'title': doc.file_name,  # Using file_name as title
                'court': doc.court,
                'year': doc.year
            },
            'similar_cases_count': len(similar_cases),
            'similar_cases': similar_cases
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error finding similar cases: {str(e)}")
        raise HTTPException(500, f"Failed to find similar cases: {str(e)}")


@router.post("/find-precedents")
def find_precedents(
    query: PrecedentQuery,
    db: Session = Depends(get_db)
):
    """
    Find precedents based on free text query.
    
    Request Body:
        - query_text: Text to search for
        - top_k: Number of results (default: 5)
        - court_filter: Filter by court name (optional)
        - year_from: Minimum year (optional)
        - year_to: Maximum year (optional)
    
    Returns:
        List of matching cases with similarity scores
    """
    try:
        if not query.query_text or not query.query_text.strip():
            raise HTTPException(400, "Query text cannot be empty")
        
        # Get precedent matcher
        matcher = get_precedent_matcher()
        
        # Find precedents
        precedents = matcher.find_precedents_by_text(
            query_text=query.query_text,
            top_k=query.top_k,
            court_filter=query.court_filter,
            year_from=query.year_from,
            year_to=query.year_to,
            db=db
        )
        
        return {
            'query': query.query_text,
            'results_count': len(precedents),
            'precedents': precedents
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error finding precedents: {str(e)}")
        raise HTTPException(500, f"Failed to find precedents: {str(e)}")