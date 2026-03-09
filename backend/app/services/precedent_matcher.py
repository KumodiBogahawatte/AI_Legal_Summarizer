"""
Precedent Matching Service for Legal Document Similarity

This module finds similar legal cases based on semantic similarity using embeddings.
Implements court hierarchy weighting and relevance scoring.
"""

import numpy as np
from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging

from app.db import get_db
from app.models.document_model import LegalDocument
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class PrecedentMatcher:
    """
    Service for finding similar legal cases (precedents) based on semantic similarity.
    """
    
    # Court hierarchy weights (Supreme Court > Court of Appeal > High Court)
    COURT_WEIGHTS = {
        'supreme court': 1.0,
        'court of appeal': 0.8,
        'high court': 0.6,
        'district court': 0.4,
        'magistrate court': 0.2
    }
    
    def __init__(self):
        """Initialize the precedent matcher."""
        self.embedding_service = get_embedding_service()
    
    def _get_court_weight(self, court_name: str) -> float:
        """
        Get weight for a court based on hierarchy.
        
        Args:
            court_name: Name of the court
            
        Returns:
            Weight between 0.2 and 1.0
        """
        if not court_name:
            return 0.5  # Default weight
        
        court_lower = court_name.lower()
        
        for court_key, weight in self.COURT_WEIGHTS.items():
            if court_key in court_lower:
                return weight
        
        return 0.5  # Default weight if court not recognized
    
    def _calculate_weighted_similarity(
        self,
        base_similarity: float,
        source_court: str,
        target_court: str,
        year_diff: Optional[int] = None
    ) -> float:
        """
        Calculate weighted similarity based on court hierarchy and recency.
        
        Args:
            base_similarity: Raw cosine similarity score
            source_court: Court of the source document
            target_court: Court of the target document
            year_diff: Years between documents (optional)
            
        Returns:
            Weighted similarity score
        """
        # Start with base similarity
        weighted_score = base_similarity
        
        # Apply court hierarchy weight
        target_weight = self._get_court_weight(target_court)
        weighted_score *= target_weight
        
        # Boost if target court is higher in hierarchy than source
        source_weight = self._get_court_weight(source_court)
        if target_weight > source_weight:
            weighted_score *= 1.1  # 10% boost for higher court
        
        # Apply recency bonus (more recent cases get slight boost)
        if year_diff is not None and year_diff >= 0:
            recency_factor = 1.0 - (year_diff * 0.01)  # 1% reduction per year
            recency_factor = max(0.8, recency_factor)  # Cap at 20% reduction
            weighted_score *= recency_factor
        
        return weighted_score
    
    def find_similar_cases(
        self,
        document_id: int,
        top_k: int = 5,
        min_similarity: float = 0.3,
        db: Session = None
    ) -> List[Dict]:
        """
        Find similar cases to a given document.
        
        Args:
            document_id: ID of the source document
            top_k: Number of similar cases to return
            min_similarity: Minimum similarity threshold
            db: Database session
            
        Returns:
            List of similar cases with metadata
        """
        try:
            if db is None:
                db = next(get_db())
            
            # Get source document
            source_doc = db.query(LegalDocument).filter(
                LegalDocument.id == document_id
            ).first()
            
            if not source_doc:
                logger.error(f"Document {document_id} not found")
                return []
            
            # Generate embedding for source if not exists
            if source_doc.embedding is None or len(source_doc.embedding) == 0:
                logger.info(f"Generating embedding for document {document_id}")
                source_text = self._prepare_text_for_embedding(source_doc)
                source_embedding = self.embedding_service.generate_document_embedding(source_text)
                
                # Store embedding
                source_doc.embedding = source_embedding.tolist()
                db.commit()
            else:
                source_embedding = np.array(source_doc.embedding)
            
            # Get all other documents with embeddings, excluding source and duplicates
            candidate_docs = db.query(LegalDocument).filter(
                and_(
                    LegalDocument.id != document_id,
                    LegalDocument.embedding.isnot(None),
                    LegalDocument.file_name != source_doc.file_name  # Exclude same filename
                )
            ).all()
            
            if not candidate_docs:
                logger.warning("No candidate documents with embeddings found")
                return []
            
            # Calculate similarities
            similar_cases = []
            seen_files = set()  # Track unique files
            
            for candidate in candidate_docs:
                try:
                    # Skip if we've already seen this file
                    if candidate.file_name in seen_files:
                        continue
                    
                    candidate_embedding = np.array(candidate.embedding)
                    
                    # Calculate base similarity (returns value between -1 and 1, typically 0 to 1)
                    base_similarity = self.embedding_service.cosine_similarity(
                        source_embedding,
                        candidate_embedding
                    )
                    
                    # Ensure similarity is in valid range [0, 1]
                    base_similarity = max(0.0, min(1.0, base_similarity))
                    
                    # Skip if below threshold
                    if base_similarity < min_similarity:
                        continue
                    
                    # Calculate year difference if possible
                    year_diff = None
                    recency_percentage = None
                    
                    if source_doc.year and candidate.year:
                        try:
                            # Handle both int and string years
                            source_year = int(str(source_doc.year)[:4])  # Take first 4 digits
                            candidate_year = int(str(candidate.year)[:4])
                            year_diff = abs(source_year - candidate_year)
                            
                            # Calculate recency as percentage (0 years = 100%, decreases by 2% per year)
                            recency_percentage = max(0, 100 - (year_diff * 2))
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Invalid year data for document {candidate.id}: {e}")
                            year_diff = None
                            recency_percentage = None
                    
                    # Calculate weighted similarity (still in 0-1 range)
                    weighted_similarity = self._calculate_weighted_similarity(
                        base_similarity,
                        source_doc.court or "",
                        candidate.court or "",
                        year_diff
                    )
                    
                    # Get court weight
                    court_weight_raw = self._get_court_weight(candidate.court or "")
                    
                    similar_cases.append({
                        'document_id': candidate.id,
                        'file_name': candidate.file_name,
                        'title': candidate.file_name,
                        'court': candidate.court,
                        'year': str(candidate.year) if candidate.year else None,
                        'case_number': candidate.case_number,
                        'similarity_score': round(base_similarity * 100, 1),  # Convert to percentage for display
                        'weighted_score': round(weighted_similarity * 100, 1),  # Convert to percentage for display
                        'court_weight': round(court_weight_raw * 100, 1),  # Convert to percentage for display
                        'recency': recency_percentage if recency_percentage is not None else None,  # Already a percentage or None
                        'binding': self._is_binding(source_doc.court, candidate.court)
                    })
                    
                    seen_files.add(candidate.file_name)
                
                except Exception as e:
                    logger.error(f"Error processing candidate {candidate.id}: {str(e)}")
                    continue
            
            # Sort by weighted score and return top-k
            similar_cases.sort(key=lambda x: x['weighted_score'], reverse=True)
            
            return similar_cases[:top_k]
        
        except Exception as e:
            logger.error(f"Error finding similar cases: {str(e)}")
            return []
    
    def find_precedents_by_text(
        self,
        query_text: str,
        top_k: int = 5,
        court_filter: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        db: Session = None
    ) -> List[Dict]:
        """
        Find precedents based on free text query.
        
        Args:
            query_text: Text to search for
            top_k: Number of results to return
            court_filter: Filter by court name
            year_from: Minimum year
            year_to: Maximum year
            db: Database session
            
        Returns:
            List of matching cases
        """
        try:
            if db is None:
                db = next(get_db())
            
            # Generate embedding for query
            query_embedding = self.embedding_service.generate_embedding(query_text)
            
            # Build query with filters
            query = db.query(LegalDocument).filter(
                LegalDocument.embedding.isnot(None)
            )
            
            if court_filter:
                query = query.filter(LegalDocument.court.ilike(f"%{court_filter}%"))
            
            if year_from:
                query = query.filter(LegalDocument.year >= year_from)
            
            if year_to:
                query = query.filter(LegalDocument.year <= year_to)
            
            candidate_docs = query.all()
            
            if not candidate_docs:
                return []
            
            # Calculate similarities
            results = []
            
            for doc in candidate_docs:
                try:
                    doc_embedding = np.array(doc.embedding)
                    similarity = self.embedding_service.cosine_similarity(
                        query_embedding,
                        doc_embedding
                    )
                    
                    results.append({
                        'document_id': doc.id,
                        'file_name': doc.file_name,
                        'title': doc.file_name,  # Using file_name as title
                        'court': doc.court,
                        'year': doc.year,
                        'case_number': doc.case_number,
                        'similarity_score': round(similarity, 4)
                    })
                
                except Exception as e:
                    logger.error(f"Error processing document {doc.id}: {str(e)}")
                    continue
            
            # Sort and return top-k
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            return results[:top_k]
        
        except Exception as e:
            logger.error(f"Error finding precedents by text: {str(e)}")
            return []
    
    def _prepare_text_for_embedding(self, document: LegalDocument) -> str:
        """
        Prepare document text for embedding generation.
        
        Args:
            document: Legal document object
            
        Returns:
            Combined text for embedding
        """
        text_parts = []
        
        # Add file name (as title)
        if document.file_name:
            text_parts.append(document.file_name)
        
        # Add case number
        if document.case_number:
            text_parts.append(document.case_number)
        
        # Add court
        if document.court:
            text_parts.append(document.court)
        
        # Add text content (prefer cleaned_text if available)
        if document.cleaned_text:
            text_parts.append(document.cleaned_text[:2000])  # Limit to first 2000 chars
        elif document.raw_text:
            # Use first 2000 characters of raw text
            text_parts.append(document.raw_text[:2000])
        
        return " ".join(text_parts)
    
    def _is_binding(self, source_court: Optional[str], target_court: Optional[str]) -> bool:
        """
        Determine if target court's decision is binding on source court.
        
        Args:
            source_court: Court of the source document
            target_court: Court of the target (precedent) document
            
        Returns:
            True if binding, False if persuasive
        """
        if not source_court or not target_court:
            return False
        
        source_weight = self._get_court_weight(source_court)
        target_weight = self._get_court_weight(target_court)
        
        # Binding if target court is higher or equal in hierarchy
        return target_weight >= source_weight


# Global instance
_precedent_matcher = None


def get_precedent_matcher() -> PrecedentMatcher:
    """Get or create the global precedent matcher instance."""
    global _precedent_matcher
    if _precedent_matcher is None:
        _precedent_matcher = PrecedentMatcher()
    return _precedent_matcher
