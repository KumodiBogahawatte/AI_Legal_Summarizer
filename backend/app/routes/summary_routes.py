from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session
import re
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


@router.get("/llm-status")
def get_llm_status():
    """
    Check AI/LLM service status: API key configured and quota (limit) availability.
    Returns whether the Gemini API is usable so the frontend can show limit/fallback messaging.
    """
    import os
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key or key == "your-openai-key-here":
        return {
            "api_key_configured": False,
            "limit_status": "no_key",
            "message": "No API key set. Set OPENAI_API_KEY in backend/.env (e.g. Gemini key) for full AI summaries.",
        }
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        resp = client.chat.completions.create(
            model="gemini-flash-latest",
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=10,
        )
        _ = resp.choices[0].message.content
        return {
            "api_key_configured": True,
            "limit_status": "ok",
            "message": "AI service is available. Full summaries and section-by-section analysis are enabled.",
        }
    except Exception as e:
        err = str(e)
        # Check expired/invalid key first (400 + API key message)
        if "API key expired" in err or "API_KEY_INVALID" in err or "400" in err and ("invalid" in err.lower() or "API key" in err):
            return {
                "api_key_configured": True,
                "limit_status": "invalid_key",
                "message": "API key expired or invalid. Create a new key at Google AI Studio (aistudio.google.com) and set OPENAI_API_KEY in backend/.env, then restart the backend.",
            }
        if "401" in err or "403" in err or "invalid" in err.lower() or "API key" in err:
            return {
                "api_key_configured": True,
                "limit_status": "invalid_key",
                "message": "API key rejected. Set a valid Gemini key in backend/.env (OPENAI_API_KEY).",
            }
        if "429" in err or "quota" in err.lower() or "RESOURCE_EXHAUSTED" in err:
            return {
                "api_key_configured": True,
                "limit_status": "quota_exceeded",
                "message": "API limit (quota) reached. Try again later or use another key. Summaries will use fallback until quota resets.",
            }
        return {
            "api_key_configured": True,
            "limit_status": "error",
            "message": f"API check failed: {err[:200]}",
        }


def _normalize_or_default(value: str | None) -> str:
    """Return trimmed value or standard fallback string."""
    text = (value or "").strip()
    return text if text else "Not mentioned in the case."


# Canonical definitions for appeal terms so LLM-generated glossary is never wrong
_APPEAL_TERM_DEFINITIONS = {
    "respondent": "party opposing the appeal (e.g. complainant or prosecution)",
    "appellant": "party bringing the appeal (e.g. the accused or the party who lost below)",
}


def _fix_glossary_appeal_terms(glossary: list) -> None:
    """Overwrite respondent/appellant definitions so they are always legally correct."""
    for entry in glossary:
        if isinstance(entry, dict):
            term = (entry.get("term") or "").strip().lower()
            if term in _APPEAL_TERM_DEFINITIONS:
                entry["definition"] = _APPEAL_TERM_DEFINITIONS[term]


@router.get("/case/{doc_id}")
def get_case_detail(doc_id: int, db: Session = Depends(get_db)):
    """
    Full case detail for CaseDetailPage — metadata, analysis summary,
    constitutional rights (in frontend-compatible format), citations, and text preview.
    """
    doc = db.query(LegalDocument).filter_by(id=doc_id).first()
    if not doc:
        raise HTTPException(404, detail=f"Document {doc_id} not found")

    text = doc.cleaned_text or doc.raw_text or ""

    # ── Constitutional rights via keyword matching ─────────────────────────
    import re
    ARTICLE_MAP = {
        10: {"title": "Freedom of Thought, Conscience and Religion",
             "keywords": ["freedom of thought", "freedom of religion", "conscience"]},
        11: {"title": "Freedom from Torture",
             "keywords": ["torture", "cruel inhuman", "degrading treatment"]},
        12: {"title": "Right to Equality",
             "keywords": ["equality", "equal protection", "discrimination", "equal before the law"]},
        13: {"title": "Freedom from Arbitrary Arrest",
             "keywords": ["arbitrary arrest", "unlawful detention", "illegal arrest", "habeas corpus"]},
        14: {"title": "Freedom of Speech and Assembly",
             "keywords": ["freedom of speech", "freedom of expression", "freedom of assembly"]},
        17: {"title": "Remedy for Infringement of Fundamental Rights",
             "keywords": ["fundamental rights", "article 17", "infringement of rights"]},
        126: {"title": "Jurisdiction of Supreme Court for Fundamental Rights",
              "keywords": ["supreme court jurisdiction", "article 126", "fundamental rights application"]},
    }

    rights = []
    text_lower = text.lower()
    for art_num, info in ARTICLE_MAP.items():
        for kw in info["keywords"]:
            if kw in text_lower:
                # Find a matched excerpt
                idx = text_lower.find(kw)
                excerpt = text[max(0, idx-80):idx+120].strip().replace('\n', ' ')
                rights.append({
                    "article_number": art_num,
                    "matched_text": excerpt,
                    "explanation_en": info["title"],
                })
                break

    # ── Citations ──────────────────────────────────────────────────────────
    cite_pattern = r'\b(?:\d{1,3}\s+(?:NLR|SLR|SLLR)\s+\d{1,4}|\(\d{4}\)\s+\d+\s+(?:NLR|SLR)\s+\d+)'
    citations = list(set(re.findall(cite_pattern, text[:6000], re.IGNORECASE)))[:10]

    # ── Entity count (simple) ──────────────────────────────────────────────
    entities_count = len(re.findall(
        r'\b(?:Supreme Court|Court of Appeal|High Court|District Court|Privy Council)\b',
        text, re.IGNORECASE
    ))

    return {
        "document_id": doc.id,
        "file_name": doc.file_name,
        "court": doc.court,
        "year": doc.year,
        "case_number": doc.case_number,
        "uploaded_at": str(doc.uploaded_at) if hasattr(doc, "uploaded_at") else None,
        "file_path": doc.file_path,
        "text": {
            "cleaned": text[:20000],   # first 20k chars for display
            "full_length": len(text),
        },
        "metadata": {
            "has_embedding": False,
            "embedding_dimension": 0,
        },
        "analysis": {
            "rights_detected": len(rights),
            "citations_found": len(citations),
            "entities_extracted": entities_count,
        },
        "rights": rights,
        "citations": citations,
        "entities": {},
    }


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


