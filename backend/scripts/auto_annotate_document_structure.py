"""
Auto-Annotation Script for Document Structure Classification
Automatically labels sections in Sri Lankan legal judgments

Sections to identify:
- FACTS: Background facts of the case
- ISSUES: Legal issues to be determined
- LEGAL_ANALYSIS: Analysis of applicable law
- REASONING: Court's reasoning process
- JUDGMENT: Final decision/ruling
- ORDERS: Specific orders issued
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

# Section identification patterns
SECTION_PATTERNS = {
    'FACTS': [
        # Strong indicators
        (r'(?i)\b(facts?|background|factual\s+background|brief\s+facts?)\b[:\-\s]', 3),
        (r'(?i)^the\s+facts?\s+(?:of\s+)?(?:the\s+)?case\s+(?:are|is)', 3),
        (r'(?i)\bplaintiff[\-\s]respondent\s+instituted\b', 2),
        (r'(?i)\bdefendant[\-\s]appellant\s+filed\b', 2),
        (r'(?i)\b(?:action|suit)\s+was\s+instituted\b', 2),
        
        # Medium indicators
        (r'(?i)\b(?:case|matter)\s+before\s+(?:us|this\s+court)\b', 1.5),
        (r'(?i)\bthe\s+position\s+(?:of|taken\s+by)\b', 1.5),
        (r'(?i)\b(?:petition|application)\s+(?:dated|filed)\b', 1.5),
        
        # Contextual indicators
        (r'(?i)\b(?:brief|summary)\s+of\s+facts?\b', 2),
        (r'(?i)\bthe\s+following\s+facts?\b', 1.5),
    ],
    
    'ISSUES': [
        # Strong indicators
        (r'(?i)\bissues?\s+(?:raised|framed|to\s+be\s+(?:determined|decided|resolved))\b', 3),
        (r'(?i)\bthe\s+questions?\s+(?:before|for)\s+(?:this\s+court|determination)\b', 3),
        (r'(?i)\bpreliminary\s+(?:issue|question|objection)\b', 2.5),
        (r'(?i)\b(?:main|principal|key)\s+issue\b', 2.5),
        
        # Medium indicators
        (r'(?i)\bwhether\s+the\s+(?:appellant|respondent|plaintiff|defendant)\b', 2),
        (r'(?i)\bthe\s+issue\s+is\b', 2),
        (r'(?i)\bquestion\s+arises\b', 2),
        (r'(?i)\b(?:matters|points)\s+(?:for|in)\s+determination\b', 2.5),
        
        # List patterns
        (r'(?i)^\s*\(?[0-9]+\)?\s*whether\b', 2),
        (r'(?i)^\s*\(?[ivx]+\)?\s*whether\b', 2),
    ],
    
    'LEGAL_ANALYSIS': [
        # Strong indicators
        (r'(?i)\blegal\s+(?:analysis|position|framework)\b', 3),
        (r'(?i)\b(?:in\s+terms\s+of|under)\s+section\s+[0-9]+', 2.5),
        (r'(?i)\bthe\s+(?:act|ordinance|law|statute)\s+(?:provides|states|requires)\b', 2.5),
        (r'(?i)\bapplicable\s+(?:law|provision|section)\b', 2.5),
        
        # Medium indicators
        (r'(?i)\b(?:article|section)\s+[0-9]+\s+(?:of|provides)\b', 2),
        (r'(?i)\bthe\s+(?:relevant|pertinent)\s+(?:provision|law)\b', 2),
        (r'(?i)\b(?:statutory|legal)\s+(?:provision|requirement|framework)\b', 2),
        (r'(?i)\bthe\s+code\s+(?:provides|states|requires)\b', 2),
        
        # Case law analysis
        (r'(?i)\bin\s+the\s+case\s+of\b.*?\bheld\s+that\b', 2),
        (r'(?i)\b(?:following|applying)\s+(?:the|this)\s+(?:judgment|decision|case)\b', 2),
    ],
    
    'REASONING': [
        # Strong indicators
        (r'(?i)\breasoning\s+(?:of|by)\s+the\s+court\b', 3),
        (r'(?i)\b(?:having\s+)?considered\s+(?:all\s+)?(?:the\s+)?(?:evidence|submissions|arguments)\b', 2.5),
        (r'(?i)\bin\s+(?:my|our)\s+(?:view|opinion|judgment)\b', 2.5),
        (r'(?i)\bit\s+(?:appears|seems)\s+(?:that|to\s+me|to\s+us)\b', 2.5),
        
        # Medium indicators
        (r'(?i)\b(?:accordingly|therefore|thus|hence|consequently)\b', 2),
        (r'(?i)\bfor\s+the\s+(?:following|aforesaid)\s+reasons?\b', 2.5),
        (r'(?i)\bhaving\s+regard\s+to\b', 2),
        (r'(?i)\bin\s+the\s+circumstances\b', 2),
        
        # Analysis phrases
        (r'(?i)\bit\s+is\s+(?:clear|evident|apparent)\s+that\b', 2),
        (r'(?i)\bthe\s+(?:court|trial\s+judge)\s+(?:held|found|concluded)\b', 2),
        (r'(?i)\b(?:applying|applying\s+these)\s+(?:principles|provisions)\b', 2),
    ],
    
    'JUDGMENT': [
        # Strong indicators
        (r'(?i)\b(?:judgment|decision|ruling)\s+(?:of|by)\s+(?:the\s+)?court\b', 3),
        (r'(?i)\b(?:we|i)\s+(?:hereby\s+)?(?:hold|declare|find)\s+that\b', 3),
        (r'(?i)\bfor\s+the\s+(?:aforesaid|foregoing)\s+reasons?\b', 2.5),
        (r'(?i)\b(?:accordingly|therefore)\s+(?:this|the)\s+(?:appeal|application)\b', 2.5),
        
        # Conclusion markers
        (r'(?i)\bin\s+conclusion\b', 3),
        (r'(?i)\bthe\s+appeal\s+(?:is|will\s+be|must\s+be)\s+(?:allowed|dismissed)\b', 3),
        (r'(?i)\bthe\s+(?:application|petition)\s+(?:is|will\s+be)\s+(?:granted|refused)\b', 3),
        
        # Medium indicators
        (r'(?i)\bit\s+is\s+my\s+view\s+that\b', 2.5),
        (r'(?i)\bi\s+(?:am\s+of\s+the\s+)?(?:view|opinion)\s+that\b', 2.5),
    ],
    
    'ORDERS': [
        # Strong indicators
        (r'(?i)\border[s]?\s+(?:made|issued|granted)\b', 3),
        (r'(?i)\b(?:hereby\s+)?order[s]?\s+(?:that|as\s+follows)\b', 3),
        (r'(?i)\b(?:declare|decree|direct)\s+(?:that|as\s+follows)\b', 3),
        (r'(?i)\bthe\s+following\s+order[s]?\b', 3),
        
        # Specific orders
        (r'(?i)\b(?:appeal|application)\s+(?:is|stands?)\s+(?:allowed|dismissed)\b', 2.5),
        (r'(?i)\bwith\s+costs\s+(?:fixed\s+at|of)\b', 2),
        (r'(?i)\b(?:registrar|clerk)\s+(?:is\s+)?directed\s+to\b', 2.5),
        
        # Relief granted
        (r'(?i)\b(?:entitled|awarded)\s+(?:to|the)\s+(?:costs|damages|relief)\b', 2),
        (r'(?i)\bthe\s+(?:plaintiff|defendant|appellant|respondent)\s+(?:shall|is\s+directed\s+to)\b', 2),
    ],
}

# Additional contextual markers
HEADER_PATTERNS = {
    'court_headings': [
        r'(?i)^(?:supreme\s+court|court\s+of\s+appeal|high\s+court)',
        r'(?i)^\s*(?:CA|SC|HC)\s+(?:NO\.?|NUMBER)?\s*[0-9]+',
    ],
    'case_name': [
        r'(?i)^\s*[A-Z\s]+\s+[Vv]s?\.?\s+[A-Z\s]+\s*$',
    ],
    'judge_name': [
        r'(?i)^\s*(?:HON\.?|HONOURABLE)\s+[A-Z\s\.]+,?\s+(?:J\.?|C\.?J\.?)',
        r'(?i)[A-Z\s\.]+,?\s+J\.?\s*[-\u2014]',
    ],
}

# Paragraph classification weights
PARAGRAPH_MIN_LENGTH = 20  # Minimum characters for a paragraph
CONTEXT_WINDOW = 3  # Look at surrounding paragraphs


class DocumentStructureAnnotator:
    """Automatically annotates legal documents with section labels"""
    
    def __init__(self, input_file: str, output_dir: str):
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.stats = {
            'total_documents': 0,
            'total_paragraphs': 0,
            'section_counts': {section: 0 for section in SECTION_PATTERNS.keys()},
            'unlabeled_paragraphs': 0,
        }
    
    def split_into_paragraphs(self, text: str) -> List[str]:
        """Split document text into paragraphs"""
        # Split by double newlines or page markers
        paragraphs = re.split(r'\n\s*\n+|---\s*Page\s+\d+\s*---', text)
        
        # Filter out very short paragraphs and clean
        cleaned = []
        for para in paragraphs:
            para = para.strip()
            if len(para) >= PARAGRAPH_MIN_LENGTH:
                # Remove excessive whitespace
                para = re.sub(r'\s+', ' ', para)
                cleaned.append(para)
        
        return cleaned
    
    def calculate_section_scores(self, paragraph: str) -> Dict[str, float]:
        """Calculate scores for each section type"""
        scores = {section: 0.0 for section in SECTION_PATTERNS.keys()}
        
        para_lower = paragraph.lower()
        
        for section, patterns in SECTION_PATTERNS.items():
            for pattern, weight in patterns:
                matches = re.findall(pattern, paragraph)
                if matches:
                    # Increase score based on number of matches and weight
                    scores[section] += len(matches) * weight
        
        return scores
    
    def classify_paragraph(self, paragraph: str, context_scores: Dict[str, float] = None) -> Tuple[str, float]:
        """Classify a paragraph into a section type"""
        scores = self.calculate_section_scores(paragraph)
        
        # Add context information if available
        if context_scores:
            for section in scores:
                scores[section] += context_scores.get(section, 0) * 0.3
        
        # Get section with highest score
        if max(scores.values()) > 0:
            best_section = max(scores.items(), key=lambda x: x[1])
            return best_section[0], best_section[1]
        
        return 'UNLABELED', 0.0
    
    def annotate_document(self, document: Dict) -> Dict:
        """Annotate a single document with section labels"""
        text = document.get('cleaned_text', document.get('raw_text', ''))
        paragraphs = self.split_into_paragraphs(text)
        
        annotations = []
        context_window = []
        
        for idx, paragraph in enumerate(paragraphs):
            # Classify current paragraph
            context_scores = {}
            if context_window:
                # Average scores from context window
                for section in SECTION_PATTERNS.keys():
                    context_scores[section] = sum(
                        score.get(section, 0) for score in context_window
                    ) / len(context_window)
            
            section, confidence = self.classify_paragraph(paragraph, context_scores)
            
            annotations.append({
                'paragraph_id': idx,
                'text': paragraph,
                'section': section,
                'confidence': round(confidence, 2),
                'length': len(paragraph),
            })
            
            # Update statistics
            if section != 'UNLABELED':
                self.stats['section_counts'][section] += 1
            else:
                self.stats['unlabeled_paragraphs'] += 1
            
            # Update context window
            scores = self.calculate_section_scores(paragraph)
            context_window.append(scores)
            if len(context_window) > CONTEXT_WINDOW:
                context_window.pop(0)
        
        self.stats['total_paragraphs'] += len(paragraphs)
        
        return {
            'file_name': document.get('file_name', 'unknown'),
            'total_paragraphs': len(paragraphs),
            'annotations': annotations,
            'section_summary': {
                section: len([a for a in annotations if a['section'] == section])
                for section in SECTION_PATTERNS.keys()
            },
        }
    
    def process_all_documents(self) -> Dict:
        """Process all documents and generate annotations"""
        print(f"Loading documents from: {self.input_file}")
        
        with open(self.input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        cases = data.get('cases', [])
        self.stats['total_documents'] = len(cases)
        
        print(f"Found {len(cases)} cases to process")
        
        all_annotations = []
        
        for idx, case in enumerate(cases, 1):
            print(f"Processing case {idx}/{len(cases)}: {case.get('file_name', 'unknown')}")
            
            annotated = self.annotate_document(case)
            all_annotations.append(annotated)
        
        # Save annotated documents
        output_file = self.output_dir / 'document_structure_annotations.json'
        result = {
            'metadata': {
                'total_documents': self.stats['total_documents'],
                'total_paragraphs': self.stats['total_paragraphs'],
                'creation_date': datetime.now().isoformat(),
                'description': 'Document structure annotations for Sri Lankan legal cases',
            },
            'statistics': self.stats,
            'annotations': all_annotations,
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Annotations saved to: {output_file}")
        
        return result
    
    def print_statistics(self):
        """Print annotation statistics"""
        print("\n" + "="*60)
        print("DOCUMENT STRUCTURE ANNOTATION STATISTICS")
        print("="*60)
        print(f"Total documents processed: {self.stats['total_documents']}")
        print(f"Total paragraphs analyzed: {self.stats['total_paragraphs']}")
        print(f"\nSection Distribution:")
        print("-"*60)
        
        for section, count in sorted(self.stats['section_counts'].items(), 
                                     key=lambda x: x[1], reverse=True):
            percentage = (count / self.stats['total_paragraphs'] * 100) if self.stats['total_paragraphs'] > 0 else 0
            print(f"  {section:20s}: {count:5d} paragraphs ({percentage:5.2f}%)")
        
        unlabeled_pct = (self.stats['unlabeled_paragraphs'] / self.stats['total_paragraphs'] * 100) if self.stats['total_paragraphs'] > 0 else 0
        print(f"  {'UNLABELED':20s}: {self.stats['unlabeled_paragraphs']:5d} paragraphs ({unlabeled_pct:5.2f}%)")
        print("="*60)
        
        # Average per document
        if self.stats['total_documents'] > 0:
            avg_paras = self.stats['total_paragraphs'] / self.stats['total_documents']
            print(f"\nAverage paragraphs per document: {avg_paras:.1f}")
        
        print()


def main():
    """Main execution function"""
    # Input and output paths
    input_file = r'e:\ai-legal-summarizer\data\processed\combined_legal_cases.json'
    output_dir = r'e:\ai-legal-summarizer\data\training_data\document_structure_annotations'
    
    print("="*60)
    print("AUTO-ANNOTATION: DOCUMENT STRUCTURE CLASSIFICATION")
    print("="*60)
    print(f"Input: {input_file}")
    print(f"Output: {output_dir}")
    print("="*60)
    print()
    
    # Create annotator and process
    annotator = DocumentStructureAnnotator(input_file, output_dir)
    result = annotator.process_all_documents()
    annotator.print_statistics()
    
    print("\n✅ Auto-annotation complete!")
    print(f"📁 Annotations saved in: {output_dir}")
    print(f"📊 Labeled {result['statistics']['total_paragraphs']} paragraphs")
    print(f"📄 From {result['statistics']['total_documents']} documents")


if __name__ == '__main__':
    main()
