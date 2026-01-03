# backend/app/services/fundamental_rights_detector.py
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.tokenize import sent_tokenize
import nltk

nltk.download("punkt", quiet=True)
# Newer NLTK versions also require 'punkt_tab' for sentence tokenization
try:
    nltk.download("punkt_tab", quiet=True)
except Exception:
    pass

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

BASE = Path(__file__).resolve().parents[3]  # backend/app/..
DATA_DIR = BASE / "data" / "sri_lanka_legal_corpus"

# File paths - using TRAINED fundamental rights data
PROCESSED_FR_PATH = DATA_DIR / "processed_fundamental_rights.json"
FR_PATTERNS_PATH = DATA_DIR / "fundamental_rights_patterns.json"
FR_ARTICLES_PATH = DATA_DIR / "fundamental_rights_articles.json"

# Load resources safely
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

# Load trained fundamental rights data
PROCESSED_FR = _load_json(PROCESSED_FR_PATH)
FR_PATTERNS = _load_json(FR_PATTERNS_PATH)
FR_ARTICLES = _load_json(FR_ARTICLES_PATH)

print(f"\n=== Loaded Fundamental Rights Training Data ===")
print(f"Processed FR articles: {len(PROCESSED_FR)}")
print(f"FR patterns: {len(FR_PATTERNS)}")
print(f"FR article metadata: {len(FR_ARTICLES)}")

# Build TF-IDF index over fundamental rights passages from trained data
FR_PASSAGE_TEXTS = []
FR_PASSAGE_METADATA = []

if isinstance(PROCESSED_FR, dict):
    for key, fr_data in PROCESSED_FR.items():
        if isinstance(fr_data, dict):
            article_num = fr_data.get("article_number", "unknown")
            
            # Extract text from sentences
            if "sentences" in fr_data and isinstance(fr_data["sentences"], list):
                for sent in fr_data["sentences"]:
                    if sent and len(sent.strip()) > 20:
                        FR_PASSAGE_TEXTS.append(sent)
                        FR_PASSAGE_METADATA.append({
                            "article": article_num,
                            "source": key
                        })
            
            # Also add title
            if "title" in fr_data and fr_data["title"] and len(fr_data["title"].strip()) > 10:
                FR_PASSAGE_TEXTS.append(fr_data["title"])
                FR_PASSAGE_METADATA.append({
                    "article": article_num,
                    "source": key
                })
            
            # Add keywords as passages
            if "keywords" in fr_data and isinstance(fr_data["keywords"], list):
                for kw in fr_data["keywords"]:
                    if kw and len(kw.strip()) > 5:
                        FR_PASSAGE_TEXTS.append(kw)
                        FR_PASSAGE_METADATA.append({
                            "article": article_num,
                            "source": key
                        })

print(f"Extracted {len(FR_PASSAGE_TEXTS)} fundamental rights passages for semantic matching")

# Build TF-IDF vectorizer
TFIDF_VECTORIZER = None
PASSAGE_MATRIX = None

if FR_PASSAGE_TEXTS and any(text.strip() for text in FR_PASSAGE_TEXTS):
    filtered_texts = [text for text in FR_PASSAGE_TEXTS if text and text.strip()]
    if filtered_texts:
        try:
            TFIDF_VECTORIZER = TfidfVectorizer(
                ngram_range=(1, 2), 
                stop_words="english", 
                max_features=1000,
                min_df=1
            )
            PASSAGE_MATRIX = TFIDF_VECTORIZER.fit_transform(filtered_texts)
            # Update metadata to match filtered texts
            FR_PASSAGE_METADATA = [FR_PASSAGE_METADATA[i] for i, text in enumerate(FR_PASSAGE_TEXTS) if text and text.strip()]
            print(f"Built TF-IDF matrix: {PASSAGE_MATRIX.shape}")
        except Exception as e:
            print(f"Error building TF-IDF: {e}")
            TFIDF_VECTORIZER = None
            PASSAGE_MATRIX = None
else:
    print("Warning: No passage texts available for TF-IDF")

# Helper: clean text
def _clean_text(s: str) -> str:
    s = re.sub(r'\s+', ' ', s).strip()
    return s

