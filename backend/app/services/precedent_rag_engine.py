"""
precedent_rag_engine.py
Chunk-level precedent matching using RAGServiceV2.

Replaces the document-level approach in precedent_matcher.py with:
- Cross-document chunk retrieval (chunk-level semantic search)
- Document scoring by aggregated chunk similarities
- Court hierarchy weighting (same as existing PrecedentMatcher)
- Structured comparison output per case
"""

import numpy as np
import logging
from typing import List, Dict, Optional
from collections import defaultdict

from app.services.rag_service_v2 import get_rag_service_v2, ChunkResult

logger = logging.getLogger(__name__)

# Court hierarchy weights (same as PrecedentMatcher)
COURT_WEIGHTS = {
    "supreme court": 1.0,
    "court of appeal": 0.8,
    "high court": 0.6,
    "district court": 0.4,
    "magistrate court": 0.2,
}

# Section importance for precedent scoring
SECTION_IMPORTANCE = {
    "ISSUES": 1.5,
    "REASONING": 1.3,
    "JUDGMENT": 1.4,
    "LEGAL_ANALYSIS": 1.2,
    "FACTS": 1.0,
    "ORDERS": 1.1,
    "OTHER": 0.8,
}


def _get_court_weight(court_name: Optional[str]) -> float:
    if not court_name:
        return 0.5
    court_lower = court_name.lower()
    for key, weight in COURT_WEIGHTS.items():
        if key in court_lower:
            return weight
    return 0.5


