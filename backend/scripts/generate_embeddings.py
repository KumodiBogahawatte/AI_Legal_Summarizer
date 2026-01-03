"""
Embedding Generation Script for Legal Documents

This script generates embeddings for all legal documents in the database
that don't already have embeddings. It uses the EmbeddingService to create
384-dimensional vectors for precedent matching.

Usage:
    python scripts/generate_embeddings.py [--batch-size 10] [--force]

Options:
    --batch-size: Number of documents to process in parallel (default: 10)
    --force: Regenerate embeddings even for documents that already have them
"""

import sys
import os
from pathlib import Path
import argparse
from tqdm import tqdm
import json

# Add parent directory to path to import from app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app.models.document_model import LegalDocument
from app.services.embedding_service import get_embedding_service


def prepare_document_text(doc: LegalDocument) -> str:
    """
    Prepare document text for embedding generation.
    
    Combines file name, court, year, and cleaned text into a coherent text.
    """
    parts = []
    
    # Add file name as title
    if doc.file_name:
        parts.append(f"Title: {doc.file_name}")
    
    # Add court and year
    court_info = []
    if doc.court:
        court_info.append(doc.court)
    if doc.year:
        court_info.append(str(doc.year))
    if court_info:
        parts.append(f"Court: {' '.join(court_info)}")
    
    # Add main content (prefer cleaned_text if available, otherwise raw_text)
    if doc.cleaned_text and len(doc.cleaned_text) > 100:
        # Use first 2000 characters to avoid extremely long documents
        parts.append(doc.cleaned_text[:2000])
    elif doc.raw_text:
        # Use first 2000 characters of raw text
        parts.append(doc.raw_text[:2000])
    
    return "\n\n".join(parts)


def count_documents_needing_embeddings(db, force: bool = False):
    """Count how many documents need embeddings."""
    if force:
        return db.query(LegalDocument).count()
    else:
        # Use IS NULL check only - JSON comparison doesn't work in PostgreSQL
        return db.query(LegalDocument).filter(
            LegalDocument.embedding.is_(None)
        ).count()


def get_documents_needing_embeddings(db, batch_size: int, force: bool = False):
    """Get documents that need embeddings in batches."""
    if force:
        query = db.query(LegalDocument)
    else:
        # Use IS NULL check only - JSON comparison doesn't work in PostgreSQL
        query = db.query(LegalDocument).filter(
            LegalDocument.embedding.is_(None)
        )
    
    return query.limit(batch_size).all()