class FundamentalRightsDetector:
    """
    Fundamental Rights detector using TRAINED data.
    Detects Articles 10-18 (Chapter III of Sri Lankan Constitution).
    Uses trained patterns and semantic matching from processed_fundamental_rights.json
    """

    def __init__(self, semantic_threshold: float = 0.35):
        self.semantic_threshold = semantic_threshold
        self.patterns = FR_PATTERNS or {}  # Trained patterns from model
        
        # Create article titles mapping from loaded data
        self.article_titles = {}
        if FR_ARTICLES:
            for art_num, art_data in FR_ARTICLES.items():
                if isinstance(art_data, dict):
                    title = art_data.get("title", f"Article {art_num}")
                    self.article_titles[str(art_num)] = title
        
        print(f"Initialized FundamentalRightsDetector with {len(self.patterns)} trained pattern sets")
        print(f"Article titles loaded: {list(self.article_titles.keys())}")

    def _extract_explicit_fr_mentions(self, text: str) -> List[Dict[str, Any]]:
        """Extract explicit mentions like 'Article 12', 'Art. 17', 'Articles 12, 17', including 14A."""
        patterns = [
            r"Article\s+(1[0-8]|14A)(?!\d)",
            r"Art\.\s+(1[0-8]|14A)(?!\d)",
            # Handle lists e.g., 'Articles 12, 17, 14A'
            r"Articles\s+((?:1[0-8]|14A)(?:\s*,\s*(?:1[0-8]|14A))*)(?!\d)"
        ]
        mentions: List[Dict[str, Any]] = []
        for pat in patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                start = max(0, m.start() - 200)  # Extended from 100 to 200
                end = min(len(text), m.end() + 200)  # Extended from 100 to 200
                ctx = text[start:end]
                # Filter corporate contexts
                lower = ctx.lower()
                if any(t in lower for t in ["articles of association", "memorandum of association", "companies act"]):
                    continue

                # If pattern is list, split and add each
                if m.lastindex and m.lastindex >= 1 and pat.startswith("Articles"):
                    nums_str = m.group(1)
                    for num in re.split(r"\s*,\s*", nums_str):
                        explanation_data = self._get_article_explanation(num)
                        mentions.append({
                            "article": str(num),
                            "method": "explicit_mention",
                            "score": 1.0,
                            "matched_text": f"Article {num}",
                            "context": ctx,
                            "article_title": explanation_data["title"],
                            "explanation": explanation_data["text"]
                        })
                else:
                    num = m.group(1)
                    explanation_data = self._get_article_explanation(num)
                    mentions.append({
                        "article": str(num),
                        "method": "explicit_mention",
                        "score": 1.0,
                        "matched_text": m.group(0),
                        "context": ctx,
                        "article_title": explanation_data["title"],
                        "explanation": explanation_data["text"]
                    })
        return mentions

    def _get_article_explanation(self, article: str) -> Dict[str, str]:
        """Get explanation for an article number with title and text."""
        # First, try hardcoded comprehensive explanations
        if str(article) in FR_ARTICLE_EXPLANATIONS:
            explanation = FR_ARTICLE_EXPLANATIONS[str(article)]
            # Split title and text by first colon
            parts = explanation.split(': ', 1)
            if len(parts) == 2:
                return {
                    "title": f"Article {article} - {parts[0]}",
                    "text": parts[1],
                    "article_number": str(article)
                }
            else:
                return {
                    "title": f"Article {article} - Fundamental Right",
                    "text": explanation,
                    "article_number": str(article)
                }
        
        # Fallback to article titles or generic
        return {
            "title": f"Article {article} - Fundamental Right",
            "text": f"Fundamental Right under Article {article} of the Constitution of Sri Lanka.",
            "article_number": str(article)
        }
    
    def detect(self, text: str, language: str = "en") -> List[Dict[str, Any]]:
        """
        Detect fundamental rights violations in text.
        Returns list of detected rights:
        [ { "article": "12", "score": 0.8, "method":"semantic"|"pattern", "matched_text": "...", "explanation": "..."} ]
        """
        results = []
        sents = sent_tokenize(text)
        
        print(f"\nDetecting fundamental rights in text with {len(sents)} sentences")

        # 1) Pattern matching using TRAINED patterns - Re-enabled with validation
        pattern_count = 0
        for art, pats in self.patterns.items():
            # Handle both list of patterns and single regex string
            if isinstance(pats, str):
                regex = re.compile(pats, re.IGNORECASE)
            elif isinstance(pats, list):
                if not pats:
                    continue
                pattern_parts = []
                for p in pats:
                    p_clean = p.strip()
                    if p_clean and len(p_clean) > 2:
                        pattern_parts.append(re.escape(p_clean))
                
                if not pattern_parts:
                    continue
                    
                joined = "|".join(pattern_parts)
                regex = re.compile(joined, re.IGNORECASE)
            else:
                continue
            
            for sent in sents:
                match = regex.search(sent)
                if match:
                    # Validate to avoid false positives
                    sent_lower = sent.lower()
                    
                    # Skip company/corporate contexts
                    if any(term in sent_lower for term in ["articles of association", "memorandum of association", "companies act"]):
                        continue
                    
                    pattern_count += 1
            # Handle both list of patterns and single regex string
            if isinstance(pats, str):
                # It's a regex pattern string - use directly
                regex = re.compile(pats, re.IGNORECASE)
            elif isinstance(pats, list):
                # It's a list of pattern strings from training - create OR pattern
                if not pats:
                    continue
                # Join patterns with OR, escape special chars
                pattern_parts = []
                for p in pats:
                    # Clean the pattern
                    p_clean = p.strip()
                    if p_clean and len(p_clean) > 2:
                        # Escape special regex chars
                        pattern_parts.append(re.escape(p_clean))
                
                if not pattern_parts:
                    continue
                    
                joined = "|".join(pattern_parts)
                regex = re.compile(joined, re.IGNORECASE)
            else:
                # Unknown format, skip
                continue
            
            for sent in sents:
                match = regex.search(sent)
                if match:
                    # Validate to avoid false positives
                    sent_lower = sent.lower()
                    
                    # Skip company/corporate contexts
                    if any(term in sent_lower for term in ["articles of association", "memorandum of association", "companies act"]):
                        continue
                    
                    pattern_count += 1
                    explanation_data = self._get_article_explanation(str(art))
                    results.append({
                        "article": str(art),
                        "method": "pattern",
                        "score": 1.0,
                        "matched_text": sent,
                        "article_title": explanation_data["title"],
                        "explanation": explanation_data["text"]
                    })
        
        print(f"Pattern matching found {pattern_count} matches")

        # 1b) Explicit mentions of FR articles (Article 10-18, 14A)
        explicit_fr = self._extract_explicit_fr_mentions(text)
        if explicit_fr:
            print(f"Explicit FR mentions: {len(explicit_fr)}")
            results.extend(explicit_fr)
        else:
            # Conservative keyword-based inference when no explicit mentions
            inferred = self._keyword_based_inference(text)
            if inferred:
                print(f"Keyword-based FR inferred: {len(inferred)}")
                results.extend(inferred)
        # 2) Semantic matching using TRAINED fundamental rights passages
        if TFIDF_VECTORIZER is not None and PASSAGE_MATRIX is not None:
            sent_texts = [_clean_text(s) for s in sents if len(s.strip()) > 10]
            if sent_texts:
                try:
                    S_vec = TFIDF_VECTORIZER.transform(sent_texts)
                    sims = cosine_similarity(S_vec, PASSAGE_MATRIX)
                    
                    semantic_count = 0
                    for i, sent in enumerate(sent_texts):
                        row = sims[i]
                        max_idx = int(np.argmax(row))
                        max_score = float(row[max_idx])
                        if max_score >= self.semantic_threshold:
                            # Validate context to prevent false positives
                            sent_lower = sent.lower()
                            
                            # Skip if it contains false positive indicators
                            false_positive_terms = [
                                "articles of association",
                                "memorandum of association",
                                "companies act",
                                "company limited",
                                "incorporated",
                                "shareholder",
                                "executive committee",
                                "ships' agents",
                                "shipping agent"
                            ]
                            
                            # Check for case narrative patterns (not fundamental rights claims)
                            case_narrative_indicators = [
                                "petitioner", "respondent", "defendant", "plaintiff"
                            ]
                            
                            has_false_positive = any(term in sent_lower for term in false_positive_terms)
                            has_case_narrative = any(term in sent_lower for term in case_narrative_indicators)
                            
                            # If it's case narrative AND has association/company terms, likely false positive
                            if has_false_positive or (has_case_narrative and "association" in sent_lower and "freedom" not in sent_lower):
                                continue
                            
                            # For very high similarity scores (0.80+), accept
                            if max_score >= 0.80:
                                semantic_count += 1
                            else:
                                # For lower scores, require strong constitutional keywords
                                constitutional_keywords = [
                                    "fundamental right",
                                    "violation of article",
                                    "infringement of article",
                                    "contravention of article",
                                    "freedom of",
                                    "right to",
                                    "discrimination",
                                    "torture",
                                    "arrest without warrant",
                                    "detention without trial"
                                ]
                                
                                has_keyword = any(kw in sent_lower for kw in constitutional_keywords)
                                if not has_keyword:
                                    continue
                                
                                semantic_count += 1
                            # Get article from metadata
                            if max_idx < len(FR_PASSAGE_METADATA):
                                metadata = FR_PASSAGE_METADATA[max_idx]
                                article = metadata.get("article", "unknown")
                            else:
                                article = "unknown"
                            
                            # Skip if article is unknown or not a valid FR article
                            if article == "unknown" or article not in ["10", "11", "12", "13", "14", "15", "16", "17", "18", "1"]:
                                continue
                            
                            explanation_data = self._get_article_explanation(str(article))
                            
                            results.append({
                                "article": str(article),
                                "method": "semantic",
                                "score": max_score,
                                "matched_text": sent,
                                "article_title": explanation_data["title"],
                                "explanation": explanation_data["text"]
                            })
                    
                    print(f"Semantic matching (trained) found {semantic_count} matches")
                except Exception as e:
                    print(f"Semantic matching error: {e}")
                    import traceback
                    traceback.print_exc()

        # Deduplicate by article number only - keep highest scoring match for each article
        dedup = {}
        for r in sorted(results, key=lambda x: -x.get("score", 0)):
            article = r["article"]
            if article not in dedup:
                dedup[article] = r

        final_results = list(dedup.values())
        print(f"Total unique fundamental rights detected: {len(final_results)} articles")
        
        return final_results

    def _keyword_based_inference(self, text: str) -> List[Dict[str, Any]]:
        """Infer likely FR articles from strong domain keywords (conservative).
        Mappings:
        - equality / equal protection / discrimination -> Article 12
        - torture / cruel / inhuman / degrading -> Article 11
        - arrest / detention / warrant / custody -> Article 13
        - speech / expression / assembly / association / trade union / movement -> Article 14
        """
        t = text.lower()
        results: List[Dict[str, Any]] = []

        def add(article: str, matched: str, score: float = 0.6):
            explanation = self._get_article_explanation(article)
            results.append({
                "article": article,
                "method": "keyword_inference",
                "score": score,
                "matched_text": matched,
                "explanation": explanation
            })

        # Article 12
        eq_terms = ["equality", "equal protection", "discrimination", "equal before the law"]
        if any(term in t for term in eq_terms):
            add("12", next((term for term in eq_terms if term in t), "equality"))

        # Article 11
        torture_terms = ["torture", "cruel", "inhuman", "degrading"]
        if any(term in t for term in torture_terms):
            add("11", next((term for term in torture_terms if term in t), "torture"))

        # Article 13
        detention_terms = ["arrest", "detention", "warrant", "custody"]
        if any(term in t for term in detention_terms):
            add("13", next((term for term in detention_terms if term in t), "arrest"))

        # Article 14
        speech_terms = [
            "freedom of speech", "speech", "expression", "assembly", "association",
            "trade union", "movement", "residence"
        ]
        if any(term in t for term in speech_terms):
            add("14", next((term for term in speech_terms if term in t), "speech"))

        # Dedup by article
        seen = set()
        deduped = []
        for r in results:
            if r["article"] not in seen:
                seen.add(r["article"])
                deduped.append(r)
        return deduped

# Test the detector if run directly
if __name__ == "__main__":
    detector = FundamentalRightsDetector()
    test_text = """
    Every person has the right to freedom of thought and conscience. 
    Equality before the law is guaranteed. The petitioner was arrested without warrant.
    There was torture and degrading treatment. Freedom of speech was violated.
    """
    results = detector.detect(test_text)
    print(f"\nTest results: {len(results)} rights detected")
    import json
    print(json.dumps(results, indent=2))
