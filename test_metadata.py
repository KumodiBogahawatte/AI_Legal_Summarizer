import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
import pdfplumber
from app.utils.sri_lanka_legal_utils import extract_case_year, extract_case_number, extract_court

pdf = pdfplumber.open('e:/ai-legal-summarizer/2020_1_SLR_123.pdf')
text = ''.join([page.extract_text() or '' for page in pdf.pages])

print('=== METADATA EXTRACTION TEST ===\n')
print(f'Text length: {len(text)} chars')
print(f'\nFirst 500 chars:\n{text[:500]}\n')

year = extract_case_year(text)
case_no = extract_case_number(text)
court = extract_court(text)

print(f'Year: {year}')
print(f'Case Number: {case_no}')
print(f'Court: {court}')
