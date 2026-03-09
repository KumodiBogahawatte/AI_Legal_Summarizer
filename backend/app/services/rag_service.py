"""
rag_service.py
Service for Retrieval-Augmented Generation (RAG) in the legal summarizer project.
- Uses sentence-transformers for embeddings
- Uses FAISS for vector search
- Uses OpenAI/HuggingFace for LLM (placeholder)
"""

import os
from typing import List, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

# Placeholder for LLM (OpenAI/HuggingFace)
def generate_answer(context: str, query: str) -> str:
    prompt = f"""
You are a legal AI assistant specialized in Sri Lankan court judgments, including New Law Reports (NLR) and Sri Lanka Law Reports (SLR).
Your target audience includes law students, legal researchers, and legal professionals. Your output must be highly accurate, neutral, well-structured, and strictly professional.

You must strictly generate answers ONLY using the retrieved context provided below.

Do NOT add information that is not present in the retrieved text.
Do NOT fabricate legal citations or case names. Do not invent laws, precedents, or external facts.
If the information is not available in the retrieved context, respond with:
\"Insufficient information in retrieved legal context.\"

Your tasks:
1. Generate structured legal summaries including:
   - Case Background / Facts
   - Legal Issues
   - Judicial Reasoning
   - Final Decision
2. Identify any Fundamental Rights implications under Chapter III of the Sri Lankan Constitution (Articles 10–18).
3. Preserve legal terminology but explain complex terms in plain language when generating executive summaries.
4. Maintain citation integrity and reference case names exactly as provided.
5. Maintain strict legal accuracy and absolute neutrality. Do not include personal opinions or biases.

Retrieved Legal Context:
{context}

User Request:
{query}

Using only the retrieved legal context below, generate a 150-word executive summary of the case in plain language suitable for non-lawyers.

Preserve:
- Core legal issue
- Constitutional rights involved (if any)
- Final ruling

Avoid:
- Complex legal jargon
- Adding information not present in the context

Retrieved Context:
{context}

Based only on the retrieved context, identify whether the judgment refers to constitutional provisions or fundamental rights.

If yes:
- Identify the relevant constitutional articles
- Explain how the court interpreted or applied those rights in the case
- Indicate whether a violation was found

If no constitutional issue is mentioned, clearly state that it is not discussed in the case.

Retrieved Context:
{context}

You are analyzing Sri Lankan legal precedents.

Using only the retrieved case texts below:

1. Compare the factual background of the cases.
2. Compare the legal issues.
3. Identify similarities in judicial reasoning.
4. Explain whether one case follows, distinguishes, or departs from the other.

Do NOT infer beyond the provided content.
Do NOT fabricate relationships between cases.

Retrieved Cases:
{context}

You are a retrieval-augmented legal analysis model.

Answer strictly using the retrieved context.
Every factual statement must be traceable to the provided text.

If a required detail is missing:
- Explicitly state that it is not available in the retrieved material.

Do not generalize beyond Sri Lankan legal context.
Do not introduce foreign legal principles.
Do not cite cases not included in the retrieved context.
"""
    # Replace with actual LLM call
    # For now, return prompt and context for testing
    return prompt.replace("{context}", context).replace("{query}", query)

class RAGService:
    def __init__(self, embedding_model_name: str = 'all-MiniLM-L6-v2', index_path: str = 'faiss_index.bin', docs_path: str = 'docs.npy'):
        self.model = SentenceTransformer(embedding_model_name)
        self.index_path = index_path
        self.docs_path = docs_path
        self.index = None
        self.documents = None
        self._load_index()

    def add_document(self, text: str):
        """Add a new document to the RAG index (in-memory, then persist)."""
        # Load or initialize
        docs = list(self.documents) if self.documents is not None else []
        docs.append(text)
        embeddings = self.model.encode(docs, show_progress_bar=False)
        # Rebuild index
        index = faiss.IndexFlatL2(embeddings.shape[1])
        index.add(np.array(embeddings).astype('float32'))
        # Save
        np.save(self.docs_path, np.array(docs, dtype=object))
        faiss.write_index(index, self.index_path)
        # Reload
        self._load_index()

    def _load_index(self):
        if os.path.exists(self.index_path) and os.path.exists(self.docs_path):
            self.index = faiss.read_index(self.index_path)
            self.documents = np.load(self.docs_path, allow_pickle=True)
        else:
            self.index = None
            self.documents = None

    def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        if self.index is None or self.documents is None:
            return []
        query_vec = self.model.encode([query])
        D, I = self.index.search(query_vec, top_k)
        return [self.documents[i] for i in I[0] if i >= 0]

    def rag_answer(self, query: str, top_k: int = 3) -> str:
        retrieved_docs = self.retrieve(query, top_k)
        context = "\n".join(retrieved_docs)
        return generate_answer(context, query)
