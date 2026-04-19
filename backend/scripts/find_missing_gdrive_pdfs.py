"""
Combined script to:
1. List all PDFs in your Google Drive (flat, all folders)
2. Load your recursive mapping (gdrive_pdf_urls_recursive.json)
3. Print all PDFs missing from your mapping

Instructions:
- Place this script in the same folder as your credentials.json and token.pickle
- Make sure gdrive_pdf_urls_recursive.json is present
- pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
- Run: python find_missing_gdrive_pdfs.py
"""
import os
import json
import pickle
import re
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Load credentials
creds = None
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)
service = build('drive', 'v3', credentials=creds)

def list_all_pdfs(service):
    pdfs = {}
    page_token = None
    while True:
        response = service.files().list(
            q="mimeType='application/pdf' and trashed=false",
            spaces='drive',
            fields='nextPageToken, files(id, name, parents)',
            pageToken=page_token,
            pageSize=1000
        ).execute()
        for file in response.get('files', []):
            pdfs[file['id']] = {
                'name': file['name'],
                'parents': file.get('parents', [])
            }
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break
    return pdfs

def main():
    print("Listing all PDFs in Google Drive (flat, all folders)...")
    all_pdfs = list_all_pdfs(service)
    print(f"Found {len(all_pdfs)} PDFs in Drive.")

    # Load mapped PDFs
    with open('gdrive_pdf_urls_recursive.json', 'r', encoding='utf-8') as f:
        mapped = json.load(f)
    print(f"Loaded {len(mapped)} mapped PDFs from gdrive_pdf_urls_recursive.json.")

    # Extract IDs from mapping
    mapped_ids = set()
    for url in mapped.values():
        m = re.search(r'id=([a-zA-Z0-9_-]+)', url)
        if m:
            mapped_ids.add(m.group(1))

    # Find missing
    missing = {fid: meta for fid, meta in all_pdfs.items() if fid not in mapped_ids}

    print(f"\nMissing {len(missing)} PDFs (in Drive but not in mapping):")
    for fid, meta in missing.items():
        print(f"{meta['name']} (ID: {fid})")

    # Optionally, save missing list
    with open('missing_gdrive_pdfs.json', 'w', encoding='utf-8') as f:
        json.dump(missing, f, indent=2)
    print("\nSaved missing PDFs to missing_gdrive_pdfs.json")

if __name__ == '__main__':
    main()
