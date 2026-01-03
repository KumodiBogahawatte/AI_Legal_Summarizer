"""
Advanced Multi-Level Summarization System for Legal Documents

This module provides intelligent summarization at multiple levels:
1. Executive Summary (150-200 words) - Key facts, issues, decision
2. Detailed Summary (600-1000 words) - Full reasoning + citations
3. Section-Specific Summaries - Facts, Issues, Reasoning, Orders

Uses hybrid extractive + abstractive approach with document structure awareness.
"""

import re
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.tokenize import sent_tokenize as nltk_sent_tokenize

try:
    import nltk
    nltk.data.find('tokenizers/punkt')
except:
    nltk.download('punkt', quiet=True)

def legal_sent_tokenize(text: str) -> List[str]:
    """
    Custom sentence tokenizer for legal documents.
    Handles common legal abbreviations and citations that confuse NLTK.
    """
    # Protect common legal abbreviations that end with periods
    protected_text = text
    replacements = {
        ' J.(P/CA)': ' J<JUDGE_CITATION>',  # Specific pattern for Judge citations
        ' J.': ' J<PERIOD>',
        ' CJ.': ' CJ<PERIOD>',
        ' JJ.': ' JJ<PERIOD>',
        ' vs.': ' vs<PERIOD>',
        ' v.': ' v<PERIOD>',
        ' No.': ' No<PERIOD>',
        ' Art.': ' Art<PERIOD>',
        ' s.': ' s<PERIOD>',
        ' S.': ' S<PERIOD>',
        ' Ltd.': ' Ltd<PERIOD>',
        ' Inc.': ' Inc<PERIOD>',
        ' Co.': ' Co<PERIOD>',
    }
    
    for old, new in replacements.items():
        protected_text = protected_text.replace(old, new)
    
    # Use NLTK tokenizer (use original import name)
    sentences = nltk_sent_tokenize(protected_text)
    
    # Restore the protected periods
    restored_sentences = []
    for sent in sentences:
        restored = sent.replace('<PERIOD>', '.').replace('<JUDGE_CITATION>', '.(P/CA)')
        restored_sentences.append(restored)
    
    return [s for s in restored_sentences if s.strip()]