def generate_embeddings(batch_size: int = 10, force: bool = False, dry_run: bool = False):
    """
    Generate embeddings for all documents in the database.
    
    Args:
        batch_size: Number of documents to process at once
        force: Regenerate embeddings for all documents (even if they have them)
        dry_run: Just count documents, don't generate embeddings
    """
    db = SessionLocal()
    embedding_service = get_embedding_service()
    
    try:
        # Count total documents
        total_docs = count_documents_needing_embeddings(db, force)
        
        if total_docs == 0:
            print("✅ All documents already have embeddings!")
            return
        
        print(f"\n{'=' * 70}")
        print(f"📊 Embedding Generation Summary")
        print(f"{'=' * 70}")
        print(f"Total documents to process: {total_docs}")
        print(f"Batch size: {batch_size}")
        print(f"Force regeneration: {force}")
        print(f"Dry run: {dry_run}")
        print(f"{'=' * 70}\n")
        
        if dry_run:
            print("🔍 Dry run mode - no embeddings will be generated")
            return
        
        # Statistics
        stats = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        # Process in batches
        with tqdm(total=total_docs, desc="Generating embeddings") as pbar:
            while True:
                # Get batch of documents
                documents = get_documents_needing_embeddings(db, batch_size, force)
                
                if not documents:
                    break
                
                for doc in documents:
                    stats['processed'] += 1
                    
                    try:
                        # Prepare text
                        text = prepare_document_text(doc)
                        
                        if not text or len(text) < 50:
                            stats['skipped'] += 1
                            stats['errors'].append({
                                'id': doc.id,
                                'title': doc.title,
                                'error': 'Insufficient text content'
                            })
                            pbar.update(1)
                            continue
                        
                        # Generate embedding
                        embedding = embedding_service.generate_document_embedding(
                            text, 
                            strategy='mean'  # Use mean pooling for document representation
                        )
                        
                        # Convert to list for PostgreSQL JSON storage
                        doc.embedding = embedding.tolist()
                        
                        # Commit to database
                        db.commit()
                        
                        stats['successful'] += 1
                        pbar.update(1)
                        
                    except Exception as e:
                        stats['failed'] += 1
                        stats['errors'].append({
                            'id': doc.id,
                            'file_name': doc.file_name,
                            'error': str(e)
                        })
                        db.rollback()
                        pbar.update(1)
                        continue
        
        # Print final statistics
        print(f"\n{'=' * 70}")
        print(f"✅ Embedding Generation Complete!")
        print(f"{'=' * 70}")
        print(f"Processed: {stats['processed']}")
        print(f"Successful: {stats['successful']} ✅")
        print(f"Failed: {stats['failed']} ❌")
        print(f"Skipped: {stats['skipped']} ⚠️")
        print(f"{'=' * 70}\n")
        
        # Print errors if any
        if stats['errors']:
            print(f"\n⚠️ Errors encountered ({len(stats['errors'])}):")
            for i, error in enumerate(stats['errors'][:10], 1):  # Show first 10 errors
                print(f"{i}. Document ID {error['id']}: {error['error']}")
                if error.get('title'):
                    print(f"   Title: {error['title']}")
            
            if len(stats['errors']) > 10:
                print(f"   ... and {len(stats['errors']) - 10} more errors")
            
            # Save full error log
            error_log_path = Path(__file__).parent.parent / 'logs' / 'embedding_errors.json'
            error_log_path.parent.mkdir(exist_ok=True)
            with open(error_log_path, 'w', encoding='utf-8') as f:
                json.dump(stats['errors'], f, indent=2)
            print(f"\n📝 Full error log saved to: {error_log_path}")
        
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()


def verify_embeddings():
    """Verify that embeddings were generated correctly."""
    db = SessionLocal()
    
    try:
        total = db.query(LegalDocument).count()
        with_embeddings = db.query(LegalDocument).filter(
            LegalDocument.embedding != None,
            LegalDocument.embedding != []
        ).count()
        
        print(f"\n{'=' * 70}")
        print(f"📊 Embedding Verification")
        print(f"{'=' * 70}")
        print(f"Total documents: {total}")
        print(f"Documents with embeddings: {with_embeddings}")
        print(f"Coverage: {(with_embeddings / total * 100):.2f}%")
        print(f"{'=' * 70}\n")
        
        # Sample verification
        sample = db.query(LegalDocument).filter(
            LegalDocument.embedding != None,
            LegalDocument.embedding != []
        ).first()
        
        if sample:
            print(f"✅ Sample document with embedding:")
            print(f"   ID: {sample.id}")
            print(f"   Title: {sample.title}")
            print(f"   Embedding dimensions: {len(sample.embedding)}")
            print(f"   First 5 values: {sample.embedding[:5]}")
        
    finally:
        db.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate embeddings for legal documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate embeddings for documents without them
    python scripts/generate_embeddings.py
    
    # Process 20 documents at a time
    python scripts/generate_embeddings.py --batch-size 20
    
    # Regenerate all embeddings
    python scripts/generate_embeddings.py --force
    
    # Verify embeddings without generating
    python scripts/generate_embeddings.py --verify
    
    # Dry run (count only)
    python scripts/generate_embeddings.py --dry-run
        """
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Number of documents to process in parallel (default: 10)'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Regenerate embeddings for all documents (even if they exist)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Count documents that need embeddings without generating'
    )
    
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify existing embeddings without generating new ones'
    )
    
    args = parser.parse_args()
    
    if args.verify:
        verify_embeddings()
    else:
        generate_embeddings(
            batch_size=args.batch_size,
            force=args.force,
            dry_run=args.dry_run
        )


if __name__ == '__main__':
    main()
