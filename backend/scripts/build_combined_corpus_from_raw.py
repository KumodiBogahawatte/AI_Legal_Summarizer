"""
Build combined_legal_cases.json from raw_documents (NLR/SLR PDFs).

Easiest & fastest with 12k+ PDFs: use a subset + parallel workers.

  python backend/scripts/build_combined_corpus_from_raw.py
  python backend/scripts/build_combined_corpus_from_raw.py --max-files 800 --workers 6

Options:
  --raw-dir     Path to raw_documents
  --out         Output JSON path
  --max-files   Max PDFs to include (default 5000). You do NOT need your full corpus: use e.g. 500–2000 for dev or smaller hosts.
  --max-chars   Chars per case (default 8000; enough for relevance)
  --workers     Parallel workers (default 6; set to CPU count - 1 for max speed)
"""

import argparse
import json
import re
import sys
import time
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import List, Optional, Tuple

# Resolve paths: script lives in backend/scripts/
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

# Prefer data/raw_documents (same as app.config RAW_DIR / bulk_ingest_corpus); fall back to repo-root raw_documents.
_data_raw = PROJECT_ROOT / "data" / "raw_documents"
_root_raw = PROJECT_ROOT / "raw_documents"
DEFAULT_RAW = _data_raw if _data_raw.is_dir() else _root_raw
DEFAULT_OUT = PROJECT_ROOT / "data" / "processed" / "combined_legal_cases.json"

# Min text length to keep a case
MIN_TEXT_LEN = 100


def _extract_one(args: Tuple[str, int]) -> Optional[Tuple[str, str, str]]:
    """Worker: (pdf_path_str, max_chars) -> (file_name, raw_text, cleaned_text) or None."""
    pdf_path_str, max_chars = args
    try:
        import pdfplumber
    except ImportError:
        return None
    text_parts = []
    total = 0
    max_pages = 30
    try:
        with pdfplumber.open(pdf_path_str) as pdf:
            for page in pdf.pages[:max_pages]:
                if total >= max_chars:
                    break
                t = page.extract_text()
                if t:
                    text_parts.append(t)
                    total += len(t)
    except Exception:
        return None
    raw = "\n".join(text_parts)
    if len(raw.strip()) < MIN_TEXT_LEN:
        return None
    if len(raw) > max_chars:
        raw = raw[:max_chars]
    cleaned = re.sub(r"\s+", " ", raw).strip()
    file_name = Path(pdf_path_str).name
    return (file_name, raw, cleaned)


def extract_text(pdf_path: Path, max_chars: int = 8000, max_pages: int = 30) -> str:
    """Extract text from PDF (used when not parallel)."""
    out = _extract_one((str(pdf_path), max_chars))
    return out[1] if out else ""


def clean_text(text: str) -> str:
    """Normalize whitespace for storage."""
    return re.sub(r"\s+", " ", text).strip()


def collect_pdf_paths(raw_dir: Path, max_files: int) -> List[Path]:
    """Collect PDF paths from raw_documents subfolders (NLR_All_Volumes all, SLR_Downloads)."""
    out = []
    if not raw_dir.exists():
        print(f"Raw documents dir not found: {raw_dir}", file=sys.stderr)
        return out
    for sub in sorted(raw_dir.iterdir()):
        if not sub.is_dir():
            continue
        for path in sub.rglob("*.pdf"):
            out.append(path)
            if len(out) >= max_files:
                return out
    return out


def main():
    ap = argparse.ArgumentParser(description="Build combined_legal_cases.json from raw_documents")
    ap.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW, help="Path to raw_documents")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSON path")
    ap.add_argument(
        "--max-files",
        type=int,
        default=5000,
        help="Max PDFs to index (subset is fine; lower = faster build and smaller JSON)",
    )
    ap.add_argument("--max-chars", type=int, default=8000, help="Max chars per case (default 8000)")
    ap.add_argument("--workers", type=int, default=min(6, max(1, cpu_count() - 1)), help="Parallel workers")
    args = ap.parse_args()

    raw_dir = args.raw_dir.resolve()
    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Scanning PDFs under: {raw_dir}")
    paths = collect_pdf_paths(raw_dir, args.max_files)
    print(f"Found {len(paths)} PDFs (max-files={args.max_files})")
    print(f"Using {args.workers} workers, {args.max_chars} chars/case")

    t0 = time.perf_counter()
    if args.workers <= 1:
        cases = []
        for i, pdf_path in enumerate(paths):
            if (i + 1) % 300 == 0 or i == 0:
                print(f"  {i + 1}/{len(paths)}: {pdf_path.name}")
            raw_text = extract_text(pdf_path, max_chars=args.max_chars)
            if len(raw_text.strip()) < MIN_TEXT_LEN:
                continue
            cases.append({
                "file_name": pdf_path.name,
                "raw_text": raw_text,
                "cleaned_text": clean_text(raw_text),
            })
    else:
        job_args = [(str(p), args.max_chars) for p in paths]
        with Pool(processes=args.workers) as pool:
            results = pool.map(_extract_one, job_args, chunksize=50)
        cases = [
            {"file_name": r[0], "raw_text": r[1], "cleaned_text": r[2]}
            for r in results if r
        ]

    elapsed = time.perf_counter() - t0
    print(f"Extracted {len(cases)} cases in {elapsed:.1f}s ({len(paths) / elapsed:.0f} PDFs/s)")

    print(f"Writing {len(cases)} cases to {out_path}")
    payload = {"cases": cases, "source": str(raw_dir), "built_from_raw_documents": True}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=0)

    # Manifest for PDF serving: file_name -> relative path from raw_dir (for /corpus-pdf endpoint)
    pdf_manifest = {}
    for p in paths:
        try:
            rel = p.relative_to(raw_dir)
            pdf_manifest[p.name] = str(rel).replace("\\", "/")
        except ValueError:
            pdf_manifest[p.name] = p.name
    manifest_path = out_path.parent / "corpus_pdf_paths.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"base_dir": str(raw_dir), "paths": pdf_manifest}, f, ensure_ascii=False)
    print(f"Wrote PDF manifest: {manifest_path} ({len(pdf_manifest)} entries)")

    print("Done. To use the new corpus: restart the backend (e.g. stop and run uvicorn again).")


if __name__ == "__main__":
    main()