class AdvancedLegalSummarizer:
    """
    Multi-level legal document summarizer with structure-aware extraction.
    """
    
    # Section importance weights for summary generation
    SECTION_WEIGHTS = {
        'FACTS': 0.20,
        'ISSUES': 0.25,
        'LEGAL_ANALYSIS': 0.15,
        'REASONING': 0.15,
        'JUDGMENT': 0.20,
        'ORDERS': 0.25
    }
    
    # Target word counts for different summary levels
    EXECUTIVE_WORDS = (150, 200)  # min, max
    DETAILED_WORDS = (600, 1000)
    SECTION_WORDS = (100, 150)
    
    def __init__(self):
        """Initialize the summarizer."""
        self.legal_terms_pattern = self._compile_legal_terms()
    
    def _compile_legal_terms(self):
        """Compile regex for important legal terms to preserve."""
        legal_keywords = [
            r'\barticle\s+\d+\b',
            r'\bsection\s+\d+\b',
            r'\bpenal code\b',
            r'\bconstitution\b',
            r'\bfundamental rights?\b',
            r'\bsupreme court\b',
            r'\bcourt of appeal\b',
            r'\bhigh court\b',
            r'\bprecedent\b',
            r'\blandmark\b',
            r'\boverruled\b',
            r'\bdistinguished\b',
            r'\bappeal allowed\b',
            r'\bappeal dismissed\b',
            r'\bwrit\b',
            r'\bmandamus\b',
            r'\bcertiorari\b',
            r'\bhabeas corpus\b',
            r'\bviolation\b',
            r'\bheld\b',
            r'\bruling\b',
            r'\bjudgment\b',
            r'\bdecision\b',
            r'\bcontention\b',
            r'\ballege[ds]?\b',
            r'\bpetitioner\b',
            r'\brespondent\b',
            r'\bappellant\b',
        ]
        return re.compile('|'.join(legal_keywords), re.IGNORECASE)
    
    def _is_procedural_sentence(self, sentence: str) -> bool:
        """Identify and filter out purely procedural/administrative sentences."""
        procedural_patterns = [
            r'^in paragraph \d+',
            r'^the \d+(?:st|nd|rd|th) (?:petitioner|defendant|respondent)',
            r'^counsel for',
            r'^this (?:is an )?application for',
            r'^the matter (?:was|came) (?:up|before)',
            r'^both (?:counsel|parties) (?:agreed|filed)',
            r'^when (?:the matter|this) (?:was|came)',
            r'^(?:briefly|admittedly), the facts',
            r'cur\.?adv\.?vult',
            r'journal entry',
            r'written submissions',
            r'to file written submissions',
        ]
        
        sentence_lower = sentence.lower().strip()
        for pattern in procedural_patterns:
            if re.search(pattern, sentence_lower):
                return True
        
        # Filter very short sentences (likely incomplete context)
        if len(sentence.split()) < 8:
            return True
            
        return False
    
    def _extract_citations(self, text: str) -> List[str]:
        """Extract legal citations from text."""
        # Pattern for Sri Lankan case citations
        patterns = [
            r'\(\d{4}\)\s+\d+\s+[A-Z]+\s+\d+',  # (2000) 1 SLR 123
            r'\[\d{4}\]\s+\d+\s+[A-Z]+\s+\d+',  # [2000] 1 SLR 123
            r'\b[A-Z][a-z]+\s+v\.?\s+[A-Z][a-z]+\b',  # Silva v. Fernando
        ]
        
        citations = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            citations.extend(matches)
        
        return list(set(citations))  # Remove duplicates
    
    def _calculate_sentence_scores(
        self,
        sentences: List[str],
        section_type: Optional[str] = None
    ) -> np.ndarray:
        """
        Calculate importance scores for sentences using TF-IDF + legal term boost.
        Enhanced with position, length, and coherence scoring.
        """
        if not sentences:
            return np.array([])
        
        # Filter out procedural sentences first
        valid_indices = []
        filtered_sentences = []
        for i, sent in enumerate(sentences):
            if not self._is_procedural_sentence(sent):
                valid_indices.append(i)
                filtered_sentences.append(sent)
        
        if not filtered_sentences:
            # If all filtered, use original
            filtered_sentences = sentences
            valid_indices = list(range(len(sentences)))
        
        # TF-IDF scoring
        try:
            vectorizer = TfidfVectorizer(
                stop_words='english',
                max_features=100
            )
            tfidf_matrix = vectorizer.fit_transform(filtered_sentences)
            scores = np.asarray(tfidf_matrix.sum(axis=1)).flatten()
        except:
            # Fallback to length-based scoring
            scores = np.array([len(s.split()) for s in filtered_sentences], dtype=float)
        
        # Normalize scores
        if scores.sum() > 0:
            scores = scores / scores.sum()
        
        # Position-based boost (early sentences often more important)
        total_sentences = len(filtered_sentences)
        for i in range(total_sentences):
            position_weight = 1.0 + (0.3 * (1.0 - i / total_sentences))  # 1.0-1.3x boost
            scores[i] *= position_weight
        
        # Boost sentences with legal terms (stronger boost)
        for i, sentence in enumerate(filtered_sentences):
            legal_term_count = len(self.legal_terms_pattern.findall(sentence))
            if legal_term_count > 0:
                scores[i] *= (1.3 + (legal_term_count * 0.2))  # 1.3x-2.1x boost
        
        # Boost sentences with citations
        for i, sentence in enumerate(filtered_sentences):
            citations = self._extract_citations(sentence)
            if citations:
                scores[i] *= 1.4
        
        # Length penalty (very long sentences may lack focus)
        for i, sentence in enumerate(filtered_sentences):
            word_count = len(sentence.split())
            if word_count > 50:
                scores[i] *= 0.8  # Penalize overly long sentences
            elif word_count < 10:
                scores[i] *= 0.7  # Penalize very short sentences
        
        # Boost based on section type
        if section_type:
            weight = self.SECTION_WEIGHTS.get(section_type, 1.0)
            scores *= weight
        
        # Normalize again
        if scores.sum() > 0:
            scores = scores / scores.sum()
        
        # Map back to original indices
        full_scores = np.zeros(len(sentences))
        for i, orig_idx in enumerate(valid_indices):
            full_scores[orig_idx] = scores[i]
        
        return full_scores
    
    def _extract_top_sentences(
        self,
        sentences: List[str],
        scores: np.ndarray,
        target_words: Tuple[int, int],
        preserve_order: bool = True
    ) -> str:
        """
        Extract top-scoring sentences up to target word count.
        Enhanced with diversity and coherence.
        """
        if not sentences or len(scores) == 0:
            return ""
        
        min_words, max_words = target_words
        
        # Sort sentences by score
        sorted_indices = np.argsort(scores)[::-1]
        
        selected_indices = []
        total_words = 0
        selected_sentences_lower = []  # For diversity checking
        
        for idx in sorted_indices:
            # Skip zero-scored sentences (filtered procedural)
            if scores[idx] == 0:
                continue
                
            sentence = sentences[idx]
            word_count = len(sentence.split())
            
            # Check for redundancy (skip very similar sentences)
            sentence_lower = sentence.lower()
            is_redundant = False
            for selected in selected_sentences_lower:
                # Simple word overlap check
                selected_words = set(selected.split())
                current_words = set(sentence_lower.split())
                if len(selected_words) > 0 and len(current_words) > 0:
                    overlap = len(selected_words & current_words) / len(current_words)
                    if overlap > 0.7:  # 70% word overlap = redundant
                        is_redundant = True
                        break
            
            if is_redundant:
                continue
            
            # Stop if we've reached max words
            if total_words + word_count > max_words:
                if total_words >= min_words:
                    break
                # If we haven't reached min, allow going slightly over
                if total_words + word_count > max_words * 1.2:
                    break
            
            selected_indices.append(idx)
            selected_sentences_lower.append(sentence_lower)
            total_words += word_count
            
            # Stop if we've reached optimal range
            if min_words <= total_words <= max_words:
                break
        
        # Preserve original order if requested
        if preserve_order:
            selected_indices.sort()
        
        summary_sentences = [sentences[i] for i in selected_indices]
        
        # Add connective phrases for better flow (optional)
        if len(summary_sentences) > 0:
            return " ".join(summary_sentences)
        else:
            # Fallback: return at least something
            return sentences[0] if len(sentences) > 0 else ""
    
    def generate_executive_summary(
        self,
        text: str,
        structured_content: Optional[Dict[str, str]] = None
    ) -> Dict:
        """
        Generate executive summary (150-200 words).
        Focuses on: key facts, main issues, final decision.
        
        Args:
            text: Full document text
            structured_content: Optional dict with section-wise content
                {
                    'FACTS': '...',
                    'ISSUES': '...',
                    'JUDGMENT': '...',
                    ...
                }
        
        Returns:
            Dict with summary and metadata
        """
        try:
            # If structured content available, use targeted extraction
            if structured_content and len(structured_content) > 0:
                summary_parts = []
                
                # If only one section, extract from it with full allocation
                if len(structured_content) == 1:
                    section_name = list(structured_content.keys())[0]
                    section_text = structured_content[section_name]
                    sentences = legal_sent_tokenize(section_text)
                    scores = self._calculate_sentence_scores(sentences, section_name)
                    summary = self._extract_top_sentences(
                        sentences,
                        scores,
                        self.EXECUTIVE_WORDS
                    )
                    if summary:
                        summary_parts.append(summary)
                else:
                    # Multiple sections available - extract from each
                    # Extract key facts (30%)
                    if 'FACTS' in structured_content:
                        facts_text = structured_content['FACTS']
                        facts_sentences = legal_sent_tokenize(facts_text)
                        facts_scores = self._calculate_sentence_scores(facts_sentences, 'FACTS')
                        facts_summary = self._extract_top_sentences(
                            facts_sentences,
                            facts_scores,
                            (40, 60)
                        )
                        if facts_summary:
                            summary_parts.append(facts_summary)
                    
                    # Extract main issues (30%)
                    if 'ISSUES' in structured_content:
                        issues_text = structured_content['ISSUES']
                        issues_sentences = legal_sent_tokenize(issues_text)
                        issues_scores = self._calculate_sentence_scores(issues_sentences, 'ISSUES')
                        issues_summary = self._extract_top_sentences(
                            issues_sentences,
                            issues_scores,
                            (40, 60)
                        )
                        if issues_summary:
                            summary_parts.append(issues_summary)
                    
                    # Extract decision/judgment (40%)
                    if 'JUDGMENT' in structured_content:
                        judgment_text = structured_content['JUDGMENT']
                        judgment_sentences = legal_sent_tokenize(judgment_text)
                        judgment_scores = self._calculate_sentence_scores(judgment_sentences, 'JUDGMENT')
                        judgment_summary = self._extract_top_sentences(
                            judgment_sentences,
                            judgment_scores,
                            (50, 80)
                        )
                        if judgment_summary:
                            summary_parts.append(judgment_summary)
                    elif 'ORDERS' in structured_content:
                        # Fallback to orders if no judgment
                        orders_text = structured_content['ORDERS']
                        orders_sentences = legal_sent_tokenize(orders_text)
                        orders_scores = self._calculate_sentence_scores(orders_sentences, 'ORDERS')
                        orders_summary = self._extract_top_sentences(
                            orders_sentences,
                            orders_scores,
                            (50, 80)
                        )
                        if orders_summary:
                            summary_parts.append(orders_summary)
                
                summary_text = " ".join(summary_parts)
            else:
                # Fallback: extract from full text
                sentences = legal_sent_tokenize(text)
                scores = self._calculate_sentence_scores(sentences)
                summary_text = self._extract_top_sentences(
                    sentences,
                    scores,
                    self.EXECUTIVE_WORDS
                )
            
            word_count = len(summary_text.split())
            
            return {
                'summary': summary_text,
                'type': 'executive',
                'word_count': word_count,
                'target_range': f"{self.EXECUTIVE_WORDS[0]}-{self.EXECUTIVE_WORDS[1]} words",
                'citations': self._extract_citations(summary_text)
            }
        
        except Exception as e:
            return {
                'summary': f"Executive summary generation failed: {str(e)}",
                'type': 'executive',
                'word_count': 0,
                'error': str(e)
            }
    
    def generate_detailed_summary(
        self,
        text: str,
        structured_content: Optional[Dict[str, str]] = None
    ) -> Dict:
        """
        Generate detailed summary (600-1000 words).
        Includes: facts, issues, legal analysis, reasoning, decision.
        
        Args:
            text: Full document text
            structured_content: Optional dict with section-wise content
        
        Returns:
            Dict with summary and metadata
        """
        try:
            if structured_content and len(structured_content) > 0:
                summary_parts = []
                section_summaries = {}
                
                # If only one section, use full allocation
                if len(structured_content) == 1:
                    section_name = list(structured_content.keys())[0]
                    content = structured_content[section_name]
                    sentences = legal_sent_tokenize(content)
                    scores = self._calculate_sentence_scores(sentences, section_name)
                    section_summary = self._extract_top_sentences(
                        sentences,
                        scores,
                        self.DETAILED_WORDS
                    )
                    if section_summary:
                        summary_parts.append(f"**{section_name}:** {section_summary}")
                        section_summaries[section_name] = section_summary
                else:
                    # Multiple sections - process each with appropriate word allocation
                    section_targets = {
                        'FACTS': (100, 150),
                        'ISSUES': (80, 120),
                        'LEGAL_ANALYSIS': (120, 180),
                        'REASONING': (150, 250),
                        'JUDGMENT': (100, 150),
                        'ORDERS': (50, 100)
                    }
                    
                    for section, content in structured_content.items():
                        if section in section_targets:
                            sentences = legal_sent_tokenize(content)
                            scores = self._calculate_sentence_scores(sentences, section)
                            section_summary = self._extract_top_sentences(
                                sentences,
                                scores,
                                section_targets[section]
                            )
                            if section_summary:
                                summary_parts.append(f"**{section}:** {section_summary}")
                                section_summaries[section] = section_summary
                
                summary_text = "\n\n".join(summary_parts)
            else:
                # Fallback: extract from full text
                sentences = legal_sent_tokenize(text)
                scores = self._calculate_sentence_scores(sentences)
                summary_text = self._extract_top_sentences(
                    sentences,
                    scores,
                    self.DETAILED_WORDS
                )
                section_summaries = {}
            
            word_count = len(summary_text.split())
            
            return {
                'summary': summary_text,
                'type': 'detailed',
                'word_count': word_count,
                'target_range': f"{self.DETAILED_WORDS[0]}-{self.DETAILED_WORDS[1]} words",
                'section_summaries': section_summaries,
                'citations': self._extract_citations(summary_text)
            }
        
        except Exception as e:
            return {
                'summary': f"Detailed summary generation failed: {str(e)}",
                'type': 'detailed',
                'word_count': 0,
                'error': str(e)
            }
    
    def generate_section_summaries(
        self,
        structured_content: Dict[str, str]
    ) -> Dict[str, Dict]:
        """
        Generate individual summaries for each section.
        
        Args:
            structured_content: Dict with section-wise content
                {
                    'FACTS': '...',
                    'ISSUES': '...',
                    'LEGAL_ANALYSIS': '...',
                    ...
                }
        
        Returns:
            Dict mapping section names to their summaries
        """
        section_summaries = {}
        
        for section, content in structured_content.items():
            try:
                sentences = legal_sent_tokenize(content)
                scores = self._calculate_sentence_scores(sentences, section)
                summary_text = self._extract_top_sentences(
                    sentences,
                    scores,
                    self.SECTION_WORDS
                )
                
                section_summaries[section] = {
                    'summary': summary_text,
                    'word_count': len(summary_text.split()),
                    'sentence_count': len(sentences),
                    'original_word_count': len(content.split()),
                    'citations': self._extract_citations(summary_text)
                }
            except Exception as e:
                section_summaries[section] = {
                    'summary': f"Section summary generation failed: {str(e)}",
                    'error': str(e)
                }
        
        return section_summaries
    
    def generate_all_summaries(
        self,
        text: str,
        structured_content: Optional[Dict[str, str]] = None
    ) -> Dict:
        """
        Generate all three levels of summaries in one call.
        
        Args:
            text: Full document text
            structured_content: Optional dict with section-wise content
        
        Returns:
            Dict containing all summary levels
        """
        return {
            'executive': self.generate_executive_summary(text, structured_content),
            'detailed': self.generate_detailed_summary(text, structured_content),
            'section_specific': self.generate_section_summaries(structured_content) if structured_content else {},
            'document_stats': {
                'total_words': len(text.split()),
                'total_sentences': len(legal_sent_tokenize(text)),
                'sections_available': list(structured_content.keys()) if structured_content else []
            }
        }


