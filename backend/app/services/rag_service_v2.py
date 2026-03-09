"""
rag_service_v2.py
Full RAG service with FAISS IndexFlatIP (cosine similarity on normalized vectors).
Replaces the stub rag_service.py.

Key improvements over stub:
- Chunk-level retrieval (not document-level)
- FAISS IndexFlatIP with L2-normalized vectors (= cosine similarity)
- MMR (Maximal Marginal Relevance) re-ranking for diversity
- Metadata-rich results (section_type, article_refs, court, year)
- In-memory index rebuilt from DB on startup, with persistence to disk
"""

import os
import json
import logging
import numpy as np
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from pathlib import Path

import faiss
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)

INDEX_PATH = Path("faiss_chunks_v2.bin")
META_PATH = Path("faiss_chunks_v2_meta.json")


@dataclass
class ChunkResult:
    """A retrieved chunk with all metadata for the generation layer."""
    chunk_id: int
    document_id: int
    chunk_index: int
    text: str
    section_type: str
    article_refs: List[str]
    citation_refs: List[str]
    similarity: float
    # Document metadata (joined from legal_documents)
    case_name: Optional[str] = None
    court: Optional[str] = None
    year: Optional[int] = None
    case_number: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "section_type": self.section_type,
            "article_refs": self.article_refs,
            "citation_refs": self.citation_refs,
            "similarity": round(float(self.similarity), 4),
            "case_name": self.case_name,
            "court": self.court,
            "year": self.year,
            "case_number": self.case_number,
        }


