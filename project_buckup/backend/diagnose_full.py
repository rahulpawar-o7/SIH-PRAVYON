"""
Diagnostic: for the FULL document, check every matching page and report
whether a table was actually detected there, and whether the header row
was successfully mapped (this catches cases where the header text is
visible but pdfplumber's table-grid detection fails or misses columns).
"""
import sys
import pdfplumber
from extract_table6 import find_table_identifier, map_columns

pdf_path = sys.argv[1]

matched_pages = 0
pages_with_tables = 0
pages_with_mapped_header = 0
total_data_rows_seen = 0

with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if not find_table_identifier(text):
            continue
        matched_pages += 1

        tables = page.extract_tables()
        if not tables:
            print(f"Page {i+1}: text matched but NO table detected by pdfplumber")
            continue
        pages_with_tables += 1

        table = tables[0]
        col = map_columns(table[0])
        if "project_name" not in col:
            print(f"Page {i+1}: table detected ({len(table)} rows) but header NOT mapped correctly. table[0] = {table[0]}")
            continue
        pages_with_mapped_header += 1
        total_data_rows_seen += len(table) - 1

print(f"\n--- Summary ---")
print(f"Pages matching text identifier: {matched_pages}")
print(f"...of which had a detected table: {pages_with_tables}")
print(f"...of which had a correctly mapped header: {pages_with_mapped_header}")
print(f"Total raw data rows seen (before code-validity filtering): {total_data_rows_seen}")