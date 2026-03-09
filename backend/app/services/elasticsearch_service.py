"""
elasticsearch_service.py
Full-text search with semantic filtering for Sri Lankan legal documents.
Implements Section 1.5 from the BUILD_ROADMAP.md.

Provides:
- Document indexing (text, entities, metadata)
- Full-text search with filters (court, year, rights articles, judge)
- Autocomplete suggestions
- Advanced search
"""

import os
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

ES_HOST = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
ES_INDEX = "sri_lanka_legal_cases"

# Elasticsearch document mapping
ES_MAPPING = {
    "mappings": {
        "properties": {
            "document_id":    {"type": "integer"},
            "file_name":      {"type": "keyword"},
            "case_number":    {"type": "keyword"},
            "court":          {"type": "keyword"},
            "year":           {"type": "integer"},
            "full_text":      {"type": "text", "analyzer": "english"},
            "cleaned_text":   {"type": "text", "analyzer": "english"},
            "executive_summary": {"type": "text"},
            "rights_articles": {"type": "keyword"},  # ["12", "13"]
            "judges":         {"type": "keyword"},
            "legal_topics":   {"type": "keyword"},
            "citations":      {"type": "keyword"},
            "uploaded_at":    {"type": "date"},
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "legal_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "stop"],
                }
            }
        }
    }
}


