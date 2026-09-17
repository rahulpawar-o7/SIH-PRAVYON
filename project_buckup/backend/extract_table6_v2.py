import re
import argparse
import pdfplumber
import pandas as pd

TABLE_SETTINGS = {"vertical_strategy": "text", "horizontal_strategy": "lines"}


def find_table_identifier(text: str) -> bool:
    if "North-East Region" in text:
        return False
    has_target_table = "Ongoing Projects as of" in text or "All Ongoing Projects" in text
    has_columns = ("Sl No" in text) or ("Sl. No" in text) or ("Sl.No" in text) or ("Project Name" in text)
    return has_target_table and has_columns


def split_project_name_cell(cell: str):
    if not cell:
        return None, None, None, None, None
    lines = [l.strip() for l in cell.split("\n") if l.strip()]
    name_lines, paren_lines = [], []
    for line in lines:
        (paren_lines if line.startswith("(") else name_lines).append(line)
    project_name = " ".join(name_lines) if name_lines else None
    agency = paren_lines[0].strip("()") if len(paren_lines) > 0 else None
    project_code = paren_lines[1].strip("()") if len(paren_lines) > 1 else None
    legacy_code, pmgid = None, None
    if len(paren_lines) > 2:
        groups = re.findall(r"\(([^)]*)\)", paren_lines[2])
        if len(groups) >= 1 and groups[0] != "-":
            legacy_code = groups[0]
        if len(groups) >= 2 and groups[1] != "-":
            pmgid = groups[1]
    # Fallback: some layouts put agency/code differently; try to salvage a
    # project_code from ANY parenthesised group that looks like a numeric ID.
    if not project_code:
        all_groups = re.findall(r"\(([^)]*)\)", cell)
        for g in all_groups:
            if re.fullmatch(r"[A-Za-z0-9\-]{3,}", g) and g != "-":
                project_code = g
                break
    return project_name, agency, project_code, legacy_code, pmgid


def split_original_revised(cell: str):
    if not cell:
        return None, None
    parts = [part.strip() for part in cell.split("\n") if part.strip()]
    original = parts[0] if parts else None
    revised = parts[1].strip("()") if len(parts) > 1 else None
    return original, None if revised == "-" else revised


def is_ministry_sector_header(name_cell: str, row: list) -> bool:
    """A ministry/sector header line: only the name cell has plain text
    (no parentheses, single line), every other cell in the row is empty."""
    if not name_cell or "(" in name_cell:
        return False
    if "\n" in name_cell.strip():
        return False
    return all((c is None or str(c).strip() == "") for c in row[1:])


def extract_table6(pdf_path: str, reporting_month: str) -> pd.DataFrame:
    records = []
    pending_headers = []
    current_ministry = None
    current_sector = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if not find_table_identifier(text):
                continue

            tables = page.extract_tables(table_settings=TABLE_SETTINGS)
            if not tables:
                tables = page.extract_tables()  # fallback to default line-based detection
            if not tables:
                continue

            for table in tables:
                for row in table:
                    if not row or len(row) < 6:
                        continue
                    name_cell = (row[0] or "").strip()
                    if not name_cell:
                        continue

                    if is_ministry_sector_header(name_cell, row):
                        pending_headers.append(name_cell)
                        continue

                    project_name, agency, project_code, legacy_code, pmgid = split_project_name_cell(row[0])
                    if not project_code:
                        continue  # not a valid, parseable project row

                    if pending_headers:
                        if len(pending_headers) >= 2:
                            current_ministry, current_sector = pending_headers[-2], pending_headers[-1]
                        else:
                            current_sector = pending_headers[-1]
                        pending_headers = []

                    ncols = len(row)
                    state = (row[2] or "").replace("\n", " ").strip() if ncols > 2 else None
                    start_date, revised_start_date = split_original_revised(row[3]) if ncols > 3 else (None, None)
                    target_doc, revised_doc = split_original_revised(row[4]) if ncols > 4 else (None, None)
                    original_cost, revised_cost = split_original_revised(row[5]) if ncols > 5 else (None, None)
                    cum_exp = (row[6] or "").strip() if ncols > 6 else None
                    phys_prog = (row[7] or "").strip() if ncols > 7 else None

                    records.append({
                        "reporting_month": reporting_month,
                        "ministry": current_ministry,
                        "sector": current_sector,
                        "project_name": project_name,
                        "agency": agency,
                        "project_code": project_code,
                        "legacy_ocms_code": legacy_code,
                        "pmgid": pmgid,
                        "state": state,
                        "approval_start_date": start_date,
                        "revised_start_date": revised_start_date,
                        "target_doc": target_doc,
                        "revised_doc": revised_doc,
                        "original_cost_cr": original_cost,
                        "revised_cost_cr": revised_cost,
                        "cumulative_expenditure_cr": cum_exp,
                        "physical_progress_pct": phys_prog,
                    })

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.drop_duplicates(subset=["project_code"], keep="first")
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf_path")
    ap.add_argument("--month", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    extracted = extract_table6(args.pdf_path, args.month)
    extracted.to_csv(args.out, index=False)
    print(f"Successfully extracted {len(extracted)} project rows -> {args.out}")