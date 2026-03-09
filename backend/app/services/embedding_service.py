"""
Embedding Service for Legal Document Similarity Matching

This module generates vector embeddings for legal documents using sentence-transformers.
Embeddings enable semantic similarity search for precedent matching.
"""

import numpy as np
from typing import List, Optional, Dict
import logging
from sentence_transformers import SentenceTransformer
import torch

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating document embeddings using transformer models.
    """
    
    def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5"):
        """
        Initialize the embedding service with a pre-trained model.

        Args:
            model_name: Name of the sentence-transformer model to use.
                       Default: BAAI/bge-base-en-v1.5 (768-dim, optimized for legal/semantic retrieval)
                       Alternative: all-MiniLM-L6-v2 (384-dim, faster but less accurate)

        BGE Note: When encoding QUERIES for retrieval, use encode_for_retrieval() which
        prepends the required instruction prefix. For document chunks, use generate_embedding().
        """
        self.model_name = model_name
        self.model = None
        self.embedding_dim = None
        self._load_model()
    
    def _load_model(self):
        """Load the sentence-transformer model."""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            
            # Set to use GPU if available
            if torch.cuda.is_available():
                self.model = self.model.to('cuda')
                logger.info("Using GPU for embeddings")
            else:
                logger.info("Using CPU for embeddings")
            
            # Get embedding dimension
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded successfully. Embedding dimension: {self.embedding_dim}")
            
        except Exception as e:
            logger.error(f"Error loading embedding model: {str(e)}")
            raise
    
    def encode_for_retrieval(self, query: str) -> np.ndarray:
        """
        Encode a QUERY with the BGE instruction prefix.
        Required for accurate retrieval with BAAI/bge-base-en-v1.5.

        Args:
            query: User query or search text

        Returns:
            Numpy array of shape (embedding_dim,). Never returns zero vector for non-empty query.
        """
        q = str(query).strip() if query is not None else ""
        if not q:
            return np.zeros(self.embedding_dim)
        try:
            # BGE instruction prefix for retrieval queries
            prefixed = f"Represent this sentence for searching relevant passages: {q}"
            out = self.model.encode(prefixed, convert_to_numpy=True, normalize_embeddings=True)
            if out is None or (isinstance(out, np.ndarray) and out.size == 0):
                raise ValueError("Model returned empty embedding")
            vec = np.asarray(out, dtype=np.float64).flatten()
            if vec.size != self.embedding_dim:
                raise ValueError(f"Embedding size {vec.size} != {self.embedding_dim}")
            n = np.linalg.norm(vec)
            if n < 1e-6:
                raise ValueError("Model returned zero-norm embedding")
            return vec.astype(np.float32)
        except Exception as e:
            logger.error(f"Error in encode_for_retrieval: {str(e)}")
            return np.zeros(self.embedding_dim)

    def encode_for_retrieval_batch(self, texts: List[str]) -> np.ndarray:
        """
        Encode a batch of texts with BGE retrieval prefix.
        Used by ConstitutionalRAGModule to encode article texts.

        Args:
            texts: List of texts to encode

        Returns:
            Numpy array of shape (len(texts), embedding_dim)
        """
        try:
            if not texts:
                return np.zeros((0, self.embedding_dim))
            prefixed = [
                f"Represent this sentence for searching relevant passages: {t}"
                for t in texts
            ]
            return self.model.encode(
                prefixed,
                convert_to_numpy=True,
                normalize_embeddings=True,
                batch_size=32,
                show_progress_bar=False,
            )
        except Exception as e:
            logger.error(f"Error in encode_for_retrieval_batch: {str(e)}")
            return np.zeros((len(texts), self.embedding_dim))

    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single document chunk (no retrieval prefix).

        Args:
            text: Input text to embed

        Returns:
            Numpy array of shape (embedding_dim,)
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided, returning zero vector")
                return np.zeros(self.embedding_dim)
            return self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            return np.zeros(self.embedding_dim)
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once
            
        Returns:
            Numpy array of shape (num_texts, embedding_dim)
        """
        try:
            if not texts:
                logger.warning("Empty text list provided")
                return np.array([])
            
            # Filter empty texts
            valid_texts = [t if t and t.strip() else " " for t in texts]
            
            # Generate embeddings in batches
            embeddings = self.model.encode(
                valid_texts,
                batch_size=batch_size,
                show_progress_bar=len(valid_texts) > 100,
                convert_to_numpy=True
            )
            
            logger.info(f"Generated embeddings for {len(texts)} texts")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            return np.zeros((len(texts), self.embedding_dim))
    
    def generate_document_embedding(
        self,
        text: str,
        max_length: int = 512,
        strategy: str = "mean"
    ) -> np.ndarray:
        """
        Generate embedding for a long document by chunking and aggregating.
        
        Args:
            text: Full document text
            max_length: Maximum tokens per chunk (approximate)
            strategy: How to combine chunk embeddings
                     'mean': Average all chunks
                     'max': Max pooling across chunks
                     'first': Use only first chunk
            
        Returns:
            Document embedding vector
        """
        try:
            if not text or not text.strip():
                return np.zeros(self.embedding_dim)
            
            # Split into sentences
            sentences = text.split('. ')
            
            # If short enough, embed directly
            if len(sentences) <= 10:
                return self.generate_embedding(text)
            
            # Otherwise, chunk sentences
            chunk_size = 5  # sentences per chunk
            chunks = []
            current_chunk = []
            
            for sentence in sentences:
                current_chunk.append(sentence)
                if len(current_chunk) >= chunk_size:
                    chunks.append('. '.join(current_chunk))
                    current_chunk = []
            
            # Add remaining sentences
            if current_chunk:
                chunks.append('. '.join(current_chunk))
            
            # Generate embeddings for all chunks
            chunk_embeddings = self.generate_embeddings_batch(chunks)
            
            # Aggregate based on strategy
            if strategy == "mean":
                doc_embedding = np.mean(chunk_embeddings, axis=0)
            elif strategy == "max":
                doc_embedding = np.max(chunk_embeddings, axis=0)
            elif strategy == "first":
                doc_embedding = chunk_embeddings[0]
            else:
                doc_embedding = np.mean(chunk_embeddings, axis=0)
            
            return doc_embedding
            
        except Exception as e:
            logger.error(f"Error generating document embedding: {str(e)}")
            return np.zeros(self.embedding_dim)
    
    def cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score between -1 and 1 (1 = most similar)
        """
        try:
            # Normalize vectors
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Calculate cosine similarity
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {str(e)}")
            return 0.0
    
    def find_most_similar(
        self,
        query_embedding: np.ndarray,
        candidate_embeddings: np.ndarray,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Find most similar embeddings to a query.
        
        Args:
            query_embedding: Query vector of shape (embedding_dim,)
            candidate_embeddings: Candidate vectors of shape (num_candidates, embedding_dim)
            top_k: Number of top results to return
            
        Returns:
            List of dicts with 'index' and 'similarity' keys
        """
        try:
            if candidate_embeddings.size == 0:
                return []
            
            # Normalize query
            query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-10)
            
            # Normalize candidates
            candidate_norms = candidate_embeddings / (
                np.linalg.norm(candidate_embeddings, axis=1, keepdims=True) + 1e-10
            )
            
            # Calculate similarities
            similarities = np.dot(candidate_norms, query_norm)
            
            # Get top-k indices
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            # Build results
            results = [
                {
                    'index': int(idx),
                    'similarity': float(similarities[idx])
                }
                for idx in top_indices
            ]
            
            return results
            
        except Exception as e:
            logger.error(f"Error finding most similar: {str(e)}")
            return []
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this service."""
        return self.embedding_dim


# Global instance
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