class RAGServiceV2:
    """
    Production-ready RAG retrieval service.
    - Loads FAISS chunk index from disk or rebuilds from DB
    - Provides semantic chunk retrieval with MMR re-ranking
    - Supports document-scoped and global retrieval
    """

    def __init__(self):
        self._embedding_service = None
        self.index: Optional[faiss.Index] = None
        self.chunk_meta: List[Dict] = []   # parallel list to FAISS index rows
        self._load_or_rebuild()

    @property
    def embedding_service(self):
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service

    # ─── Index Management ──────────────────────────────────────────────────────

    def _load_or_rebuild(self):
        """Load index from disk if available, otherwise rebuild from DB."""
        if INDEX_PATH.exists() and META_PATH.exists():
            try:
                self.index = faiss.read_index(str(INDEX_PATH))
                with open(META_PATH, "r", encoding="utf-8") as f:
                    self.chunk_meta = json.load(f)
                logger.info(
                    f"✅ RAGServiceV2: Loaded FAISS index with {self.index.ntotal} chunks from disk"
                )
                return
            except Exception as e:
                logger.warning(f"Failed to load FAISS index from disk: {e}. Rebuilding...")

        self._rebuild_from_db()

    def _rebuild_from_db(self):
        """Rebuild FAISS index from all chunks stored in PostgreSQL."""
        try:
            from app.models.document_chunk_model import DocumentChunk
            from app.models.document_model import LegalDocument

            db = SessionLocal()
            try:
                chunks = db.query(DocumentChunk).filter(
                    DocumentChunk.embedding.isnot(None)
                ).all()

                if not chunks:
                    logger.info("No chunks with embeddings found. Index is empty.")
                    self.index = None
                    self.chunk_meta = []
                    return

                embeddings = []
                self.chunk_meta = []

                for chunk in chunks:
                    emb = np.array(chunk.embedding, dtype=np.float32)
                    emb = emb / (np.linalg.norm(emb) + 1e-10)  # L2-normalize
                    embeddings.append(emb)

                    # Join document metadata
                    doc = db.query(LegalDocument).filter(
                        LegalDocument.id == chunk.document_id
                    ).first()

                    self.chunk_meta.append({
                        "chunk_id": chunk.id,
                        "document_id": chunk.document_id,
                        "chunk_index": chunk.chunk_index,
                        "text": chunk.text,
                        "section_type": chunk.section_type or "OTHER",
                        "article_refs": chunk.article_refs or [],
                        "citation_refs": chunk.citation_refs or [],
                        "case_name": doc.file_name if doc else None,
                        "court": doc.court if doc else None,
                        "year": doc.year if doc else None,
                        "case_number": doc.case_number if doc else None,
                    })

                dim = len(embeddings[0])
                self.index = faiss.IndexFlatIP(dim)  # Inner Product = cosine on normalized
                self.index.add(np.array(embeddings, dtype=np.float32))

                # Persist to disk
                faiss.write_index(self.index, str(INDEX_PATH))
                with open(META_PATH, "w", encoding="utf-8") as f:
                    json.dump(self.chunk_meta, f)

                logger.info(
                    f"✅ RAGServiceV2: Built FAISS index from {len(chunks)} chunks (dim={dim})"
                )
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error rebuilding FAISS index: {e}")
            self.index = None
            self.chunk_meta = []

    def add_chunks_to_index(self, chunks_data: List[Dict]):
        """
        Add newly ingested chunks to the in-memory FAISS index and persist.
        Called by the Celery ingestion task after saving chunks to DB.
        """
        if not chunks_data:
            return

        new_embeddings = []
        for data in chunks_data:
            emb = np.array(data["embedding"], dtype=np.float32)
            emb = emb / (np.linalg.norm(emb) + 1e-10)
            new_embeddings.append(emb)
            meta = {k: v for k, v in data.items() if k != "embedding"}
            self.chunk_meta.append(meta)

        arr = np.array(new_embeddings, dtype=np.float32)
        if self.index is None:
            self.index = faiss.IndexFlatIP(arr.shape[1])

        self.index.add(arr)

        # Persist
        faiss.write_index(self.index, str(INDEX_PATH))
        with open(META_PATH, "w", encoding="utf-8") as f:
            json.dump(self.chunk_meta, f)

        logger.info(f"Added {len(chunks_data)} new chunks to FAISS index")

    # ─── Retrieval ─────────────────────────────────────────────────────────────

    def retrieve_for_document(
        self,
        query: str,
        doc_id: int,
        top_k: int,
        db: Session,
        section_filter: Optional[str] = None,
    ) -> List[ChunkResult]:
        """
        Retrieve top-k chunks from a single document by semantic similarity.
        Uses DB embeddings so the user's uploaded doc is always searchable.
        """
        from app.models.document_chunk_model import DocumentChunk
        from app.models.document_model import LegalDocument

        chunks = (
            db.query(DocumentChunk)
            .filter(
                DocumentChunk.document_id == doc_id,
                DocumentChunk.embedding.isnot(None),
            )
            .order_by(DocumentChunk.chunk_index)
            .all()
        )
        if section_filter:
            chunks = [c for c in chunks if (c.section_type or "").upper() == section_filter.upper()]
        if not chunks:
            logger.debug("No chunks with embeddings for doc_id=%s", doc_id)
            return []

        doc = db.query(LegalDocument).filter(LegalDocument.id == doc_id).first()
        case_name = doc.file_name if doc else None
        court = getattr(doc, "court", None) if doc else None
        year = getattr(doc, "year", None) if doc else None
        case_number = getattr(doc, "case_number", None) if doc else None

        q = (query or "").strip() if isinstance(query, str) else ""
        if not q:
            return []

        try:
            query_vec = self.embedding_service.encode_for_retrieval(q)
        except Exception as e:
            logger.warning("Query embedding failed for doc-scoped retrieval: %s", e)
            # Return chunks in document order so user still sees content
            return [
                ChunkResult(
                    chunk_id=c.id,
                    document_id=c.document_id,
                    chunk_index=c.chunk_index,
                    text=c.text,
                    section_type=c.section_type or "OTHER",
                    article_refs=c.article_refs or [],
                    citation_refs=c.citation_refs or [],
                    similarity=0.0,
                    case_name=case_name,
                    court=court,
                    year=year,
                    case_number=case_number,
                )
                for c in chunks[:top_k]
            ]

        query_vec = np.array(query_vec, dtype=np.float32)
        n = np.linalg.norm(query_vec)
        if n < 1e-6:
            logger.warning("Query embedding is zero; returning chunks by order.")
            return [
                ChunkResult(
                    chunk_id=c.id,
                    document_id=c.document_id,
                    chunk_index=c.chunk_index,
                    text=c.text,
                    section_type=c.section_type or "OTHER",
                    article_refs=c.article_refs or [],
                    citation_refs=c.citation_refs or [],
                    similarity=0.0,
                    case_name=case_name,
                    court=court,
                    year=year,
                    case_number=case_number,
                )
                for c in chunks[:top_k]
            ]

        query_vec = query_vec / n

        results: List[ChunkResult] = []
        for c in chunks:
            emb = np.array(c.embedding, dtype=np.float32)
            emb = emb / (np.linalg.norm(emb) + 1e-10)
            sim = float(np.dot(query_vec, emb))
            results.append(
                ChunkResult(
                    chunk_id=c.id,
                    document_id=c.document_id,
                    chunk_index=c.chunk_index,
                    text=c.text,
                    section_type=c.section_type or "OTHER",
                    article_refs=c.article_refs or [],
                    citation_refs=c.citation_refs or [],
                    similarity=sim,
                    case_name=case_name,
                    court=court,
                    year=year,
                    case_number=case_number,
                )
            )

        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:top_k]

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        doc_id_filter: Optional[int] = None,
        section_filter: Optional[str] = None,
        mmr_lambda: float = 0.6,
        db: Optional[Session] = None,
    ) -> List[ChunkResult]:
        """
        Retrieve top-k chunks relevant to the query.
        When doc_id_filter and db are set, searches only within that document (DB).
        Otherwise uses the global FAISS index.
        """
        if doc_id_filter is not None and db is not None:
            return self.retrieve_for_document(
                query=query,
                doc_id=doc_id_filter,
                top_k=top_k,
                db=db,
                section_filter=section_filter,
            )

        if self.index is None or self.index.ntotal == 0:
            logger.warning("FAISS index is empty. No results.")
            return []

        try:
            # Encode query with retrieval prefix (required by BGE)
            query_vec = self.embedding_service.encode_for_retrieval(query)
            query_vec = query_vec / (np.linalg.norm(query_vec) + 1e-10)
            query_vec = query_vec.astype(np.float32).reshape(1, -1)

            # Fetch more than top_k initially for filtering + MMR
            fetch_k = min(top_k * 10, self.index.ntotal)
            distances, indices = self.index.search(query_vec, fetch_k)

            candidates: List[ChunkResult] = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < 0 or idx >= len(self.chunk_meta):
                    continue
                meta = self.chunk_meta[idx]

                # Apply filters
                if doc_id_filter is not None and meta["document_id"] != doc_id_filter:
                    continue
                if section_filter and meta["section_type"] != section_filter:
                    continue

                candidates.append(ChunkResult(
                    chunk_id=meta["chunk_id"],
                    document_id=meta["document_id"],
                    chunk_index=meta["chunk_index"],
                    text=meta["text"],
                    section_type=meta["section_type"],
                    article_refs=meta["article_refs"],
                    citation_refs=meta["citation_refs"],
                    similarity=float(dist),
                    case_name=meta.get("case_name"),
                    court=meta.get("court"),
                    year=meta.get("year"),
                    case_number=meta.get("case_number"),
                ))

            if not candidates:
                return []

            # MMR re-ranking for diversity
            results = self._mmr_rerank(
                query_vec=query_vec,
                candidates=candidates,
                top_k=top_k,
                lambda_mult=mmr_lambda,
            )

            return results

        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            return []

    def _mmr_rerank(
        self,
        query_vec: np.ndarray,
        candidates: List[ChunkResult],
        top_k: int,
        lambda_mult: float = 0.6,
    ) -> List[ChunkResult]:
        """
        Maximal Marginal Relevance re-ranking.
        Balances relevance to query and diversity among selected chunks.
        """
        if not candidates:
            return []
        if len(candidates) <= top_k:
            return sorted(candidates, key=lambda c: c.similarity, reverse=True)

        selected: List[ChunkResult] = []
        candidate_pool = list(candidates)

        while len(selected) < top_k and candidate_pool:
            if not selected:
                # First pick: highest similarity to query
                best = max(candidate_pool, key=lambda c: c.similarity)
            else:
                # MMR score: lambda * sim_to_query - (1-lambda) * max_sim_to_selected
                best = None
                best_score = float("-inf")

                for cand in candidate_pool:
                    # Max similarity to already selected chunks
                    max_sim_selected = max(
                        self._text_overlap(cand.text, sel.text) for sel in selected
                    )
                    score = lambda_mult * cand.similarity - (1 - lambda_mult) * max_sim_selected
                    if score > best_score:
                        best_score = score
                        best = cand

            if best is None:
                break

            selected.append(best)
            candidate_pool.remove(best)

        return selected

    def _text_overlap(self, text1: str, text2: str) -> float:
        """Simple word-overlap similarity for MMR (fast, no embedding needed)."""
        w1 = set(text1.lower().split())
        w2 = set(text2.lower().split())
        if not w1 or not w2:
            return 0.0
        return len(w1 & w2) / len(w1 | w2)

    def retrieve_for_constitutional(
        self,
        query: str,
        top_k: int = 3,
    ) -> List[ChunkResult]:
        """Retrieve chunks containing constitutional article references."""
        # Get broader set and filter by article_refs
        raw = self.retrieve(query, top_k=top_k * 5, mmr_lambda=0.7)
        constitutional = [c for c in raw if c.article_refs]
        return constitutional[:top_k] if constitutional else raw[:top_k]

    def retrieve_cross_document(
        self,
        query: str,
        exclude_doc_id: Optional[int] = None,
        top_k: int = 5,
    ) -> List[ChunkResult]:
        """Retrieve chunks from all documents except the specified one."""
        all_chunks = self.retrieve(query, top_k=top_k * 10)
        filtered = [c for c in all_chunks if c.document_id != exclude_doc_id]

        # Group by document and pick top chunk per doc
        seen_docs: Dict[int, ChunkResult] = {}
        for chunk in filtered:
            if chunk.document_id not in seen_docs:
                seen_docs[chunk.document_id] = chunk

        # Sort by similarity
        unique_docs = sorted(seen_docs.values(), key=lambda c: c.similarity, reverse=True)
        return unique_docs[:top_k]

    def invalidate_index(self):
        """Force rebuild of FAISS index (call after bulk import)."""
        if INDEX_PATH.exists():
            INDEX_PATH.unlink()
        if META_PATH.exists():
            META_PATH.unlink()
        self._rebuild_from_db()


# Global singleton
_rag_service_v2: Optional[RAGServiceV2] = None


def get_rag_service_v2() -> RAGServiceV2:
    global _rag_service_v2
    if _rag_service_v2 is None:
        _rag_service_v2 = RAGServiceV2()
    return _rag_service_v2
