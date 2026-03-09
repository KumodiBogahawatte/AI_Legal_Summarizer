"""
constitutional_rag_module.py
RAG sub-pipeline specifically for constitutional rights analysis.

At startup:
- Encodes all Chapter III Articles (10-18 + 14A) as embeddings
- Builds a small in-memory FAISS index (~20 vectors)

At query time:
- Matches case text chunks against constitutional articles
- Returns matched articles with similarity scores and explanations
"""

import numpy as np
import logging
from typing import List, Dict, Optional, Tuple

import faiss

from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)

# Sri Lankan Constitution Chapter III - Fundamental Rights
FUNDAMENTAL_RIGHTS_CORPUS = {
    "10": {
        "title": "Freedom of Thought, Conscience and Religion",
        "text": (
            "Every person is entitled to freedom of thought, conscience and religion, "
            "including the freedom to have or to adopt a religion or belief of his choice."
        ),
    },
    "11": {
        "title": "Freedom from Torture",
        "text": (
            "No person shall be subjected to torture or to cruel, inhuman or degrading "
            "treatment or punishment."
        ),
    },
    "12": {
        "title": "Right to Equality",
        "text": (
            "All persons are equal before the law and are entitled to the equal protection "
            "of the law. No citizen shall be discriminated against on grounds of race, religion, "
            "language, caste, sex, political opinion, place of birth or any such grounds. "
            "No person shall be subjected to any disability on grounds of race, religion, language "
            "or caste with regard to access to shops, public restaurants, hotels or places of "
            "public entertainment and places of public worship of his own religion."
        ),
    },
    "13": {
        "title": "Freedom from Arbitrary Arrest, Detention and Punishment",
        "text": (
            "No person shall be arrested except according to procedure established by law. "
            "Any person arrested shall be informed of the reason for his arrest. Every person "
            "held in custody, detained or otherwise deprived of personal liberty shall be "
            "brought before the judge of the nearest competent court. Every person charged with "
            "an offence shall be entitled to be heard, in person or by an attorney-at-law, at a "
            "fair trial by a competent court."
        ),
    },
    "14": {
        "title": "Freedom of Speech, Assembly, Association, Occupation and Movement",
        "text": (
            "Every citizen is entitled to the freedom of speech and expression including "
            "publication; the freedom of peaceful assembly; the freedom of association; "
            "the freedom to form and join a trade union; the freedom to manifest his religion; "
            "the freedom to engage in any lawful occupation, profession, trade, business or "
            "enterprise; the freedom of movement and of choosing his residence within Sri Lanka."
        ),
    },
    "14A": {
        "title": "Right to Access Information",
        "text": (
            "Every citizen shall have the right of access to any information as provided for "
            "by law, being information that is required for the exercise or protection of a "
            "citizen's right. No restrictions shall be placed on the right declared and recognized "
            "by this Article, other than such restrictions as may be prescribed by law in the "
            "interests of national security, the prevention of crime or the protection of public "
            "health or morality."
        ),
    },
    "15": {
        "title": "Restrictions on Fundamental Rights",
        "text": (
            "The exercise and operation of the fundamental rights declared and recognized by "
            "Articles 12(1), 13 and 14 shall be subject to such restrictions as may be prescribed "
            "by law in the interests of national security, public order and the protection of "
            "public health or morality, or for the purpose of securing due recognition and respect "
            "for the rights and freedoms of others, or of meeting the just requirements of the "
            "general welfare of a democratic society."
        ),
    },
    "16": {
        "title": "Existing Written Law and Unwritten Law",
        "text": (
            "All existing written law and unwritten law shall, to the extent that they are "
            "inconsistent with the provisions of this Chapter, be and shall be deemed to have "
            "been amended or repealed on the commencement of the Constitution."
        ),
    },
    "17": {
        "title": "Remedy for Infringement of Fundamental Rights by Executive Action",
        "text": (
            "Every person shall be entitled to apply to the Supreme Court, as provided by "
            "Article 126, in respect of the infringement or imminent infringement by executive "
            "or administrative action of any fundamental right to which such person is entitled "
            "under the provisions of this Chapter."
        ),
    },
    "18": {
        "title": "Restrictions on Fundamental Rights — Derogation",
        "text": (
            "The exercise and operation of the fundamental rights shall be subject to such "
            "restrictions as may be prescribed by law in the interests of national security "
            "in any period of public emergency as declared under Article 155."
        ),
    },
    # Important jurisdictional articles often cited alongside FR
    "126": {
        "title": "Jurisdiction of Supreme Court for Fundamental Rights",
        "text": (
            "The Supreme Court shall have sole and exclusive jurisdiction to hear and determine "
            "any question relating to the infringement or imminent infringement by executive or "
            "administrative action of any fundamental right or language right declared and "
            "recognized by Chapter III or Chapter IV."
        ),
    },
    "140": {
        "title": "Jurisdiction of Court of Appeal — Writs",
        "text": (
            "The Court of Appeal shall have power to grant and issue according to law, "
            "orders in the nature of writs of certiorari, prohibition, procedendo, mandamus "
            "and quo warranto against any person or body of persons performing any "
            "public duty."
        ),
    },
}


