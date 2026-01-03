"""
Import legal cases from combined_legal_cases.json into database for precedent matching.

This script:
1. Loads all legal cases from the dataset
2. Imports them into the legal_documents table
3. Generates embeddings for precedent matching
4. Provides progress tracking and statistics

Usage:
    python scripts/import_dataset_for_precedents.py [--batch-size 10] [--dry-run]
"""

import sys
import json
import argparse
from pathlib import Path
from tqdm import tqdm

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db import SessionLocal
from app.models.document_model import LegalDocument
from app.services.embedding_service import EmbeddingService

def import_dataset(dataset_path: Path, batch_size: int = 10, dry_run: bool = False):
    """
    Import legal cases from dataset and generate embeddings.

    Args:
        dataset_path: Path to combined_legal_cases.json
        batch_size: Number of documents to process at once
        dry_run: If True, don't actually import or generate embeddings
    """
    print("\n" + "=" * 80)
    print("📚 Legal Dataset Import for Precedent Matching")
    print("=" * 80)

    # Load dataset
    print(f"\n📖 Loading dataset from: {dataset_path}")
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cases = data.get('cases', [])
    metadata = data.get('metadata', {})
    total_cases = len(cases)
    print(f"✅ Found {total_cases} legal cases in dataset")
    print(f"📊 Metadata: {metadata.get('description', 'N/A')}")

    if dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made")
        return

    db = SessionLocal()
    embedding_service = EmbeddingService()

    stats = {
        'imported': 0,
        'skipped': 0,
        'embeddings_generated': 0,
        'errors': []
    }

    try:
        print("\n🚀 Starting import process...")
        print("=" * 80)

        for case in tqdm(cases, desc="Importing cases"):
            try:
                file_name = case.get('file_name')
                cleaned_text = case.get('cleaned_text', '')
                raw_text = case.get('raw_text', '')
                court = case.get('court')
                year = case.get('case_year')
                case_number = case.get('case_number')

                if not file_name or (not cleaned_text and not raw_text):
                    stats['skipped'] += 1
                    continue

                # Check if already exists
                existing = db.query(LegalDocument).filter_by(file_name=file_name).first()
                if existing:
                    stats['skipped'] += 1
                    continue

                # Create document
                doc = LegalDocument(
                    file_name=file_name,
                    file_path=f"dataset/{file_name}",
                    raw_text=raw_text,
                    cleaned_text=cleaned_text,
                    court=court,
                    year=year,
                    case_number=case_number
                )

                db.add(doc)
                db.flush()

                # Generate embedding (use first 2000 chars)
                text_for_embedding = (cleaned_text or raw_text)[:2000]
                embedding = embedding_service.generate_embedding(text_for_embedding)
                doc.embedding = embedding.tolist()
                stats['embeddings_generated'] += 1

                db.commit()
                stats['imported'] += 1

            except Exception as e:
                stats['errors'].append({'file': file_name, 'error': str(e)})
                db.rollback()

        print("\n" + "=" * 80)
        print("✅ Import Complete!")
        print("=" * 80)
        print(f"📊 Statistics:")
        print(f"  - Total cases in dataset: {total_cases}")
        print(f"  - Imported: {stats['imported']} ✅")
        print(f"  - Embeddings generated: {stats['embeddings_generated']} ✅")
        print(f"  - Skipped (duplicates): {stats['skipped']} ⚠️")
        print(f"  - Errors: {len(stats['errors'])} ❌")

        if stats['errors']:
            print("\n❌ Errors encountered:")
            for err in stats['errors'][:10]:
                print(f"  - {err['file']}: {err['error']}")

        total_docs = db.query(LegalDocument).count()
        docs_with_embeddings = db.query(LegalDocument).filter(
            LegalDocument.embedding.isnot(None)
        ).count()
        print(f"\n📈 Database Summary:")
        print(f"  - Total documents: {total_docs}")
        print(f"  - Documents with embeddings: {docs_with_embeddings}")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Import legal cases dataset')
    parser.add_argument('--dry-run', action='store_true', help='Simulate without changes')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size')

    args = parser.parse_args()

    dataset_path = Path(__file__).parent.parent / 'data' / 'processed' / 'combined_legal_cases.json'

    if not dataset_path.exists():
        print(f"❌ Dataset not found: {dataset_path}")
        sys.exit(1)

    import_dataset(dataset_path, args.batch_size, args.dry_run)