import requests
import os

# Find a PDF file to test
pdf_dir = r"E:\ai-legal-summarizer\backend\data\raw_documents\Constitution"
pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]

if pdf_files:
    test_file = os.path.join(pdf_dir, pdf_files[0])
    print(f"Testing with file: {test_file}")
    
    with open(test_file, 'rb') as f:
        files = {'file': (pdf_files[0], f, 'application/pdf')}
        
        try:
            response = requests.post(
                'http://127.0.0.1:8000/api/documents/upload-sri-lanka',
                files=files
            )
            
            print(f"\nStatus Code: {response.status_code}")
            print(f"Response: {response.text}")
            
        except Exception as e:
            print(f"Error: {e}")
else:
    print("No PDF files found")