class PrecedentRAGEngine:
    """
    Chunk-based precedent matching for Sri Lankan legal cases.

    For each query case:
    1. Retrieve its most important chunks (ISSUES + REASONING focus)
    2. Search for similar chunks across all other documents
    3. Aggregate chunk similarities per source document
    4. Score by: avg_similarity * court_weight * section_importance
    5. Return top-5 similar cases with structured comparison info
    """

    def __init__(self):
        self._rag = None

    @property
    def rag(self):
        if self._rag is None:
            self._rag = get_rag_service_v2()
        return self._rag

    def find_similar_cases(
        self,
        document_id: int,
        source_court: Optional[str] = None,
        source_year: Optional[int] = None,
        top_k: int = 5,
        min_similarity: float = 0.4,
    ) -> List[Dict]:
        """
        Find cases similar to the given document using chunk-level RAG.

        Args:
            document_id: Source document ID to find precedents for
            source_court: Court of the source document (for binding analysis)
            source_year: Year of the source document (for recency scoring)
            top_k: Number of similar cases to return
            min_similarity: Minimum aggregate similarity threshold

        Returns:
            List of similar case dicts with comparison metadata
        """
        try:
            # 1. Get important chunks from this document (focus on ISSUES, REASONING, JUDGMENT)
            doc_chunks = self._get_key_chunks_for_document(document_id)
            if not doc_chunks:
                logger.warning(f"No chunks found for document {document_id}")
                return []

            # 2. For each key chunk, retrieve cross-document similar chunks
            doc_scores: Dict[int, List[Dict]] = defaultdict(list)  # doc_id → list of match info

            for chunk in doc_chunks:
                cross_chunks = self.rag.retrieve_cross_document(
                    query=chunk.text,
                    exclude_doc_id=document_id,
                    top_k=10,
                )

                section_weight = SECTION_IMPORTANCE.get(chunk.section_type, 1.0)

                for match in cross_chunks:
                    doc_scores[match.document_id].append({
                        "similarity": match.similarity,
                        "section_weight": section_weight,
                        "match_section": match.section_type,
                        "chunk_text": match.text[:200],
                        "court": match.court,
                        "year": match.year,
                        "case_name": match.case_name,
                        "case_number": match.case_number,
                        "article_refs": match.article_refs,
                    })

            # 3. Aggregate per document
            results = []

            for target_doc_id, matches in doc_scores.items():
                if not matches:
                    continue

                # Require at least one strong match in a high-importance section
                # (e.g. ISSUES / REASONING / JUDGMENT / LEGAL_ANALYSIS) to treat
                # a case as genuinely related.
                has_strong_key_section = any(
                    m["section_weight"] >= 1.3 and m["similarity"] >= 0.5
                    for m in matches
                )
                if not has_strong_key_section:
                    continue

                similarities = [m["similarity"] * m["section_weight"] for m in matches]
                avg_similarity = float(np.mean(similarities))
                max_similarity = float(np.max([m["similarity"] for m in matches]))

                if avg_similarity < min_similarity:
                    continue

                # Court weight and binding
                target_court = matches[0]["court"]
                target_year = matches[0]["year"]
                target_name = matches[0]["case_name"]
                target_case_number = matches[0]["case_number"]

                court_weight = _get_court_weight(target_court)
                source_weight = _get_court_weight(source_court)
                is_binding = court_weight >= source_weight

                # Recency factor
                recency = None
                if source_year and target_year:
                    try:
                        year_diff = abs(int(str(source_year)[:4]) - int(str(target_year)[:4]))
                        recency = max(0, 100 - year_diff * 2)
                    except (ValueError, TypeError):
                        pass

                # Combine: avg_similarity * court_weight (with small recency boost)
                weighted_score = avg_similarity * court_weight
                if court_weight > source_weight:
                    weighted_score *= 1.1  # Boost for higher court precedent

                # Shared constitutional articles
                all_article_refs = []
                for m in matches:
                    all_article_refs.extend(m.get("article_refs", []))
                shared_articles = list(set(all_article_refs))

                # Collect sample matching section texts for comparison
                section_matches = {}
                for m in matches:
                    sec = m["match_section"]
                    if sec not in section_matches:
                        section_matches[sec] = m["chunk_text"]

                results.append({
                    "document_id": target_doc_id,
                    "case_name": target_name or f"Document {target_doc_id}",
                    "case_number": target_case_number,
                    "court": target_court,
                    "year": str(target_year) if target_year else None,
                    "similarity_score": round(avg_similarity * 100, 1),
                    "max_similarity": round(max_similarity * 100, 1),
                    "weighted_score": round(weighted_score * 100, 1),
                    "court_weight": round(court_weight * 100, 1),
                    "binding": is_binding,
                    "recency": recency,
                    "shared_constitutional_articles": shared_articles,
                    "matching_sections": list(section_matches.keys()),
                    "section_snippets": section_matches,
                    "match_count": len(matches),
                    "authority_type": "Binding" if is_binding else "Persuasive",
                })

            # 4. Sort by weighted score
            results.sort(key=lambda r: r["weighted_score"], reverse=True)
            return results[:top_k]

        except Exception as e:
            logger.error(f"Error in PrecedentRAGEngine.find_similar_cases: {e}")
            return []

    def _get_key_chunks_for_document(
        self,
        document_id: int,
        priority_sections: Optional[List[str]] = None,
    ) -> List[ChunkResult]:
        """
        Get the most important chunks from a document for precedent query.
        Priorities: ISSUES > REASONING > JUDGMENT > LEGAL_ANALYSIS > others.
        """
        if priority_sections is None:
            priority_sections = ["ISSUES", "REASONING", "JUDGMENT", "LEGAL_ANALYSIS"]

        # Retrieve all chunks for this document by section
        all_chunks: List[ChunkResult] = []

        for section in priority_sections:
            section_chunks = self.rag.retrieve(
                query=f"legal issues judgment reasoning in {section}",
                top_k=3,
                doc_id_filter=document_id,
                section_filter=section,
                mmr_lambda=0.5,
            )
            all_chunks.extend(section_chunks)

        # If specific sections are empty, fall back to general retrieval
        if len(all_chunks) < 3:
            general = self.rag.retrieve(
                query="main legal issue judgment court held",
                top_k=8,
                doc_id_filter=document_id,
                mmr_lambda=0.5,
            )
            all_chunks.extend(general)

        # Deduplicate by chunk_id
        seen_ids = set()
        unique_chunks = []
        for c in all_chunks:
            if c.chunk_id not in seen_ids:
                seen_ids.add(c.chunk_id)
                unique_chunks.append(c)

        return unique_chunks[:10]  # Max 10 query chunks

    def compare_cases(
        self,
        source_doc_id: int,
        target_doc_id: int,
    ) -> Dict:
        """
        Generate a structured comparison between two cases using their chunks.
        Used for the side-by-side comparison feature.
        """
        source_chunks = self._get_key_chunks_for_document(source_doc_id)
        target_chunks = self._get_key_chunks_for_document(target_doc_id)

        if not source_chunks or not target_chunks:
            return {"error": "Insufficient chunk data for comparison"}

        # Group chunks by section
        def group_by_section(chunks: List[ChunkResult]) -> Dict[str, str]:
            grouped: Dict[str, List[str]] = defaultdict(list)
            for c in chunks:
                grouped[c.section_type].append(c.text)
            return {sec: " ".join(texts[:2]) for sec, texts in grouped.items()}

        source_sections = group_by_section(source_chunks)
        target_sections = group_by_section(target_chunks)

        # Calculate overall similarity
        source_texts = " ".join(c.text for c in source_chunks[:3])
        target_texts = " ".join(c.text for c in target_chunks[:3])

        # Word overlap similarity as a quick metric
        s_words = set(source_texts.lower().split())
        t_words = set(target_texts.lower().split())
        overlap = len(s_words & t_words) / (len(s_words | t_words) + 1e-10)

        return {
            "source_doc_id": source_doc_id,
            "target_doc_id": target_doc_id,
            "overall_similarity": round(float(overlap), 3),
            "source_sections": source_sections,
            "target_sections": target_sections,
            "common_sections": list(set(source_sections.keys()) & set(target_sections.keys())),
            "source_article_refs": list({a for c in source_chunks for a in c.article_refs}),
            "target_article_refs": list({a for c in target_chunks for a in c.article_refs}),
        }


# Global singleton
_precedent_rag: Optional[PrecedentRAGEngine] = None


def get_precedent_rag() -> PrecedentRAGEngine:
    global _precedent_rag
    if _precedent_rag is None:
        _precedent_rag = PrecedentRAGEngine()
    return _precedent_rag
