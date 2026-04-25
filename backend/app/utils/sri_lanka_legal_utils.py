import re
import os
import json
import PyPDF2
import requests
from typing import Dict, List, Any

# -----------------------------
# CONFIGURATION
# -----------------------------

def _resolve_data_dir() -> str:
    """Use app.config.DATA_DIR in Docker / production; fallback for local dev."""
    try:
        from app.config import DATA_DIR as _cfg
        return os.path.normpath(str(_cfg))
    except Exception:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))


DATA_DIR = _resolve_data_dir()

# -----------------------------
# LEGAL TERMS LOADER
# -----------------------------

def load_legal_terms():
    """Load legal terms from JSON file, fallback to empty dict if not found"""
    _here = os.path.dirname(__file__)
    possible_paths = [
        os.path.join(DATA_DIR, "sri_lanka_legal_corpus", "legal_glossary_si_en_ta.json"),
        os.path.join(_here, "..", "..", "frontend", "src", "utils", "sri_lanka_legal_terms.json"),
        os.path.join(_here, "..", "..", "..", "data", "sri_lanka_legal_corpus", "legal_glossary_si_en_ta.json"),
        os.path.join(os.getcwd(), "data", "sri_lanka_legal_corpus", "legal_glossary_si_en_ta.json"),
        os.path.join(os.getcwd(), "frontend", "src", "utils", "sri_lanka_legal_terms.json"),
        "sri_lanka_legal_terms.json",
    ]
    for path in possible_paths:
        path = os.path.normpath(path)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                print(f"Loaded legal terms from: {path}")
                return json.load(f)
        except Exception as e:
            print(f"Warning: could not read legal terms at {path}: {e}")
    print("Legal terms file not found. Using empty dictionary.")
    return {}

# Expose legal_terms globally
legal_terms = load_legal_terms()

# -----------------------------
# GLOSSARY DEFINITION - FALLBACK
# -----------------------------

GLOSSARY_SI_EN_TA = {
    "මූලික අයිතිවාසිකම්": {
        "en": "Fundamental Rights",
        "ta": "அடிப்படை உரிமைகள்"
    },
    "සමානාත්මතාවය": {
        "en": "Equality", 
        "ta": "சமத்துவம்"
    },
    "විවේචනාත්මක අදහස්": {
        "en": "Critical Opinions",
        "ta": "விமர்சனக் கருத்துகள்"
    },
    "අත්අඩංගුව": {
        "en": "Arrest",
        "ta": "கைது"
    },
    "නඩු විභාගය": {
        "en": "Trial",
        "ta": "விசாரணை"
    },
    "අපරාධ": {
        "en": "Offense",
        "ta": "குற்றம்"
    },
    "අධිකරණය": {
        "en": "Court",
        "ta": "நீதிமன்றம்"
    },
    "නීතිය": {
        "en": "Law",
        "ta": "சட்டம்"
    },
    "අයිතිවාසිකම්": {
        "en": "Rights",
        "ta": "உரிமைகள்"
    },
    "සාක්ෂි": {
        "en": "Evidence",
        "ta": "சாட்சியம்"
    }
}

# -----------------------------
# CONSTITUTIONAL DATA LOADER
# -----------------------------

def load_constitutional_data():
    """Load all constitutional data files"""
    constitutional_data = {}
    
    try:
        # Load enriched rights patterns (under sri_lanka_legal_corpus in repo)
        ENRICHED_RIGHTS_PATH = os.path.join(
            DATA_DIR, "sri_lanka_legal_corpus", "enriched_fundamental_rights_patterns.json"
        )
        if os.path.exists(ENRICHED_RIGHTS_PATH):
            with open(ENRICHED_RIGHTS_PATH, "r", encoding="utf-8") as f:
                constitutional_data["rights_patterns"] = json.load(f)
            print(f"Loaded enriched rights patterns from: {ENRICHED_RIGHTS_PATH}")
        else:
            print(f"Warning: Enriched rights patterns not found at {ENRICHED_RIGHTS_PATH}")
            constitutional_data["rights_patterns"] = {}
    except Exception as e:
        print(f"Error loading rights patterns: {e}")
        constitutional_data["rights_patterns"] = {}

    try:
        # Load constitution articles
        ARTICLES_PATH = os.path.join(DATA_DIR, "sri_lanka_legal_corpus", "constitution_articles.json")
        if os.path.exists(ARTICLES_PATH):
            with open(ARTICLES_PATH, "r", encoding="utf-8") as f:
                constitutional_data["articles"] = json.load(f)
            print(f"Loaded constitution articles from: {ARTICLES_PATH}")
        else:
            print(f"Warning: Constitution articles not found at {ARTICLES_PATH}")
            constitutional_data["articles"] = {}
    except Exception as e:
        print(f"Error loading constitution articles: {e}")
        constitutional_data["articles"] = {}

    try:
        # Load processed constitutions (ADDED HERE)
        CONSTITUTION_PATH = os.path.join(DATA_DIR, "sri_lanka_legal_corpus", "processed_constitutions.json")
        if os.path.exists(CONSTITUTION_PATH):
            with open(CONSTITUTION_PATH, "r", encoding="utf-8") as f:
                constitutional_data["processed_constitutions"] = json.load(f)
            print(f"Loaded processed constitutions from: {CONSTITUTION_PATH}")
        else:
            print(f"Warning: Processed constitutions not found at {CONSTITUTION_PATH}")
            constitutional_data["processed_constitutions"] = {}
    except Exception as e:
        print(f"Error loading processed constitutions: {e}")
        constitutional_data["processed_constitutions"] = {}

    return constitutional_data

