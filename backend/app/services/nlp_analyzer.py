import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
from nltk.tokenize import sent_tokenize
import spacy
from pathlib import Path
from typing import List, Dict, Tuple

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    print("Downloading NLTK punkt_tab data...")
    nltk.download('punkt_tab', quiet=True)

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("Downloading NLTK punkt data...")
    nltk.download('punkt', quiet=True)

class NLPAnalyzer:
    # Load the trained legal NER model once at class level
    _ner_model = None
    
    @classmethod
    def _get_ner_model(cls):
        """Lazy load the NER model"""
        if cls._ner_model is None:
            try:
                model_path = Path(__file__).parent.parent.parent / "models" / "legal_ner"
                cls._ner_model = spacy.load(str(model_path))
                print(f"✅ Loaded legal NER model from {model_path}")
            except Exception as e:
                print(f"⚠️ Could not load NER model: {e}")
                cls._ner_model = None
        return cls._ner_model

    @staticmethod
    def extractive_summary(text: str, n_sentences: int = 5) -> str:
        if not text or len(text.strip()) == 0:
            return "No text available for summarization."

        try:
            sentences = sent_tokenize(text)

            if len(sentences) <= n_sentences:
                return text

            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform(sentences)

            scores = tfidf_matrix.sum(axis=1).A1
            ranked_indices = np.argsort(scores)[-n_sentences:]

            selected = [sentences[i] for i in sorted(ranked_indices)]
            return "\n".join(selected)  # FIXED: Proper indentation
        except Exception as e:
            print(f"Summarization error: {e}")
            return f"Summary generation failed: {str(e)}"

    @staticmethod
    def extract_keywords(text: str, top_k: int = 10):
        if not text or len(text.strip()) == 0:
            return []

        try:
            vectorizer = TfidfVectorizer(max_features=top_k, stop_words="english")
            vectorizer.fit([text])
            return vectorizer.get_feature_names_out().tolist()
        except Exception as e:
            print(f"Keyword extraction error: {e}")
            return []
    
    @classmethod
    def extract_legal_entities(cls, text: str) -> Dict[str, List[Dict[str, any]]]:
        """
        Extract legal entities from text using the trained NER model.
        
        Returns:
            Dictionary with entity types as keys and lists of entity details as values.
            Example:
            {
                "CASE_NAME": [{"text": "Silva vs. Fernando", "start": 10, "end": 28}],
                "COURT": [{"text": "Supreme Court", "start": 50, "end": 63}],
                ...
            }
        """
        if not text or len(text.strip()) == 0:
            return {}
        
        try:
            nlp = cls._get_ner_model()
            if nlp is None:
                return {"error": "NER model not available"}
            
            doc = nlp(text)
            
            # Group entities by type
            entities_by_type = {}
            for ent in doc.ents:
                entity_info = {
                    "text": ent.text,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "label": ent.label_
                }
                
                if ent.label_ not in entities_by_type:
                    entities_by_type[ent.label_] = []
                
                entities_by_type[ent.label_].append(entity_info)
            
            return entities_by_type
            
        except Exception as e:
            print(f"Entity extraction error: {e}")
            return {"error": str(e)}
    
    @classmethod
    def extract_legal_entities_list(cls, text: str) -> List[Tuple[str, str]]:
        """
        Extract legal entities as a simple list of (text, label) tuples.
        
        Returns:
            List of tuples: [("Silva vs. Fernando", "CASE_NAME"), ...]
        """
        if not text or len(text.strip()) == 0:
            return []
        
        try:
            nlp = cls._get_ner_model()
            if nlp is None:
                return []
            
            doc = nlp(text)
            return [(ent.text, ent.label_) for ent in doc.ents]
            
        except Exception as e:
            print(f"Entity extraction error: {e}")
            return []