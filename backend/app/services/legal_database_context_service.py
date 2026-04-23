"""
legal_database_context_service.py
──────────────────────────────────
Loads and caches the full Sri Lankan legal document corpus from:
  - data/processed/combined_legal_cases.json   (72 NLR/SLR cases with full text)
  - data/sri_lanka_legal_corpus/*.json          (constitutional articles, fundamental rights)

Provides:
  - get_relevant_past_cases(query_text, top_k) → concise summaries for LLM injection
  - get_constitutional_context(article_numbers) → constitutional text for grounding
  - get_fundamental_rights_context()            → fundamental rights text for grounding

These are used to provide the LLM with a grounding database of past cases BEFORE
it analyses a newly uploaded document, ensuring 90%+ accuracy.
"""

import json
import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

# ── Data Paths (project root data/ only) ───────────────────────────────────────
BACKEND_DIR = Path(__file__).parent.parent.parent  # backend/
DATA_DIR = BACKEND_DIR.parent / "data"
CORPUS_DIR = DATA_DIR / "sri_lanka_legal_corpus"

COMBINED_CASES_PATH = DATA_DIR / "processed" / "combined_legal_cases.json"
CONSTITUTION_PATH   = CORPUS_DIR / "constitution_articles.json"
FUNDAMENTAL_RIGHTS_PATH = CORPUS_DIR / "fundamental_rights_articles.json"


