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
def summarize_document(document_id: int, use_ai: bool = True, db: Session = Depends(get_db)):
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

        # Use BART for better summaries (free, open-source)
        if use_ai:
            try:
                from ..services.bart_summarizer import BARTLegalSummarizer
                bart = BARTLegalSummarizer()
                
                summary = bart.summarize_legal_document(doc.cleaned_text, max_length=200, min_length=100)
                keywords = bart.extract_key_points(doc.cleaned_text, num_points=7)
                
                print("✅ BART summary generated successfully")
            except Exception as e:
                print(f"⚠️ BART failed, falling back to basic summarizer: {e}")
                # Fallback to existing summarizer
                nlp_analyzer = NLPAnalyzer()
                summary = nlp_analyzer.extractive_summary(doc.cleaned_text, n_sentences=5)
                keywords = nlp_analyzer.extract_keywords(doc.cleaned_text)
        else:
            # Use existing NLP analyzer
            nlp_analyzer = NLPAnalyzer()
            summary = nlp_analyzer.extractive_summary(doc.cleaned_text, n_sentences=5)
            keywords = nlp_analyzer.extract_keywords(doc.cleaned_text)

        # Initialize engines
        legal_engine = SriLankaLegalEngine()

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
            "keywords": keywords,
            "multilingual_legal_terms": legal_engine.detect_multilingual_terms(doc.cleaned_text),
            "fundamental_rights": fundamental_rights,
            "constitutional_provisions": constitutional_provisions,
            "summary_model": "facebook/bart-large-cnn" if use_ai else "extractive"
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
                'id': doc.id,
                'title': doc.file_name,
                'court': doc.court,
                'year': doc.year,
                'case_number': doc.case_number
            },
            'similar_cases_count': len(similar_cases),
            'similar_cases': similar_cases
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error finding similar cases: {str(e)}")
        raise HTTPException(500, f"Failed to find similar cases: {str(e)}")


@router.get("/case/{document_id}")
def get_case_details(document_id: int, db: Session = Depends(get_db)):
    """
    Get full details of a specific case with analysis.
    """
    try:
        # Get document
        doc = db.query(LegalDocument).filter_by(id=document_id).first()
        if not doc:
            raise HTTPException(404, f"Case {document_id} not found")
        
        # Get or generate entities
        try:
            from ..models.legal_entity_model import LegalEntity
            entities = db.query(LegalEntity).filter_by(document_id=document_id).all()
            
            # If no entities found, extract them
            if not entities and doc.cleaned_text:
                nlp_analyzer = NLPAnalyzer()
                extracted_entities = nlp_analyzer.extract_legal_entities(doc.cleaned_text)
                
                # Save entities to database
                for entity_type, entity_list in extracted_entities.items():
                    for entity_data in entity_list:
                        new_entity = LegalEntity(
                            document_id=document_id,
                            entity_text=entity_data['text'],
                            entity_type=entity_type,
                            start_pos=entity_data.get('start', 0),
                            end_pos=entity_data.get('end', 0),
                            context=entity_data.get('context', '')
                        )
                        db.add(new_entity)
                db.commit()
                
                # Refresh entities list
                entities = db.query(LegalEntity).filter_by(document_id=document_id).all()
            
            entities_by_type = {}
            for entity in entities:
                if entity.entity_type not in entities_by_type:
                    entities_by_type[entity.entity_type] = []
                entities_by_type[entity.entity_type].append({
                    "text": entity.entity_text,
                    "context": entity.context if hasattr(entity, 'context') else None
                })
        except Exception as e:
            print(f"Could not load/generate entities: {e}")
            entities_by_type = {}
            entities = []
        
        # Get or generate rights
        try:
            from ..models.rights_model import DetectedRight
            rights = db.query(DetectedRight).filter_by(document_id=document_id).all()
            
            # If no rights found, detect them
            if not rights and doc.cleaned_text:
                legal_engine = SriLankaLegalEngine()
                detected_rights = legal_engine.analyze_rights(
                    db=db,
                    document_id=document_id,
                    text=doc.cleaned_text,
                    language="en"
                )
                
                # Refresh rights list
                rights = db.query(DetectedRight).filter_by(document_id=document_id).all()
            
            rights_list = [{
                "article_number": r.article_number,
                "matched_text": r.matched_text,
                "explanation_en": r.explanation_en
            } for r in rights]
        except Exception as e:
            print(f"Could not load/generate rights: {e}")
            rights_list = []
            rights = []
        
        # Get or generate citations
        try:
            from ..models.citation_model import SLCitation
            citations = db.query(SLCitation).filter_by(document_id=document_id).all()
            
            # If no citations found, extract them
            if not citations and doc.cleaned_text:
                legal_engine = SriLankaLegalEngine()
                legal_engine.extract_citations(
                    db=db,
                    doc_id=document_id,
                    text=doc.cleaned_text
                )
                
                # Refresh citations list
                citations = db.query(SLCitation).filter_by(document_id=document_id).all()
            
            citations_list = [c.citation_text for c in citations]
        except Exception as e:
            print(f"Could not load/generate citations: {e}")
            citations_list = []
        
        # Build response
        response = {
            "document_id": doc.id,
            "file_name": doc.file_name,
            "court": doc.court,
            "year": doc.year,
            "case_number": doc.case_number,
            "text": {
                "cleaned": doc.cleaned_text[:5000] if doc.cleaned_text else None,
                "full_length": len(doc.cleaned_text) if doc.cleaned_text else 0
            },
            "metadata": {
                "has_embedding": doc.embedding is not None and len(doc.embedding) > 0 if doc.embedding else False,
                "embedding_dimension": len(doc.embedding) if doc.embedding else 0
            },
            "analysis": {
                "rights_detected": len(rights_list),
                "citations_found": len(citations_list),
                "entities_extracted": len(entities)
            },
            "rights": rights_list[:10],
            "citations": citations_list[:10],
            "entities": entities_by_type
        }
        
        if hasattr(doc, 'uploaded_at') and doc.uploaded_at:
            response["uploaded_at"] = doc.uploaded_at.isoformat()
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting case details: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to get case details: {str(e)}")


