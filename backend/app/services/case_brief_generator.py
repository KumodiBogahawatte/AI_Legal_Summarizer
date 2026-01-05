import re
from typing import Dict, List, Optional

class CaseBriefGenerator:
    """
    Generate structured legal case briefs from Sri Lankan judgments (NLR/SLR)
    Strictly follows Sri Lankan legal research assistant format
    - No assumptions beyond what is stated in judgment
    - Clear, neutral, exam-ready legal English
    - Explicit acknowledgment when information is not available
    """
    
    @staticmethod
    def generate_case_brief(text: str, metadata: Dict = None) -> Dict:
        """Generate case brief strictly based on judgment contents"""
        
        if not text or len(text) < 100:
            return CaseBriefGenerator._get_fallback_brief(metadata)
        
        try:
            return {
                'case_identification': CaseBriefGenerator._safe_extract(
                    lambda: CaseBriefGenerator._extract_case_identification(text, metadata),
                    {'case_name': 'Not identified', 'court': 'N/A', 'year': 'N/A', 'citation': 'N/A'}
                ),
                'facts': CaseBriefGenerator._safe_extract(
                    lambda: CaseBriefGenerator._extract_facts(text),
                    "Facts: The judgment does not provide a clear factual summary."
                ),
                'issues': CaseBriefGenerator._safe_extract(
                    lambda: CaseBriefGenerator._extract_issues(text),
                    ["Legal issues: The exact legal questions decided are not explicitly stated in the judgment."]
                ),
                'holding': CaseBriefGenerator._safe_extract(
                    lambda: CaseBriefGenerator._extract_holding(text),
                    "Holding/Decision: The court's decision is not clearly stated in the available text."
                ),
                'reasoning': CaseBriefGenerator._safe_extract(
                    lambda: CaseBriefGenerator._extract_reasoning(text),
                    "Reasoning: The court's legal reasoning is not explicitly set out in the judgment."
                ),
                'ratio_decidendi': CaseBriefGenerator._safe_extract(
                    lambda: CaseBriefGenerator._extract_ratio_decidendi(text),
                    ["Ratio decidendi: No binding legal principles are expressly stated in the judgment."]
                ),
                'procedural_principles': CaseBriefGenerator._safe_extract(
                    lambda: CaseBriefGenerator._extract_procedural_principles(text),
                    {'note': 'No specific procedural or evidentiary principles were applied or discussed.'}
                ),
                'key_takeaways': CaseBriefGenerator._safe_extract(
                    lambda: CaseBriefGenerator._generate_key_takeaways(text),
                    ["Case significance: The judgment requires full reading for proper legal analysis."]
                ),
                'final_order': CaseBriefGenerator._safe_extract(
                    lambda: CaseBriefGenerator._extract_final_order(text),
                    "Final Order: The court's final operative order is not clearly stated."
                )
            }
        except Exception as e:
            print(f"Error generating case brief: {str(e)}")
            import traceback
            traceback.print_exc()
            return CaseBriefGenerator._get_fallback_brief(metadata)
    
    @staticmethod
    def _safe_extract(extraction_func, fallback):
        """Safely execute extraction with explicit fallback"""
        try:
            result = extraction_func()
            return result if result else fallback
        except Exception as e:
            print(f"Extraction error: {str(e)}")
            return fallback
    
    @staticmethod
    def _extract_case_identification(text: str, metadata: Dict = None) -> Dict:
        """Extract case name, court, year"""
        try:
            case_name = "Case name not identified"
            
            # Extract party names (v./vs.)
            try:
                match = re.search(r'([A-Z][A-Za-z\s]{3,50}?)\s+v\.\s+([A-Z][A-Za-z\s]{3,50}?)[\s\.]', text[:1000])
                if match:
                    case_name = f"{match.group(1).strip()} v. {match.group(2).strip()}"
            except:
                pass
            
            court = metadata.get('court', 'N/A') if metadata else 'N/A'
            year = str(metadata.get('year', 'N/A')) if metadata else 'N/A'
            citation = 'N/A'
            
            return {
                'case_name': case_name,
                'court': court,
                'year': year,
                'citation': citation
            }
        except:
            return {'case_name': 'Not identified', 'court': 'N/A', 'year': 'N/A', 'citation': 'N/A'}
    
    @staticmethod
    def _extract_facts(text: str) -> str:
        """
        Extract ONLY material facts found by the court.
        Do NOT include arguments or conclusions.
        """
        try:
            # Pattern 1: "THE charge" (criminal cases)
            match = re.search(r'(THE charge|The accused).{100,600}', text[:5000], re.IGNORECASE)
            if match:
                facts = match.group(0)
                words = facts.split()
                if len(words) > 150:
                    facts = " ".join(words[:150]) + "..."
                return f"Facts: {facts}"
            
            # Pattern 2: First substantial paragraph (civil cases)
            paragraphs = [p for p in text[:3000].split('\n\n') if 100 < len(p) < 800]
            if paragraphs:
                words = paragraphs[0].split()
                if len(words) > 150:
                    return f"Facts: {' '.join(words[:150])}..."
                return f"Facts: {paragraphs[0]}"
            
            return "Facts: The judgment does not provide a clear factual summary. Please refer to the full text."
        except:
            return "Facts: Material facts are not clearly identifiable from the judgment."
    
    @staticmethod
    def _extract_issues(text: str) -> List[str]:
        """
        Formulate the EXACT legal question(s) decided by the court.
        Based only on what is stated, not inferred.
        """
        issues = []
        try:
            # Find "whether" questions
            matches = re.finditer(r'[Ww]hether\s+.{20,180}[.?]', text[:8000])
            for match in matches:
                issue = match.group(0).strip()
                if not issue.endswith('?'):
                    issue = issue.rstrip('.') + '?'
                issues.append(issue)
                if len(issues) >= 4:
                    break
        except:
            pass
        
        return issues if issues else [
            "Legal Issues: The exact legal questions decided by the court are not explicitly stated.",
            "Please refer to the full judgment to identify the issues raised."
        ]
    
    @staticmethod
    def _extract_holding(text: str) -> str:
        """
        State the court's decision for each issue (allowed/dismissed/quashed/remitted).
        """
        try:
            # Look for appeal outcome
            match = re.search(r'(?:The |This )?appeal (?:is|was) (?:hereby )?(?:allowed|dismissed|quashed).{0,80}', text[-3000:], re.IGNORECASE)
            if match:
                return f"Holding/Decision: {match.group(0)}."
            
            # Look for conviction/acquittal
            match2 = re.search(r'(?:The )?(?:conviction|acquittal) (?:is|was) (?:upheld|quashed|set aside).{0,60}', text[-3000:], re.IGNORECASE)
            if match2:
                return f"Holding/Decision: {match2.group(0)}."
            
            return "Holding/Decision: The court's decision is not clearly stated in the available judgment text."
        except:
            return "Holding/Decision: Unable to identify the court's final decision."
    
    @staticmethod
    def _extract_reasoning(text: str) -> str:
        """
        Explain the court's legal reasoning including statutory interpretation and evaluation of evidence.
        """
        try:
            # Look for reasoning language
            match = re.search(r'(?:The Court|I am of opinion|It is clear).{60,250}', text[2000:10000], re.IGNORECASE)
            if match:
                return f"Reasoning: {match.group(0)}"
            
            return "Reasoning: The court's legal reasoning is not explicitly set out in this extract of the judgment."
        except:
            return "Reasoning: Court's reasoning requires review of the full judgment text."
    
    @staticmethod
    def _extract_final_order(text: str) -> str:
        """State the final operative order of the court."""
        try:
            match = re.search(r'(?:appeal|conviction|sentence) (?:is|was) (?:allowed|dismissed|quashed|upheld).{0,80}', text[-2000:], re.IGNORECASE)
            if match:
                return f"Final Order: {match.group(0)}."
            
            return "Final Order: The court's final operative order is not clearly stated in the judgment."
        except:
            return "Final Order: Unable to identify from judgment text."
    
    @staticmethod
    def _extract_ratio_decidendi(text: str) -> List[str]:
        """
        Extract binding legal principle(s) ESSENTIAL to the decision.
        Stated as general rules of law, not case-specific facts.
        """
        principles = []
        try:
            patterns = [
                r'It is (?:settled|established|clear) that\s+.{30,120}\.',
                r'(?:The Court|I) hold that\s+.{30,120}\.',
                r'The (?:rule|principle|law) is that\s+.{30,120}\.'
            ]
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    principle = match.group(0)
                    if len(principle) > 40:  # Minimum meaningful length
                        principles.append(principle)
                        if len(principles) >= 3:
                            break
        except:
            pass
        
        return principles if principles else [
            "Ratio decidendi: No binding legal principles are expressly stated as general rules in this judgment.",
            "The legal significance must be derived from reading the full reasoning."
        ]
    
    @staticmethod
    def _extract_procedural_principles(text: str) -> Dict:
        """
        Identify procedural or evidentiary rules applied.
        If none discussed, explicitly state so.
        """
        principles = {'statutory_provisions': [], 'procedural_rules': []}
        found_any = False
        
        try:
            # Find statutory references
            matches = re.finditer(r'(?:Section|Article|Rule)\s+\d+[A-Z]?\s+of\s+(?:the\s+)?[\w\s]+(?:Act|Code|Ordinance)', text)
            for match in matches:
                provision = match.group(0)
                if len(provision) < 90:
                    principles['statutory_provisions'].append(provision)
                    found_any = True
                    if len(principles['statutory_provisions']) >= 5:
                        break
            
            # Find procedural mentions
            proc_patterns = [
                r'(?:burden of proof|onus).{20,100}',
                r'(?:defect in (?:the )?charge).{20,100}',
                r'Criminal Procedure Code.{20,100}'
            ]
            for pattern in proc_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    principles['procedural_rules'].append(match.group(0))
                    found_any = True
                    if len(principles['procedural_rules']) >= 3:
                        break
            
            # Remove empty lists
            principles = {k: v for k, v in principles.items() if v}
            
        except:
            pass
        
        if not found_any:
            return {'note': 'No specific procedural or evidentiary principles were applied or discussed in the judgment.'}
        
        return principles if principles else {'note': 'No specific procedural or evidentiary principles were applied or discussed.'}
    
    @staticmethod
    def _generate_key_takeaways(text: str) -> List[str]:
        """
        Provide 3-5 concise points explaining case significance.
        Based only on what can be determined from the judgment.
        """
        takeaways = []
        try:
            # Identify area of law
            if re.search(r'\bconstitutional\b', text[:3000], re.IGNORECASE):
                takeaways.append("This case concerns constitutional law and fundamental rights.")
            elif re.search(r'\bcriminal\b', text[:3000], re.IGNORECASE):
                takeaways.append("This case addresses criminal law procedure and/or evidence.")
            
            # Check for fundamental rights
            if re.search(r'Article\s+(?:1[0-8]|14A)', text):
                takeaways.append("The judgment discusses Sri Lankan fundamental rights provisions.")
            
            # Check for procedural issues
            if re.search(r'(?:defect|irregularity|jurisdiction)', text, re.IGNORECASE):
                takeaways.append("The case establishes procedural requirements for lower courts.")
            
            # Generic takeaway if nothing specific found
            if len(takeaways) < 2:
                takeaways.append("Full judgment review required to assess precedential value.")
                takeaways.append("Case significance should be determined by legal professionals.")
        except:
            pass
        
        return takeaways[:5] if takeaways else [
            "Case significance: The judgment requires comprehensive legal analysis.",
            "Consult the full judgment for proper evaluation of its precedential value."
        ]
    
    @staticmethod
    def _get_fallback_brief(metadata: Dict = None) -> Dict:
        """Fallback when extraction fails"""
        return {
            'case_identification': {
                'case_name': 'Case name not identified',
                'court': metadata.get('court', 'N/A') if metadata else 'N/A',
                'year': str(metadata.get('year', 'N/A')) if metadata else 'N/A',
                'citation': 'N/A'
            },
            'facts': 'Facts: Material facts cannot be determined from available judgment text.',
            'issues': ['Legal Issues: The legal questions decided are not explicitly stated.'],
            'holding': 'Holding/Decision: The court\'s decision is not clearly stated.',
            'reasoning': 'Reasoning: Court\'s legal reasoning requires review of full judgment.',
            'ratio_decidendi': ['Ratio decidendi: Binding principles must be extracted from complete judgment.'],
            'procedural_principles': {'note': 'No specific procedural or evidentiary principles were applied or discussed.'},
            'key_takeaways': ['Full judgment review required for proper legal analysis.'],
            'final_order': 'Final Order: The court\'s operative order is not clearly stated.'
        }
