"""
Prepare annotation batches from legal documents for Label Studio.

This script extracts relevant text chunks from the combined legal cases JSON
and prepares them for NER annotation in Label Studio.
"""

import json
import os
import re
from pathlib import Path
from typing import List, Dict
import random

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent
COMBINED_CASES_PATH = PROJECT_ROOT / "data" / "processed" / "combined_legal_cases.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "training_data" / "ner_annotations" / "annotation_batches"
BATCH_SIZE = 50  # Number of texts per batch
MIN_TEXT_LENGTH = 150  # Reduced minimum for more passages
MAX_TEXT_LENGTH = 2000  # Maximum characters per text chunk
MAX_PASSAGES = 1000  # Limit total passages for reasonable annotation workload


def load_legal_cases() -> List[Dict]:
    """Load legal cases from the combined JSON file."""
    print(f"📂 Loading legal cases from: {COMBINED_CASES_PATH}")
    
    with open(COMBINED_CASES_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    cases = data.get('cases', [])
    print(f"✅ Loaded {len(cases)} legal cases")
    return cases


def extract_relevant_passages(case: Dict) -> List[str]:
    """
    Extract relevant passages from a legal case.
    
    Focuses on sections with high entity density:
    - Case headings
    - Court and judge information
    - Legal holdings
    - Case citations
    """
    passages = []
    raw_text = case.get('raw_text', '') or case.get('cleaned_text', '')
    
    if not raw_text:
        return passages
    
    # Split by pages
    pages = raw_text.split('--- Page')
    
    # Process first 15 pages (most legal entities are in early pages)
    for page in pages[:15]:
        # Clean page text
        page_text = page.replace('---', '').strip()
        
        if len(page_text) < 100:  # Skip empty/short pages
            continue
        
        # Split into paragraphs (double newline separated)
        paragraphs = [p.strip() for p in page_text.split('\n\n') if p.strip()]
        
        if not paragraphs:
            # Try single newline split if no double newlines
            paragraphs = [p.strip() for p in page_text.split('\n') if p.strip() and len(p.strip()) > 50]
        
        for para in paragraphs:
            # Skip very short paragraphs
            if len(para) < MIN_TEXT_LENGTH:
                continue
                
            # If paragraph is good size and has legal markers, add it
            if len(para) <= MAX_TEXT_LENGTH:
                if has_legal_markers(para):
                    passages.append(para)
            else:
                # Split long paragraphs into chunks
                chunks = split_into_chunks(para, MAX_TEXT_LENGTH)
                for chunk in chunks:
                    if has_legal_markers(chunk):
                        passages.append(chunk)
    
    return passages


def has_legal_markers(text: str) -> bool:
    """Check if text contains legal markers indicating high entity density."""
    markers = [
        r'\bvs?\.\s',  # Case names (v. or vs.)
        r'\bSupreme Court\b',
        r'\bCourt of Appeal\b',
        r'\bHigh Court\b',
        r'\bJustice\b',
        r'\bArticle\s+\d+',
        r'\bSection\s+\d+',
        r'\b\d{4}\]\s+\d+\s+SLR',  # Citations
        r'\bNLR\s+\d+',
        r'\bAct\b.*\bNo\.\s+\d+',
        r'\bpenal code\b',
        r'\bconstitution\b',
        r'\bfundamental rights\b',
    ]
    
    for pattern in markers:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def split_into_chunks(text: str, max_length: int) -> List[str]:
    """Split long text into chunks at sentence boundaries."""
    chunks = []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_length:
            current_chunk += sentence + " "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return [c for c in chunks if len(c) >= MIN_TEXT_LENGTH]


def prepare_label_studio_format(passages: List[str]) -> List[Dict]:
    """Convert passages to Label Studio import format."""
    tasks = []
    for idx, passage in enumerate(passages):
        task = {
            "data": {
                "text": passage
            },
            "meta": {
                "source": "combined_legal_cases",
                "passage_id": idx + 1
            }
        }
        tasks.append(task)
    
    return tasks


def create_annotation_batches(all_tasks: List[Dict], batch_size: int) -> List[List[Dict]]:
    """Split tasks into annotation batches."""
    random.shuffle(all_tasks)  # Shuffle for variety
    
    batches = []
    for i in range(0, len(all_tasks), batch_size):
        batch = all_tasks[i:i + batch_size]
        batches.append(batch)
    
    return batches


def save_batches(batches: List[List[Dict]], output_dir: Path):
    """Save annotation batches to JSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for idx, batch in enumerate(batches, start=1):
        output_file = output_dir / f"batch_{idx:03d}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(batch, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved batch {idx}: {len(batch)} tasks -> {output_file.name}")


def generate_annotation_summary(batches: List[List[Dict]], output_dir: Path):
    """Generate summary of annotation batches."""
    total_tasks = sum(len(batch) for batch in batches)
    
    summary = {
        "total_batches": len(batches),
        "total_tasks": total_tasks,
        "batch_size": BATCH_SIZE,
        "min_text_length": MIN_TEXT_LENGTH,
        "max_text_length": MAX_TEXT_LENGTH,
        "batches": [
            {
                "batch_number": idx + 1,
                "filename": f"batch_{idx + 1:03d}.json",
                "task_count": len(batch)
            }
            for idx, batch in enumerate(batches)
        ]
    }
    
    summary_file = output_dir / "batches_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n📊 Summary saved to: {summary_file.name}")
    return summary


def main():
    """Main execution function."""
    print("=" * 70)
    print("Preparing Legal Document Annotation Batches for Label Studio")
    print("=" * 70)
    print()
    
    # Load legal cases
    cases = load_legal_cases()
    
    # Extract relevant passages
    print(f"\n📝 Extracting relevant passages from legal cases...")
    all_passages = []
    
    for idx, case in enumerate(cases, 1):
        passages = extract_relevant_passages(case)
        all_passages.extend(passages)
        
        # Progress update every 10 cases
        if idx % 10 == 0:
            print(f"   Processed {idx}/{len(cases)} cases... ({len(all_passages)} passages so far)")
    
    print(f"\n✅ Extracted {len(all_passages)} passages from {len(cases)} cases")
    
    # Limit passages if needed
    if len(all_passages) > MAX_PASSAGES:
        print(f"\n⚠️  Limiting to {MAX_PASSAGES} passages (randomly selected)")
        random.shuffle(all_passages)
        all_passages = all_passages[:MAX_PASSAGES]
    
    # Convert to Label Studio format
    print("\n🔄 Converting to Label Studio format...")
    tasks = prepare_label_studio_format(all_passages)
    
    # Create batches
    print(f"\n📦 Creating annotation batches (batch size: {BATCH_SIZE})...")
    batches = create_annotation_batches(tasks, BATCH_SIZE)
    
    # Save batches
    print(f"\n💾 Saving {len(batches)} batches to disk...")
    save_batches(batches, OUTPUT_DIR)
    
    # Generate summary
    summary = generate_annotation_summary(batches, OUTPUT_DIR)
    
    # Print final summary
    print("\n" + "=" * 70)
    print("ANNOTATION BATCHES READY!")
    print("=" * 70)
    print(f"📁 Output directory: {OUTPUT_DIR}")
    print(f"📊 Total batches: {summary['total_batches']}")
    print(f"📝 Total annotation tasks: {summary['total_tasks']}")
    print()
    print("Next steps:")
    print("1. Install Label Studio: pip install label-studio")
    print("2. Start Label Studio: label-studio start")
    print("3. Create a new project")
    print("4. Import batches from: data/training_data/ner_annotations/annotation_batches/")
    print("=" * 70)


if __name__ == "__main__":
    main()