@router.get("/case/{document_id}/full-text")
def get_case_full_text(document_id: int, db: Session = Depends(get_db)):
    """
    Get the complete text of a case.
    Separate endpoint to avoid loading large text in list views.
    """
    try:
        doc = db.query(LegalDocument).filter_by(id=document_id).first()
        if not doc:
            raise HTTPException(404, f"Case {document_id} not found")
        
        return {
            "document_id": doc.id,
            "file_name": doc.file_name,
            "cleaned_text": doc.cleaned_text,
            "raw_text": doc.raw_text,
            "text_length": len(doc.cleaned_text or doc.raw_text or "")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting full text: {str(e)}")
        raise HTTPException(500, f"Failed to get full text: {str(e)}")


@router.post("/compare-documents")
def compare_documents(
    source_document_id: int,
    target_document_id: int,
    threshold: float = 0.5,
    db: Session = Depends(get_db)
):
    """
    Compare two documents and return matching sentences
    
    Args:
        source_document_id: The uploaded document
        target_document_id: The case to compare against
        threshold: Minimum similarity score (0-1)
    
    Returns:
        Matching sentences with similarity scores and highlighted text
    """
    try:
        from ..services.text_similarity_service import get_similarity_service
        
        # Get documents
        source_doc = db.query(LegalDocument).filter_by(id=source_document_id).first()
        target_doc = db.query(LegalDocument).filter_by(id=target_document_id).first()
        
        if not source_doc or not target_doc:
            raise HTTPException(404, "Document not found")
        
        source_text = source_doc.cleaned_text or source_doc.raw_text
        target_text = target_doc.cleaned_text or target_doc.raw_text
        
        if not source_text or not target_text:
            raise HTTPException(400, "Documents have no text content")
        
        # Compare documents
        similarity_service = get_similarity_service()
        comparison = similarity_service.compare_documents(
            source_text,
            target_text,
            threshold
        )
        
        # Generate highlighted text
        highlighted_text = similarity_service.highlight_matching_text(
            target_text,
            comparison['highlighted_sentences']
        )
        
        return {
            'source_document_id': source_document_id,
            'target_document_id': target_document_id,
            'comparison': comparison,
            'highlighted_text': highlighted_text
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Document comparison error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Comparison failed: {str(e)}")


@router.get("/case-brief/{document_id}")
def generate_case_brief(document_id: int, db: Session = Depends(get_db)):
    """
    Generate structured legal case brief suitable for law students and research
    
    Returns:
        - Case citation (name, court, year)
        - Executive summary (100-150 words)
        - Facts
        - Issues
        - Holding/Decision
        - Reasoning
        - Final Order
        - Ratio Decidendi (2-4 bullet points)
        - Procedural/Evidentiary Principles
    """
    try:
        from ..services.case_brief_generator import CaseBriefGenerator
        
        # Get document
        doc = db.query(LegalDocument).filter_by(id=document_id).first()
        if not doc:
            raise HTTPException(404, "Document not found")
        
        text = doc.cleaned_text or doc.raw_text
        if not text:
            raise HTTPException(400, "Document has no text content")
        
        # Prepare metadata
        metadata = {
            'court': doc.court,
            'year': doc.year,
            'case_number': doc.case_number
        }
        
        # Generate case brief
        brief = CaseBriefGenerator.generate_case_brief(text, metadata)
        
        return {
            'document_id': document_id,
            'file_name': doc.file_name,
            'case_brief': brief
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Case brief generation error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Brief generation failed: {str(e)}")
