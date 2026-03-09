import sys, json
sys.path.insert(0, '.')
from app.services.document_processor import DocumentProcessor
from app.services.case_brief_generator import CaseBriefGenerator

pdf_path = r'uploaded_docs/025-SLLR-SLLR-2008-V-1-EDMAN-ABEYWICKREMA-v.-DR.-UPALI-ATHAUDA-AND-ANOTHER.pdf'
with open(pdf_path, 'rb') as f:
    file_bytes = f.read()

raw = DocumentProcessor.extract_text_from_pdf(file_bytes)
cleaned = DocumentProcessor.clean_text(raw, filename='025-SLLR-SLLR-2008-V-1-EDMAN-ABEYWICKREMA-v.-DR.-UPALI-ATHAUDA-AND-ANOTHER.pdf')
metadata = {
    'file_name': '025-SLLR-SLLR-2008-V-1-EDMAN-ABEYWICKREMA-v.-DR.-UPALI-ATHAUDA-AND-ANOTHER.pdf',
    'court': 'Supreme Court',
    'year': 2005,
    'citation': None
}
brief = CaseBriefGenerator.generate_case_brief(cleaned, metadata)
ci = brief['case_identification']

output = []
output.append("YEAR: " + str(ci['year']) + " (should be 2008)")
output.append("ISSUES COUNT: " + str(len(brief['issues'])))
for i, iss in enumerate(brief['issues']):
    output.append("  " + str(i+1) + ". " + iss[:100])
output.append("HOLDING: " + brief['holding'][:300])
output.append("RATIO COUNT: " + str(len(brief['ratio_decidendi'])))

result = '\n'.join(output)
with open('final_check.txt', 'w', encoding='utf-8') as f:
    f.write(result)
print("DONE")
