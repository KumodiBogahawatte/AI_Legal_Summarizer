#!/usr/bin/env python3
"""
Ingest Google Drive PDF cases into the legal database.
Downloads PDFs from Google Drive URLs and extracts text, metadata, and embeddings.
"""

import os
import json
import re
import argparse
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple
import requests
import pdfplumber
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s]   %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
# Add milliseconds to logging
logging.Formatter.default_time_format = '%Y-%m-%d %H:%M:%S'
logging.Formatter.default_msec_format = '%s,%03d'

# Import database and models
from app.db import SessionLocal
from app.models.document_models import LegalDocument

# Court keywords for classification
COURT_KEYWORDS = {
    'Supreme': ['supreme', 'sc'],
    'Appeal': ['appeal', 'court of appeal', 'ca'],
    'High': ['high court', 'hc'],
    'District': ['district', 'dc'],
    'Magistrate': ['magistrate', 'mag']
}

def load_gdrive_urls(json_path: str = 'data/gdrive_pdf_urls_recursive.json') -> Dict[str, str]:
    """Load Google Drive PDF URLs from JSON mapping file."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Google Drive URLs mapping file not found: {json_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON file {json_path}: {e}")
        return {}

def get_case_name_from_path(file_path: str) -> str:
    """Extract case name from file path."""
    # Get filename without extension
    filename = Path(file_path).stem
    # Replace underscores with spaces
    case_name = filename.replace('_', ' ')
    return case_name

def extract_court_from_text(text: str) -> Optional[str]:
    """Extract court type from PDF text."""
    text_lower = text.lower()
    for court_type, keywords in COURT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return court_type
    return None

def extract_year(text: str) -> Optional[int]:
    """Extract year from PDF text (4-digit pattern between 1800-2099)."""
    years = re.findall(r'\b(1[89]\d{2}|20\d{2})\b', text)
    if years:
        # Return the most recent year found
        return max([int(y) for y in years])
    return None

def extract_case_number(text: str) -> Optional[str]:
    """Extract case number/citation from text."""
    # Look for NLR or SLR citations
    citations = re.findall(r'(?:NLR|SLR)\s*\[\d+\]', text, re.IGNORECASE)
    if citations:
        return citations[0]
    
    # Look for format like "1998/2 SC"
    citations = re.findall(r'\d+/\d+\s*(?:SC|CA|HC|DC|MAG)', text, re.IGNORECASE)
    if citations:
        return citations[0]
    
    return None

def download_and_extract_pdf(gdrive_url: str, max_pages: int = 200) -> Optional[str]:
    """Download PDF from Google Drive and extract text."""
    try:
        # Ensure URL has export=view parameter
        if '?id=' in gdrive_url:
            url = gdrive_url.replace('export=download', 'export=view')
            if 'export=' not in url:
                url = gdrive_url + '&export=view'
        else:
            url = gdrive_url
        
        logger.info(f"Downloading: {gdrive_url.split('/')[-1] if '/' in gdrive_url else gdrive_url}")
        
        # Download PDF with timeout
        response = requests.get(url, timeout=30, allow_redirects=True)
        response.raise_for_status()
        
        # Extract text using pdfplumber
        text = ""
        try:
            import io
            pdf_file = io.BytesIO(response.content)
            with pdfplumber.open(pdf_file) as pdf:
                page_count = min(len(pdf.pages), max_pages)
                for i, page in enumerate(pdf.pages[:page_count]):
                    try:
                        text += page.extract_text() or ""
                    except Exception as e:
                        logger.warning(f"Error extracting text from page {i+1}: {e}")
                        continue
        except Exception as e:
            logger.error(f"Error opening PDF: {e}")
            return None
        
        return text if text else None
        
    except requests.RequestException as e:
        logger.warning(f"Error downloading PDF: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        return None

def ingest_case(
    file_path: str,
    gdrive_url: str,
    session,
    skip_existing: bool = False
) -> Tuple[bool, str]:
    """
    Ingest a single case from Google Drive.
    Returns: (success: bool, message: str)
    """
    try:
        filename = Path(file_path).name
        
        # Check if already exists
        if skip_existing:
            existing = session.query(LegalDocument).filter(
                LegalDocument.file_name == file_path
            ).first()
            if existing:
                return True, f"Skipped (already exists)"
        
        # Download and extract PDF text
        logger.info(f"Downloading: {filename}")
        text = download_and_extract_pdf(gdrive_url)
        if not text:
            return False, "Failed to extract text from PDF"
        
        logger.info(f"Extracting text: {filename}")
        
        # Extract metadata
        case_name = get_case_name_from_path(file_path)
        court = extract_court_from_text(text)
        year = extract_year(text)
        case_number = extract_case_number(text)
        
        logger.info(f"✓ Extracted {len(text)} characters")
        
        # Create document
        doc = LegalDocument(
            file_name=file_path,
            case_name=case_name or "Unknown Case",
            document_text=text,
            court=court or "Unknown",
            year=year or datetime.now().year,
            citation=case_number or "Unknown",
            source='google_drive',
            pdf_link=gdrive_url.replace('export=download', 'export=view')
        )
        
        session.add(doc)
        session.commit()
        
        logger.info(f"✓ Stored in database (ID: {doc.id})")
        
        return True, f"Ingested: {case_name}"
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error ingesting case {file_path}: {e}")
        return False, f"Error: {str(e)[:100]}"

def main():
    parser = argparse.ArgumentParser(description='Ingest Google Drive PDF cases into database')
    parser.add_argument('--max-docs', type=int, default=None, help='Maximum number of documents to ingest')
    parser.add_argument('--skip-existing', action='store_true', help='Skip documents that already exist')
    parser.add_argument('--json-path', default='data/gdrive_pdf_urls_recursive.json', help='Path to Google Drive URLs JSON file')
    
    args = parser.parse_args()
    
    # Load Google Drive URLs
    logger.info(f"Loading Google Drive URLs from {args.json_path}...")
    gdrive_urls = load_gdrive_urls(args.json_path)
    
    if not gdrive_urls:
        logger.error("No Google Drive URLs loaded. Exiting.")
        return
    
    logger.info(f"Found {len(gdrive_urls)} documents in mapping file")
    
    # Create database session
    session = SessionLocal()
    
    processed = 0
    skipped = 0
    failed = 0
    
    try:
        for file_path, gdrive_url in gdrive_urls.items():
            # Check limit
            if args.max_docs and processed >= args.max_docs:
                logger.info(f"Reached maximum documents limit ({args.max_docs})")
                break
            
            success, message = ingest_case(file_path, gdrive_url, session, args.skip_existing)
            
            if success:
                if "Skipped" in message:
                    skipped += 1
                else:
                    processed += 1
            else:
                failed += 1
                logger.error(f"  ✗ {message}")
    
    finally:
        session.close()
    
    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info(f"Ingestion Summary:")
    logger.info(f"  Processed: {processed}")
    logger.info(f"  Skipped: {skipped}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"  Total: {processed + skipped + failed}/{len(gdrive_urls)}")
    logger.info(f"{'='*60}")

if __name__ == '__main__':
    main()
