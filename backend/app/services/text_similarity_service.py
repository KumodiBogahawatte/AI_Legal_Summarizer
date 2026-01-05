from sentence_transformers import SentenceTransformer, util
import torch
from typing import List, Dict, Tuple
import re

class TextSimilarityService:
    """Compare text similarity at sentence level"""
    
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.device = 0 if torch.cuda.is_available() else -1
    
    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Split by sentence boundaries
        sentences = re.split(r'[.!?]+', text)
        # Clean and filter
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        return sentences
    
    def compare_documents(
        self, 
        source_text: str, 
        target_text: str, 
        threshold: float = 0.5
    ) -> Dict:
        """
        Compare two documents and find matching sentences
        
        Args:
            source_text: The uploaded document text
            target_text: The case to compare against
            threshold: Minimum similarity score (0-1)
        
        Returns:
            Dictionary with matching sentences and scores
        """
        # Split into sentences
        source_sentences = self.split_into_sentences(source_text)
        target_sentences = self.split_into_sentences(target_text)
        
        # Encode sentences
        source_embeddings = self.model.encode(
            source_sentences, 
            convert_to_tensor=True,
            show_progress_bar=False
        )
        target_embeddings = self.model.encode(
            target_sentences,
            convert_to_tensor=True,
            show_progress_bar=False
        )
        
        # Compute similarity matrix
        similarity_matrix = util.cos_sim(source_embeddings, target_embeddings)
        
        # Find best matches
        matches = []
        for i, source_sent in enumerate(source_sentences):
            # Get best matching target sentence
            scores = similarity_matrix[i]
            best_idx = torch.argmax(scores).item()
            best_score = scores[best_idx].item()
            
            if best_score >= threshold:
                matches.append({
                    'source_sentence': source_sent,
                    'target_sentence': target_sentences[best_idx],
                    'target_index': best_idx,
                    'similarity': round(best_score, 3)
                })
        
        # Get target sentences that should be highlighted
        highlighted_indices = set([m['target_index'] for m in matches])
        
        return {
            'total_matches': len(matches),
            'matches': matches[:20],  # Return top 20 matches
            'highlighted_sentences': highlighted_indices,
            'similarity_score': round(sum(m['similarity'] for m in matches) / len(matches), 3) if matches else 0
        }
    
    def highlight_matching_text(
        self, 
        text: str, 
        matching_indices: set
    ) -> str:
        """
        Return HTML with highlighted matching sentences
        
        Args:
            text: The full text to highlight
            matching_indices: Set of sentence indices to highlight
        
        Returns:
            HTML string with highlighted sentences
        """
        sentences = self.split_into_sentences(text)
        
        highlighted = []
        for idx, sentence in enumerate(sentences):
            if idx in matching_indices:
                # High similarity - green highlight
                highlighted.append(
                    f'<span class="highlight-similar" data-similarity="high">{sentence}.</span>'
                )
            else:
                highlighted.append(f'{sentence}.')
        
        return ' '.join(highlighted)

_similarity_service = None

def get_similarity_service():
    """Get singleton instance"""
    global _similarity_service
    if _similarity_service is None:
        _similarity_service = TextSimilarityService()
    return _similarity_service
