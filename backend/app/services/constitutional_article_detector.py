# backend/app/services/constitutional_article_detector.py
import json
import re
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.tokenize import sent_tokenize
import nltk

nltk.download("punkt", quiet=True)

# Comprehensive Fundamental Rights Article Explanations (Sri Lankan Constitution Chapter III)
FR_ARTICLE_EXPLANATIONS = {
    "10": "Freedom of Thought, Conscience and Religion: Every person is entitled to freedom of thought, conscience and religion, including the freedom to have or to adopt a religion or belief of his choice.",
    "11": "Freedom from Torture: No person shall be subjected to torture or to cruel, inhuman or degrading treatment or punishment.",
    "12": "Right to Equality: (1) All persons are equal before the law and are entitled to the equal protection of the law. (2) No citizen shall be discriminated against on grounds of race, religion, language, caste, sex, political opinion, place of birth or any such grounds. (3) No person shall be subjected to any disability, liability, restriction or condition with regard to access to shops, public restaurants, hotels, places of public entertainment and places of public worship of his own religion on the ground only of race, religion, language, caste, sex or any one of such grounds.",
    "13": "Freedom from Arbitrary Arrest, Detention and Punishment: (1) No person shall be arrested except according to procedure established by law. Any person arrested shall be informed of the reason for his arrest. (2) Every person held in custody, detained or otherwise deprived of personal liberty shall be brought before the judge of the nearest competent court according to procedure established by law, and shall not be further held in custody, detained or deprived of personal liberty except upon and in terms of the order of such judge made in accordance with procedure established by law. (3) Every person charged with an offence shall be entitled to be heard, in person or by an attorney-at-law, at a fair trial by a competent court.",
    "14": "Freedom of Speech, Assembly, Association, Occupation and Movement: Every citizen is entitled to: (a) the freedom of speech and expression including publication; (b) the freedom of peaceful assembly; (c) the freedom of association; (d) the freedom to form and join a trade union; (e) the freedom, either by himself or in association with others, and either in public or in private, to manifest his religion or belief in worship, observance, practice and teaching; (f) the freedom by himself or in association with others to enjoy and promote his own culture and to use his own language; (g) the freedom to engage by himself or in association with others in any lawful occupation, profession, trade, business or enterprise; (h) the freedom of movement and of choosing his residence within Sri Lanka; (i) the freedom to return to Sri Lanka.",
    "14A": "Right to Access Information: (1) Every citizen shall have the right of access to any information as provided for by law, being information that is required for the exercise or protection of a citizen's right. (2) No restrictions shall be placed on the right declared and recognized by this Article, other than such restrictions as may be prescribed by law in the interests of national security, the prevention of crime or the protection of public health or morality, or for the purpose of protecting the privacy of other persons.",
    "15": "Restrictions on Fundamental Rights: The exercise and operation of the fundamental rights declared and recognized by Articles 12(1), 13 and 14 shall be subject to such restrictions as may be prescribed by law in the interests of national security, public order and the protection of public health or morality, or for the purpose of securing due recognition and respect for the rights and freedoms of others, or of meeting the just requirements of the general welfare of a democratic society.",
    "16": "Existing Written Law and Unwritten Law: (1) All existing written law and unwritten law shall, to the extent that they are inconsistent with the provisions of this Chapter, be and shall be deemed to have been amended or repealed on the commencement of the Constitution and thereafter continue in force as so amended and such amendment or repeal shall be in addition to any amendment or repeal effected by any other provision of the Constitution.",
    "17": "Duties of Every Person: Every person shall be subject to such duties as are determined by law. Such duties shall include respect for the national flag and the national anthem and such other duties as tend to uphold and strengthen national solidarity."
}

BASE = Path(__file__).resolve().parents[3]
DATA_DIR = BASE / "data" / "sri_lanka_legal_corpus"

PROCESSED_CONSTITUTIONS_PATH = DATA_DIR / "processed_constitutions.json"
CONSTITUTION_ARTICLES_PATH = DATA_DIR / "constitution_articles.json"
FUNDAMENTAL_RIGHTS_ARTICLES_PATH = DATA_DIR / "fundamental_rights_articles.json"

# Load resources
def _load_json(path: Path):
    if not path.exists():
        print(f"Warning: File not found - {path}")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"Loaded {path.name}: {len(data) if isinstance(data, (list, dict)) else 'N/A'} items")
            return data
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return {}

CONSTITUTIONS = _load_json(PROCESSED_CONSTITUTIONS_PATH)
CONSTITUTION_ARTICLES = _load_json(CONSTITUTION_ARTICLES_PATH)
FUNDAMENTAL_RIGHTS_ARTICLES = _load_json(FUNDAMENTAL_RIGHTS_ARTICLES_PATH)
FUNDAMENTAL_RIGHTS_ARTICLES = _load_json(FUNDAMENTAL_RIGHTS_ARTICLES_PATH)