class ConstitutionalRAGModule:
    """
    Dedicated RAG module for constitutional rights analysis.
    Encodes all Chapter III articles at startup and matches case chunks against them.
    """

    def __init__(self, similarity_threshold: float = 0.40):
        self.similarity_threshold = similarity_threshold
        self._embedding_service = None
        self.article_index: Optional[faiss.Index] = None
        self.article_keys: List[str] = []  # parallel to FAISS rows
        self._build_article_index()

    @property
    def embedding_service(self):
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service

    def _build_article_index(self):
        """Encode all constitutional articles and build in-memory FAISS index."""
        try:
            keys = list(FUNDAMENTAL_RIGHTS_CORPUS.keys())
            texts = [
                f"Article {k}: {v['title']}. {v['text']}"
                for k, v in FUNDAMENTAL_RIGHTS_CORPUS.items()
            ]

            embeddings = self.embedding_service.encode_for_retrieval_batch(texts)
            # Normalize
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-10
            embeddings = (embeddings / norms).astype(np.float32)

            dim = embeddings.shape[1]
            self.article_index = faiss.IndexFlatIP(dim)
            self.article_index.add(embeddings)
            self.article_keys = keys

            logger.info(
                f"✅ ConstitutionalRAGModule: Indexed {len(keys)} articles "
                f"(dim={dim})"
            )

        except Exception as e:
            logger.error(f"Failed to build constitutional article index: {e}")
            self.article_index = None
            self.article_keys = []

    def match_articles(
        self,
        text: str,
        top_k: int = 5,
    ) -> List[Dict]:
        """
        Given case text (or a chunk), find matching constitutional articles.

        Returns:
            List of dicts:
              - article_number: str (e.g. "12")
              - title: str
              - explanation: str
              - similarity: float (0–1)
              - matched_text: str (the input text snippet)
        """
        if self.article_index is None or not text.strip():
            return []

        try:
            query_vec = self.embedding_service.encode_for_retrieval(text)
            query_vec = query_vec / (np.linalg.norm(query_vec) + 1e-10)
            query_vec = query_vec.astype(np.float32).reshape(1, -1)

            k = min(top_k, len(self.article_keys))
            distances, indices = self.article_index.search(query_vec, k)

            results = []
            seen = set()

            for dist, idx in zip(distances[0], indices[0]):
                if idx < 0 or idx >= len(self.article_keys):
                    continue
                similarity = float(dist)
                if similarity < self.similarity_threshold:
                    continue

                article_num = self.article_keys[idx]
                if article_num in seen:
                    continue
                seen.add(article_num)

                article_data = FUNDAMENTAL_RIGHTS_CORPUS[article_num]

                # Extract a short matched snippet from input text
                words = text.split()
                snippet = " ".join(words[:30]) + ("..." if len(words) > 30 else "")

                results.append({
                    "article_number": article_num,
                    "title": article_data["title"],
                    "explanation": article_data["text"],
                    "similarity": round(similarity, 4),
                    "matched_text": snippet,
                    "is_fundamental_right": article_num not in ("126", "140"),
                })

            return sorted(results, key=lambda r: r["similarity"], reverse=True)

        except Exception as e:
            logger.error(f"Error in constitutional article matching: {e}")
            return []

    def analyse_case_chunks(
        self,
        chunks: List[Dict],
        top_k_per_chunk: int = 3,
    ) -> List[Dict]:
        """
        Analyse a list of retrieved chunks and return deduplicated constitutional matches.

        Args:
            chunks: List of chunk dicts (must have 'text' key)
            top_k_per_chunk: How many articles to match per chunk

        Returns:
            Deduplicated set of constitutional article matches, sorted by avg similarity
        """
        article_scores: Dict[str, List[float]] = {}
        article_data_map: Dict[str, Dict] = {}

        for chunk in chunks:
            text = chunk.get("text", "")
            if not text:
                continue

            matches = self.match_articles(text, top_k=top_k_per_chunk)
            for match in matches:
                art_num = match["article_number"]
                if art_num not in article_scores:
                    article_scores[art_num] = []
                    article_data_map[art_num] = match
                article_scores[art_num].append(match["similarity"])

        # Build final list with average similarity
        results = []
        for art_num, scores in article_scores.items():
            entry = dict(article_data_map[art_num])
            entry["similarity"] = round(float(np.mean(scores)), 4)
            entry["occurrence_count"] = len(scores)
            results.append(entry)

        return sorted(results, key=lambda r: r["similarity"], reverse=True)


# Global singleton
_constitutional_rag: Optional[ConstitutionalRAGModule] = None


def get_constitutional_rag() -> ConstitutionalRAGModule:
    global _constitutional_rag
    if _constitutional_rag is None:
        _constitutional_rag = ConstitutionalRAGModule()
    return _constitutional_rag
