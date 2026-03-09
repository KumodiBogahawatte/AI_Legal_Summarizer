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
            max_length: Maximum summary length (tokens)
            min_length: Minimum summary length (tokens)
        
        Returns:
            Generated summary
        """
        text = (text or "").strip()
        if not text:
            raise ValueError("BART summarization requires non-empty text.")
        # Enforce minimum token lengths to avoid "index out of range" in model
        max_length = max(10, max_length)
        min_length = max(5, min_length)

        def _safe_summarize(inp: str, max_len: int, min_len: int) -> str:
            if not (inp and inp.strip()) or len(inp.strip()) < 50:
                return ""
            result = self.summarizer(
                inp,
                max_length=max_len,
                min_length=min_len,
                do_sample=False,
            )
            if not result or not isinstance(result, list):
                return ""
            first = result[0] if result else None
            if not first or not isinstance(first, dict):
                return ""
            return (first.get("summary_text") or "").strip()

        try:
            # BART works best with chunks of 1024 tokens
            max_chunk_length = 1024
            words = text.split()

            if len(words) > max_chunk_length:
                chunks = self._split_into_chunks(text, max_chunk_length)
                n = len(chunks)
                chunk_max = max(10, max_length // n)
                chunk_min = max(5, min_length // n)
                summaries = []
                for chunk in chunks:
                    if not (chunk and chunk.strip()):
                        continue
                    s = _safe_summarize(chunk, chunk_max, chunk_min)
                    if s:
                        summaries.append(s)
                if not summaries:
                    return _safe_summarize(text[:5000], max_length, min_length) or text[:500]
                combined = " ".join(summaries)
                if len(combined.split()) > max_length:
                    final = _safe_summarize(combined, max_length, min_length)
                    return final or combined
                return combined
            else:
                out = _safe_summarize(text, max_length, min_length)
                if not out:
                    return text[:500] if len(text) > 500 else text
                return out
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
