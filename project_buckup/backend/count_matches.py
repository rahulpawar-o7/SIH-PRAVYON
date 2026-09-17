import pdfplumber
from extract_table6_v3 import find_table_identifier

with pdfplumber.open("FlashReport_October_2025.pdf") as pdf:
    matched = 0
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if find_table_identifier(text):
            matched += 1
    print(f"Total pages: {len(pdf.pages)}")
    print(f"Pages matching identifier: {matched}")
    