# Build comprehensive sentence corpus from all constitution documents
CONSTITUTIONAL_SENTENCES = []
SENTENCE_METADATA = []  # Track which document and position each sentence comes from

print("\nBuilding constitutional sentence corpus...")
for doc_name, doc_data in CONSTITUTIONS.items():
    if isinstance(doc_data, dict) and "sentences" in doc_data:
        sentences = doc_data["sentences"]
        for idx, sent in enumerate(sentences):
            if sent and len(sent.strip()) > 20:  # Filter very short sentences
                CONSTITUTIONAL_SENTENCES.append(sent)
                SENTENCE_METADATA.append({
                    "document": doc_name,
                    "sentence_index": idx
                })

print(f"Built corpus with {len(CONSTITUTIONAL_SENTENCES)} constitutional sentences")

# Build TF-IDF vectorizer for semantic matching
TFIDF_VECTORIZER = None
SENTENCE_MATRIX = None

if CONSTITUTIONAL_SENTENCES:
    try:
        TFIDF_VECTORIZER = TfidfVectorizer(
            ngram_range=(1, 3),
            max_features=5000,
            stop_words="english",
            min_df=2
        )
        SENTENCE_MATRIX = TFIDF_VECTORIZER.fit_transform(CONSTITUTIONAL_SENTENCES)
        print(f"Built TF-IDF matrix: {SENTENCE_MATRIX.shape}")
    except Exception as e:
        print(f"Error building TF-IDF matrix: {e}")

# Article number extraction patterns - detect all constitutional articles
ARTICLE_PATTERNS = [
    r'Article\s+(\d+[A-Z]?|1[0-9]{2}[A-Z]?)(?!\d)',  # Any article number (1-199+, including 41A, 104B, etc.)
    r'Art\.\s+(\d+[A-Z]?|1[0-9]{2}[A-Z]?)(?!\d)',
]

