"""
Recursively list all PDFs in a Google Drive folder (including subfolders), capture file IDs,
and write artifacts for the hosted backend:

  data/corpus_google_drive_map.json   (preferred: basename + relative path → id / view URL)
  data/gdrive_pdf_urls_recursive.json (legacy: relative path → download URL only)

The API matches corpus rows by PDF *basename* (e.g. Case-Name.pdf). The map must include
`by_file_name` so /documents/past-case-pdf and Related Cases "Open PDF" work on a server
with no local raw_documents folder.

Setup:
  1. In Google Cloud Console, create OAuth credentials (Desktop app) and save as
     backend/scripts/credentials.json
  2. pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
  3. Set DRIVE_FOLDER_ID below (folder id from the Drive URL).
  4. From repo root:  python backend/scripts/list_gdrive_pdfs_recursive.py

For CI / headless servers, use a service account with Drive API and a separate script
(OAuth run_local_server cannot run on a droplet).
"""

from __future__ import annotations

import json
import os
import pickle
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Folder id from: https://drive.google.com/drive/folders/THIS_PART?...
DRIVE_FOLDER_ID = "17rxYz3UwcK3ecNb_BKSE4qAKo7a0tRR4"

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
CREDENTIALS = SCRIPT_DIR / "credentials.json"
TOKEN = SCRIPT_DIR / "token.pickle"


def drive_view_url(file_id: str) -> str:
    return f"https://drive.google.com/file/d/{file_id}/view"


def drive_download_url(file_id: str) -> str:
    return f"https://drive.google.com/uc?export=download&id={file_id}"


def list_folder_recursive(service, folder_id: str, parent_path: str = "") -> dict:
    """Returns rel_path_posix -> { file_id, view_url, download_url }."""
    out = {}
    query = f"'{folder_id}' in parents and trashed=false"
    page_token = None
    prefix = parent_path.replace("\\", "/").strip("/")
    while True:
        response = (
            service.files()
            .list(
                q=query,
                spaces="drive",
                fields="nextPageToken, files(id, name, mimeType)",
                pageToken=page_token,
                pageSize=1000,
            )
            .execute()
        )
        for f in response.get("files", []):
            name = f["name"]
            rel = f"{prefix}/{name}" if prefix else name
            rel = rel.replace("\\", "/")
            mid = f.get("mimeType") or ""
            if mid == "application/pdf":
                fid = f["id"]
                out[rel] = {
                    "file_id": fid,
                    "view_url": drive_view_url(fid),
                    "download_url": drive_download_url(fid),
                }
                print(f"  PDF: {rel}  id={fid}")
            elif mid == "application/vnd.google-apps.folder":
                print(f"  Subfolder: {rel}")
                sub = list_folder_recursive(service, f["id"], rel)
                out.update(sub)
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return out


def build_by_file_name(by_rel_path: dict):
    """Basename (lowercase) -> meta. Warns on ambiguous duplicate basenames."""
    by_name: dict = {}
    collisions: list = []
    for rel, meta in by_rel_path.items():
        base = rel.split("/")[-1].strip().lower()
        if not base:
            continue
        if base in by_name and by_name[base].get("file_id") != meta.get("file_id"):
            collisions.append(base)
        by_name[base] = meta
    return by_name, collisions


def main() -> None:
    if not CREDENTIALS.is_file():
        print(f"Missing {CREDENTIALS}", file=sys.stderr)
        sys.exit(1)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    creds = None
    if TOKEN.is_file():
        with open(TOKEN, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN, "wb") as token:
            pickle.dump(creds, token)

    service = build("drive", "v3", credentials=creds)
    print(f"Listing PDFs under folder {DRIVE_FOLDER_ID} …\n")
    by_rel_path = list_folder_recursive(service, DRIVE_FOLDER_ID)
    by_file_name, collisions = build_by_file_name(by_rel_path)

    if collisions:
        print(
            f"\nWarning: {len(set(collisions))} duplicate basename(s) in different folders; "
            "last path wins in by_file_name. Use unique PDF names or extend the API to use full rel paths.\n"
        )

    preferred = {
        "version": 1,
        "folder_id": DRIVE_FOLDER_ID,
        "by_rel_path": by_rel_path,
        "by_file_name": by_file_name,
    }
    out_preferred = DATA_DIR / "corpus_google_drive_map.json"
    with open(out_preferred, "w", encoding="utf-8") as f:
        json.dump(preferred, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_preferred} ({len(by_rel_path)} PDFs, {len(by_file_name)} unique basenames)")

    legacy_flat = {rel: meta["download_url"] for rel, meta in by_rel_path.items()}
    out_legacy = DATA_DIR / "gdrive_pdf_urls_recursive.json"
    with open(out_legacy, "w", encoding="utf-8") as f:
        json.dump(legacy_flat, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_legacy} (legacy path → download URL)")


if __name__ == "__main__":
    main()
