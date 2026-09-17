"""
Diagnostic: find out WHY a specific PDF is returning 0 extracted rows.
Usage: python diagnose_pdf.py FRApril2025.pdf
"""
import sys
import pdfplumber

pdf_path = sys.argv[1]

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}\n")
    match_count = 0
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        has_ongoing = "Ongoing Projects" in text
        has_slno = "Sl.No" in text
        has_projname = "Project Name" in text
        if has_ongoing or (has_slno or has_projname):
            match_count += 1
            print(f"--- Page {i+1} ---")
            print(f"  'Ongoing Projects' found: {has_ongoing}")
            print(f"  'Sl.No' found: {has_slno}")
            print(f"  'Project Name' found: {has_projname}")
            print(f"  First 200 chars: {text[:200]!r}")
            tables = page.extract_tables()
            print(f"  Tables detected: {len(tables)}")
            if tables:
                print(f"  First table row count: {len(tables[0])}, first row: {tables[0][0]}")
            print()
            if match_count >= 3:
                break
    if match_count == 0:
        print("NO pages matched any of the search phrases at all.")