"""
Show the raw text of specific pages, to see the EXACT heading wording
near where the target table should start (per the PDF's table of contents).
"""
import sys
import pdfplumber

pdf_path = sys.argv[1]
start_page = int(sys.argv[2])
end_page = int(sys.argv[3])

with pdfplumber.open(pdf_path) as pdf:
    for i in range(start_page - 1, min(end_page, len(pdf.pages))):
        page = pdf.pages[i]
        text = page.extract_text() or ""
        print(f"\n========== PAGE {i+1} ==========")
        print(text[:400])