class LegalDatabaseContextService:
    """
    Singleton service that loads the full legal corpus in memory and
    provides fast lookup for the LLM grounding pipeline.
    """

    _instance: Optional["LegalDatabaseContextService"] = None
    _loaded: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._loaded:
            return
        self._cases: List[Dict] = []
        self._constitution: Dict = {}
        self._fundamental_rights: Dict = {}
        self._cases_mtime: float = 0.0
        self._load_all()
        LegalDatabaseContextService._loaded = True

    def reload_corpus_if_changed(self) -> None:
        """
        Re-read combined_legal_cases.json when the file mtime changes (or was empty on first load).
        Fixes dev/prod where the JSON is added or rebuilt while uvicorn stays running.
        """
        path = COMBINED_CASES_PATH
        if not path.is_file():
            return
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return
        if mtime == self._cases_mtime and self._cases:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._cases = data.get("cases", [])
            self._cases_mtime = mtime
            logger.info("LegalDatabaseContextService: reloaded %d corpus cases", len(self._cases))
        except Exception as exc:
            logger.warning("Corpus reload failed: %s", exc)

    # ── Data Loading ──────────────────────────────────────────────────────────

    def _load_all(self):
        logger.info("📚 LegalDatabaseContextService: Loading corpus...")

        # 1. Processed NLR/SLR cases (from build_combined_corpus_from_raw.py or existing JSON)
        json_path = COMBINED_CASES_PATH
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._cases = data.get("cases", [])
            try:
                self._cases_mtime = json_path.stat().st_mtime
            except OSError:
                self._cases_mtime = 0.0
            logger.info(f"  ✅ Loaded {len(self._cases)} past cases from {json_path.name}")
        else:
            logger.warning(f"  ⚠️  combined_legal_cases.json not found at {COMBINED_CASES_PATH}")

        # 2. Constitutional articles
        if CONSTITUTION_PATH.exists():
            with open(CONSTITUTION_PATH, "r", encoding="utf-8") as f:
                self._constitution = json.load(f)
            logger.info(f"  ✅ Loaded {len(self._constitution)} constitutional articles")
        else:
            logger.warning("  ⚠️  constitution_articles.json not found")

        # 3. Fundamental rights
        if FUNDAMENTAL_RIGHTS_PATH.exists():
            with open(FUNDAMENTAL_RIGHTS_PATH, "r", encoding="utf-8") as f:
                self._fundamental_rights = json.load(f)
            logger.info(f"  ✅ Loaded {len(self._fundamental_rights)} fundamental rights articles")
        else:
            logger.warning("  ⚠️  fundamental_rights_articles.json not found")

    # ── Case Lookup ───────────────────────────────────────────────────────────

    # Topic clusters: if query and case share terms in a cluster, boost score (thematic relevance)
    _TOPIC_CLUSTERS = [
        ("lease", "rent", "assignment", "lessee", "lessor", "purchaser", "voet", "dominium", "conveyance"),
        ("partition", "co-owner", "co-ownership", "divided", "allotment"),
        ("fundamental rights", "article 12", "article 14", "discrimination", "equality"),
        ("habeas corpus", "detention", "arrest", "custody"),
        ("bank", "loan", "mortgage", "debt", "default", "guarantee"),
    ]

    def _score_case_relevance(self, case: Dict, query_text: str) -> float:
        """
        Score case relevance by keyword overlap, with extra weight for shared legal topics
        and for distinctive terms (party names, subject matter). Uses first 6000 chars of
        query so the document's headnote/facts drive the score, not generic boilerplate.
        """
        # Focus on the distinctive part of the query document (headnote + early facts)
        query_focus = query_text[:6000].lower()
        case_text = (case.get("cleaned_text") or case.get("raw_text") or "")[:8000].lower()

        # 1) Topic boost: if query and case share a topic cluster, add substantial score
        topic_boost = 0.0
        for keywords in self._TOPIC_CLUSTERS:
            in_query = sum(1 for k in keywords if k in query_focus)
            in_case = sum(1 for k in keywords if k in case_text)
            if in_query >= 2 and in_case >= 2:  # both clearly about this topic
                topic_boost += 20.0 + (in_query + in_case) * 2.5
                break  # one topic match is enough

        # 2) Distinctive terms: party names (X v. Y) and 5+ char words — higher weight so different docs rank differently
        party_pattern = re.compile(r"\b([a-z]{2,}\s+v(?:s?)\.?\s+[a-z]{2,})\b", re.IGNORECASE)
        query_parties = set(m.group(1).lower() for m in party_pattern.finditer(query_focus))
        distinct_terms = set(re.findall(r"\b[a-z]{5,}\b", query_focus))
        # Drop very common legal words that appear in almost every judgment
        generic = {"court", "plaintiff", "defendant", "appeal", "judgment", "case", "order", "held", "section", "article", "respondent", "appellant", "learned", "counsel", "petitioner", "application", "rights", "law", "evidence", "trial", "magistrate", "judge"}
        distinct_terms -= generic

        score = 0.0
        for term in query_parties:
            if term in case_text:
                score += 4.0  # party name match is strong signal
        for term in distinct_terms:
            if term in case_text:
                score += 1.0

        # 3) Key legal terms (articles, sections, statutes) — moderate weight
        legal_terms = set(re.findall(
            r"\b(?:article\s+\d+|section\s+\d+|ordinance|act\s+no\.|fundamental rights|habeas corpus|mandamus|certiorari|injunction|writ|locus standi|res judicata)\b",
            query_focus
        ))
        for term in legal_terms:
            if term in case_text:
                score += 2.0

        return score + topic_boost

    _LEX_GENERIC = {
        "court", "plaintiff", "defendant", "appeal", "judgment", "case", "order", "held", "section",
        "article", "respondent", "appellant", "learned", "counsel", "petitioner", "application",
        "rights", "law", "evidence", "trial", "magistrate", "judge", "therefore", "however",
        "whether", "against", "within", "under", "above", "following", "accordance",
    }

    def _fallback_lexical_overlap(self, case: Dict, query_text: str) -> float:
        """
        When _score_case_relevance returns 0 for everything (common for short OCR text or
        mismatched eras), rank by overlap of 4+ letter tokens so Related Cases still surfaces
        plausible NLR/SLR items.
        """
        q = (query_text or "")[:8000].lower()
        case_text = (case.get("cleaned_text") or case.get("raw_text") or "")[:15000].lower()
        if not q.strip() or not case_text.strip():
            return 0.0
        words = set(re.findall(r"\b[a-z]{4,}\b", q))
        words -= self._LEX_GENERIC
        if not words:
            # Very noisy OCR / odd encodings often yield no 4+ char tokens after stopword removal.
            words3 = set(re.findall(r"\b[a-z]{3,}\b", q))
            words3 -= self._LEX_GENERIC
            words3 -= self._LEX_GENERIC_3
            if not words3:
                return 0.0
            hits3 = sum(1 for w in words3 if re.search(rf"\b{re.escape(w)}\b", case_text))
            if hits3 <= 0:
                return 0.0
            return min(8.0, hits3 * 0.22)
        hits = sum(1 for w in words if w in case_text)
        if hits <= 0:
            return 0.0
        return min(12.0, hits * 0.35)

    _LEX_GENERIC_3 = {
        "the", "and", "for", "not", "but", "are", "was", "has", "had", "his", "her", "its",
        "may", "can", "all", "any", "per", "one", "our", "out", "who", "how", "why", "way",
        "two", "six", "ten", "etc", "viz", "cum",
    }

    def legal_filename_tokens(self, file_name: str) -> set[str]:
        """
        Party / subject hints from the PDF basename (e.g. READ-v.-SAMSUDIN → read, samsudin).
        Used when body text scores are all zero so Related Cases still finds the indexed judgment.
        """
        if not file_name:
            return set()
        base = file_name.strip().lower()
        while base.endswith(".pdf"):
            base = base[:-4]
        toks = set(re.findall(r"[a-z]{3,}", base))
        noise = {"pdf", "nlr", "slr", "sllr", "clr", "vol", "part", "copy", "scan", "final"}
        return {t for t in toks if t not in noise}

    def _filename_token_overlap_score(self, case: Dict, name_tokens: set[str]) -> float:
        """
        Match basename tokens against corpus file name + head of judgment (word boundaries).

        Tokens like "read" appear in almost every judgment ("we read the evidence"), so short
        tokens only count when a distinctive token (length >= 5) also matches, or when at least
        two short tokens match (e.g. ALI + KHAN).
        """
        if not name_tokens:
            return 0.0
        blob = " ".join(
            [
                (case.get("file_name") or "").lower(),
                ((case.get("cleaned_text") or case.get("raw_text") or "")[:12000]).lower(),
            ]
        )
        if not blob.strip():
            return 0.0

        def hit(tok: str) -> bool:
            return bool(re.search(rf"\b{re.escape(tok)}\b", blob))

        long_hits = sum(1 for t in name_tokens if len(t) >= 5 and hit(t))
        short_hits = sum(1 for t in name_tokens if len(t) < 5 and hit(t))
        if long_hits > 0:
            hits = long_hits + short_hits
        elif short_hits >= 2:
            hits = short_hits
        else:
            return 0.0
        return min(28.0, 4.0 + float(hits) * 6.0)

    def get_relevant_past_cases(self, query_text: str, top_k: int = 10) -> str:
        """
        Returns a formatted text block of the top-k most relevant past cases
        for injection into the LLM's 'SAVED PAST CASES DATABASE' slot.

        Each entry is a concise summary including:
        - Case name and citation
        - Court and year
        - Key legal principle (first 800 chars of cleaned text)
        """
        if not self._cases:
            return "No past cases database available."

        # Score and rank all cases
        scored = []
        for case in self._cases:
            file_name = case.get("file_name", "Unknown")
            score = self._score_case_relevance(case, query_text)
            scored.append((score, case, file_name))

        # Sort by relevance, take top_k
        scored.sort(key=lambda x: x[0], reverse=True)
        top_cases = scored[:top_k]

        # Format for LLM injection
        lines = ["=== PAST CASES DATABASE (Top Relevant Sri Lankan Legal Precedents) ===\n"]
        
        for rank, (score, case, file_name) in enumerate(top_cases, 1):
            # Extract a concise digest from the cleaned text
            full_text = (case.get("cleaned_text") or case.get("raw_text") or "")[:3000]
            
            # Try to extract case name from the text
            case_name = self._extract_case_name_from_text(full_text) or file_name
            
            # Try to extract citation
            citation = self._extract_citation(full_text, file_name)
            
            # Extract sentences from the text as a digest
            sentences = case.get("sentences", [])
            digest = ""
            if sentences:
                # Take a few key sentences from the middle of the document (judgment area)
                mid = len(sentences) // 3
                digest = " ".join(sentences[mid:mid+5])[:600]
            else:
                digest = full_text[500:1200].strip()  # Skip the header/digest pages

            lines.append(
                f"--- Case {rank} ---\n"
                f"Source File: {file_name}\n"
                f"Citation: {citation}\n"
                f"Case Name: {case_name}\n"
                f"Key Content:\n{digest}\n"
            )

        return "\n".join(lines)

    def _extract_case_name_from_text(self, text: str) -> Optional[str]:
        """Extract case name pattern 'X vs Y' or 'X v Y' from text."""
        patterns = [
            r'\b([A-Z][A-Za-z\s]+)\s+[Vv][Ss]?\.?\s+([A-Z][A-Za-z\s]+)\b',
            r'\b([A-Z][A-Za-z\s]+)\s+[Vv]\.\s+([A-Z][A-Za-z\s]+)\b',
        ]
        for pat in patterns:
            m = re.search(pat, text[:2000])
            if m:
                name = m.group(0).strip()
                if 5 < len(name) < 80:
                    return name
        return None

    def _extract_citation(self, text: str, filename: str) -> str:
        """
        Extract NLR/SLR citation from text or filename.
        Handles OCR-distorted variants like 'SRI L R', 'SRI L.R.', 'Sri Lanka Law Reports' etc.
        Progressive fallback: text patterns → filename parsing → volume inference.
        """
        search_text = text[:4000]

        # Tier 1: Standard citation formats in text
        tier1_patterns = [
            r'\(\d{4}\)\s*\d+\s+(?:SLR|NLR)\s+\d+',            # (2006) 2 SLR 45
            r'\[\d{4}\]\s*\d+\s+(?:SLR|NLR)\s+\d+',            # [2006] 2 SLR 45
            r'\b\d{1,3}\s+(?:NLR|SLR)\s+\d{1,4}\b',            # 45 NLR 123
        ]
        for pat in tier1_patterns:
            m = re.search(pat, search_text, re.IGNORECASE)
            if m:
                return m.group(0).strip()

        # Tier 2: SRI L.R. / SRI L R (OCR variants of "Sri Lanka Law Reports")
        tier2_patterns = [
            r'\[?\(?(\d{4})\)?\]?\s*(\d+)\s+SRI\s+L\.?\s*R\.?',   # [2005] 2 SRI L.R.
            r'(\d+)\s+SRI\s+L\.?\s*R\.?\s+(\d+)',                  # 2 SRI L.R. 45
        ]
        for pat in tier2_patterns:
            m = re.search(pat, search_text, re.IGNORECASE)
            if m:
                return m.group(0).strip()

        # Tier 3: "Sri Lanka Law Reports" spelled out
        m = re.search(
            r'Sri\s+Lanka\s+Law\s+Reports.*?(\d{4}).*?[Pp]art\s*(\d+)',
            search_text, re.DOTALL
        )
        if m:
            return f"Sri Lanka Law Reports ({m.group(1)}) Part {m.group(2)}"

        # Tier 4: NLR volume mentioned in text
        m = re.search(r'(?:New\s+Law\s+Reports?|NLR)[,\s]*Vol(?:ume)?\.?\s*(\d+)', search_text, re.IGNORECASE)
        if m:
            return f"NLR Vol. {m.group(1)}"

        # Tier 4b: Old NLR header "C. R., Colombo, 1,129" or "Colombo, 1,129"
        m = re.search(r'C\.\s*R\.,\s*Colombo,?\s*(\d[\d,\s]*)', search_text, re.IGNORECASE)
        if m:
            num = re.sub(r'[\s,]', '', m.group(1))[:6]
            if num.isdigit():
                return f"C. R. Colombo, {int(num)}"

        # Tier 4c: Year in first 1500 chars (common in NLR headnotes) → "NLR (YYYY)"
        year_m = re.search(r'\b(18[5-9]\d|19[0-9]{2}|20[0-2]\d)\b', search_text[:1500])
        if year_m:
            return f"NLR ({year_m.group(1)})"

        # ── Filename-based fallback ──────────────────────────────────────────
        fn = filename.upper().replace("_", "-")

        # Tier 5: SLR filename: YYYY-VOL-SRI-L.-R.-Part-NN-... 
        # e.g. 2006-2-SRI-L.-R.-Part-03-uckrf5.pdf
        slr_fn = re.match(
            r'(\d{4})-(\d+)-SRI[.-]+L[.-]+R[.-]+-?(?:PARTS?-?([\d-]+))?',
            fn
        )
        if slr_fn:
            year = slr_fn.group(1)
            vol  = slr_fn.group(2)
            part = slr_fn.group(3)
            if part:
                # Extract individual part numbers cleanly (e.g. "9-10" -> "9 & 10", "03" -> "3")
                part_nums = re.findall(r'\d+', part)
                part_clean = ' & '.join(str(int(p)) for p in part_nums) if part_nums else part
                return f"[{year}] {vol} Sri L.R. (Parts {part_clean})"
            return f"[{year}] {vol} Sri L.R."

        # Tier 6: NLR filename: NLR-VOL-NN-... or VOL-NN-NLR-...
        # e.g. NLR-VOL-45.pdf, VOL-45-NLR.pdf, NLR_Vol_45.pdf
        nlr_fn = re.search(r'NLR.*?VOL[.-]?(\d+)|VOL[.-]?(\d+).*?NLR', fn)
        if nlr_fn:
            vol = nlr_fn.group(1) or nlr_fn.group(2)
            return f"NLR Vol. {vol}"

        # Tier 7: SLR year-only from filename
        year_m = re.search(r'(19\d{2}|20\d{2})', fn)
        vol_m  = re.search(r'[-_](\d{1})[-_](?:SRI|SLR)', fn)
        if year_m:
            year = year_m.group(1)
            if 'SRI' in fn or 'SLR' in fn:
                vol = vol_m.group(1) if vol_m else ""
                vol_part = f" {vol}" if vol else ""
                return f"[{year}]{vol_part} Sri L.R."
            if 'NLR' in fn:
                return f"NLR ({year})"

        # Tier 8: Filename like 119-NLR-NLR-V-41-... or NLR-V-41-...
        nlr_vol = re.search(r'(?:^|\D)NLR[-_]?V(?:ol)?[-_]?(\d+)|(\d+)[-_]NLR[-_]NLR[-_]V[-_](\d+)', fn)
        if nlr_vol:
            vol = nlr_vol.group(1) or nlr_vol.group(3)
            if vol:
                return f"NLR Vol. {vol}"

        # No citation found: return empty so UI can show "—" instead of "Citation not specified"
        return ""


    # ── Constitutional Context ────────────────────────────────────────────────

    def get_constitutional_context(self, article_numbers: Optional[List[str]] = None) -> str:
        """
        Returns constitutional article text for grounding.
        If article_numbers provided, returns only those articles.
        Otherwise returns a compact overview of the most important articles.
        """
        if not self._constitution and not self._fundamental_rights:
            return ""

        lines = ["=== SRI LANKAN CONSTITUTIONAL PROVISIONS (for grounding) ===\n"]

        # Use fundamental_rights_articles.json for the key rights articles
        if self._fundamental_rights:
            key_articles = article_numbers or list(self._fundamental_rights.keys())[:12]
            for art_num in key_articles:
                art_str = str(art_num)
                if art_str in self._fundamental_rights:
                    art = self._fundamental_rights[art_str]
                    title = art.get("title", "")[:80]
                    desc = art.get("description", "")[:300]
                    lines.append(f"Article {art_num} – {title}\n  {desc}\n")

        return "\n".join(lines)

    def get_fundamental_rights_context(self) -> str:
        """Returns a brief summary of the fundamental rights chapter (Arts 10-18)."""
        if not self._fundamental_rights:
            return ""

        lines = ["=== FUNDAMENTAL RIGHTS (Chapter III, Articles 10-18) ===\n"]
        for art_num, art in self._fundamental_rights.items():
            title = art.get("category", art.get("title", ""))[:60]
            rights = art.get("rights_protected", [])
            if rights:
                rights_str = "; ".join(rights[:4])
                lines.append(f"Art. {art_num}: {title} — Protects: {rights_str}")
        return "\n".join(lines)

    def get_total_cases_count(self) -> int:
        return len(self._cases)


# ── Singleton Accessor ────────────────────────────────────────────────────────

_db_context_service: Optional[LegalDatabaseContextService] = None

def get_legal_db_context() -> LegalDatabaseContextService:
    """Get or create the singleton LegalDatabaseContextService."""
    global _db_context_service
    if _db_context_service is None:
        _db_context_service = LegalDatabaseContextService()
    _db_context_service.reload_corpus_if_changed()
    return _db_context_service
