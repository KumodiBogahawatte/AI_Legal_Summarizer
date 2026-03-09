"""
search_routes.py
Full-text search API endpoints using Elasticsearch.
Implements Section 1.5 from BUILD_ROADMAP.md.

Routes:
- POST /api/search/documents   — full-text search with filters
- GET  /api/search/suggest     — autocomplete suggestions
- POST /api/search/advanced    — advanced search with all filters
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.elasticsearch_service import get_elasticsearch_service

router = APIRouter(tags=["Search"])


# ─── Request Models ─────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    court: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    rights_articles: Optional[List[str]] = None
    judge: Optional[str] = None
    page: int = 1
    page_size: int = 10


# ─── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/documents")
def search_documents(request: SearchRequest):
    """
    Full-text search over Sri Lankan legal documents.

    Filters:
    - court: exact match ("Supreme Court", "Court of Appeal", "High Court")
    - year_from / year_to: date range
    - rights_articles: list of article numbers e.g. ["12", "13"]
    - judge: fuzzy match on judge names

    Returns:
    - hits: list of matching documents with highlights
    - total: total match count
    - page / page_size: pagination info
    """
    es = get_elasticsearch_service()
    results = es.search(
        query=request.query,
        court=request.court,
        year_from=request.year_from,
        year_to=request.year_to,
        rights_articles=request.rights_articles,
        judge=request.judge,
        page=request.page,
        page_size=request.page_size,
    )
    return results


@router.get("/suggest")
def search_suggest(prefix: str, size: int = 8):
    """
    Autocomplete suggestions for case file names.
    Returns up to `size` matching case name suggestions.
    """
    if not prefix or len(prefix) < 2:
        return {"suggestions": []}

    es = get_elasticsearch_service()
    suggestions = es.suggest(prefix=prefix, size=size)
    return {"suggestions": suggestions}


@router.post("/advanced")
def advanced_search(request: SearchRequest):
    """
    Advanced search — same as /documents but aliased for frontend routing clarity.
    Supports all filters: court, year range, rights articles, judge.
    """
    es = get_elasticsearch_service()
    results = es.search(
        query=request.query,
        court=request.court,
        year_from=request.year_from,
        year_to=request.year_to,
        rights_articles=request.rights_articles,
        judge=request.judge,
        page=request.page,
        page_size=request.page_size,
    )
    return results


@router.get("/status")
def search_status():
    """Check if Elasticsearch is available."""
    es = get_elasticsearch_service()
    return {
        "elasticsearch_available": es.available,
        "message": (
            "Elasticsearch connected and ready"
            if es.available
            else "Elasticsearch not available. Start ES or check ELASTICSEARCH_URL in .env"
        ),
    }
