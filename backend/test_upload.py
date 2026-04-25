import os
import sys
from pathlib import Path

import requests

# Same dev port as uvicorn/docker-compose for this project
API_BASE = os.environ.get("LEGAL_SUMMARIZER_API", "http://127.0.0.1:8011").rstrip("/")
UPLOAD_URL = f"{API_BASE}/api/documents/upload-sri-lanka"

_backend_root = Path(__file__).resolve().parent
_default_pdf_dir = _backend_root / "data" / "raw_documents" / "Constitution"
pdf_dir = Path(os.environ.get("TEST_UPLOAD_PDF_DIR", _default_pdf_dir))

if not pdf_dir.is_dir():
    print(f"No PDF directory at {pdf_dir}. Set TEST_UPLOAD_PDF_DIR or create the folder.")
    sys.exit(1)

pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith(".pdf")]
if not pdf_files:
    print(f"No PDF files found in {pdf_dir}")
    sys.exit(1)

test_file = pdf_dir / pdf_files[0]
print(f"Testing with file: {test_file}")
print(f"POST {UPLOAD_URL}")

with open(test_file, "rb") as f:
    files = {"file": (pdf_files[0], f, "application/pdf")}
    try:
        response = requests.post(UPLOAD_URL, files=files)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
