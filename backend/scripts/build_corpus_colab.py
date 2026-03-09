"""
Run this in Google Colab to build combined_legal_cases.json from your PDFs.

Setup options:
  A) Upload a ZIP of your NLR/SLR PDFs to Colab, then unzip into /content/pdfs
  B) Mount Google Drive and point PDF_DIR to your folder (e.g. MyDrive/raw_documents)

Output: downloads combined_legal_cases.json to your machine (or saves to Drive).
"""

# ============== 1. Install dependency ==============
# !pip install -q pdfplumber

# ============== 2. Config (edit these) ==============
import json
import re
import sys
import time
from pathlib import Path

# Where your PDFs are in Colab (after unzip or Drive mount)
PDF_DIR = Path("/content/pdfs")   # e.g. /content/pdfs or /content/drive/MyDrive/raw_documents/NLR_All_Volumes all
MAX_FILES = 2000                  # process first 2000 PDFs (fast)
MAX_CHARS = 5000                  # chars per case
OUT_FILE = Path("/content/combined_legal_cases.json")

# ============== 3. Collect PDF paths ==============
def collect_pdfs(root: Path, max_files: int):
    out = []
    if not root.exists():
        return out
    for path in root.rglob("*.pdf"):
        out.append(path)
        if len(out) >= max_files:
            return out
    return out

# ============== 4. Extract text from one PDF ==============
def extract_one(pdf_path: Path, max_chars: int = 5000):
    try:
        import pdfplumber
    except ImportError:
        return None
    text_parts = []
    total = 0
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages[:30]:
                if total >= max_chars:
                    break
                t = page.extract_text()
                if t:
                    text_parts.append(t)
                    total += len(t)
    except Exception:
        return None
    raw = "\n".join(text_parts)
    if len(raw.strip()) < 100:
        return None
    if len(raw) > max_chars:
        raw = raw[:max_chars]
    cleaned = re.sub(r"\s+", " ", raw).strip()
    return {"file_name": pdf_path.name, "raw_text": raw, "cleaned_text": cleaned}

# ============== 5. Main ==============
def main():
    print("Collecting PDF paths...")
    paths = collect_pdfs(PDF_DIR, MAX_FILES)
    print(f"Found {len(paths)} PDFs")
    if not paths:
        print("No PDFs found. Check PDF_DIR and upload/unzip or mount Drive.")
        return

    print("Extracting text (this may take a few minutes)...")
    t0 = time.perf_counter()
    cases = []
    for i, p in enumerate(paths):
        if (i + 1) % 200 == 0 or i == 0:
            print(f"  {i + 1}/{len(paths)}")
        rec = extract_one(p, MAX_CHARS)
        if rec:
            cases.append(rec)
    elapsed = time.perf_counter() - t0
    print(f"Done. {len(cases)} cases in {elapsed:.1f}s")

    payload = {"cases": cases, "built_from_raw_documents": True}
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=0)
    print(f"Saved to {OUT_FILE}")

    # Download in Colab
    try:
        from google.colab import files
        files.download(str(OUT_FILE))
        print("Download started: combined_legal_cases.json")
    except Exception:
        print("To download: use Colab's file browser or add 'from google.colab import files' and files.download(...)")

if __name__ == "__main__":
    main()
