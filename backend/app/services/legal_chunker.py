"""
legal_chunker.py
Splits legal documents into overlapping, semantically coherent chunks.
Preserves:
  - Legal citations (never split mid-citation)
  - Constitutional article references
  - Section boundaries (FACTS / ISSUES / REASONING / etc.)
"""

import re
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Section keywords mapped to section types (from existing document_processor.py patterns)
SECTION_PATTERNS = {
    "FACTS": [
        r"\bfacts?\b", r"\bbackground\b", r"\bstatement of facts?\b",
        r"\bfactual background\b", r"\bbrief facts?\b", r"\bpleadings?\b",
    ],
    "ISSUES": [
        r"\bissues? (?:for )?determination\b", r"\bquestions? of law\b",
        r"\bmatters? (?:in )?(?:dispute|issue)\b", r"\bissues? (?:raised|to be)\b",
    ],
    "LEGAL_ANALYSIS": [
        r"\blegal analysis\b", r"\banalysis\b", r"\blaw\b", r"\bstatute\b",
        r"\bordinance\b", r"\bsection \d+\b", r"\bunder the act\b",
    ],
    "REASONING": [
        r"\breasoning\b", r"\bwe (?:are )?of (?:the )?(?:view|opinion)\b",
        r"\bwe hold\b", r"\bwe find\b", r"\bin our (?:judgment|view)\b",
        r"\bwe consider\b", r"\bwe are satisfied\b",
    ],
    "JUDGMENT": [
        r"\bjudgment\b", r"\bjudgement\b", r"\bverdict\b", r"\bdecision\b",
        r"\bheld\b", r"\bwe (?:allow|dismiss|uphold|affirm|set aside)\b",
    ],
    "ORDERS": [
        r"\borders?\b", r"\bit is (?:hereby )?ordered\b", r"\brelief\b",
        r"\bwe (?:make|grant|award)\b", r"\bcosts?\b", r"\bdamages?\b",
    ],
}

# Citation patterns — never split inside these
SL_CITATION_PATTERN = re.compile(
    r'[\[\(]\d{4}[\]\)]\s+\d*\s*(?:SLR|NLR|SLLR|CLR)\s+\d+'
    r'|(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+v\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
    re.MULTILINE
)

# Constitutional article pattern
ARTICLE_PATTERN = re.compile(
    r'Articles?\s+\d+[A-Z]?(?:\(\d+\))?(?:\s*(?:and|,)\s*\d+[A-Z]?(?:\(\d+\))?)*',
    re.IGNORECASE
)


class LegalChunk:
    """Represents a single RAG-ready chunk of a legal document."""
    def __init__(
        self,
        text: str,
        chunk_index: int,
        char_start: int,
        char_end: int,
        section_type: str = "OTHER",
        article_refs: Optional[List[str]] = None,
        citation_refs: Optional[List[str]] = None,
    ):
        self.text = text
        self.chunk_index = chunk_index
        self.char_start = char_start
        self.char_end = char_end
        self.section_type = section_type
        self.article_refs = article_refs or []
        self.citation_refs = citation_refs or []

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "chunk_index": self.chunk_index,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "section_type": self.section_type,
            "article_refs": self.article_refs,
            "citation_refs": self.citation_refs,
        }


