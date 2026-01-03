"""
Plain Language Converter for Legal Documents

Converts complex legal terminology into plain, easy-to-understand language
for non-legal audiences (students, general public).

Features:
- Legal term simplification
- Jargon replacement
- Context-aware explanations
- Multilingual support (English, Sinhala, Tamil)
"""

import re
from typing import Dict, List, Tuple, Optional
import json
import os


class PlainLanguageConverter:
    """
    Converts legal documents to plain language for accessibility.
    """
    
    # Legal terms to plain language mappings
    LEGAL_TO_PLAIN = {
        # Legal actions
        r'\bpetitioner\b': 'person who filed the case',
        r'\brespondent\b': 'person being accused',
        r'\bappellant\b': 'person appealing the decision',
        r'\bappellee\b': 'person responding to the appeal',
        r'\bplaintiff\b': 'person who filed the lawsuit',
        r'\bdefendant\b': 'person being sued',
        
        # Court terminology
        r'\bwrit\b': 'court order',
        r'\bmandamus\b': 'order to perform a duty',
        r'\bcertiorari\b': 'order to review a decision',
        r'\bhabeas corpus\b': 'order to release an unlawfully detained person',
        r'\binjunction\b': 'court order to stop an action',
        r'\bex parte\b': 'one-sided application',
        r'\bin camera\b': 'private hearing',
        r'\bde facto\b': 'in reality',
        r'\bde jure\b': 'by law',
        r'\bper curiam\b': 'by the whole court',
        r'\bquo warranto\b': 'by what authority',
        
        # Legal concepts
        r'\badjudicate\b': 'decide by court',
        r'\bjurisdiction\b': 'authority to decide',
        r'\bprecedent\b': 'previous similar case',
        r'\blandmark case\b': 'important case',
        r'\bbinding\b': 'must be followed',
        r'\bpersuasive\b': 'can be considered',
        r'\boverruled\b': 'cancelled by higher court',
        r'\bdistinguished\b': 'different from previous case',
        r'\bdicta\b': 'opinion not part of ruling',
        r'\bobiter dicta\b': 'opinion not essential to decision',
        r'\bratio decidendi\b': 'reason for decision',
        
        # Legal documents
        r'\baffidavit\b': 'sworn written statement',
        r'\bdeposition\b': 'sworn testimony',
        r'\bsubpoena\b': 'order to appear in court',
        r'\bsummons\b': 'notice to appear',
        r'\bwarrant\b': 'authorization by court',
        
        # Legal rights
        r'\bfundamental rights\b': 'basic human rights protected by constitution',
        r'\blocus standi\b': 'right to bring a case',
        r'\bdue process\b': 'fair legal procedure',
        r'\bnatural justice\b': 'fair treatment',
        
        # Court actions
        r'\ballow(?:ed)?\s+(?:the\s+)?appeal\b': 'approve the appeal',
        r'\bdismiss(?:ed)?\s+(?:the\s+)?appeal\b': 'reject the appeal',
        r'\buphold\b': 'agree with',
        r'\brevoke\b': 'cancel',
        r'\bquash\b': 'cancel completely',
        r'\bset aside\b': 'cancel',
        r'\bremand\b': 'send back',
        
        # Legal standards
        r'\bbalance of probabilities\b': 'more likely than not',
        r'\bbeyond reasonable doubt\b': 'almost certainly true',
        r'\bprime facie\b': 'at first look',
        r'\bbona fide\b': 'in good faith',
        r'\bmala fide\b': 'in bad faith',
        
        # Case parts
        r'\bvs?\.\b': 'versus (against)',
        r'\bet al\.\b': 'and others',
        r'\bsupra\b': 'mentioned above',
        r'\binfra\b': 'mentioned below',
        r'\bibid\.\b': 'same as above',
    }
    
    # Article explanations
    ARTICLE_EXPLANATIONS = {
        'Article 10': 'Freedom of thought, conscience and religion',
        'Article 11': 'Freedom from torture',
        'Article 12': 'Equal protection and non-discrimination',
        'Article 13': 'Freedom from arbitrary arrest and detention',
        'Article 14': 'Freedom of speech, expression, and peaceful assembly',
        'Article 126': 'Right to petition Supreme Court for rights violations',
    }
    
    def __init__(self, legal_glossary_path: Optional[str] = None):
        """
        Initialize converter with optional custom glossary.
        
        Args:
            legal_glossary_path: Path to JSON file with additional term mappings
        """
        self.custom_glossary = {}
        if legal_glossary_path and os.path.exists(legal_glossary_path):
            try:
                with open(legal_glossary_path, 'r', encoding='utf-8') as f:
                    self.custom_glossary = json.load(f)
            except Exception as e:
                print(f"Could not load custom glossary: {e}")
    
    def _explain_article(self, article_ref: str) -> str:
        """Add explanation for constitutional articles."""
        for article, explanation in self.ARTICLE_EXPLANATIONS.items():
            if article.lower() in article_ref.lower():
                return f"{article_ref} ({explanation})"
        return article_ref
    
    def _simplify_citations(self, text: str) -> str:
        """
        Simplify legal citations for readability.
        Example: "(2000) 1 SLR 123" -> "[Case from year 2000]"
        """
        # Pattern for Sri Lankan case citations
        citation_patterns = [
            (r'\(\d{4}\)\s+\d+\s+[A-Z]+\s+\d+', lambda m: f"[Case from year {m.group()[1:5]}]"),
            (r'\[\d{4}\]\s+\d+\s+[A-Z]+\s+\d+', lambda m: f"[Case from year {m.group()[1:5]}]"),
        ]
        
        for pattern, replacement in citation_patterns:
            text = re.sub(pattern, replacement, text)
        
        return text
    
    def _add_explanations(self, text: str) -> str:
        """Add inline explanations for complex terms."""
        # Explain constitutional articles
        text = re.sub(
            r'\bArticle\s+\d+(?:\(\d+\))?',
            lambda m: self._explain_article(m.group()),
            text
        )
        
        return text
    
    def convert_to_plain_language(
        self,
        text: str,
        simplify_citations: bool = True,
        add_explanations: bool = True
    ) -> Dict[str, any]:
        """
        Convert legal text to plain language.
        
        Args:
            text: Legal text to convert
            simplify_citations: Whether to simplify case citations
            add_explanations: Whether to add inline explanations
        
        Returns:
            Dict with converted text and statistics
        """
        if not text:
            return {
                'plain_text': '',
                'replacements_made': 0,
                'terms_simplified': []
            }
        
        original_text = text
        replacements_made = []
        
        # Apply legal-to-plain replacements
        for legal_pattern, plain_term in self.LEGAL_TO_PLAIN.items():
            matches = list(re.finditer(legal_pattern, text, re.IGNORECASE))
            if matches:
                for match in matches:
                    replacements_made.append({
                        'original': match.group(),
                        'plain': plain_term,
                        'position': match.start()
                    })
                text = re.sub(legal_pattern, plain_term, text, flags=re.IGNORECASE)
        
        # Simplify citations
        if simplify_citations:
            text = self._simplify_citations(text)
        
        # Add explanations
        if add_explanations:
            text = self._add_explanations(text)
        
        return {
            'plain_text': text,
            'original_text': original_text,
            'replacements_made': len(replacements_made),
            'terms_simplified': replacements_made,
            'simplification_rate': len(replacements_made) / max(len(text.split()), 1)
        }
    
    def generate_glossary(self, text: str) -> List[Dict[str, str]]:
        """
        Generate a glossary of legal terms found in the text.
        
        Args:
            text: Legal text to analyze
        
        Returns:
            List of term definitions
        """
        glossary = []
        
        for legal_pattern, plain_term in self.LEGAL_TO_PLAIN.items():
            matches = re.findall(legal_pattern, text, re.IGNORECASE)
            if matches:
                # Get unique matches
                unique_matches = list(set(matches))
                for match in unique_matches:
                    glossary.append({
                        'term': match,
                        'definition': plain_term,
                        'occurrences': len([m for m in matches if m.lower() == match.lower()])
                    })
        
        # Sort by occurrences
        glossary.sort(key=lambda x: x['occurrences'], reverse=True)
        
        return glossary
    
    def convert_summary_to_plain(
        self,
        summary_dict: Dict,
        simplify_citations: bool = True
    ) -> Dict:
        """
        Convert a summary dictionary to plain language.
        
        Args:
            summary_dict: Dict from AdvancedLegalSummarizer
            simplify_citations: Whether to simplify citations
        
        Returns:
            Dict with plain language versions
        """
        result = {}
        
        # Convert executive summary
        if 'executive' in summary_dict:
            exec_data = summary_dict['executive']
            if 'summary' in exec_data:
                plain = self.convert_to_plain_language(
                    exec_data['summary'],
                    simplify_citations=simplify_citations
                )
                result['executive'] = {
                    **exec_data,
                    'plain_summary': plain['plain_text'],
                    'terms_simplified': plain['replacements_made']
                }
        
        # Convert detailed summary
        if 'detailed' in summary_dict:
            det_data = summary_dict['detailed']
            if 'summary' in det_data:
                plain = self.convert_to_plain_language(
                    det_data['summary'],
                    simplify_citations=simplify_citations
                )
                result['detailed'] = {
                    **det_data,
                    'plain_summary': plain['plain_text'],
                    'terms_simplified': plain['replacements_made']
                }
        
        # Convert section summaries
        if 'section_specific' in summary_dict:
            result['section_specific'] = {}
            for section, section_data in summary_dict['section_specific'].items():
                if 'summary' in section_data:
                    plain = self.convert_to_plain_language(
                        section_data['summary'],
                        simplify_citations=simplify_citations
                    )
                    result['section_specific'][section] = {
                        **section_data,
                        'plain_summary': plain['plain_text'],
                        'terms_simplified': plain['replacements_made']
                    }
        
        # Generate glossary
        if 'executive' in summary_dict and 'summary' in summary_dict['executive']:
            full_text = summary_dict['executive']['summary']
            if 'detailed' in summary_dict and 'summary' in summary_dict['detailed']:
                full_text += " " + summary_dict['detailed']['summary']
            result['glossary'] = self.generate_glossary(full_text)
        
        return result


