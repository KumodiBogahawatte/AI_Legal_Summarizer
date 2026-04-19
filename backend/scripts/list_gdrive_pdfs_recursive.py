"""
Recursively list all PDFs in a Google Drive folder (including subfolders), generate direct links, and save a mapping of relative path -> direct link to a JSON file.

Instructions:
1. Place credentials.json (from Google Cloud Console) in this folder.
2. pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
3. Set DRIVE_FOLDER_ID to your Google Drive folder ID.
4. Run: python list_gdrive_pdfs_recursive.py
"""
import os
import json
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
DRIVE_FOLDER_ID = '17rxYz3UwcK3ecNb_BKSE4qAKo7a0tRR4'  # <-- Set your folder ID here

creds = None
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)
service = build('drive', 'v3', credentials=creds)

def get_direct_link(file_id):
    return f'https://drive.google.com/uc?export=download&id={file_id}'

def list_folder_recursive(service, folder_id, parent_path=""):
    pdfs = {}
    # List all files and folders in the current folder
    print(f"Entering folder: {parent_path or '[root]'} (ID: {folder_id})")
    query = f"'{folder_id}' in parents and trashed=false"
    page_token = None
    while True:
        response = service.files().list(q=query,
                                        spaces='drive',
                                        fields='nextPageToken, files(id, name, mimeType)',
                                        pageToken=page_token,
                                        pageSize=1000).execute()
        for file in response.get('files', []):
            file_path = os.path.join(parent_path, file['name'])
            pdf_path = file_path.replace('\\', '/')
            if file['mimeType'] == 'application/pdf':
                print(f"  Found PDF: {pdf_path} (ID: {file['id']})")
                pdfs[pdf_path] = get_direct_link(file['id'])
            elif file['mimeType'] == 'application/vnd.google-apps.folder':
                print(f"  Entering subfolder: {pdf_path} (ID: {file['id']})")
                pdfs.update(list_folder_recursive(service, file['id'], file_path))
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break
    return pdfs

def main():
    print(f"Listing all PDFs in Drive folder ID: {DRIVE_FOLDER_ID}\n")
    pdf_links = list_folder_recursive(service, DRIVE_FOLDER_ID)
    with open('gdrive_pdf_urls_recursive.json', 'w', encoding='utf-8') as f:
        json.dump(pdf_links, f, indent=2)
    print(f"\nSaved {len(pdf_links)} PDF links to gdrive_pdf_urls_recursive.json")

if __name__ == '__main__':
    main()
