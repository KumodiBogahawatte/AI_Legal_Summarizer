"""
Script to generate embeddings and FAISS index for RAG
"""
import os
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import json

# Path to your documents (adjust as needed)
DOCS_PATH = '../../data/processed/combined_legal_cases.json'
EMBEDDINGS_PATH = 'docs.npy'
INDEX_PATH = 'faiss_index.bin'
MODEL_NAME = 'all-MiniLM-L6-v2'

# Load documents
def load_documents():
    with open(DOCS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Assume data is a list of dicts with a 'text' field
    return [d['text'] for d in data if 'text' in d]

def main():
    model = SentenceTransformer(MODEL_NAME)
    docs = load_documents()
    embeddings = model.encode(docs, show_progress_bar=True)
    np.save(EMBEDDINGS_PATH, np.array(docs))
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(np.array(embeddings).astype('float32'))
    faiss.write_index(index, INDEX_PATH)
    print(f"Saved {len(docs)} docs and index.")

if __name__ == "__main__":
    main()