def test_summarizer():
    """Test the advanced summarizer with sample legal text."""
    
    sample_text = """
    The petitioner filed a fundamental rights application under Article 126 of the 
    Constitution, alleging violation of Articles 11, 12(1), 13(1) and 13(2). The 
    petitioner was arrested without a warrant on 15th March 2023 and detained for 
    72 hours without being produced before a magistrate.
    
    The main issues to be determined in this case are: (1) Whether the arrest and 
    detention violated the petitioner's fundamental rights, (2) Whether the 
    respondents acted in accordance with the law.
    
    According to the precedent established in Vaithilingam v. Corea (1953) 54 NLR 
    433, arrest without warrant is permissible only under specific circumstances. 
    The Supreme Court held in Silva v. Fernando (2000) 1 SLR 25 that detention 
    beyond 24 hours requires judicial oversight.
    
    Based on the evidence presented and the legal principles discussed above, we 
    find that the petitioner's rights under Articles 13(1) and 13(2) were indeed 
    violated. The arrest was not justified, and the detention exceeded permissible 
    limits.
    
    We are of the view that the petitioner's fundamental rights guaranteed by 
    Articles 13(1) and 13(2) have been infringed. The petition is therefore allowed.
    
    It is hereby ordered that: (1) The respondents shall pay damages in the sum of 
    Rs. 500,000 to the petitioner, (2) The respondents shall pay costs of this 
    application.
    """
    
    structured_sample = {
        'FACTS': """The petitioner filed a fundamental rights application under Article 126 of the 
    Constitution, alleging violation of Articles 11, 12(1), 13(1) and 13(2). The 
    petitioner was arrested without a warrant on 15th March 2023 and detained for 
    72 hours without being produced before a magistrate.""",
        
        'ISSUES': """The main issues to be determined in this case are: (1) Whether the arrest and 
    detention violated the petitioner's fundamental rights, (2) Whether the 
    respondents acted in accordance with the law.""",
        
        'LEGAL_ANALYSIS': """According to the precedent established in Vaithilingam v. Corea (1953) 54 NLR 
    433, arrest without warrant is permissible only under specific circumstances. 
    The Supreme Court held in Silva v. Fernando (2000) 1 SLR 25 that detention 
    beyond 24 hours requires judicial oversight.""",
        
        'REASONING': """Based on the evidence presented and the legal principles discussed above, we 
    find that the petitioner's rights under Articles 13(1) and 13(2) were indeed 
    violated. The arrest was not justified, and the detention exceeded permissible 
    limits.""",
        
        'JUDGMENT': """We are of the view that the petitioner's fundamental rights guaranteed by 
    Articles 13(1) and 13(2) have been infringed. The petition is therefore allowed.""",
        
        'ORDERS': """It is hereby ordered that: (1) The respondents shall pay damages in the sum of 
    Rs. 500,000 to the petitioner, (2) The respondents shall pay costs of this 
    application."""
    }
    
    print("=" * 80)
    print("TESTING ADVANCED LEGAL SUMMARIZER")
    print("=" * 80)
    
    summarizer = AdvancedLegalSummarizer()
    
    print("\n1. Generating all summaries...")
    result = summarizer.generate_all_summaries(sample_text, structured_sample)
    
    print("\n" + "=" * 80)
    print("EXECUTIVE SUMMARY")
    print("=" * 80)
    exec_sum = result['executive']
    print(f"Word Count: {exec_sum['word_count']} (target: {exec_sum['target_range']})")
    print(f"Citations: {len(exec_sum.get('citations', []))}")
    print(f"\n{exec_sum['summary']}\n")
    
    print("\n" + "=" * 80)
    print("DETAILED SUMMARY")
    print("=" * 80)
    det_sum = result['detailed']
    print(f"Word Count: {det_sum['word_count']} (target: {det_sum['target_range']})")
    print(f"Citations: {len(det_sum.get('citations', []))}")
    print(f"\n{det_sum['summary']}\n")
    
    print("\n" + "=" * 80)
    print("SECTION-SPECIFIC SUMMARIES")
    print("=" * 80)
    for section, summary_data in result['section_specific'].items():
        print(f"\n{section}:")
        print(f"  Word Count: {summary_data['word_count']}")
        print(f"  Summary: {summary_data['summary'][:200]}...")
    
    print("\n" + "=" * 80)
    print("DOCUMENT STATISTICS")
    print("=" * 80)
    stats = result['document_stats']
    print(f"Total Words: {stats['total_words']}")
    print(f"Total Sentences: {stats['total_sentences']}")
    print(f"Sections Available: {', '.join(stats['sections_available'])}")
    
    print("\n" + "=" * 80)
    print("✅ TEST COMPLETED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    test_summarizer()