@router.get("/constitutional/{document_id}")
def get_constitutional_overview(
    document_id: int,
    db: Session = Depends(get_db),
):
    """
    Unified constitutional/fundamental-rights endpoint for the Constitutional tab.

    Aggregates:
      - stored fundamental rights detections (DetectedRight rows),
      - fresh constitutional article detections from ConstitutionalArticleDetector,
      - constitutional RAG analysis (ConstitutionalRAGModule + LLM).
    """
    # Load document and text
    doc = db.query(LegalDocument).filter_by(id=document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    full_text = doc.cleaned_text or doc.raw_text or ""
    if not full_text.strip():
        raise HTTPException(status_code=400, detail="Document has no text content")

    # Fundamental rights from DB (created by FundamentalRightsDetector / pipeline)
    from ..models.rights_model import DetectedRight
    from ..services.constitutional_article_detector import ConstitutionalArticleDetector

    const_detector = ConstitutionalArticleDetector(semantic_threshold=0.70)
    rights_rows = db.query(DetectedRight).filter_by(document_id=document_id).all()

    # Deduplicate fundamental rights by (article_number, matched_text) so we don't show
    # the same FR card multiple times (e.g. keyword + semantic paths both hitting Art. 13).
    fr_by_key: dict[tuple[str, str], dict] = {}
    for r in rights_rows:
        article_str = str(r.article_number)
        matched = (r.matched_text or "").strip()
        key = (article_str, matched)
        if key in fr_by_key:
            continue

        provision_list = const_detector.get_provision_from_processed_constitutions(article_str)
        provision_texts = [p["text"] for p in provision_list] if provision_list else []

        # Avoid showing the exact same FR text twice: if explanation_en is identical
        # (ignoring whitespace) to the provision text we already attach, drop it.
        explanation_en = r.explanation_en
        if explanation_en and provision_texts:
            norm_expl = " ".join(str(explanation_en).split())
            for t in provision_texts:
                if norm_expl == " ".join(str(t).split()):
                    explanation_en = None
                    break

        fr_by_key[key] = {
            "id": r.id,
            "article_number": article_str,
            "matched_text": matched,
            "explanation_en": explanation_en,
            "explanation_si": r.explanation_si,
            "explanation_ta": r.explanation_ta,
            "constitution_provision_text": provision_texts,
            "constitution_source_documents": list({p["document"] for p in provision_list}) if provision_list else [],
        }

    fundamental_rights = list(fr_by_key.values())

    # Constitutional provisions: only those matching processed_constitutions.json (100% accurate)
    try:
        const_provisions = const_detector.detect(
            full_text,
            only_from_processed_constitutions=True,
        )
        constitutional_articles = [
            {
                "article_number": p.get("article"),
                "article_title": p.get("article_title"),
                "matched_text": p.get("matched_text"),
                "context": p.get("context"),
                "method": p.get("method"),
                "score": p.get("score"),
                "explanation": p.get("explanation"),
                "constitution_provision_text": p.get("constitution_provision_text") or [],
                "constitution_source_documents": p.get("constitution_source_documents") or [],
            }
            for p in const_provisions
        ]
    except Exception as e:
        print(f"Constitutional article detection failed in overview endpoint: {e}")
        constitutional_articles = []

    # Constitutional RAG + LLM analysis (mirror rag_v2_routes.rag_constitutional)
    from app.services.constitutional_rag_module import get_constitutional_rag
    from app.services.llm_generation_service import get_llm_service
    from app.models.document_chunk_model import DocumentChunk
    import re

    const_rag = get_constitutional_rag()

    # Match against curated FR corpus using head + tail of judgment
    search_text = full_text[:8000]
    matched_articles = const_rag.match_articles(search_text, top_k=8)
    if len(full_text) > 10000:
        tail_matches = const_rag.match_articles(full_text[-4000:], top_k=5)
        seen = {m["article_number"] for m in matched_articles}
        for m in tail_matches:
            if m["article_number"] not in seen:
                matched_articles.append(m)
                seen.add(m["article_number"])

    matched_articles = sorted(matched_articles, key=lambda x: x["similarity"], reverse=True)

    # Small chunk sample for LLM grounding
    db_chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .limit(6)
        .all()
    )
    chunks_dicts = [
        {
            "text": c.text,
            "section_type": getattr(c, "section_type", ""),
            "document_id": document_id,
        }
        for c in db_chunks
        if c.text
    ]

    # Textual cues that the judgment actually discusses constitutional issues
    has_textual_const = bool(fundamental_rights) or bool(
        re.search(
            r'fundamental rights?|article\s+1[0-8]|article\s+126|habeas corpus'
            r'|freedom of speech|freedom of assembly|right to equality|arbitrary arrest',
            full_text[:6000],
            re.IGNORECASE,
        )
    )

    # We only treat the case as having constitutional issues when the text itself
    # mentions FR/constitutional concepts or when explicit constitutional articles
    # have been detected (not just semantic FR matches from RAG).
    has_const_issues = has_textual_const or bool(constitutional_articles)

    NO_CONSTITUTIONAL_MESSAGE = (
        "No constitutional provisions or fundamental rights were identified in this document. "
        "This case does not engage fundamental rights (Articles 10–18) or other constitutional "
        "provisions in our corpus."
    )
    if not has_const_issues:
        constitutional_analysis = NO_CONSTITUTIONAL_MESSAGE
        # Matched articles from the FR corpus are not surfaced when there is no
        # textual constitutional hook in the judgment.
        matched_articles = []
    else:
        try:
            llm = get_llm_service()
            constitutional_analysis = llm.generate_constitutional_analysis(chunks_dicts, matched_articles)
            if not constitutional_analysis or len(constitutional_analysis.strip()) < 40:
                constitutional_analysis = NO_CONSTITUTIONAL_MESSAGE
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower() or "RESOURCE_EXHAUSTED" in str(e):
                constitutional_analysis = (
                    "Constitutional analysis is temporarily unavailable due to high demand. "
                    "Please try again in a few minutes. The matched provisions and fundamental rights below are still available."
                )
            else:
                constitutional_analysis = "Analysis could not be generated at this time. Please try again later. Matched provisions are still shown below."
            import traceback
            traceback.print_exc()

    return {
        "document_id": document_id,
        "file_name": doc.file_name,
        "court": doc.court,
        "year": doc.year,
        "has_constitutional_issues": has_const_issues,
        "fundamental_rights": fundamental_rights,
        "constitutional_articles": constitutional_articles,
        "constitutional_analysis": constitutional_analysis,
        "matched_articles": matched_articles,
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
        if not DocumentProcessor.is_sri_lanka_legal_document(doc.cleaned_text, file_name=doc.file_name):
            raise HTTPException(
                status_code=400, 
                detail="This document does not appear to be a Sri Lankan legal case (SLR or NLR). Please upload valid Sri Lankan Law Reports (SLR) or New Law Reports (NLR) judgments. If it is a valid case, try adding 'NLR' or 'SLR' to the file name."
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
        if len(text.strip()) < 200:
            raise HTTPException(
                400,
                "Document has too little text for a reliable summary. "
                "The PDF may be image-only or poorly extracted. Try re-uploading a text-based PDF or ensure OCR is enabled."
            )

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
        from ..services.llm_generation_service import get_llm_service
        llm = get_llm_service()
        summary_source = "extractive"  # overwritten when LLM/flan_t5 path is used
        if llm._mode in ("openai", "google_genai"):
            # Generate or retrieve the comprehensive analysis for this document
            metadata = {
                "court": doc.court or "Unknown Court",
                "year": doc.year or "Unknown Year",
                "case_name": doc.file_name or "Unknown Case"
            }
            
            # This calls the LLM, populates the structured JSON, and catches errors
            master = llm.generate_full_analysis(document_id, text, metadata)

            if master.get("_source") not in ("regex", "regex_fallback"):
                summary_source = master.get("_source") or "llm"
                from ..services.advanced_summarizer import AdvancedLegalSummarizer
                summarizer = AdvancedLegalSummarizer()
                detailed_dict = master.get("detailed_summary") or {}
                # Accept LLM detailed whether it's a dict (structured) or a single string block
                has_llm_detailed = bool(
                    (isinstance(detailed_dict, str) and detailed_dict.strip())
                    or (
                        isinstance(detailed_dict, dict)
                        and any(
                            isinstance(v, (str, dict)) and str(v).strip()
                            for v in detailed_dict.values()
                        )
                    )
                )

                if has_llm_detailed:
                    detailed_text = _format_detailed(detailed_dict)
                    detailed_word_count = len(detailed_text.split())
                    detailed_source = "llm_detailed_summary"
                else:
                    # Use extractive summarizer so we get multiple sections (FACTS, ISSUES, REASONING, JUDGMENT) from document structure
                    detailed_fallback = summarizer.generate_detailed_summary(text, structured_content)
                    detailed_text = detailed_fallback.get("summary", "") or ""
                    detailed_word_count = int(detailed_fallback.get("word_count") or 0)
                    detailed_source = "extractive_fallback"

                section_specific_raw = master.get("section_summaries") or {}
                if not section_specific_raw:
                    # Fill section_specific from extractive (document structure)
                    sec_content = structured_content if structured_content else {"FULL_TEXT": text}
                    section_specific_raw = summarizer.generate_section_summaries(
                        sec_content,
                        executive_summary_text=str(master.get("executive_summary", "") or ""),
                    )
                    section_specific_raw = {k: v.get("summary", "") if isinstance(v, dict) else str(v) for k, v in section_specific_raw.items()}
                # Always merge in Case Identification, Facts, Legal Issue, etc. from case brief when missing
                # so export and UI keep the same structure (Section-by-Section, Case Identification, Structured Brief)
                try:
                    from ..services.case_brief_generator import CaseBriefGenerator
                    _brief = CaseBriefGenerator.generate_case_brief(text, {"court": doc.court or "Unknown", "year": doc.year or "Unknown", "case_name": doc.file_name or "Unknown Case"})
                    _sec = _section_specific_from_brief(_brief) if isinstance(_brief, dict) else {}
                    for k, v in (_sec or {}).items():
                        if v and (k not in section_specific_raw or not section_specific_raw.get(k)):
                            section_specific_raw[k] = v
                except Exception:
                    pass

                # If detailed is one block (no ** sections) but we have multiple section_specific, build detailed from sections
                if "**" not in detailed_text and len(section_specific_raw) > 1:
                    parts = []
                    for label in ("Case Identification", "Statutory Provisions", "Legal Issue", "Facts", "Procedural History", "Arguments", "Court's Reasoning", "Decision / Holding", "Rule of Law", "Key Takeaways"):
                        if section_specific_raw.get(label):
                            parts.append(f"**{label.upper()}:**\n{section_specific_raw[label]}")
                    if parts:
                        detailed_text = "\n\n".join(parts)
                        detailed_word_count = len(detailed_text.split())
                        detailed_source = "section_combined_fallback"

                summaries = {
                    "executive": {
                        "summary": master.get("executive_summary", ""),
                        "word_count": len(str(master.get("executive_summary", "")).split()),
                        "target_range": "150-200 words",
                        "type": "executive"
                    },
                    "detailed": {
                        "summary": detailed_text,
                        "word_count": detailed_word_count,
                        "target_range": "600-1000 words",
                        "type": "detailed",
                        "source": detailed_source,
                    },
                    "section_specific": {
                        k: {"summary": v, "word_count": len(str(v).split())}
                        for k, v in section_specific_raw.items() if v
                    },
                    "document_stats": {"sections_available": list(section_specific_raw.keys())}
                }

            else:
                # LLM failed (429/parse) or regex_fallback: use extractive summaries but prefer BART executive from master
                from ..services.advanced_summarizer import AdvancedLegalSummarizer
                summarizer = AdvancedLegalSummarizer()
                summaries = summarizer.generate_all_summaries(text, structured_content)
                summary_source = master.get("_source", "extractive")
                if master.get("executive_summary"):
                    exec_text = str(master.get("executive_summary", "")).strip()
                    if exec_text:
                        summaries["executive"] = {
                            "summary": exec_text,
                            "word_count": len(exec_text.split()),
                            "target_range": "150-200 words",
                            "type": "executive",
                        }
                if master.get("detailed_summary"):
                    det = master.get("detailed_summary")
                    if isinstance(det, dict) and any(str(v).strip() for v in det.values()):
                        detailed_text = _format_detailed(det)
                        if detailed_text.strip():
                            summaries["detailed"] = {
                                "summary": detailed_text,
                                "word_count": len(detailed_text.split()),
                                "target_range": "600-1000 words",
                                "type": "detailed",
                                "source": "extractive_fallback",
                            }
                    elif isinstance(det, str) and det.strip():
                        summaries["detailed"] = {
                            "summary": det.strip(),
                            "word_count": len(det.strip().split()),
                            "target_range": "600-1000 words",
                            "type": "detailed",
                            "source": "extractive_fallback",
                        }
        else:
            # No API key or not openai mode: fallback to TF-IDF extractive (multiple sections from document structure)
            from ..services.advanced_summarizer import AdvancedLegalSummarizer
            summarizer = AdvancedLegalSummarizer()
            summaries = summarizer.generate_all_summaries(text, structured_content)

        # Add plain language versions if requested
        if include_plain_language:
            converter = PlainLanguageConverter()
            plain_versions = converter.convert_summary_to_plain(summaries)
            # Generate glossary from full document text so we capture more terms (not just from summary)
            full_text = doc.cleaned_text or doc.raw_text or ""
            if full_text.strip():
                plain_versions["glossary"] = converter.generate_glossary(full_text)
            if not plain_versions.get("glossary") and getattr(llm, "_mode", None) == "openai" and getattr(llm, "_last_full_analysis", None):
                plain_versions["glossary"] = [
                    {"term": k, "definition": v.get("simplified", str(v)), "occurrences": v.get("occurrences", 1)}
                    for k, v in llm._last_full_analysis.get("legal_terms_glossary", {}).items()
                ]
            if plain_versions.get("glossary"):
                _fix_glossary_appeal_terms(plain_versions["glossary"])
            summaries['plain_language'] = plain_versions
        
        return {
            "document_id": document_id,
            "file_name": doc.file_name,
            "summaries": summaries,
            "structure_aware": structured_content is not None,
            "summary_source": summary_source,
            "using_fallback": summary_source in ("extractive", "regex_fallback"),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Multi-level summarization error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Summarization failed: {str(e)}")


@router.get("/summaries/{document_id}")
def get_overview_summaries(
    document_id: int,
    include_plain_language: bool = False,
    db: Session = Depends(get_db),
):
    """
    Canonical Overview tab endpoint.

    Wraps generate_multi_level_summary so that the frontend can call
    /api/analysis/summaries/{document_id} and receive:
      - executive summary,
      - detailed summary,
      - optional section-specific + plain language variants.
    """
    return generate_multi_level_summary(
        document_id=document_id,
        include_plain_language=include_plain_language,
        db=db,
    )


@router.get("/summarize/section-wise/{document_id}")
def generate_section_wise_summary(document_id: int, db: Session = Depends(get_db)):
    """
    Generate a structured section-wise summary using conceptual headings:
    Case Identification, Statutory Provisions, Legal Issue, Facts,
    Procedural History, Arguments, Court’s Reasoning, Decision / Holding,
    Rule of Law, Key Takeaways.

    If a field is not present in the judgment, it is explicitly set to
    "Not mentioned in the case." (or a list containing that string for
    key_takeaways).
    """
    try:
        # Get document
        doc = db.query(LegalDocument).filter_by(id=document_id).first()
        if not doc:
            raise HTTPException(404, "Document not found")

        text = doc.cleaned_text or doc.raw_text
        if not text:
            raise HTTPException(400, "Document has no text content")

        from ..services.llm_generation_service import get_llm_service
        llm = get_llm_service()

        metadata = {
            "court": doc.court or "Unknown Court",
            "year": doc.year or "Unknown Year",
            "case_name": doc.file_name or "Unknown Case",
            "citation": doc.case_number or "",
        }

        master = llm.generate_full_analysis(document_id, text, metadata)

        # If LLM analysis is available, prefer section_summaries from it
        section_wise: dict
        if master.get("_source") not in ("regex", "regex_fallback") and isinstance(
            master.get("section_summaries"), dict
        ):
            ss = master.get("section_summaries") or {}

            # LLM section_summaries keys expected as conceptual headings
            case_identification = _normalize_or_default(ss.get("Case Identification"))
            statutory_provisions = _normalize_or_default(
                ss.get("Statutory Provisions")
            )
            legal_issue = _normalize_or_default(ss.get("Legal Issue"))
            facts = _normalize_or_default(ss.get("Facts"))
            procedural_history = _normalize_or_default(ss.get("Procedural History"))
            arguments = _normalize_or_default(ss.get("Arguments"))
            courts_reasoning = _normalize_or_default(ss.get("Court’s Reasoning"))
            decision_holding = _normalize_or_default(ss.get("Decision / Holding"))
            rule_of_law = _normalize_or_default(ss.get("Rule of Law"))

            kt_raw = ss.get("Key Takeaways")
            key_takeaways_list: list[str]
            if isinstance(kt_raw, list):
                key_takeaways_list = [
                    s.strip() for s in kt_raw if isinstance(s, str) and s.strip()
                ] or ["Not mentioned in the case."]
            else:
                kt_text = (kt_raw or "").strip()
                if not kt_text:
                    key_takeaways_list = ["Not mentioned in the case."]
                else:
                    # Split into bullets by line or sentence
                    parts = [
                        p.strip("- ").strip()
                        for p in kt_text.splitlines()
                        if p.strip()
                    ]
                    if not parts:
                        parts = [kt_text]
                    key_takeaways_list = parts

            section_wise = {
                "case_identification": case_identification,
                "statutory_provisions": statutory_provisions,
                "legal_issue": legal_issue,
                "facts": facts,
                "procedural_history": procedural_history,
                "arguments": arguments,
                "courts_reasoning": courts_reasoning,
                "decision_holding": decision_holding,
                "rule_of_law": rule_of_law,
                "key_takeaways": key_takeaways_list,
            }
        else:
            # Fallback: build section-wise summary from regex-based case brief
            from ..services.case_brief_generator import CaseBriefGenerator

            brief = CaseBriefGenerator.generate_case_brief(text, metadata)
            ci = brief.get("case_identification", {}) or {}
            case_identification = _normalize_or_default(
                f"{ci.get('case_name', '')} | Court: {ci.get('court', '')} | Year: {ci.get('year', '')} | Citation: {ci.get('citation', '')}"
            )

            proc = brief.get("procedural_principles", {}) or {}
            statutory_list = proc.get("statutory_provisions", []) or []
            statutory_provisions = (
                "; ".join(statutory_list) if statutory_list else "Not mentioned in the case."
            )

            issues_list = brief.get("issues", []) or []
            legal_issue = (
                " ".join(issues_list) if any(issues_list) else "Not mentioned in the case."
            )

            facts = _normalize_or_default(brief.get("facts"))
            # Procedural history is not explicitly modelled in brief; fall back to note
            procedural_history = "Not mentioned in the case."

            arguments = "Not mentioned in the case."
            courts_reasoning = _normalize_or_default(brief.get("reasoning"))
            decision_holding = _normalize_or_default(brief.get("holding"))

            ratio_list = brief.get("ratio_decidendi", []) or []
            rule_of_law = (
                " ".join(ratio_list) if any(ratio_list) else "Not mentioned in the case."
            )

            kt_list = brief.get("key_takeaways", []) or []
            key_takeaways_list = (
                [s for s in kt_list if isinstance(s, str) and s.strip()]
                or ["Not mentioned in the case."]
            )

            section_wise = {
                "case_identification": case_identification,
                "statutory_provisions": statutory_provisions,
                "legal_issue": legal_issue,
                "facts": facts,
                "procedural_history": procedural_history,
                "arguments": arguments,
                "courts_reasoning": courts_reasoning,
                "decision_holding": decision_holding,
                "rule_of_law": rule_of_law,
                "key_takeaways": key_takeaways_list,
            }

        return {
            "document_id": document_id,
            "file_name": doc.file_name,
            "section_wise_summary": section_wise,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Section-wise summary error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Section-wise summary failed: {str(e)}")


def _format_detailed(detailed: dict) -> str:
    """Helper to format detailed summary dictionary into text blocks.
    Handles both old schema (issues/holding/reasoning) and new schema
    (procedural_posture/courts_analysis/decision/arguments).
    If the LLM returns a single string instead of a dict, return it as-is.
    """
    if not detailed:
        return ""
    if isinstance(detailed, str):
        return detailed.strip()
    parts = []
    if detailed.get("facts"):             parts.append(f"**FACTS:**\n{detailed['facts']}")
    issues_val = detailed.get("issues")
    if issues_val:
        issues_str = "\n".join(issues_val) if isinstance(issues_val, list) else str(issues_val)
        if issues_str.strip(): parts.append(f"**ISSUES:**\n{issues_str}")
    if detailed.get("procedural_posture"): parts.append(f"**PROCEDURAL POSTURE:**\n{detailed['procedural_posture']}")
    args = detailed.get("arguments", {})
    if isinstance(args, dict):
        if args.get("petitioner"): parts.append(f"**PETITIONER'S ARGUMENTS:**\n{args['petitioner']}")
        if args.get("respondent"): parts.append(f"**RESPONDENT'S ARGUMENTS:**\n{args['respondent']}")
    if detailed.get("courts_analysis"): parts.append(f"**COURT'S ANALYSIS:**\n{detailed['courts_analysis']}")
    if detailed.get("holding"):          parts.append(f"**HOLDING:**\n{detailed['holding']}")
    if detailed.get("reasoning"):        parts.append(f"**REASONING:**\n{detailed['reasoning']}")
    if detailed.get("decision"):         parts.append(f"**DECISION:**\n{detailed['decision']}")
    return "\n\n".join(parts)


def _detailed_dict_from_brief(brief: dict) -> dict:
    """Build the detailed-summary dict expected by _format_detailed from a case brief."""
    if not brief: return {}
    facts = brief.get("facts") or ""
    if isinstance(facts, str) and facts.startswith("Facts:"):
        facts = facts[6:].strip()
    proc = brief.get("procedural_principles") or {}
    proc_rules = (proc.get("procedural_rules") or []) if isinstance(proc, dict) else []
    procedural_posture = " ".join(str(r) for r in proc_rules) if proc_rules else ""
    issues = brief.get("issues")
    if isinstance(issues, list):
        issues = [str(i).strip() for i in issues if str(i).strip()]
    reasoning = brief.get("reasoning") or ""
    if isinstance(reasoning, str) and reasoning.startswith("Reasoning:"):
        reasoning = reasoning[10:].strip()
    holding = brief.get("holding") or ""
    final_order = brief.get("final_order") or ""
    decision = holding if holding else final_order
    if isinstance(decision, str) and (decision.startswith("Holding") or decision.startswith("Final")):
        decision = re.sub(r"^(?:Holding/Decision|Final Order):\s*", "", decision, flags=re.IGNORECASE).strip()
    issues_out = brief.get("issues")
    if isinstance(issues_out, list):
        issues_out = [str(i).strip() for i in issues_out if str(i).strip()]
    return {
        "facts": facts,
        "issues": issues_out or None,
        "procedural_posture": procedural_posture or None,
        "arguments": {},
        "courts_analysis": reasoning or None,
        "decision": decision or None,
    }


def _section_specific_from_brief(brief: dict) -> dict:
    """Build section_specific (phase-by-phase) from case brief for Section-by-Section Analysis."""
    if not brief: return {}
    out = {}
    cid = brief.get("case_identification") or {}
    if not isinstance(cid, dict):
        cid = {}
    case_id = ", ".join(filter(None, [
        cid.get("case_name"), cid.get("court"), str(cid.get("year") or ""), cid.get("citation")
    ]))
    if case_id:
        out["Case Identification"] = case_id
    proc = brief.get("procedural_principles") or {}
    if isinstance(proc, dict):
        provisions = proc.get("statutory_provisions") or []
        if provisions:
            out["Statutory Provisions"] = "; ".join(str(p) for p in provisions)
        rules = proc.get("procedural_rules") or []
        if rules:
            out["Procedural History"] = " ".join(str(r) for r in rules)
    # If proc was a dict with only 'note', use it as procedural history
    if "Procedural History" not in out and isinstance(proc, dict) and proc.get("note"):
        out["Procedural History"] = str(proc.get("note"))
    issues = brief.get("issues")
    if issues:
        issues_str = "\n".join(f"• {i}" for i in (issues if isinstance(issues, list) else [issues]))
        out["Legal Issue"] = issues_str
    facts = brief.get("facts")
    if facts:
        out["Facts"] = facts[6:].strip() if isinstance(facts, str) and facts.startswith("Facts:") else str(facts)
    reasoning = brief.get("reasoning")
    if reasoning:
        out["Court's Reasoning"] = reasoning[10:].strip() if isinstance(reasoning, str) and reasoning.startswith("Reasoning:") else str(reasoning)
    holding = brief.get("holding")
    if holding:
        out["Decision / Holding"] = re.sub(r"^Holding/Decision:\s*", "", str(holding), flags=re.IGNORECASE).strip()
    final = brief.get("final_order")
    if final:
        out["Decision / Holding"] = out.get("Decision / Holding") or re.sub(r"^Final Order:\s*", "", str(final), flags=re.IGNORECASE).strip()
    ratio = brief.get("ratio_decidendi") or []
    if ratio:
        out["Rule of Law"] = "\n".join(f"• {r}" for r in (ratio if isinstance(ratio, list) else [ratio]))
    return {k: v for k, v in out.items() if v}

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
        
        from ..services.llm_generation_service import get_llm_service
        llm = get_llm_service()
        
        if llm._mode in ("openai", "google_genai"):
            metadata = {
                "court": doc.court or "Unknown Court",
                "year": doc.year or "Unknown Year",
                "case_name": doc.file_name or "Unknown Case"
            }
            master = llm.generate_full_analysis(document_id, text, metadata)
            if master.get("_source") not in ("regex", "regex_fallback"):
                exec_text = str(master.get("executive_summary", "") or "")
                return {
                    "document_id": document_id,
                    "file_name": doc.file_name,
                    "summary": exec_text,
                    "word_count": len(exec_text.split()),
                    "target_range": "150-200 words",
                    "type": "executive"
                }

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
        except Exception:
            pass

        from ..services.llm_generation_service import get_llm_service
        llm = get_llm_service()
        
        if llm._mode in ("openai", "google_genai"):
            metadata = {
                "court": doc.court or "Unknown Court",
                "year": doc.year or "Unknown Year",
                "case_name": doc.file_name or "Unknown Case"
            }
            master = llm.generate_full_analysis(document_id, text, metadata)
            if master.get("_source") not in ("regex", "regex_fallback"):
                detailed_dict = master.get("detailed_summary") or {}
                has_llm_detailed = bool(
                    isinstance(detailed_dict, dict)
                    and any(
                        isinstance(v, (str, dict)) and str(v).strip()
                        for v in detailed_dict.values()
                    )
                )

                if has_llm_detailed:
                    formatted = _format_detailed(detailed_dict)
                    word_count = len(formatted.split())
                    source = "llm_detailed_summary"
                else:
                    summarizer = AdvancedLegalSummarizer()
                    summary_fallback = summarizer.generate_detailed_summary(text, structured_content)
                    formatted = summary_fallback.get("summary", "") or ""
                    word_count = int(summary_fallback.get("word_count") or 0)
                    source = "extractive_fallback"

                return {
                    "document_id": document_id,
                    "file_name": doc.file_name,
                    "summary": formatted,
                    "word_count": word_count,
                    "target_range": "600-1000 words",
                    "type": "detailed"
                }

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
    Find similar cases from the official NLR/SLR corpus database (combined_legal_cases.json).
    NEVER returns user-uploaded documents — only the historical legal corpus.
    """
    try:
        # Verify document exists
        doc = db.query(LegalDocument).filter_by(id=document_id).first()
        if not doc:
            raise HTTPException(404, f"Document {document_id} not found")

        full_text = doc.cleaned_text or doc.raw_text or ""
        if not full_text.strip():
            raise HTTPException(400, "Document has no text content — cannot find similar cases")

        # Use a focused slice so scoring reflects this document's subject (headnote + facts),
        # not the full length which dilutes with generic legal language and yields same top cases
        head = full_text[:8000]
        tail = full_text[-3000:] if len(full_text) > 12000 else ""
        query_text = (head + " " + tail).strip()

        # ── Use LegalDatabaseContextService (corpus-only, never user-uploaded docs) ──
        from ..services.legal_database_context_service import (
            get_legal_db_context,
            COMBINED_CASES_PATH,
        )
        from ..utils.corpus_drive_map import (
            drive_meta_resolve,
            corpus_drive_map_present,
            iter_drive_corpus_pdf_entries,
        )
        import re

        db_ctx = get_legal_db_context()
        all_cases = db_ctx._cases  # list of case dicts from combined_legal_cases.json
        corpus_json_found = COMBINED_CASES_PATH.is_file()
        name_tokens = db_ctx.legal_filename_tokens(doc.file_name or "")

        # Score each corpus case against the uploaded document
        scored = []
        for case in all_cases:
            primary = db_ctx._score_case_relevance(case, query_text)
            fb = db_ctx._fallback_lexical_overlap(case, query_text)
            name_h = db_ctx._filename_token_overlap_score(case, name_tokens)
            score = max(primary, fb, name_h)
            if score > 0:
                scored.append((score, case))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # Normalize scores to 0-100 range
        max_score = scored[0][0] if scored else 1.0

        # Normalize file name for "same document" check (strip trailing .pdf variants, collapse dots)
        def _norm_fname(name):
            if not name:
                return ""
            s = name.strip().lower()
            while s.endswith(".pdf"):
                s = s[:-4]
            s = re.sub(r"\.+", ".", s).strip(". ")
            return s

        source_norm = _norm_fname(doc.file_name or "")

        # Build result list (exclude source doc; dedupe by file_name/title)
        results = []
        seen_keys = set()
        for raw_score, case in scored[:top_k * 5]:  # over-fetch for filtering/dedup
            # Do NOT gate on min_sim_raw * max_score: one outlier score makes the floor huge and drops every other row.
            if raw_score <= 0:
                continue

            file_name = case.get("file_name", "Unknown")
            # Don't show the same document as a "related" case
            if _norm_fname(file_name) == source_norm:
                continue

            full_text = (case.get("cleaned_text") or case.get("raw_text") or "")[:4000]

            case_name = db_ctx._extract_case_name_from_text(full_text) or file_name
            citation  = db_ctx._extract_citation(full_text, file_name)

            # Infer court
            t_upper = full_text[:3000].upper()
            if "SUPREME COURT" in t_upper:      court = "Supreme Court"
            elif "COURT OF APPEAL" in t_upper:   court = "Court of Appeal"
            elif "PRIVY COUNCIL" in t_upper:     court = "Privy Council"
            elif "HIGH COURT" in t_upper:        court = "High Court"
            else:                                court = "Supreme Court"

            # Infer year
            year_m = re.search(r'\b(19[0-9]{2}|20[0-2][0-9])\b', full_text[:2000])
            year = int(year_m.group(1)) if year_m else None

            similarity_pct = round((raw_score / max_score) * 100, 1)

            # Dedupe: same file_name (same PDF must not appear twice)
            if file_name.strip().lower() in seen_keys:
                continue
            seen_keys.add(file_name.strip().lower())

            drive_meta = drive_meta_resolve(file_name)
            row = {
                "document_id": -1,         # corpus cases have no DB id
                "file_name":   file_name,
                "title":       case_name,
                "citation":    citation,
                "court":       court,
                "year":        year,
                "similarity_score":  similarity_pct,
                "weighted_score":    similarity_pct,
                "binding":     court in ("Supreme Court", "Privy Council"),
                "court_weight": 100.0 if court in ("Supreme Court", "Privy Council") else 70.0,
                "recency":     None,
                "source":      "NLR/SLR Corpus Database",
            }
            if drive_meta:
                row["drive_file_id"] = drive_meta.get("file_id") or drive_meta.get("id")
                row["drive_view_url"] = drive_meta.get("view_url")
            results.append(row)

            if len(results) >= top_k:
                break

        # ── Fallback: corpus PDFs live only on Google Drive (no combined_legal_cases.json) ──
        drive_map_present = corpus_drive_map_present()
        drive_catalog: list = []
        drive_fallback_used = False
        if drive_map_present:
            drive_catalog = iter_drive_corpus_pdf_entries()
        if len(results) < top_k and drive_map_present and drive_catalog:
            drive_scored = []
            for ent in drive_catalog:
                fn = ent.get("file_name") or ""
                blob = (fn.replace("_", " ").replace("-", " ")).lower()
                pseudo = {"file_name": fn, "cleaned_text": blob, "raw_text": blob}
                sc = max(
                    db_ctx._score_case_relevance(pseudo, query_text),
                    db_ctx._fallback_lexical_overlap(pseudo, query_text),
                    db_ctx._filename_token_overlap_score(pseudo, name_tokens),
                )
                if sc > 0:
                    drive_scored.append((sc, ent))
            drive_scored.sort(key=lambda x: x[0], reverse=True)
            if drive_scored:
                drive_fallback_used = True
                max_d = drive_scored[0][0] if drive_scored else 1.0
                for sc, ent in drive_scored:
                    if len(results) >= top_k:
                        break
                    fn = ent.get("file_name", "")
                    if not fn or _norm_fname(fn) == source_norm:
                        continue
                    kl = fn.strip().lower()
                    if kl in seen_keys:
                        continue
                    seen_keys.add(kl)
                    rel = ent.get("rel_path") or ""
                    year_m2 = re.search(r"/(\d{4})/", rel)
                    year2 = int(year_m2.group(1)) if year_m2 else None
                    title = fn.replace("_", " ")
                    sim2 = round((sc / max_d) * 100, 1) if max_d > 0 else 0.0
                    dm = ent.get("drive_meta") or {}
                    row = {
                        "document_id": -1,
                        "file_name": fn,
                        "title": title,
                        "citation": None,
                        "court": "Supreme Court",
                        "year": year2,
                        "similarity_score": sim2,
                        "weighted_score": sim2,
                        "binding": True,
                        "court_weight": 100.0,
                        "recency": None,
                        "source": "NLR/SLR corpus (Google Drive index, filename match)",
                    }
                    fid = dm.get("file_id") or dm.get("id")
                    if fid:
                        row["drive_file_id"] = fid
                    if dm.get("view_url"):
                        row["drive_view_url"] = dm.get("view_url")
                    elif fid:
                        row["drive_view_url"] = f"https://drive.google.com/file/d/{fid}/view"
                    results.append(row)

        src_label = "Official NLR/SLR Corpus Database (combined_legal_cases.json)"
        if drive_fallback_used and not all_cases:
            src_label = "NLR/SLR corpus via Google Drive map (filename / keyword match; deploy combined_legal_cases.json for full-text ranking)"
        elif drive_fallback_used:
            src_label = "NLR/SLR Corpus (combined JSON + Google Drive supplement)"

        return {
            'document_id': document_id,
            'source_document': {
                'id':  doc.id,
                'title': doc.file_name,
                'court': doc.court,
                'year':  doc.year,
                'case_number': doc.case_number
            },
            'similar_cases_count': len(results),
            'similar_cases': results,
            'source': src_label,
            'corpus_json_found': corpus_json_found,
            'corpus_index_size': len(all_cases),
            'corpus_drive_map_present': drive_map_present,
            'corpus_drive_catalog_size': len(drive_catalog),
            'corpus_drive_fallback_used': drive_fallback_used,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error finding similar cases: {str(e)}")
        import traceback; traceback.print_exc()
        raise HTTPException(500, f"Failed to find similar cases: {str(e)}")


@router.get("/related-cases/{document_id}")
def get_related_cases(
    document_id: int,
    top_k: int = 5,
    db: Session = Depends(get_db),
):
    """
    Unified Related Cases endpoint for the Related Cases tab.

    Aggregates three signals:
      - NLR/SLR corpus-based similar cases (combined_legal_cases.json),
      - document-level embedding precedents (PrecedentMatcher),
      - chunk-level RAG precedents (PrecedentRAGEngine).
    """
    # Ensure source document exists
    doc = db.query(LegalDocument).filter_by(id=document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    # 1) Corpus-based similar cases (reuse existing endpoint logic)
    corpus_payload = get_similar_cases(
        document_id=document_id,
        top_k=top_k,
        min_similarity=0.3,
        db=db,
    )
    corpus_cases = corpus_payload.get("similar_cases", []) if isinstance(corpus_payload, dict) else []

    # 2) Document-level embedding precedents
    matcher = get_precedent_matcher()
    doc_embedding_cases = matcher.find_similar_cases(
        document_id=document_id,
        top_k=top_k,
        db=db,
    )

    # 3) Chunk-level RAG precedents
    from ..services.precedent_rag_engine import get_precedent_rag

    precedent_engine = get_precedent_rag()
    rag_cases = precedent_engine.find_similar_cases(
        document_id=document_id,
        source_court=doc.court,
        source_year=doc.year,
        top_k=top_k,
    )

    related_cases = []

    # Normalize corpus cases
    for c in corpus_cases:
        related_cases.append({
            "source_type": "nlr_slr_corpus",
            "document_id": None,
            "file_name": c.get("file_name"),
            "case_name": c.get("title") or c.get("file_name"),
            "citation": c.get("citation"),
            "court": c.get("court"),
            "year": c.get("year"),
            "similarity_score": c.get("similarity_score"),
            "weighted_score": c.get("weighted_score"),
            "binding": c.get("binding"),
            "authority_type": "Binding" if c.get("binding") else "Persuasive",
            "why_related": (
                "High overlap in legal topics and citation patterns in the NLR/SLR corpus "
                f"(score ~{c.get('similarity_score')}%)."
            ),
        })

    # Normalize document-level embedding precedents
    for c in doc_embedding_cases:
        related_cases.append({
            "source_type": "doc_embedding",
            "document_id": c.get("document_id"),
            "file_name": c.get("file_name"),
            "case_name": c.get("title") or c.get("file_name"),
            "citation": None,
            "court": c.get("court"),
            "year": c.get("year"),
            "similarity_score": c.get("similarity_score"),
            "weighted_score": c.get("weighted_score"),
            "binding": c.get("binding"),
            "authority_type": "Binding" if c.get("binding") else "Persuasive",
            "why_related": (
                "Overall judgment text and metadata are semantically similar, "
                f"with court hierarchy and recency taken into account (weighted score {c.get('weighted_score')}%)."
            ),
            "court_weight": c.get("court_weight"),
            "recency": c.get("recency"),
        })

    # Normalize chunk-level RAG precedents
    for c in rag_cases:
        sections = c.get("matching_sections") or []
        shared_articles = c.get("shared_constitutional_articles") or []
        reason_bits = []
        if sections:
            reason_bits.append(f"overlapping key sections: {', '.join(sections)}")
        if shared_articles:
            reason_bits.append(f"shared constitutional articles: {', '.join(shared_articles)}")
        why = "Chunk-level similarity in " + "; ".join(reason_bits) if reason_bits else \
            "Chunk-level similarity across issues, reasoning and judgment."

        related_cases.append({
            "source_type": "rag_chunks",
            "document_id": c.get("document_id"),
            "file_name": None,
            "case_name": c.get("case_name"),
            "citation": None,
            "court": c.get("court"),
            "year": c.get("year"),
            "similarity_score": c.get("similarity_score"),
            "weighted_score": c.get("weighted_score"),
            "binding": c.get("binding"),
            "authority_type": c.get("authority_type"),
            "why_related": why,
            "matching_sections": sections,
            "shared_constitutional_articles": shared_articles,
            "max_similarity": c.get("max_similarity"),
            "match_count": c.get("match_count"),
        })

    # Sort all related cases by weighted_score descending where available
    related_cases.sort(
        key=lambda x: (x.get("weighted_score") is not None, x.get("weighted_score") or 0),
        reverse=True,
    )

    # Dedupe: same case can appear from corpus + doc_embedding + RAG; keep highest score
    def _related_case_key(rc):
        name = (rc.get("case_name") or rc.get("title") or "").strip()
        fn = (rc.get("file_name") or "").strip()
        year = rc.get("year")
        # Normalize for comparison: lowercase, collapse spaces
        name_norm = re.sub(r"\s+", " ", name).lower() if name else ""
        fn_norm = fn.lower() if fn else ""
        return (fn_norm or name_norm, year)

    seen_related = set()
    deduped = []
    for rc in related_cases:
        k = _related_case_key(rc)
        if k in seen_related:
            continue
        seen_related.add(k)
        deduped.append(rc)

    return {
        "document_id": document_id,
        "source_document": {
            "id": doc.id,
            "title": doc.file_name,
            "court": doc.court,
            "year": doc.year,
            "case_number": doc.case_number,
        },
        "related_cases_count": len(deduped),
        "related_cases": deduped,
    }



@router.get("/corpus-case")
def get_corpus_case(file_name: str):
    """
    Retrieve a case from the NLR/SLR corpus (combined_legal_cases.json) by file name.
    Enables reading historical cases that are NOT stored in the SQLite database.
    Accepts .pdf.pdf and normalizes to match stored file_name (single .pdf).
    """
    try:
        from ..services.legal_database_context_service import get_legal_db_context
        from ..utils.corpus_drive_map import drive_meta_resolve
        import re

        db_ctx = get_legal_db_context()
        fn_lower = file_name.lower() if file_name else ""
        norm_lower = _normalize_corpus_filename(file_name or "").lower()

        def _matches(c):
            cfn = (c.get("file_name") or "").lower()
            return cfn == fn_lower or cfn == norm_lower

        match = next((c for c in db_ctx._cases if _matches(c)), None)
        if not match:
            dm = drive_meta_resolve(file_name or "")
            if dm:
                canonical_name = _normalize_corpus_filename(file_name) or file_name
                stem = (canonical_name.rsplit(".pdf", 1)[0] if canonical_name.lower().endswith(".pdf") else canonical_name).replace("_", " ")
                out = {
                    "file_name": canonical_name,
                    "case_name": stem,
                    "citation": None,
                    "court": "Supreme Court",
                    "year": None,
                    "source": "Google Drive corpus (full text not on server)",
                    "text": "",
                    "text_length": 0,
                    "drive_only": True,
                    "notice": (
                        "Full judgment text is not in combined_legal_cases.json on this server. "
                        "Use Open PDF / Google Drive to read or download the judgment."
                    ),
                }
                year_m = re.search(r"\b(19[0-9]{2}|20[0-2][0-9])\b", canonical_name)
                if year_m:
                    out["year"] = int(year_m.group(1))
                out["drive_file_id"] = dm.get("file_id") or dm.get("id")
                out["drive_view_url"] = dm.get("view_url")
                out["drive_download_url"] = dm.get("download_url")
                return out
            raise HTTPException(404, f"Corpus case '{file_name}' not found in NLR/SLR database")

        full_text = (match.get("cleaned_text") or match.get("raw_text") or "")
        case_name = db_ctx._extract_case_name_from_text(full_text[:3000]) or file_name
        citation  = db_ctx._extract_citation(full_text[:3000], file_name)

        t_upper = full_text[:3000].upper()
        if "SUPREME COURT" in t_upper:     court = "Supreme Court"
        elif "COURT OF APPEAL" in t_upper:  court = "Court of Appeal"
        elif "PRIVY COUNCIL" in t_upper:    court = "Privy Council"
        elif "HIGH COURT" in t_upper:       court = "High Court"
        else:                               court = "Supreme Court"

        year_m = re.search(r'\b(19[0-9]{2}|20[0-2][0-9])\b', full_text[:2000])
        if not year_m:
            year_m = re.search(r'\b(19[0-9]{2}|20[0-2][0-9])\b', file_name)
        year = int(year_m.group(1)) if year_m else None

        # Return canonical file_name from corpus so frontend/PDF link use same key (e.g. single .pdf)
        canonical_name = match.get("file_name") or _normalize_corpus_filename(file_name) or file_name
        drive_meta = drive_meta_resolve(canonical_name)
        out = {
            "file_name": canonical_name, "case_name": case_name,
            "citation": citation, "court": court, "year": year,
            "source": "NLR/SLR Corpus Database",
            "text": full_text[:50000],
            "text_length": len(full_text),
        }
        if drive_meta:
            out["drive_file_id"] = drive_meta.get("file_id") or drive_meta.get("id")
            out["drive_view_url"] = drive_meta.get("view_url")
            out["drive_download_url"] = drive_meta.get("download_url")
        return out
    except HTTPException:
        raise
    except Exception as e:
        print(f"Corpus case retrieval error: {str(e)}")
        raise HTTPException(500, f"Failed to retrieve corpus case: {str(e)}")


def _normalize_corpus_filename(file_name: str) -> str:
    """Prefer single .pdf: e.g. KAPURUHAMY-v.-HENDRICK-et-al.pdf.pdf -> KAPURUHAMY-v.-HENDRICK-et-al.pdf."""
    if not file_name or not file_name.lower().endswith(".pdf"):
        return file_name
    s = file_name
    while s.lower().endswith(".pdf.pdf"):
        s = s[:-4]  # strip trailing .pdf
    return s


def _get_corpus_pdf_path(file_name: str):
    """
    Resolve corpus PDF path from manifest (corpus_pdf_paths.json).
    For deployment: set CORPUS_PDF_DIR to the directory that contains the corpus PDFs
    (e.g. /app/data/raw_documents or a volume mount). If unset, uses base_dir from manifest.
    Tries exact file_name, then normalized (.pdf.pdf -> .pdf), then space-for-hyphen variant.
    """
    import os
    import json as _json
    from pathlib import Path

    backend_dir = Path(__file__).resolve().parent.parent
    project_root = backend_dir.parent
    data_processed = project_root / "data" / "processed"
    backend_processed = backend_dir / "data" / "processed"
    manifest_path = data_processed / "corpus_pdf_paths.json"
    if not manifest_path.exists():
        manifest_path = backend_processed / "corpus_pdf_paths.json"

    # If manifest is missing, fall back to empty mapping but still try filesystem search
    data = {}
    paths_map = {}
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = _json.load(f) or {}
            paths_map = data.get("paths") or {}
        except Exception:
            data = {}
            paths_map = {}
    candidates = [
        file_name,
        _normalize_corpus_filename(file_name),
        file_name.replace(" ", "_"),
        _normalize_corpus_filename(file_name).replace(" ", "_"),
    ]
    rel_path = None
    for c in candidates:
        if not c:
            continue
        rel_path = paths_map.get(c)
        if rel_path:
            break

    base = os.environ.get("CORPUS_PDF_DIR")
    if base:
        base_path = Path(base)
    else:
        base_path = Path(data.get("base_dir", str(project_root / "raw_documents")))

    # 1) If manifest has a relative path, try that first
    if rel_path:
        full = base_path / rel_path
        if full.is_file():
            return full

    # 2) Fallback: search the corpus directory tree for any of the candidate names
    #    This helps when manifest is stale or key normalisation doesn't match,
    #    but the PDF actually exists somewhere under CORPUS_PDF_DIR/raw_documents.
    try:
        for root, _dirs, files in os.walk(base_path):
            files_set = set(files)
            for c in candidates:
                if not c:
                    continue
                if c in files_set:
                    return Path(root) / c
    except Exception:
        # Best-effort search; if it fails we just return None.
        pass

    return None


@router.get("/corpus-pdf-view", response_class=HTMLResponse)
def get_corpus_pdf_view(file_name: str, title: str = ""):
    """
    Serve a minimal HTML page that embeds the corpus PDF so the browser tab shows the case name.
    Use this for 'Open PDF' links; the tab title will be the case name instead of 'corpus-pdf'.
    """
    if not file_name or ".." in file_name or "/" in file_name or "\\" in file_name:
        raise HTTPException(400, "Invalid file_name")
    # Ensure PDF exists
    path = _get_corpus_pdf_path(file_name)
    if not path:
        raise HTTPException(404, f"PDF for corpus case '{file_name}' not found.")
    display_title = (title or file_name or "Corpus case").strip()
    if display_title.lower().endswith(".pdf"):
        display_title = display_title[:-4]
    display_title = display_title.replace("-", " ").replace("_", " ").replace(".pdf", "")
    import html as html_module
    from urllib.parse import quote
    safe_title = html_module.escape(display_title)
    pdf_url = f"/api/analysis/corpus-pdf?file_name={quote(file_name)}"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{safe_title}</title>
  <style>body {{ margin: 0; font-family: system-ui; }} iframe {{ width: 100%; height: 100vh; border: none; }}</style>
</head>
<body>
  <iframe src="{pdf_url}" title="{safe_title}"></iframe>
</body>
</html>"""
    return HTMLResponse(html)


@router.get("/corpus-pdf")
def get_corpus_pdf(file_name: str):
    """
    Stream the PDF file for a corpus case by file_name.
    Requires corpus_pdf_paths.json (generated by build_combined_corpus_from_raw.py).
    For deployment: set env CORPUS_PDF_DIR to the path where corpus PDFs are stored.
    Response uses the case file name (e.g. ALLIS-v.-SIGERA.pdf) so the browser tab/save dialog shows it.
    """
    if not file_name or ".." in file_name or "/" in file_name or "\\" in file_name:
        raise HTTPException(400, "Invalid file_name")
    path = _get_corpus_pdf_path(file_name)
    if not path:
        raise HTTPException(404, f"PDF for corpus case '{file_name}' not found. Run the corpus build script and set CORPUS_PDF_DIR if deployed.")
    # Use case filename so browser shows e.g. "KAPURUHAMY-v.-HENDRICK-et-al.pdf" (never .pdf.pdf)
    safe_name = _normalize_corpus_filename(file_name.replace('"', "'").strip()) or "document.pdf"
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=safe_name,
        headers={
            "Content-Disposition": f'inline; filename="{safe_name}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


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
                "cleaned": doc.cleaned_text if doc.cleaned_text else None,
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
        from ..services.llm_generation_service import get_llm_service
        
        # Get document
        doc = db.query(LegalDocument).filter_by(id=document_id).first()
        if not doc:
            raise HTTPException(404, "Document not found")
        
        text = doc.cleaned_text or doc.raw_text
        if not text:
            raise HTTPException(400, "Document has no text content")
        if len(text.strip()) < 200:
            raise HTTPException(
                400,
                "Document has too little text for a reliable case brief. "
                "The PDF may be image-only or poorly extracted."
            )
        
        # Prepare metadata — derive case_name from filename so brief shows e.g. "ALLIS v. SIGERA"
        from ..services.case_brief_generator import case_name_from_filename
        file_name = doc.file_name or ""
        metadata = {
            "court": doc.court,
            "year": doc.year,
            "case_number": doc.case_number,
            "file_name": file_name,
            "case_name": case_name_from_filename(file_name) or None,
            "citation": doc.case_number or "",
        }
        
        # Generate case brief using OpenAI
        llm = get_llm_service()
        brief = llm.generate_case_brief(
            doc_id=document_id,
            text=text,
            metadata=metadata
        )
        
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