class ConstitutionalArticleDetector:
    """
    Detects references to constitutional articles and provisions in legal text.
    """
    
    def __init__(self, semantic_threshold: float = 0.70):
        self.semantic_threshold = semantic_threshold  # Increased to 0.70 to reduce false positives
    
    def _is_constitutional_context(self, context: str, article_num: str) -> bool:
        """Check if the article mention is in a constitutional context, not a false positive."""
        context_lower = context.lower()
        
        # FALSE POSITIVE indicators - if these appear near "Article", it's likely NOT constitutional
        false_positive_terms = [
            "articles of association",
            "memorandum of association",
            "articles of incorporation"
        ]
        
        for term in false_positive_terms:
            if term in context_lower:
                return False
        
        # For fundamental rights articles (10-18), use looser validation
        # Accept if ANY of these conditions are met:
        # 1. Has constitutional keywords
        # 2. Appears in judgment/legal context (not company registration)
        if article_num.isdigit() and 10 <= int(article_num) <= 18:
            # Check for constitutional keywords (looser list)
            constitutional_keywords = [
                "fundamental right",
                "constitution",
                "supreme court",
                "court of appeal",
                "petitioner",
                "respondent",
                "violation",
                "infringement",
                "freedom",
                "right",
                "equality",
                "discrimination",
                "arrest",
                "detention",
                "torture",
                "petition",
                "relief",
                "remedy",
                "judgment",
                "held",
                "appeal",
                "application"
            ]
            
            has_keyword = any(kw in context_lower for kw in constitutional_keywords)
            
            # Also check if it's NOT a company context
            company_terms = [
                "companies act",
                "incorporated under",
                "certificate of incorporation",
                "limited liability",
                "company limited",
                "registrar"
            ]
            is_company_context = any(term in context_lower for term in company_terms)
            
            # Accept if has constitutional keywords OR (not company context AND mentions article)
            if has_keyword or not is_company_context:
                return True
            return False
        
        return True
        
    def extract_article_mentions(self, text: str) -> List[Dict[str, Any]]:
        """Extract explicit mentions of articles/sections in text."""
        mentions = []
        
        for pattern in ARTICLE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                article_num = match.group(1)
                # Get surrounding context (200 chars before and after for better context)
                start = max(0, match.start() - 200)
                end = min(len(text), match.end() + 200)
                context = text[start:end]
                
                # Validate if this is a genuine constitutional reference
                if not self._is_constitutional_context(context, article_num):
                    continue
                
                explanation = self._get_article_explanation(article_num)
                mention = {
                    "article": article_num,
                    "matched_text": match.group(0),
                    "context": context,
                    "method": "explicit_mention",
                    "score": 1.0,
                    "article_title": explanation['title'] if explanation else f"Article {article_num}"
                }
                if explanation:
                    mention["explanation"] = explanation['text']
                mentions.append(mention)
        
        return mentions
    
    def detect_semantic_matches(self, text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Find semantically similar constitutional provisions."""
        if TFIDF_VECTORIZER is None or SENTENCE_MATRIX is None:
            return []
        
        results = []
        sentences = sent_tokenize(text)
        
        # Filter sentences (ignore very short ones)
        valid_sentences = [s for s in sentences if len(s.strip()) > 20]
        
        if not valid_sentences:
            return results
        
        try:
            # Vectorize input sentences
            query_matrix = TFIDF_VECTORIZER.transform(valid_sentences)
            
            # Compute similarities
            similarities = cosine_similarity(query_matrix, SENTENCE_MATRIX)
            
            # For each query sentence, find top matches
            for sent_idx, sent in enumerate(valid_sentences):
                sent_sims = similarities[sent_idx]
                
                # Get top K matches above threshold
                top_indices = np.argsort(sent_sims)[-top_k:][::-1]
                
                for idx in top_indices:
                    score = float(sent_sims[idx])
                    if score >= self.semantic_threshold:
                        metadata = SENTENCE_METADATA[idx]
                        const_sent = CONSTITUTIONAL_SENTENCES[idx]
                        
                        # Validate that this is actually a constitutional provision
                        # Skip if it looks like case text (has accused, petitioner, etc.)
                        if self._is_case_text(sent):
                            continue
                        
                        # Try to extract article number from constitutional sentence
                        article_num = self._extract_article_from_sentence(const_sent)
                        
                        explanation = self._get_article_explanation(article_num) if article_num else None
                        
                        result = {
                            "matched_text": sent,
                            "constitutional_provision": const_sent[:300] + "..." if len(const_sent) > 300 else const_sent,
                            "document": metadata["document"],
                            "article": article_num or "Unknown",
                            "method": "semantic",
                            "score": score
                        }
                        if explanation:
                            result["explanation"] = explanation
                        results.append(result)
        
        except Exception as e:
            print(f"Semantic matching error: {e}")
        
        return results
    
    def _extract_article_from_sentence(self, sentence: str) -> str:
        """Try to extract article number from a constitutional sentence."""
        for pattern in ARTICLE_PATTERNS:
            match = re.search(pattern, sentence, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _is_case_text(self, text: str) -> bool:
        """Check if text is from case proceedings rather than constitutional provisions."""
        case_indicators = [
            r'\baccused\b', r'\bdefendant\b', r'\bpetitioner\b', r'\brespondent\b',
            r'\bappellant\b', r'\bplaintiff\b', r'\bwitness\b', r'\btestif',
            r'\bconvicted\b', r'\bfined\b', r'\bsentenced\b', r'\bprosecution\b',
            r'\bmagistrate\b', r'\bjudge\s+held\b', r'\bcourt\s+held\b',
            r'\bappeal\b', r'\bverdict\b', r'\btrial\b'
        ]
        
        text_lower = text.lower()
        matches = sum(1 for pattern in case_indicators if re.search(pattern, text_lower))
        
        # If text has 2 or more case-related terms, it's likely case text, not constitutional provision
        return matches >= 2
    
    def _get_article_explanation(self, article_num: str) -> dict:
        """Get the full text/explanation of a constitutional article with title."""
        if not article_num:
            return None
        
        article_num_clean = article_num.upper()  # Handle suffixes like 41A
        base_num = ''.join(filter(str.isdigit, article_num))
        
        # For fundamental rights articles (10-18, 14A), use hardcoded explanations first
        if article_num in FR_ARTICLE_EXPLANATIONS or article_num_clean in FR_ARTICLE_EXPLANATIONS:
            explanation = FR_ARTICLE_EXPLANATIONS.get(article_num) or FR_ARTICLE_EXPLANATIONS.get(article_num_clean)
            # Extract title (first part before colon)
            parts = explanation.split(': ', 1)
            if len(parts) == 2:
                title = f"Article {article_num} - {parts[0]}"
                text = parts[1]
            else:
                title = f"Article {article_num}"
                text = explanation
            return {
                "title": title,
                "text": text,
                "article_number": article_num
            }
        
        # Try FUNDAMENTAL_RIGHTS_ARTICLES for articles 10-18
        if base_num.isdigit() and 10 <= int(base_num) <= 18:
            if FUNDAMENTAL_RIGHTS_ARTICLES and base_num in FUNDAMENTAL_RIGHTS_ARTICLES:
                article_data = FUNDAMENTAL_RIGHTS_ARTICLES[base_num]
                full_text = article_data.get("full_text", article_data.get("description", ""))
                # Try to extract a cleaner title from the full text
                title = f"Article {article_num} - Fundamental Right"
                return {
                    "title": title,
                    "text": full_text if full_text else f"Fundamental Right under Article {article_num}",
                    "article_number": article_num
                }
        
        # For all other constitutional articles, use constitution_articles.json
        article_key = f"Article{article_num}"
        if CONSTITUTION_ARTICLES and article_key in CONSTITUTION_ARTICLES:
            article_data = CONSTITUTION_ARTICLES[article_key]
            if isinstance(article_data, dict):
                text = article_data.get("text", "")
                # Create a meaningful title
                title = f"Article {article_num}"
                return {
                    "title": title,
                    "text": text if text else f"Constitutional Article {article_num}",
                    "article_number": article_num
                }
        
        # If no data found, return minimal info
        return {
            "title": f"Article {article_num}",
            "text": f"Constitutional Article {article_num} (detailed text available in full constitution)",
            "article_number": article_num
        }
    
    def detect(self, text: str, language: str = "en") -> List[Dict[str, Any]]:
        """
        Detect constitutional provisions in text.
        Returns results from explicit article mentions; additionally applies
        conservative keyword-based inference when explicit mentions are absent.
        """
        print(f"\n=== Detecting Constitutional Provisions ===")
        
        # 1. Extract explicit article mentions
        explicit_mentions = self.extract_article_mentions(text)
        print(f"Explicit mentions: {len(explicit_mentions)}")
        
        # 2. If no explicit mentions found, apply conservative keyword inference
        inferred: List[Dict[str, Any]] = []
        if not explicit_mentions:
            inferred = self._keyword_based_inference(text)
            if inferred:
                print(f"Keyword-based inferred provisions: {len(inferred)}")
        
        # Combine explicit + inferred
        all_results = explicit_mentions + inferred
        
        # Deduplicate by (article, matched_text snippet)
        seen = set()
        unique_results = []
        
        for result in all_results:
            key = (result.get("article", ""), result["matched_text"][:100])
            if key not in seen:
                seen.add(key)
                unique_results.append(result)
        
        print(f"Total unique provisions detected: {len(unique_results)}")
        return unique_results

    def _keyword_based_inference(self, text: str) -> List[Dict[str, Any]]:
        """Infer likely constitutional articles from strong domain keywords.
        This is intentionally conservative to avoid false positives.
        Mappings:
        - writ/mandamus/certiorari/prohibition/quo warranto -> Article 140
        - fundamental rights application / SCFR / Article 126 context -> Article 126
        - equality / equal protection / discrimination -> Article 12
        """
        t = text.lower()
        results: List[Dict[str, Any]] = []

        def add(article: str, matched: str, score: float = 0.6):
            explanation = self._get_article_explanation(article)
            item = {
                "article": article,
                "matched_text": matched,
                "context": matched,
                "method": "keyword_inference",
                "score": score,
            }
            if explanation:
                item["explanation"] = f"{explanation['title']}\n\n{explanation['text']}"
                item["article_title"] = explanation['title']
            results.append(item)

        # Article 140: writ jurisdiction keywords
        writ_terms = [
            "writ", "mandamus", "certiorari", "prohibition", "quo warranto",
            "court of appeal writ"
        ]
        if any(term in t for term in writ_terms):
            add("140", next((term for term in writ_terms if term in t), "writ"))

        # Article 126: fundamental rights jurisdiction keywords
        fr126_terms = [
            "fundamental rights application", "scfr", "article 126", "supreme court fr"
        ]
        if any(term in t for term in fr126_terms):
            add("126", next((term for term in fr126_terms if term in t), "fundamental rights application"))

        # Article 12: equality/discrimination keywords
        eq_terms = [
            "equality", "equal protection", "discrimination", "equal before the law"
        ]
        if any(term in t for term in eq_terms):
            add("12", next((term for term in eq_terms if term in t), "equality"))

        # Dedup by article
        seen = set()
        deduped = []
        for r in results:
            if r["article"] not in seen:
                seen.add(r["article"])
                deduped.append(r)
        return deduped


# Test if run directly
if __name__ == "__main__":
    detector = ConstitutionalArticleDetector()
    
    test_text = """
    The Supreme Court held that under Article 126 of the Constitution, 
    fundamental rights jurisdiction lies with the Supreme Court. 
    The petitioner alleged violation of Article 12(1) which guarantees 
    equality before the law. The Court also considered Article 13 
    regarding arrest and detention procedures.
    """
    
    results = detector.detect(test_text)
    
    import json
    print("\n=== TEST RESULTS ===")
    print(json.dumps(results, indent=2))
