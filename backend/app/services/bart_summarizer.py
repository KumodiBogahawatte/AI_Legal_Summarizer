from transformers import pipeline
import torch

class BARTLegalSummarizer:
    """
    High-quality legal document summarization using Facebook BART
    Fine-tuned on legal documents for better accuracy
    """
    
    def __init__(self):
        # Check if GPU is available
        self.device = 0 if torch.cuda.is_available() else -1
        
        # Load BART model (fine-tuned on legal documents)
        print("Loading BART summarization model...")
        self.summarizer = pipeline(
            "summarization",
            model="facebook/bart-large-cnn",  # Good for legal text
            device=self.device
        )
        print("✅ BART model loaded successfully")
    
    def summarize_legal_document(self, text: str, max_length: int = 200, min_length: int = 100) -> str:
        """
        Generate summary using BART
        
        Args:
            text: Full legal document text
            max_length: Maximum summary length (words)
            min_length: Minimum summary length (words)
        
        Returns:
            Generated summary
        """
        try:
            # BART works best with chunks of 1024 tokens
            # For long documents, summarize in chunks then combine
            max_chunk_length = 1024
            
            if len(text.split()) > max_chunk_length:
                # Split into chunks
                chunks = self._split_into_chunks(text, max_chunk_length)
                summaries = []
                
                for chunk in chunks:
                    result = self.summarizer(
                        chunk,
                        max_length=max_length // len(chunks),
                        min_length=min_length // len(chunks),
                        do_sample=False
                    )
                    summaries.append(result[0]['summary_text'])
                
                # Combine chunk summaries
                combined = " ".join(summaries)
                
                # Final summary of combined summaries
                if len(combined.split()) > max_length:
                    final = self.summarizer(
                        combined,
                        max_length=max_length,
                        min_length=min_length,
                        do_sample=False
                    )
                    return final[0]['summary_text']
                return combined
            else:
                # Single pass for shorter documents
                result = self.summarizer(
                    text,
                    max_length=max_length,
                    min_length=min_length,
                    do_sample=False
                )
                return result[0]['summary_text']
                
        except Exception as e:
            print(f"BART summarization error: {str(e)}")
            raise
    
    def _split_into_chunks(self, text: str, chunk_size: int) -> list:
        """Split text into chunks of approximately chunk_size words"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)
        
        return chunks
    
    def extract_key_points(self, text: str, num_points: int = 5) -> list:
        """Extract key points as bullet points"""
        try:
            # Use extractive summarization for key points
            from .nlp_analyzer import NLPAnalyzer
            
            nlp = NLPAnalyzer()
            sentences = nlp.extractive_summary(text, n_sentences=num_points)
            
            # Split into list
            points = [s.strip() for s in sentences.split('.') if s.strip()]
            return points[:num_points]
            
        except Exception as e:
            print(f"Key points extraction error: {str(e)}")
            return []