# Load constitutional data
CONSTITUTIONAL_DATA = load_constitutional_data()

# Extract data for easier access
FUNDAMENTAL_RIGHTS_PATTERNS = CONSTITUTIONAL_DATA.get("rights_patterns", {})
CONSTITUTION_ARTICLES = CONSTITUTIONAL_DATA.get("articles", {})
PROCESSED_CONSTITUTIONS = CONSTITUTIONAL_DATA.get("processed_constitutions", {})

# -----------------------------
# PDF TEXT EXTRACTOR
# -----------------------------

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF file"""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return text

# -----------------------------
# METADATA EXTRACTORS
# -----------------------------

def extract_case_year(text: str):
    # Look for 4-digit years (1800-2100)
    pattern = r'\b(1[89]\d{2}|20\d{2})\b'
    matches = re.findall(pattern, text)
    
    years = [int(year) for year in matches if 1800 <= int(year) <= 2100]
    
    # Return the earliest year found (likely the judgment year)
    return min(years) if years else None

def extract_case_number(text: str):
    # Try various case number patterns
    patterns = [
        r'(S\.?\s*C\.?|C\.?\s*A\.?|H\.?\s*C\.?)\s*(FR|App|Rev|Application)?\s*No\.?\s*\d{1,5}[\/\-]?\d{0,4}',  # SC FR No. 123/2020
        r'P\.\s*C[,\.]\s*[\w\s]+[,\.]\s*\d{1,5}(?:[,\.]\d{3})*',  # P. C, Nuwara Eliya, 8,928
        r'D\.\s*C[,\.]\s*[\w\s]+[,\.]\s*\d{1,5}(?:[,\.]\d{3})*',  # D. C, Location, 123
        r'Case\s+No\.?\s*\d{1,5}',  # Case No. 123
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return None

def extract_court(text: str, file_name: str = "") -> str:
    """
    Extract the court name from the judgment text (and optionally filename).
    Checks Sri Lankan court levels and NLR-style abbreviations (P. C., D. C., C. R., S. C.).
    Searches first 6000 chars to catch headnote court labels.
    """
    search_text = (text or "")[:6000]
    text_upper = search_text.upper()
    fn_upper = (file_name or "").upper()

    # Priority order: highest court first (full names then abbreviations)
    court_patterns = [
        (r'\bPRIVY\s+COUNCIL\b',                        'Privy Council'),
        (r'\bJUDICIAL\s+COMMITTEE\b',                   'Privy Council'),
        (r'\bP\.\s*C\.\b',                              'Privy Council'),   # NLR headnote
        (r'\bSUPREME\s+COURT\b',                        'Supreme Court'),
        (r'\bS\.C\.\s+(?:APPEAL|FR|SPL)\b',             'Supreme Court'),
        (r'\bS\.\s*C\.\b',                              'Supreme Court'),   # NLR/SLR abbreviation
        (r'\bSC\s+(?:APPEAL|FR|APPLICATION)\s+NO\b',   'Supreme Court'),
        (r'\bFULL\s+BENCH\b',                           'Supreme Court'),
        (r'\bCOURT\s+OF\s+APPEAL\b',                    'Court of Appeal'),
        (r'\bC\.A\.\s+NO\b',                            'Court of Appeal'),
        (r'\bHIGH\s+COURT\b',                           'High Court'),
        (r'\bH\.C\.\s+NO\b',                            'High Court'),
        (r'\bDISTRICT\s+COURT\b',                       'District Court'),
        (r'\bD\.\s*C\.',                                'District Court'),   # D. C. or D.C.
        (r'\bD\.C[,\.\s]',                              'District Court'),
        (r'\bD\.?-?J\.\b',                              'District Court'),
        (r'\bCOURT\s+OF\s+REQUESTS?\b',                 'Court of Requests'),
        (r'\bC\.\s*R\.',                                'Court of Requests'), # C. R. in NLR
        (r'\bCOMMISSIONER.S\s+COURT\b',                 'Commissioner\'s Court'),
        (r'\bMAGISTRATE.{0,5}COURT\b',                  "Magistrate's Court"),
    ]
    for pat, name in court_patterns:
        if re.search(pat, text_upper):
            return name

    # Filename hint: NLR volumes often indicate Privy Council in headnote; SLR often Supreme Court
    if 'NLR' in fn_upper or 'NEW-LAW' in fn_upper.replace(' ', '-'):
        if re.search(r'\bP\.\s*C\.\b', text_upper):
            return 'Privy Council'
        if re.search(r'\bD\.\s*C\.|\bD\.C\.', text_upper):
            return 'District Court'
        if re.search(r'\bC\.\s*R\.|\bC\.R\.', text_upper):
            return 'Court of Requests'
    if 'SLR' in fn_upper or 'SRI-L' in fn_upper.replace(' ', '-'):
        if re.search(r'\bS\.\s*C\.\b|\bSUPREME\s+COURT\b', text_upper):
            return 'Supreme Court'
        if re.search(r'\bCOURT\s+OF\s+APPEAL\b|\bC\.A\.', text_upper):
            return 'Court of Appeal'
    return None


def extract_case_citation(text: str, filename: str = '') -> str:
    """
    Extract the primary NLR/SLR citation for storage in the DB.
    Tries text first, then falls back to filename parsing.
    """
    cite_patterns = [
        r'\(\d{4}\)\s*\d+\s+(?:SLR|NLR|SLLR)\s+\d+',
        r'\[\d{4}\]\s*\d+\s+(?:SLR|NLR|SLLR)\s+\d+',
        r'\b\d{1,3}\s+(?:SLR|NLR|SLLR)\s+\d{1,4}\b',
    ]
    for pat in cite_patterns:
        m = re.search(pat, text[:3000], re.IGNORECASE)
        if m:
            return m.group(0).strip()
    # Filename fallback
    if filename:
        fn = filename.upper().replace('_', '-')
        mv = re.search(r'NLR-V(?:OL)?[\-]?(\d+)', fn)
        if mv:
            vol = mv.group(1)
            mp = re.search(r'NLR-V(?:OL)?[\-]?\d+[\-][A-Z0-9\.-]+-([\d]+)[\-]', fn)
            page = mp.group(1) if mp else ''
            return f'{vol} NLR {page}'.strip()
    return ''


def extract_case_year(text: str) -> int:
    """
    Extract the case year from the judgment text.
    Uses the most-prominent year (highest frequency) in the first 2000 chars
    rather than the minimum — this avoids picking up ancient Roman-Dutch dates.
    Prefers years in citation patterns (most reliable).
    """
    # First try: years embedded in NLR/SLR citation pattern (most reliable)
    cite_year = re.search(
        r'(?:\(|\[)(1[89]\d{2}|20\d{2})(?:\)|\])(?:\s+\d+)?\s+(?:NLR|SLR|SLLR)',
        text[:3000], re.IGNORECASE
    )
    if cite_year:
        return int(cite_year.group(1))

    # Second: find all 4-digit years in first 2000 chars and pick most frequent
    pattern = r'\b(1[89]\d{2}|20\d{2})\b'
    all_years = [int(y) for y in re.findall(pattern, text[:2000])
                 if 1800 <= int(y) <= 2030]
    if not all_years:
        return None
    # Most frequent year = likely the judgment or publication year
    from collections import Counter
    freq = Counter(all_years)
    return freq.most_common(1)[0][0]


# -----------------------------
# CONSTITUTIONAL PROVISION DETECTOR
# -----------------------------

def detect_constitutional_provisions(text: str) -> Dict[str, List[str]]:
    """Detect references to constitutional articles in text"""
    detected_rights = {}
    
    # If we have enriched patterns, use them
    if FUNDAMENTAL_RIGHTS_PATTERNS:
        for article, pattern in FUNDAMENTAL_RIGHTS_PATTERNS.items():
            if isinstance(pattern, str):
                try:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    found_matches = []
                    for match in matches:
                        # Get context around the match
                        start = max(0, match.start() - 50)
                        end = min(len(text), match.end() + 50)
                        context = text[start:end].strip()
                        found_matches.append(context)
                    
                    if found_matches:
                        detected_rights[article] = found_matches
                except re.error as e:
                    print(f"Regex error for article {article}: {e}")
    else:
        # Fallback to default patterns
        default_patterns = {
            10: r"freedom\sof\sthought|freedom\sof\sconscience|freedom\sof\sreligion",
            11: r"torture|cruel\sinhuman|degrading\spunishment",
            12: r"equal\sprotection\sof\sthe\slaw|equality\s(before|under)\sthe\slaw",
            13: r"unlawful\s(arrest|detention)|illegal\s(arrest|detention)",
            14: r"freedom\sof\sspeech|freedom\sof\sexpression|freedom\sof\sassembly"
        }
        
        for article, pattern in default_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            found_matches = []
            for match in matches:
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                found_matches.append(context)
            
            if found_matches:
                detected_rights[str(article)] = found_matches
    
    return detected_rights

# -----------------------------
# CITATION PATTERNS
# -----------------------------

CITATION_PATTERN_NLR = r"\d+\s+NLR\s+\d+"
CITATION_PATTERN_SLR = r"\[\d{4}\]\s+\d+\s+SLR\s+\d+"

# -----------------------------
# GLOSSARY LOADER
# -----------------------------

def load_glossary():
    """Load legal glossary - compatible with Colab"""
    try:
        # For Colab, you might need to upload the file first
        GLOSSARY_PATH = "/content/legal_glossary_si_en_ta.json"
        with open(GLOSSARY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        try:
            # Alternative path
            GLOSSARY_PATH = "legal_glossary_si_en_ta.json"
            with open(GLOSSARY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print("Glossary file not found. Using built-in glossary.")
            return {"legal_terms": GLOSSARY_SI_EN_TA}  # Fallback to built-in glossary

# -----------------------------
# MAIN PROCESSING FUNCTION
# -----------------------------

def process_legal_document(text: str, source_type: str = "case") -> Dict[str, Any]:
    """Process legal document and extract fundamental rights references"""
    
    result = {
        "metadata": {
            "year": extract_case_year(text),
            "case_number": extract_case_number(text),
            "court": extract_court(text),
            "source_type": source_type
        },
        "fundamental_rights_detected": detect_constitutional_provisions(text),
        "citations": {
            "NLR": re.findall(CITATION_PATTERN_NLR, text),
            "SLR": re.findall(CITATION_PATTERN_SLR, text)
        },
        "summary": {
            "total_rights_detected": 0,
            "primary_rights": []
        }
    }
    
    # Calculate summary statistics
    result["summary"]["total_rights_detected"] = len(result["fundamental_rights_detected"])
    result["summary"]["primary_rights"] = list(result["fundamental_rights_detected"].keys())
    
    return result

# -----------------------------
# USAGE EXAMPLE FOR COLAB
# -----------------------------

def example_usage_in_colab():
    """Example of how to use this in Google Colab"""
    
    # Method 1: Upload PDF directly to Colab
    pdf_text = extract_text_from_pdf("/content/fundamental_rights.pdf")
    
    # Method 2: Use the text you already have
    # pdf_text = your_extracted_text_here
    
    # Process the document
    analysis_result = process_legal_document(pdf_text, source_type="constitution")
    
    # Print results
    print("=== FUNDAMENTAL RIGHTS ANALYSIS ===")
    print(f"Document Type: {analysis_result['metadata']['source_type']}")
    print(f"Rights Detected: {analysis_result['summary']['total_rights_detected']}")
    print("\nDetected Rights:")
    for article, contexts in analysis_result['fundamental_rights_detected'].items():
        print(f"  {article}: {len(contexts)} references")
        for i, context in enumerate(contexts[:2]):  # Show first 2 contexts
            print(f"    {i+1}. {context}...")
    
    return analysis_result

# Test with your PDF content
if __name__ == "__main__":
    # You can test with a sample text from your PDF
    sample_text = """
    Every person is entitled to freedom of thought, conscience and religion, including the freedom to have or to adopt a religion or belief of his choice.
    No person shall be subjected to torture or to cruel, inhuman or degrading treatment or punishment.
    All persons are equal before the law and are entitled to the equal protection of the law.
    """
    
    result = process_legal_document(sample_text, "constitution")
    print(json.dumps(result, indent=2))
    
    # Print information about loaded data
    print("\n=== LOADED CONSTITUTIONAL DATA ===")
    print(f"Rights patterns loaded: {len(FUNDAMENTAL_RIGHTS_PATTERNS)}")
    print(f"Constitution articles loaded: {len(CONSTITUTION_ARTICLES)}")
    print(f"Processed constitutions loaded: {len(PROCESSED_CONSTITUTIONS)}")