class ElasticsearchService:
    """
    Service for full-text search over Sri Lankan legal documents.
    Gracefully handles cases where Elasticsearch is not running.
    """

    def __init__(self):
        self._es = None
        self._available = False
        self._init_client()

    def _init_client(self):
        """Connect to Elasticsearch and ensure index exists."""
        try:
            from elasticsearch import Elasticsearch
            self._es = Elasticsearch([ES_HOST], request_timeout=5)
            if self._es.ping():
                self._ensure_index()
                self._available = True
                logger.info(f"✅ ElasticsearchService: Connected to {ES_HOST}")
            else:
                logger.warning(f"⚠️ Elasticsearch not reachable at {ES_HOST}. Search disabled.")
        except ImportError:
            logger.warning("elasticsearch-py not installed. Run: pip install elasticsearch>=8.0")
        except Exception as e:
            logger.warning(f"⚠️ Elasticsearch unavailable: {e}. Search features disabled.")

    def _ensure_index(self):
        """Create the index with mapping if it doesn't exist."""
        try:
            if not self._es.indices.exists(index=ES_INDEX):
                self._es.indices.create(index=ES_INDEX, body=ES_MAPPING)
                logger.info(f"Created Elasticsearch index: {ES_INDEX}")
        except Exception as e:
            logger.error(f"Error creating ES index: {e}")

    @property
    def available(self) -> bool:
        return self._available

    # ─── Indexing ─────────────────────────────────────────────────────────────

    def index_document(self, document_data: Dict) -> bool:
        """
        Index a legal document into Elasticsearch.

        Args:
            document_data: Dict with keys matching ES_MAPPING properties

        Returns:
            True if successful
        """
        if not self._available:
            return False
        try:
            doc_id = document_data.get("document_id")
            self._es.index(
                index=ES_INDEX,
                id=str(doc_id),
                body=document_data,
            )
            logger.info(f"Indexed document {doc_id} in Elasticsearch")
            return True
        except Exception as e:
            logger.error(f"Error indexing document: {e}")
            return False

    def update_document(self, document_id: int, fields: Dict) -> bool:
        """Update specific fields of an indexed document."""
        if not self._available:
            return False
        try:
            self._es.update(
                index=ES_INDEX,
                id=str(document_id),
                body={"doc": fields},
            )
            return True
        except Exception as e:
            logger.error(f"Error updating ES document {document_id}: {e}")
            return False

    def delete_document(self, document_id: int) -> bool:
        """Remove a document from the index."""
        if not self._available:
            return False
        try:
            self._es.delete(index=ES_INDEX, id=str(document_id), ignore=[404])
            return True
        except Exception as e:
            logger.error(f"Error deleting ES document {document_id}: {e}")
            return False

    # ─── Search ───────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        court: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        rights_articles: Optional[List[str]] = None,
        judge: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Dict:
        """
        Full-text search with optional filters.

        Returns:
            Dict with keys: hits, total, page, page_size
        """
        if not self._available:
            return {"hits": [], "total": 0, "page": page, "page_size": page_size,
                    "error": "Elasticsearch not available"}

        try:
            must_clauses = []
            filter_clauses = []

            # Main text query
            if query:
                must_clauses.append({
                    "multi_match": {
                        "query": query,
                        "fields": ["full_text^1", "cleaned_text^2", "executive_summary^3"],
                        "type": "best_fields",
                        "operator": "or",
                        "fuzziness": "AUTO",
                    }
                })

            # Filters
            if court:
                filter_clauses.append({"term": {"court": court}})

            if year_from or year_to:
                range_filter: Dict[str, Any] = {}
                if year_from:
                    range_filter["gte"] = year_from
                if year_to:
                    range_filter["lte"] = year_to
                filter_clauses.append({"range": {"year": range_filter}})

            if rights_articles:
                filter_clauses.append({"terms": {"rights_articles": rights_articles}})

            if judge:
                filter_clauses.append({
                    "match": {"judges": {"query": judge, "fuzziness": "AUTO"}}
                })

            # Build final query
            es_query: Dict[str, Any] = {
                "bool": {
                    "must": must_clauses if must_clauses else [{"match_all": {}}],
                    "filter": filter_clauses,
                }
            }

            from_ = (page - 1) * page_size
            response = self._es.search(
                index=ES_INDEX,
                body={
                    "query": es_query,
                    "from": from_,
                    "size": page_size,
                    "highlight": {
                        "fields": {
                            "full_text": {"fragment_size": 200, "number_of_fragments": 2},
                            "cleaned_text": {"fragment_size": 200, "number_of_fragments": 2},
                        }
                    },
                    "sort": [
                        {"_score": {"order": "desc"}},
                        {"year": {"order": "desc"}},
                    ],
                }
            )

            hits = response.get("hits", {})
            raw_hits = hits.get("hits", [])
            total = hits.get("total", {}).get("value", 0)

            results = []
            for hit in raw_hits:
                source = hit.get("_source", {})
                result = {
                    "document_id": source.get("document_id"),
                    "file_name": source.get("file_name"),
                    "case_number": source.get("case_number"),
                    "court": source.get("court"),
                    "year": source.get("year"),
                    "score": round(hit.get("_score", 0), 3),
                    "highlights": hit.get("highlight", {}),
                    "rights_articles": source.get("rights_articles", []),
                    "executive_summary": source.get("executive_summary", "")[:300],
                }
                results.append(result)

            return {
                "hits": results,
                "total": total,
                "page": page,
                "page_size": page_size,
            }

        except Exception as e:
            logger.error(f"Elasticsearch search error: {e}")
            return {"hits": [], "total": 0, "page": page, "page_size": page_size,
                    "error": str(e)}

    def suggest(self, prefix: str, size: int = 8) -> List[str]:
        """
        Autocomplete suggestions for case names / file names.

        Args:
            prefix: Partial text to complete
            size: Max number of suggestions

        Returns:
            List of suggestion strings
        """
        if not self._available or not prefix:
            return []
        try:
            response = self._es.search(
                index=ES_INDEX,
                body={
                    "query": {
                        "prefix": {"file_name": {"value": prefix.lower()}}
                    },
                    "size": size,
                    "_source": ["file_name", "case_number", "court", "year"],
                }
            )
            suggestions = []
            for hit in response.get("hits", {}).get("hits", []):
                src = hit.get("_source", {})
                suggestions.append(
                    f"{src.get('file_name', '')} ({src.get('court', '')} {src.get('year', '')})"
                )
            return suggestions
        except Exception as e:
            logger.error(f"Suggest error: {e}")
            return []


# Global singleton
_es_service: Optional[ElasticsearchService] = None


def get_elasticsearch_service() -> ElasticsearchService:
    global _es_service
    if _es_service is None:
        _es_service = ElasticsearchService()
    return _es_service
