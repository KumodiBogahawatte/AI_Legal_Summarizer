import sys
sys.path.insert(0, 'backend')
import pdfplumber
import re

pdf = pdfplumber.open('e:/ai-legal-summarizer/2020_1_SLR_123.pdf')
text = ''.join([page.extract_text() or '' for page in pdf.pages])
text_upper = text.upper()

print('=== VALIDATION SCORING ===\n')

patterns = [
    ('ACCUSED', r'\bACCUSED\b', 10),
    ('JUDGMENT', r'\bJUDGMENT\b', 5),
    ('APPEAL', r'\bAPPEAL\b', 5),
    ('CONVICTION', r'\bCONVICTION\b', 5),
    ('ORDINANCE NO.', r'\bORDINANCE\s+NO\.\s+\d+', 10),
    ('SECTION', r'\bSECTION\s+\d+', 5),
    ('CHAPTER', r'\bCHAPTER\s+\w+', 5),
    ('P.C.', r'\bP\.\s*C[,\.]', 10),
    ('CRIMINAL PROCEDURE CODE', r'\bCRIMINAL\s+PROCEDURE\s+CODE', 10),
]

total = 0
for name, pattern, points in patterns:
    if re.search(pattern, text_upper):
        print(f'{name}: YES (+{points})')
        total += points
    else:
        print(f'{name}: NO')

print(f'\n=== TOTAL SCORE: {total} (need 30+) ===')
print(f'Validation: {"PASS ✓" if total >= 30 else "FAIL ✗"}')
