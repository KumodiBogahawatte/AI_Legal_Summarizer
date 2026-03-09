# backend/app/services/document_processor.py

import pdfplumber
import pytesseract
from PIL import Image
import io
import re
from sqlalchemy.orm import Session
from ..models.document_model import LegalDocument
from ..utils.sri_lanka_legal_utils import extract_case_year, extract_case_number, extract_court

# Import hybrid document classifier for structure analysis
try:
    import sys
    from pathlib import Path
    # Add backend directory to path if needed
    backend_dir = Path(__file__).parent.parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    
    from services.hybrid_document_classifier import HybridDocumentClassifier
    CLASSIFIER_AVAILABLE = True
    print("✅ Hybrid Document Classifier loaded for structure analysis")
except ImportError as e:
    CLASSIFIER_AVAILABLE = False
    print(f"ℹ️  Document structure classifier not installed: {e}")
except Exception as e:
    CLASSIFIER_AVAILABLE = False
    # Don't show DLL errors in production - these are expected if PyTorch isn't fully set up
    if "DLL" in str(e) or "torch" in str(e).lower():
        print(f"ℹ️  Document structure classifier disabled (PyTorch dependencies not fully configured)")
    else:
        print(f"⚠️  Document structure classifier error: {e}")

class DocumentProcessor:
    
    # Class-level classifier instance (singleton pattern)
    _classifier = None
    
    @classmethod
    def get_classifier(cls):
        """Get or initialize the document structure classifier"""
        if cls._classifier is None and CLASSIFIER_AVAILABLE:
            try:
                cls._classifier = HybridDocumentClassifier()
            except Exception as e:
                print(f"Failed to initialize classifier: {e}")
                cls._classifier = None
        return cls._classifier

    @staticmethod
    def extract_text_from_pdf(file_bytes: bytes) -> str:
        """
        Extracts text using pdfplumber.
        If no text found -> fallback to OCR (Tesseract).
        """
        text = ""

        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"

        except Exception as e:
            print("PDFPlumber extraction failed:", e)

        # Fallback: OCR
        if len(text.strip()) < 50:
            print("Fallback to OCR...")
            images = DocumentProcessor.convert_pdf_to_images(file_bytes)
            for img in images:
                text += pytesseract.image_to_string(img)

        return text

    @staticmethod
    def convert_pdf_to_images(file_bytes: bytes):
        """Convert PDF to images for OCR"""
        try:
            from pdf2image import convert_from_bytes
            return convert_from_bytes(file_bytes)
        except:
            return []

    @staticmethod
    def clean_text(text: str) -> str:
        """Remove line breaks, special chars, normalize spacing."""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @staticmethod
    def is_sri_lanka_legal_document(text: str, file_name: str = "") -> bool:
        """Validate if document is a Sri Lankan legal case (SLR or NLR).

        Only original law reports (NLR, SLR, SLLR, CLR) are accepted. Analysis documents,
        summaries, or case briefs are rejected even if they cite NLR/SLR.

        Strategy:
        0. Reject non-original documents: filename or text suggests analysis/summary/brief.
        1. Filename fast-path: if the filename contains NLR/SLR/New Law/Sri Lanka Law,
           return True immediately. Individual case PDFs extracted from NLR volumes
           often don't repeat the report series name in their body text.
        2. Fallback text scoring: accumulate evidence across many weak signals.
           Threshold is low (10 pts) so a few unambiguous hits suffice.
        """
        # ── 0. Reject analysis / summary / brief documents (not original reports) ───
        if file_name:
            f_lower = file_name.lower()
            non_original_indicators = [
                "_analysis.", " analysis.", "_analysis.pdf",
                "_summary.", " summary.", "_summary.pdf",
                "_brief.", " brief.", "_brief.pdf", "case_brief",
                "-analysis.", "-summary.", "-brief.",
            ]
            for ind in non_original_indicators:
                if ind in f_lower or f_lower.endswith(ind.rstrip(".")):
                    print(f"Validation rejected: '{file_name}' looks like analysis/summary/brief (not original NLR/SLR).")
                    return False
            if f_lower.endswith("analysis.pdf") or f_lower.endswith("summary.pdf"):
                print(f"Validation rejected: '{file_name}' appears to be an analysis or summary document.")
                return False

        # Optional: reject if text starts with analysis-style phrasing (first ~1500 chars)
        if text and len(text.strip()) > 100:
            text_start = text[:1500].lower()
            if re.search(r"\b(this\s+)?(document\s+)?(is\s+)?(an?\s+)?(case\s+)?analysis\b", text_start):
                if not re.search(r"\b(judgment|held|cur\.\s*adv\.\s*vult|supreme\s+court|district\s+court)\b", text_start):
                    print("Validation rejected: Text appears to be a case analysis, not an original report.")
                    return False

        # ── 1. Filename fast-path ───────────────────────────────────────────
        if file_name:
            fname_upper = file_name.upper().replace("-", " ").replace("_", " ")
            filename_indicators = [
                r'\bNLR\b',
                r'\bSLR\b',
                r'\bNEW\s+LAW\s+REPORT',
                r'\bSRI\s+LANKA\s+LAW',
                r'\bSRI\s+L\b',
                r'\bCEYLON\s+LAW',
            ]
            for pat in filename_indicators:
                if re.search(pat, fname_upper):
                    print(f"\u2705 Filename fast-path: '{file_name}' matches SLR/NLR pattern [{pat}]")
                    return True

        if not text or len(text.strip()) < 50:
            print("Validation failed: Text too short or empty")
            return False

        text_upper = text.upper()
        score = 0
        matched_indicators = []

        # ═══════════════════════════════════════════════════════════════════
        # LAYER 1 ── Report series name & citation formats
        # Observed across NLR Vol-1 – Vol-80 and SLR 1978 – 2014
        # ═══════════════════════════════════════════════════════════════════
        report_series = [
            # Abbreviations
            (r'\bNLR\b',                                           35, "NLR"),
            (r'\bSLR\b',                                           35, "SLR"),
            # Full names
            (r'\bNEW\s+LAW\s+REPORTS?\b',                         35, "New Law Reports"),
            (r'\bSRI\s+LANKA\s+LAW\s+REPORTS?\b',                 35, "Sri Lanka Law Reports"),
            (r'\bCEYLON\s+LAW\s+REPORTS?\b',                      30, "Ceylon Law Reports"),
            (r'\bLANKA\s+LAW\b',                                   25, "LankaLaw"),
            # Publisher line seen in LankaLAW PDFs
            (r'\bLANKALAW\b',                                      25, "LankaLAW"),
            (r'\bCOPYRIGHT\s+LANKALAW\b',                          25, "Copyright LankaLAW"),
            # Sri L.R. inline format (SLR body text)
            (r'\bSRI\s+L\.\s*R\.\b',                               30, "Sri L.R."),
            (r'\bSRI\s+LANKA\s+L\.R\.\b',                          30, "Sri Lanka L.R."),
            # Volume-number citation — e.g., "5 NLR 281" or "(2005) 1 SLR 1"
            (r'\d+\s+NLR\s+\d+',                                   35, "NLR vol citation"),
            (r'\d+\s+SLR\s+\d+',                                   35, "SLR vol citation"),
            (r'\(\d{4}\)\s*\d*\s*SLR\s+\d+',                      35, "SLR (year) citation"),
            (r'\(\d{4}\)\s*NLR\s+\d+',                             35, "NLR (year) citation"),
            (r'\[\d{4}\]\s*\d*\s*SLR\s+\d+',                      35, "SLR [year] citation"),
            (r'\[\d{4}\]\s*NLR\s+\d+',                             35, "NLR [year] citation"),
            # Volume-number headers seen on case list pages
            (r'\bVOLUME\s+\d+\b',                                  12, "Volume N"),
            (r'\bNEW\s+LAW\s+REPORT\s+V(?:OL(?:UME)?)?\s*\.?\s*\d+', 30, "NLR Vol header"),
        ]
        for pat, pts, label in report_series:
            if re.search(pat, text_upper):
                score += pts
                matched_indicators.append(f"{label} (+{pts})")
                if score >= 35:
                    break

        # ═══════════════════════════════════════════════════════════════════
        # LAYER 2 ── Party name format  (NAME v. NAME  /  KING v. NAME)
        # NLR uses ALL-CAPS parties; SLR uses mixed-case
        # ═══════════════════════════════════════════════════════════════════
        party_patterns = [
            r'[A-Z]{2,}(?:\s+[A-Z]{2,})*\s+v\.\s+[A-Z]{2,}',          # ALL-CAPS v.
            r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+[Vv]\.\s+[A-Z][a-z]+', # Mixed-case v.
            r'\bKING\s+v\.\s+[A-Z]',                                     # KING v. X
            r'\bQUEEN\s+v\.\s+[A-Z]',                                    # QUEEN v. X
            r'\bREX\s+v\.\s+[A-Z]',                                      # REX v. X
            r'\b(?:ATTORNEY|SOLICITOR)\s+GENERAL\s+v\.',                 # AG/SG v.
            r'\bIN\s+(?:RE|THE\s+MATTER\s+OF)\b',                        # In Re / In the Matter of
            r'\bET\s+AL[.,]\b',                                           # et al.
            r'\bEt\s+Al[.,]\b',
        ]
        for pat in party_patterns:
            if re.search(pat, text[:3000]):
                score += 15
                matched_indicators.append("Party name format (+15)")
                break

        # ═══════════════════════════════════════════════════════════════════
        # LAYER 3 ── Sri Lankan court labels & abbreviations
        # NLR uses: D.-J., D.C., O.R., S.C., J.C., C.R., P.C.
        # ═══════════════════════════════════════════════════════════════════
        court_pats = [
            (r'\bSUPREME\s+COURT\b',                      15),
            (r'\bCOURT\s+OF\s+APPEAL\b',                  15),
            (r'\bHIGH\s+COURT\b',                         12),
            (r'\bDISTRICT\s+COURT\b',                     12),
            (r'\bMAGISTRATE.{0,10}COURT\b',               10),
            (r'\bPRIVY\s+COUNCIL\b',                      15),
            (r'\bFISCAL.{0,20}COURT\b',                   12),
            (r'\bCOMMISSIONER[\'S ]{0,5}COURT\b',         10),
            (r'\bJUDICIAL\s+COMMITTEE\b',                 15),  # Privy Council alt name
            (r'\bCOURT\s+OF\s+FIRST\s+INSTANCE\b',        10),
            (r'\bCOURT\s+OF\s+CASSATION\b',                10),
            (r'\bCOURT\s+OF\s+REQUESTS\b',                 12),  # Historical Ceylon
            (r'\bDIVISIONAL\s+COURT\b',                    10),
            (r'\bFULL\s+BENCH\b',                          12),  # Full Bench references
            # Court codes used in headnotes
            (r'\bD\.-J\.\b',                               14),  # District Judge
            (r'\bO\.R\.\b',                                14),  # Original Report / Original
            (r'\bS\.C\.\b',                                10),  # Supreme Court abbrev
            (r'\bJ\.C\.\b',                                10),  # Judicial Committee
            (r'\bC\.R\.\b',                                10),  # Court of Requests
            (r'\bP\.C\.\b',                                10),  # Privy Council
            (r'\bD\.C\.\b',                                10),  # District Court abbrev
        ]
        for pat, pts in court_pats:
            if re.search(pat, text_upper):
                score += pts
                matched_indicators.append(f"Court ref (+{pts})")
                break

        # ═══════════════════════════════════════════════════════════════════
        # LAYER 4 ── Sri Lankan geographic signals
        # Covering all 9 provinces and major cities/towns
        # ═══════════════════════════════════════════════════════════════════
        sl_places = [
            # Western Province
            (r'\bCOLOMBO\b',           20), (r'\bGAMPAHA\b',          18),
            (r'\bKALUTARA\b',          18), (r'\bWATTALA\b',          15),
            (r'\bNEGOMBO\b',           15), (r'\bPANADURA\b',         15),
            (r'\bMORAGAHAKANDA\b',     15), (r'\bKADUWELA\b',         12),
            # Central Province
            (r'\bKANDY\b',             20), (r'\bNUWARA\s+ELIYA\b',   18),
            (r'\bMATALE\b',            15), (r'\bHATTON\b',           13),
            (r'\bBADULLA\b',           15),
            # Southern Province
            (r'\bGALLE\b',             18), (r'\bMATARA\b',           18),
            (r'\bHAMBANTOTA\b',        18), (r'\bTANGALLE\b',         15),
            (r'\bAMBALANGODA\b',        13),
            # Northern Province
            (r'\bJAFFNA\b',            20), (r'\bMULLAITTIVU\b',      20),
            (r'\bKILINOCHCHI\b',       18), (r'\bMANNAR\b',           18),
            (r'\bVAVUNIYA\b',          18), (r'\bPOINT\s+PEDRO\b',    15),
            # Eastern Province
            (r'\bBATTICALOA\b',        20), (r'\bTRINCOMALEE\b',      20),
            (r'\bAMPARA\b',            18), (r'\bKALMUNAI\b',         15),
            # North Western Province
            (r'\bKURUNEGALA\b',        18), (r'\bPUTTALAM\b',         15),
            (r'\bCHILAW\b',            13),
            # North Central Province
            (r'\bANURADHAPURA\b',      20), (r'\bPOLONNARUWA\b',      18),
            # Uva Province
            (r'\bBADULLA\b',           15), (r'\bMONARAGALA\b',       15),
            # Sabaragamuwa
            (r'\bKEGALLE\b',           15), (r'\bRATNAPURA\b',        15),
            # General/historic
            (r'\bCEYLON\b',            22), (r'\bSRI\s+LANKA\b',      20),
            (r'\bWATTEGAMA\b',          12), (r'\bAVISSAWELLA\b',      12),
        ]
        for pat, pts in sl_places:
            if re.search(pat, text_upper):
                score += pts
                matched_indicators.append(f"SL place (+{pts})")
                if score >= 35:
                    break

        # ═══════════════════════════════════════════════════════════════════
        # LAYER 5 ── Sri Lankan surname / title signals
        # Exhaustively extracted from NLR Vol 1–80 case indices
        # ═══════════════════════════════════════════════════════════════════
        sl_names = [
            # Common Sinhalese surnames
            (r'\bPERERA\b',            10), (r'\bSILVA\b',             10),
            (r'\bFERNANDO\b',          10), (r'\bDE\s+SILVA\b',        12),
            (r'\bDE\s+SARAM\b',        12), (r'\bDE\s+ZOYSA\b',        12),
            (r'\bWICKREMESINGHE\b',    12), (r'\bWICKRAMASINGHE\b',    12),
            (r'\bSENANAYAKE\b',        12), (r'\bJAYASURIYA\b',        12),
            (r'\bJAYAWARDENE\b',       12), (r'\bJAYATILAKA\b',        12),
            (r'\bGUNASEKERA\b',        10), (r'\bGUNASEKERE\b',        10),
            (r'\bGUNATILAKE\b',        10), (r'\bGOONETILLEKE\b',      10),
            (r'\bRANASINGHE\b',        10), (r'\bRAJAPAKSE\b',         10),
            (r'\bRAJAPAKSA\b',         10), (r'\bDHARMAWARDENE\b',     12),
            (r'\bWIJEYESEKERE\b',      12), (r'\bWIJEYARATNE\b',       12),
            (r'\bWIJESINGHE\b',        10), (r'\bWEERAKOON\b',         12),
            (r'\bDISANAYAKE\b',        10), (r'\bDISSANAYAKE\b',       10),
            (r'\bABEYSEKERA\b',        10), (r'\bABEYWARDENE\b',       10),
            (r'\bABEYGUNAWARDENE\b',   10), (r'\bABEYWICKREME\b',      10),
            (r'\bBANDARANAYAKE\b',     12), (r'\bBANDARA\b',            8),
            (r'\bAMARAWEERA\b',        10), (r'\bAMARASEKERA\b',       10),
            (r'\bKUMARASINGHE\b',      10), (r'\bSAMARASINGHE\b',      10),
            (r'\bSAMARASINHA\b',       10), (r'\bSIRIWARDENE\b',       10),
            (r'\bSIRIWARDENA\b',       10), (r'\bHERATH\b',            10),
            (r'\bPUNNYASINGHE\b',      10), (r'\bPILLAY\b',            10),
            # Titles/ honorifics used in NLR
            (r'\bAPPU\b',              10), (r'\bAPPUHAMY\b',          10),
            (r'\bHAMINE\b',            12), (r'\bHAMINI\b',            12),
            (r'\bUNNANSE\b',           14), (r'\bTHERO\b',             14),
            (r'\bUMMA\b',              12), (r'\bLEBBE\b',             12),
            (r'\bSINGHO\b',            10), (r'\bSINHA\b',             10),
            (r'\bMUDALIYAR\b',         14), (r'\bMUDALI\b',            10),
            (r'\bKANGANY\b',           12), (r'\bKANGANI\b',           12),
            # Tamil surnames
            (r'\bSELVADURAI\b',        14), (r'\bNESADURAI\b',         14),
            (r'\bSINNATAMBY\b',        12), (r'\bSINNATAMBI\b',        12),
            (r'\bVEERAKATTI\b',        12), (r'\bTHAMOTHERAMPILLAI\b', 14),
            (r'\bKANAPATHIPILLAI\b',   14), (r'\bARULAMPALAM\b',       12),
            (r'\bSATHIASEELAN\b',       12), (r'\bSEBASTIAMPILLAI\b',  12),
            (r'\bPILLAI\b',            10), (r'\bCHETTY\b',            12),
            (r'\bCHETTIAR\b',          12), (r'\bNATCHIAR\b',           12),
            (r'\bNATCHIYAR\b',         12), (r'\bMARIKAR\b',           10),
            (r'\bMARIKKAR\b',          10), (r'\bMARICAR\b',           10),
            # Burgher / Dutch Burgher surnames common in NLR
            (r'\bDE\s+CROOS\b',        12), (r'\bDE\s+LIVERA\b',       12),
            (r'\bFOENANDER\b',         12), (r'\bVANDERLAN\b',          12),
            (r'\bKREITZHEIM\b',        12), (r'\bPOULIER\b',           10),
            (r'\bLEEMBRUGGEN\b',       12), (r'\bRODRIGO\b',           10),
            (r'\bDE\s+SARAM\b',        12), (r'\bPEIRIS\b',            10),
            # Muslim names
            (r'\bMOHIDEEN\b',          10), (r'\bMOHAMMED\b',          10),
            (r'\bABDUL\b',             10), (r'\bABDAN\b',             10),
            (r'\bMAHMOOD\b',           10), (r'\bCASSIM\b',            10),
            (r'\bUSOOF\b',             10), (r'\bLEBBE\b',             10),
            (r'\bSAIBO\b',             10), (r'\bASHRAFF\b',           10),
        ]
        for pat, pts in sl_names:
            if re.search(pat, text_upper):
                score += pts
                matched_indicators.append(f"SL name (+{pts})")
                if score >= 35:
                    break

        # ═══════════════════════════════════════════════════════════════════
        # LAYER 6 ── Sri Lankan statutes, ordinances, codes, institutions
        # ═══════════════════════════════════════════════════════════════════
        sl_statutes = [
            # Criminal & Civil Procedure
            (r'\bCIVIL\s+PROCEDURE\s+CODE\b',             12),
            (r'\bCRIMINAL\s+PROCEDURE\s+CODE\b',           12),
            (r'\bCODE\s+OF\s+CRIMINAL\s+PROCEDURE\b',      12),
            (r'\bPENAL\s+CODE\b',                          12),
            # Ordinances
            (r'\bFISCAL[\'S]{0,2}\s+ORDINANCE\b',          12),
            (r'\bCEYLON\s+COURTS\s+ORDINANCE\b',           14),
            (r'\bLAND\s+REGISTRATION\s+ORDINANCE\b',       12),
            (r'\bACQUISITION\s+OF\s+LANDS\s+ORDINANCE\b',  12),
            (r'\bCOMMON\s+LAW\s+OF\s+CEYLON\b',            14),
            (r'\bROMAN.DUTCH\s+LAW\b',                     16),  # Distinctive SL legal system
            (r'\bROMANO.DUTCH\b',                          16),
            (r'\bROMANDUTCH\b',                            14),
            (r'\bVOET[\'S]{0,2}\s+COMM',                   12),  # Voet's Commentaries - cited in NLR
            (r'\bGROTIUS\b',                               12),  # Grotius - Roman-Dutch authority
            (r'\bSOUTH\s+AFRICAN\s+LAW\b',                  8),  # Referenced in Roman-Dutch cases
            # Modern statutes
            (r'\bPREVENTION\s+OF\s+TERRORISM\s+ACT\b',     14),
            (r'\bEMERGENCY\s+REGULATIONS\b',                12),
            (r'\bLAND\s+REFORM\s+LAW\b',                   12),
            (r'\bNATIONALISATION\s+LAW\b',                 12),
            (r'\bIMMIGRATION\s+ACT\b',                     10),
            (r'\bINCOME\s+TAX\s+ORDINANCE\b',              12),
            (r'\bSTAMPS\s+ORDINANCE\b',                    10),
            (r'\bINSOLVENCY\s+ORDINANCE\b',                10),
            (r'\bTESTAMENTARY\b',                          10),  # Testamentary cases common
            # Institutions
            (r'\bATTORNEY.?GENERAL\b',                     12),
            (r'\bSOLICITOR.?GENERAL\b',                    12),
            (r'\bBANK\s+OF\s+CEYLON\b',                    14),
            (r'\bPEOPLE.S\s+BANK\b',                       12),
            (r'\bCEYLON\s+ELECTRICITY\b',                  12),
            (r'\bCEYLON\s+TRANSPORT\b',                    12),
            (r'\bCEYLON\s+PETROLEUM\b',                    12),
            (r'\bCEYLON\s+PORT\b',                         12),
            (r'\bHARBOUR\s+MASTER\b',                       8),
            (r'\bGOVERNMENT\s+AGENT\b',                    10),
            (r'\bASSISTANT\s+GOVERNMENT\s+AGENT\b',        12),
            (r'\bA\.G\.A\.\b',                             12),   # AGA abbreviation
            (r'\bCEYLON\s+(?:POLICE|ARMY|NAVY|AIR\s+FORCE)\b', 12),
            # Constitutional
            (r'\bFUNDAMENTAL\s+RIGHTS?\b',                 12),
            (r'\bCHAPTER\s+III\b',                         10),   # FR chapter in constitution
            (r'\bARTICLE\s+1[0-8]\b',                      12),   # Articles 10-18 (FR)
            (r'\bCONSTITUTION\s+OF\s+(?:SRI\s+LANKA|CEYLON)\b', 14),
        ]
        for pat, pts in sl_statutes:
            if re.search(pat, text_upper):
                score += pts
                matched_indicators.append(f"SL statute (+{pts})")
                if score >= 35:
                    break

        # ═══════════════════════════════════════════════════════════════════
        # LAYER 7 ── Case structure & NLR-specific formatting patterns
        # ═══════════════════════════════════════════════════════════════════
        case_structure = [
            # Standard legal roles
            (r'\bPETITIONER\b',         5), (r'\bRESPONDENT\b',        5),
            (r'\bAPPELLANT\b',          5), (r'\bPLAINTIFF\b',         5),
            (r'\bDEFENDANT\b',          5), (r'\bINTERVENER\b',        5),
            (r'\bCROSS[-\s]APPELLANT\b', 5), (r'\bCROSS[-\s]RESPONDENT\b', 5),
            (r'\bPROSECUTOR\b',         5), (r'\bACCUSED\b',           5),
            (r'\bDECEASED\b',           5), (r'\bCLAIMANT\b',          5),
            # Case terms
            (r'\bJUDGMENT\b',           5), (r'\bJUDGEMENT\b',         5),
            (r'\bAPPEAL\b',             5), (r'\bRULING\b',            5),
            (r'\bCOUNSEL\b',            5), (r'\bAFFIDAVIT\b',         5),
            (r'\bWRIT\b',               5), (r'\bMANDAMUS\b',          8),
            (r'\bCERTIORARI\b',         8), (r'\bHABEAS\s+CORPUS\b',   8),
            (r'\bQUO\s+WARRANTO\b',     8), (r'\bPROHIBITION\b',       5),
            # NLR formal headnote patterns
            (r'\bCUR\.?\s*ADV\.?\s*VULT\b',   14), # Curia advisari vult (common in NLR)
            (r'\bPER\s+CURIAM\b',              10), # Per Curiam
            (r'\bSED\s+QUAERE\b',              10), # Sed Quaere
            (r'\bOBITER\s+DICTUM\b',           10), # Obiter dictum
            (r'\bOBITER\b',                     8),
            (r'\bRATIO\s+DECIDENDI\b',          10),
            (r'\bSTARE\s+DECISIS\b',            10),
            (r'\bIN\s+LIMINE\b',                 8),
            (r'\bEX\s+PARTE\b',                  8),
            (r'\bINTER\s+PARTES\b',              8),
            (r'\bSUB\s+JUDICE\b',                8),
            (r'\bPRIMA\s+FACIE\b',               8),
            (r'\bRES\s+JUDICATA\b',              10),
            (r'\bEX\s+CONTRACTU\b',              10),
            (r'\bMALUM\s+IN\s+SE\b',             8),
            # SLR headnote patterns
            (r'\bISSUE\s+\d+\s*\([A-Z]\)',      10), # "Issue 1 (a)" format from SLR
            (r'\bANSWER\s*:\s+(?:YES|NO)\b',    10), # "Answer: Yes" from SLR
            (r'\bHELD[,:\s]',                   10), # "HELD:" in headnotes
            (r'\bORDERED\s+ACCORDINGLY\b',       12),
            (r'\bDISMISSED\s+WITH\s+COSTS\b',   10),
            (r'\bALLOWED\s+WITH\s+COSTS\b',     10),
        ]
        for pat, pts in case_structure:
            if re.search(pat, text_upper):
                score += pts
                matched_indicators.append(f"Case structure (+{pts})")

        # ═══════════════════════════════════════════════════════════════════
        # LAYER 8 ── NLR/SLR body text opening phrases & headnote styling
        # ═══════════════════════════════════════════════════════════════════
        body_markers = [
            # NLR judgments open with "THE defendant being ...", "THE plaintiff ..."
            (r'\bTHE\s+(?:defendant|plaintiff|accused|petitioner|appellant)\s+being\b', 12),
            (r'\bTHE\s+(?:DEFENDANT|PLAINTIFF|ACCUSED)\s+BEING\b', 12),
            # "This is an appeal from the judgment of the..."
            (r'\bTHIS\s+IS\s+AN\s+APPEAL\s+FROM\b',               10),
            (r'\bAPPEAL\s+FROM\s+THE\s+JUDGMENT\b',               10),
            # Judgment opening patterns in NLR
            (r'\b[A-Z]+,\s+(?:C\.?J\.?|D\.?J\.?|J\.?)\s*\.',     10), # "BERWICK, D.-J."
            (r'\b[A-Z]+,\s+J\.?\s*[:.]',                           10), # "SILVA, J.:"
            (r'\b[A-Z]+,\s+C\.?J\.?\s*[:.]',                       10), # "BANDARANAYAKE, C.J.:"
            # Date-format in NLR headnote region
            (r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b', 8),
            (r'\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b', 8),
            # "Cur.adv.vult" or "Cur. adv. vult"
            (r'\bCur\.?\s*adv\.?\s*vult\b',                        14),
            # "Re PERERA, M.A." style citation
            (r'\bRe\s+[A-Z][a-z]+,\s+[A-Z]',                       12),
            (r'\bIN\s+RE\s+[A-Z]',                                  12),
            # "APPEAL from..." phrasing
            (r'\bAPPEAL\s+from\s+the\b',                           10),
            # "S.C.(Spl)\s+No...." or "S.C. Appeal No."
            (r'\bS\.C\..*?\bNo\.',                                   10),
            (r'\bSC\s+.*?\bNO\.',                                    10),
            (r'\bC\.A\..*?\bNO\.',                                   10),  # CA No.
            (r'\bH\.C\..*?\bNO\.',                                    8),  # HC No.
            # "CONFIRMED" / "REVERSED" at start of headnote
            (r'\bCONFIRMED\b',                                       8),
            (r'\bREVERSED\b',                                        8),
            (r'\bAFFIRMED\b',                                        8),
            (r'\bVARIED\b',                                          8),
        ]
        for pat, pts in body_markers:
            if re.search(pat, text[:5000]):
                score += pts
                matched_indicators.append(f"Body marker (+{pts})")

        # ═══════════════════════════════════════════════════════════════════
        # LAYER 9 ── Legal subject-matter keywords (additive)
        # ═══════════════════════════════════════════════════════════════════
        legal_keywords = [
            (r'\bORDINANCE\b',              5), (r'\bSECTION\s+\d+\b',      5),
            (r'\bARTICLE\s+\d+\b',          5), (r'\bSCHEDULE\b',           4),
            (r'\bSUBSECTION\b',             4), (r'\bREGULATION\s+\d+\b',   5),
            (r'\bCONSTITUTION\b',           8), (r'\bSTATUTE\b',            5),
            (r'\bINJUNCTION\b',             5), (r'\bINTERLOCUTORY\b',      5),
            (r'\bDAMAGES\b',                4), (r'\bLIABILITY\b',          4),
            (r'\bNEGLIGENCE\b',             5), (r'\bCONTRACT\b',           4),
            (r'\bEJECTMENT\b',              6), (r'\bPARTITION\b',          5),
            (r'\bPRESCRIPTION\b',           6), (r'\bUSUFRUCT\b',           8), # Roman-Dutch
            (r'\bFIDEICOMMISSUM\b',         8), (r'\bLEGACY\b',             5),
            (r'\bPROBATE\b',                5), (r'\bINTESTATE\b',          5),
            (r'\bTESTATOR\b',               5), (r'\bTESTATRIX\b',          5),
            (r'\bDOWRY\b',                  6), (r'\bTHIDIYANAM\b',          8), # Kandyan law
            (r'\bHUSBAND\s+AND\s+WIFE\b',   5), (r'\bMARRIAGE\s+ORDINANCE\b', 6),
            (r'\bMORTGAGE\b',               5), (r'\bFIDEJUSSOR\b',          8), # Roman-Dutch
            (r'\bGUARANTOR\b',              5), (r'\bSURETY\b',              5),
            (r'\bGROSS\s+NEGLIGENCE\b',     6), (r'\bVICARIOUS\s+LIABILITY\b', 6),
        ]
        for pat, pts in legal_keywords:
            if re.search(pat, text_upper):
                score += pts
                matched_indicators.append(f"Legal keyword (+{pts})")

        # ═══════════════════════════════════════════════════════════════════
        # Determine pass/fail
        # ═══════════════════════════════════════════════════════════════════
        THRESHOLD = 10
        print(f"📋 Document validation score: {score} (threshold: {THRESHOLD})")
        if matched_indicators:
            print(f"   Matched [{len(matched_indicators)} signals]: {', '.join(matched_indicators[:10])}")
        else:
            print(f"   No indicators found. Text preview: {text[:300]!r}")

        if score < THRESHOLD:
            print(f"❌ VALIDATION FAILED: score {score} < {THRESHOLD}")
            print(f"   Tip: Include 'NLR' or 'SLR' in the filename to fast-track validation.")

        return score >= THRESHOLD


    @staticmethod
    def segment_into_paragraphs(text: str) -> list:
        """Split text into paragraphs for structure analysis"""
        # Split by double newlines or paragraph markers
        paragraphs = re.split(r'\n\s*\n', text)
        # Filter out very short segments
        paragraphs = [p.strip() for p in paragraphs if len(p.strip()) > 50]
        return paragraphs
    
    @classmethod
    def analyze_document_structure(cls, text: str) -> dict:
        """
        Analyze document structure using hybrid classifier
        
        Returns:
            Dictionary with structure analysis results or None if classifier unavailable
        """
        classifier = cls.get_classifier()
        if not classifier:
            return None
        
        try:
            # Segment document
            paragraphs = cls.segment_into_paragraphs(text)
            
            if not paragraphs:
                return None
            
            # Classify using hybrid approach
            result = classifier.classify_document(paragraphs)
            
            return {
                'total_paragraphs': result['statistics']['total_paragraphs'],
                'section_distribution': result['statistics']['section_distribution'],
                'method_distribution': result['statistics']['method_distribution'],
                'sections': result['sections']  # Full paragraph-level classification
            }
        except Exception as e:
            print(f"Structure analysis failed: {e}")
            return None

    @staticmethod
    def process_and_save(db: Session, file_name: str, file_path: str, file_bytes: bytes):
        """Full pipeline: extract, clean, parse metadata, analyze structure, save to DB."""

        raw_text = DocumentProcessor.extract_text_from_pdf(file_bytes)
        cleaned = DocumentProcessor.clean_text(raw_text)
        
        # Validate that this is actually a Sri Lankan legal document
        # Pass the filename so we can use it as a strong signal (e.g. 119-NLR-...)
        if not DocumentProcessor.is_sri_lanka_legal_document(cleaned, file_name=file_name):
            raise ValueError(
                "This document does not appear to be a Sri Lankan legal case (SLR or NLR). "
                "Please upload only Sri Lankan Law Reports (SLR) or New Law Reports (NLR) documents."
            )

        year = extract_case_year(cleaned)
        case_no = extract_case_number(cleaned)
        court = extract_court(cleaned, file_name=file_name)
        
        # Analyze document structure (Section 1.3)
        structure_analysis = DocumentProcessor.analyze_document_structure(cleaned)

        document = LegalDocument(
            file_name=file_name,
            file_path=file_path,
            raw_text=raw_text,
            cleaned_text=cleaned,
            year=year,
            case_number=case_no,
            court=court
        )

        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Attach structure analysis to document object (not saved to DB, just returned)
        if structure_analysis:
            document.structure_analysis = structure_analysis
            print(f"✅ Document structure analyzed: {structure_analysis['total_paragraphs']} paragraphs")
            print(f"   Sections: {structure_analysis['section_distribution']}")

        return document