class LegalChunker:
    """
    Splits legal document text into overlapping chunks optimized for RAG.

    Strategy:
    1. Split on sentence boundaries (not mid-sentence).
    2. Group sentences into chunks of ~chunk_size tokens (approximate: 1 token ≈ 4 chars).
    3. Overlap consecutive chunks by overlap_size tokens to preserve context across boundaries.
    4. Never split citation text across chunks.
    5. Annotate each chunk with section_type, article_refs, citation_refs.
    """

    def __init__(
        self,
        chunk_size: int = 512,      # approximate tokens per chunk
        overlap: int = 128,          # overlap in tokens between chunks
        min_chunk_chars: int = 100,  # skip chunks shorter than this
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_chars = min_chunk_chars
        # Characters per token approximation
        self._chars_per_token = 4

    def _approx_tokens(self, text: str) -> int:
        return max(1, len(text) // self._chars_per_token)

    def _detect_section_type(self, text: str) -> str:
        """Detect the dominant section type of a chunk using keyword matching."""
        text_lower = text.lower()
        scores: Dict[str, int] = {s: 0 for s in SECTION_PATTERNS}
        for section, patterns in SECTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    scores[section] += 1
        best = max(scores, key=lambda s: scores[s])
        return best if scores[best] > 0 else "OTHER"

    def _extract_article_refs(self, text: str) -> List[str]:
        """Extract constitutional article numbers referenced in the chunk."""
        refs = []
        for match in ARTICLE_PATTERN.finditer(text):
            # Extract all numbers from the match
            numbers = re.findall(r'\d+[A-Z]?', match.group())
            for num in numbers:
                base = re.sub(r'[A-Z]', '', num)
                if base.isdigit():
                    int_num = int(base)
                    if 10 <= int_num <= 18 or int_num in (126, 140):
                        refs.append(num)
        return list(set(refs))

    def _extract_citation_refs(self, text: str) -> List[str]:
        """Extract SLR/NLR citations from the chunk."""
        return list(set(SL_CITATION_PATTERN.findall(text)))

    def _split_into_sentences(self, text: str) -> List[Tuple[str, int]]:
        """
        Split text into (sentence, char_start) tuples.
        Protects legal abbreviations so sentence boundaries are correct.
        """
        # Protect safe abbreviations
        protected = text
        abbrevs = {
            " v. ": " v<DOT> ", " vs. ": " vs<DOT> ", " J. ": " J<DOT> ",
            " CJ. ": " CJ<DOT> ", " No. ": " No<DOT> ", " Art. ": " Art<DOT> ",
            " Sec. ": " Sec<DOT> ", " Ltd. ": " Ltd<DOT> ", " et al. ": " et_al<DOT> ",
        }
        for old, new in abbrevs.items():
            protected = protected.replace(old, new)

        # Split on sentence endings
        sentence_splitter = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
        raw_sentences = sentence_splitter.split(protected)

        # Restore abbreviations and compute char offsets
        sentences_with_offsets: List[Tuple[str, int]] = []
        offset = 0
        for raw in raw_sentences:
            restored = raw
            for old, new in abbrevs.items():
                restored = restored.replace(new, old)
            # Find where this sentence starts in original text
            start = text.find(restored[:40], offset)
            if start == -1:
                start = offset
            sentences_with_offsets.append((restored, start))
            offset = start + len(restored)

        return sentences_with_offsets

    def chunk(self, text: str) -> List[LegalChunk]:
        """
        Main entry point. Returns a list of LegalChunk objects.
        """
        if not text or len(text.strip()) < self.min_chunk_chars:
            return []

        sentences = self._split_into_sentences(text)
        if not sentences:
            return []

        chunks: List[LegalChunk] = []
        chunk_index = 0

        # Convert overlap to sentence count (approximate)
        overlap_chars = self.overlap * self._chars_per_token
        max_chars = self.chunk_size * self._chars_per_token

        i = 0
        while i < len(sentences):
            current_sentences = []
            current_chars = 0
            char_start = sentences[i][1]

            # Collect sentences until we hit the chunk size limit
            j = i
            while j < len(sentences):
                sent, sent_start = sentences[j]
                sent_chars = len(sent)

                # Check if adding this sentence would exceed chunk_size
                if current_chars + sent_chars > max_chars and current_sentences:
                    break

                current_sentences.append(sent)
                current_chars += sent_chars + 1  # +1 for space
                j += 1

            # Build chunk text
            chunk_text = " ".join(current_sentences).strip()

            if len(chunk_text) >= self.min_chunk_chars:
                char_end = char_start + len(chunk_text)
                section_type = self._detect_section_type(chunk_text)
                article_refs = self._extract_article_refs(chunk_text)
                citation_refs = self._extract_citation_refs(chunk_text)

                chunks.append(LegalChunk(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    char_start=char_start,
                    char_end=char_end,
                    section_type=section_type,
                    article_refs=article_refs,
                    citation_refs=citation_refs,
                ))
                chunk_index += 1

            # Move forward, but overlap by going back in sentences
            if j >= len(sentences):
                break

            # Find overlap: step back by overlap_chars worth of sentences
            overlap_sentences = 0
            overlap_accumulated = 0
            for k in range(j - 1, i, -1):
                overlap_accumulated += len(sentences[k][0])
                overlap_sentences += 1
                if overlap_accumulated >= overlap_chars:
                    break

            # Advance i, but leave overlap sentences
            i = max(i + 1, j - overlap_sentences)

        logger.info(
            f"LegalChunker: {len(chunks)} chunks from {len(text)} chars "
            f"(chunk_size={self.chunk_size}, overlap={self.overlap})"
        )
        return chunks


# Convenience function
def chunk_legal_document(
    text: str,
    chunk_size: int = 512,
    overlap: int = 128,
) -> List[LegalChunk]:
    """Convenience wrapper around LegalChunker."""
    return LegalChunker(chunk_size=chunk_size, overlap=overlap).chunk(text)