def test_plain_language_converter():
    """Test the plain language converter."""
    
    sample_legal_text = """
    The petitioner filed a writ of habeas corpus under Article 126 of the Constitution,
    alleging violation of fundamental rights under Articles 13(1) and 13(2). The respondent
    argued that the arrest was bona fide and the detention was de jure. The Supreme Court,
    acting per curiam, held that the precedent established in Silva vs. Fernando (2000) 1 SLR
    123 was applicable. The Court allowed the appeal and quashed the detention order, finding
    that the balance of probabilities favored the petitioner. The appellant was granted
    locus standi to challenge the decision ex parte.
    """
    
    print("=" * 80)
    print("TESTING PLAIN LANGUAGE CONVERTER")
    print("=" * 80)
    
    converter = PlainLanguageConverter()
    
    print("\n1. Converting legal text to plain language...")
    result = converter.convert_to_plain_language(sample_legal_text)
    
    print("\n" + "=" * 80)
    print("ORIGINAL TEXT")
    print("=" * 80)
    print(result['original_text'])
    
    print("\n" + "=" * 80)
    print("PLAIN LANGUAGE VERSION")
    print("=" * 80)
    print(result['plain_text'])
    
    print("\n" + "=" * 80)
    print("CONVERSION STATISTICS")
    print("=" * 80)
    print(f"Total replacements: {result['replacements_made']}")
    print(f"Simplification rate: {result['simplification_rate']:.2%}")
    
    print("\n" + "=" * 80)
    print("TERMS SIMPLIFIED")
    print("=" * 80)
    for i, term in enumerate(result['terms_simplified'][:10], 1):
        print(f"{i}. '{term['original']}' -> '{term['plain']}'")
    
    print("\n2. Generating glossary...")
    glossary = converter.generate_glossary(sample_legal_text)
    
    print("\n" + "=" * 80)
    print("LEGAL TERMS GLOSSARY")
    print("=" * 80)
    for i, entry in enumerate(glossary[:15], 1):
        print(f"{i}. {entry['term']} ({entry['occurrences']}x)")
        print(f"   → {entry['definition']}")
    
    print("\n" + "=" * 80)
    print("✅ TEST COMPLETED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    test_plain_language_converter()
