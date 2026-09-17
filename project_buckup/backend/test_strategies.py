"""
Try different pdfplumber table-detection strategies on a page known 
to contain real project data, to find which strategy actually works
for this PDF's formatting.
"""
import pdfplumber

pdf_path = "FlashReport_October_2025.pdf"
page_num = 44  # 1-indexed page known to have real data

strategies = [
    ("default (lines)", {}),
    ("text-based", {"vertical_strategy": "text", "horizontal_strategy": "text"}),
    ("lines_strict + text", {"vertical_strategy": "lines_strict", "horizontal_strategy": "text"}),
    ("text + lines", {"vertical_strategy": "text", "horizontal_strategy": "lines"}),
]

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[page_num - 1]
    for name, settings in strategies:
        tables = page.extract_tables(table_settings=settings) if settings else page.extract_tables()
        print(f"\n--- Strategy: {name} ---")
        print(f"Tables found: {len(tables)}")
        if tables:
            t = tables[0]
            print(f"Rows: {len(t)}, columns in row0: {len(t[0]) if t else 0}")
            print(f"Row 0: {t[0]}")
            if len(t) > 1:
                print(f"Row 1: {t[1]}")