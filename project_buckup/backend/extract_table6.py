import argparse
import math
import re

import pandas as pd
import pdfplumber


TEXT_LINES_SETTINGS = {
    "vertical_strategy": "text",
    "horizontal_strategy": "lines",
}


# ---------------------------------------------------------
# BASIC CLEANING
# ---------------------------------------------------------

def clean_text(value):
    """
    Convert PDF/Pandas junk values into proper None.
    """
    if value is None:
        return None

    try:
        if isinstance(value, float) and math.isnan(value):
            return None
    except Exception:
        pass

    text = str(value).replace("\xa0", " ").strip()

    if not text:
        return None

    if text.lower() in {
        "nan",
        "none",
        "null",
        "n.a.",
        "n.a",
        "na",
        "-",
    }:
        return None

    return re.sub(r"\s+", " ", text)


def is_empty(value):
    return clean_text(value) is None


# ---------------------------------------------------------
# PAGE / TABLE DETECTION
# ---------------------------------------------------------

def find_table_identifier(text: str) -> bool:
    if not text:
        return False

    if "North-East Region" in text:
        return False

    has_target_table = (
        "All Ongoing Projects" in text
        or "Ongoing Projects as of" in text
        or "Project List: Ongoing Projects" in text
    )

    has_columns = (
        "Project Name" in text
        and (
            "Physical Progress" in text
            or "Cumulative Expenditure" in text
        )
    )

    return has_target_table and has_columns


# ---------------------------------------------------------
# COLUMN MAPPING
# Supports both:
#
# 2026 format:
# Sl.No | Project Name | State | Date...
#
# Older format:
# State | Sector | Sl No | Project Name | Date...
# ---------------------------------------------------------

def map_columns(header_row):
    joined = [
        str(c or "").replace("\n", " ").strip().lower()
        for c in header_row
    ]

    idx = {}

    for i, cell in enumerate(joined):

        if not cell:
            continue

        if "sl" in cell and "no" in cell:
            idx.setdefault("sl_no", i)

        elif "project" in cell and "name" in cell:
            idx.setdefault("project_name", i)

        elif "ministry" in cell or "allocated to" in cell:
            idx.setdefault("ministry", i)

        elif "sector" in cell:
            idx.setdefault("sector", i)

        elif "state" in cell:
            idx.setdefault("state", i)

        elif "approval" in cell and "date" in cell:
            idx.setdefault("approval_date", i)

        elif "commission" in cell or "target" in cell:
            idx.setdefault("target_date", i)

        elif "cumulative" in cell or "expenditure" in cell:
            idx.setdefault("expenditure", i)

        elif "physical" in cell or "progress" in cell:
            idx.setdefault("progress", i)

        elif "cost" in cell:
            idx.setdefault("cost", i)

    return idx


# ---------------------------------------------------------
# PROJECT NAME / AGENCY / CODE
# ---------------------------------------------------------

def split_project_name_cell(cell):
    cell = clean_text(cell)

    if not cell:
        return None, None, None, None, None

    raw_lines = str(cell).split("\n")
    lines = [
        line.strip()
        for line in raw_lines
        if line.strip()
    ]

    name_lines = []
    paren_lines = []

    for line in lines:
        if line.startswith("("):
            paren_lines.append(line)
        else:
            name_lines.append(line)

    project_name = (
        " ".join(name_lines).strip()
        if name_lines
        else None
    )

    agency = None
    project_code = None
    legacy_code = None
    pmgid = None

    # -----------------------------------------------------
    # 2026 FORMAT
    #
    # (Agency)
    # (Project Code)
    # (Legacy OCMS Code) (PMGID)
    # -----------------------------------------------------

    if len(paren_lines) >= 1:
        agency = paren_lines[0].strip()

        agency = agency.strip("()").strip()

    if len(paren_lines) >= 2:
        groups = re.findall(
            r"\(([^()]*)\)",
            paren_lines[1]
        )

        if groups:
            project_code = clean_text(groups[0])

    if len(paren_lines) >= 3:
        groups = re.findall(
            r"\(([^()]*)\)",
            paren_lines[2]
        )

        if len(groups) >= 1:
            legacy_code = clean_text(groups[0])

        if len(groups) >= 2:
            pmgid = clean_text(groups[1])

    # -----------------------------------------------------
    # FALLBACK:
    # Search all parenthesized groups
    # -----------------------------------------------------

    all_groups = re.findall(
        r"\(([^()]*)\)",
        str(cell)
    )

    if not project_code:

        for group in all_groups:

            group = clean_text(group)

            if not group:
                continue

            # PAIMANA project code examples:
            # 612786
            # 701107
            # N04000106
            # N22000584
            if re.fullmatch(r"\d{4,8}", group):
                project_code = group
                break

            if re.fullmatch(
                r"[A-Za-z]\d{5,}",
                group
            ):
                project_code = group
                break

    return (
        project_name,
        agency,
        project_code,
        legacy_code,
        pmgid,
    )


# ---------------------------------------------------------
# ORIGINAL / REVISED VALUES
# ---------------------------------------------------------

def split_original_revised(cell):
    if not cell:
        return None, None

    parts = [
        clean_text(part)
        for part in str(cell).split("\n")
    ]

    parts = [
        p for p in parts
        if p is not None
    ]

    original = parts[0] if parts else None

    revised = (
        parts[1]
        if len(parts) > 1
        else None
    )

    return original, revised


# ---------------------------------------------------------
# HEADER ROW DETECTION
# ---------------------------------------------------------

def is_section_header_row(row, name_col):
    """
    2026 PDFs contain rows such as:

    Ministry of Coal
    Coal

    These rows have text only in the Project Name column.
    """

    if name_col is None:
        return False

    if name_col >= len(row):
        return False

    name = clean_text(row[name_col])

    if not name:
        return False

    # Total rows are not section headers
    if name.lower().startswith("total"):
        return False

    for i, value in enumerate(row):

        if i == name_col:
            continue

        if not is_empty(value):
            return False

    return True


def looks_like_ministry(text):
    text = clean_text(text)

    if not text:
        return False

    lower = text.lower()

    return (
        lower.startswith("ministry ")
        or lower.startswith("department ")
        or "department of " in lower
    )


# ---------------------------------------------------------
# MAIN HEADER-BASED PARSER
# ---------------------------------------------------------

def parse_via_header_map(
    table,
    current_ministry=None,
    current_sector=None,
):

    if not table or len(table) < 2:
        return None, current_ministry, current_sector

    col = map_columns(table[0])

    if "project_name" not in col:
        return None, current_ministry, current_sector

    rows_out = []

    name_col = col.get("project_name")
    sl_col = col.get("sl_no")

    ministry_col = col.get("ministry")
    sector_col = col.get("sector")

    for row in table[1:]:

        if row is None:
            continue

        # -------------------------------------------------
        # DIRECT MINISTRY COLUMN
        # -------------------------------------------------

        if ministry_col is not None and ministry_col < len(row):

            ministry_value = clean_text(
                row[ministry_col]
            )

            if ministry_value:
                current_ministry = ministry_value

        # -------------------------------------------------
        # DIRECT SECTOR COLUMN
        # Older PDFs have this.
        # -------------------------------------------------

        if sector_col is not None and sector_col < len(row):

            sector_value = clean_text(
                row[sector_col]
            )

            if sector_value:
                current_sector = sector_value

        # -------------------------------------------------
        # SECTION HEADER
        # Used heavily in 2026 format.
        # -------------------------------------------------

        if is_section_header_row(
            row,
            name_col
        ):

            header_value = clean_text(
                row[name_col]
            )

            if looks_like_ministry(header_value):

                current_ministry = header_value

            else:

                current_sector = header_value

            continue

        # -------------------------------------------------
        # SL NO
        # -------------------------------------------------

        sl_no = ""

        if sl_col is not None and sl_col < len(row):
            sl_no = clean_text(row[sl_col]) or ""

        # Ignore totals
        if (
            name_col is not None
            and name_col < len(row)
        ):

            possible_name = clean_text(
                row[name_col]
            )

            if possible_name and possible_name.lower().startswith("total"):
                continue

        # If no serial number column exists,
        # don't force it.
        if sl_col is not None:

            if not sl_no:
                continue

            if not sl_no.isdigit():
                continue

        # -------------------------------------------------
        # CELL HELPER
        # -------------------------------------------------

        def cell(key):

            index = col.get(key)

            if (
                index is None
                or index >= len(row)
            ):
                return None

            return row[index]

        # -------------------------------------------------
        # PROJECT
        # -------------------------------------------------

        (
            project_name,
            agency,
            project_code,
            legacy_code,
            pmgid,
        ) = split_project_name_cell(
            cell("project_name")
        )

        if not project_code:
            continue

        # -------------------------------------------------
        # STATE
        # -------------------------------------------------

        state = clean_text(
            cell("state")
        )

        # -------------------------------------------------
        # DATES
        # -------------------------------------------------

        start_date, _ = split_original_revised(
            cell("approval_date")
        )

        target_doc, revised_doc = split_original_revised(
            cell("target_date")
        )

        # -------------------------------------------------
        # COST
        # -------------------------------------------------

        original_cost, revised_cost = split_original_revised(
            cell("cost")
        )

        # -------------------------------------------------
        # EXPENDITURE / PROGRESS
        # -------------------------------------------------

        cumulative_expenditure = clean_text(
            cell("expenditure")
        )

        physical_progress = clean_text(
            cell("progress")
        )

        rows_out.append({

            "ministry": current_ministry,

            "sector": current_sector,

            "project_name": project_name,

            "agency": agency,

            "project_code": project_code,

            "legacy_ocms_code": legacy_code,

            "pmgid": pmgid,

            "state": state,

            "approval_start_date": start_date,

            "target_doc": target_doc,

            "revised_doc": revised_doc,

            "original_cost_cr": original_cost,

            "revised_cost_cr": revised_cost,

            "cumulative_expenditure_cr":
                cumulative_expenditure,

            "physical_progress_pct":
                physical_progress,
        })

    return (
        rows_out,
        current_ministry,
        current_sector,
    )


# ---------------------------------------------------------
# POSITIONAL FALLBACK
# ---------------------------------------------------------

def parse_via_positional(
    table,
    current_ministry=None,
    current_sector=None,
):

    rows_out = []

    for row in table:

        if not row:
            continue

        cleaned = [
            clean_text(x)
            for x in row
        ]

        # We need enough columns
        if len(cleaned) < 8:
            continue

        # In some PDFs first column is serial number
        sl_no = cleaned[0]

        if not sl_no or not sl_no.isdigit():
            continue

        # Usually:
        # 0 Sl No
        # 1 Project
        # 2 State
        # 3 Approval
        # 4 Target
        # 5 Cost
        # 6 Expenditure
        # 7 Progress

        project_cell = cleaned[1]

        (
            project_name,
            agency,
            project_code,
            legacy_code,
            pmgid,
        ) = split_project_name_cell(
            project_cell
        )

        if not project_code:
            continue

        state = cleaned[2]

        start_date, _ = split_original_revised(
            cleaned[3]
        )

        target_doc, revised_doc = split_original_revised(
            cleaned[4]
        )

        original_cost, revised_cost = split_original_revised(
            cleaned[5]
        )

        cumulative_expenditure = cleaned[6]

        physical_progress = cleaned[7]

        rows_out.append({

            "ministry": current_ministry,

            "sector": current_sector,

            "project_name": project_name,

            "agency": agency,

            "project_code": project_code,

            "legacy_ocms_code": legacy_code,

            "pmgid": pmgid,

            "state": state,

            "approval_start_date": start_date,

            "target_doc": target_doc,

            "revised_doc": revised_doc,

            "original_cost_cr": original_cost,

            "revised_cost_cr": revised_cost,

            "cumulative_expenditure_cr":
                cumulative_expenditure,

            "physical_progress_pct":
                physical_progress,
        })

    return (
        rows_out,
        current_ministry,
        current_sector,
    )


# ---------------------------------------------------------
# MAIN EXTRACTOR
# ---------------------------------------------------------

def extract_table6(
    pdf_path: str,
    reporting_month: str
) -> pd.DataFrame:

    records = []

    # IMPORTANT:
    # These variables are NOT reset for every page.
    current_ministry = None
    current_sector = None

    with pdfplumber.open(pdf_path) as pdf:

        for page_number, page in enumerate(
            pdf.pages,
            start=1
        ):

            text = page.extract_text() or ""

            if not find_table_identifier(text):
                continue

            page_records = []

            # =================================================
            # APPROACH A
            # Normal PDF table extraction
            # =================================================

            default_tables = page.extract_tables()

            for table in default_tables:

                (
                    parsed,
                    current_ministry,
                    current_sector,
                ) = parse_via_header_map(
                    table,
                    current_ministry,
                    current_sector,
                )

                if parsed:
                    page_records.extend(parsed)

            # =================================================
            # APPROACH B
            # Alternative extraction for different PDF layouts
            # =================================================

            if not page_records:

                alt_tables = page.extract_tables(
                    table_settings=TEXT_LINES_SETTINGS
                )

                for table in alt_tables:

                    (
                        parsed,
                        new_ministry,
                        new_sector,
                    ) = parse_via_header_map(
                        table,
                        current_ministry,
                        current_sector,
                    )

                    if parsed:

                        page_records.extend(parsed)

                        current_ministry = new_ministry
                        current_sector = new_sector

                    else:

                        (
                            parsed,
                            current_ministry,
                            current_sector,
                        ) = parse_via_positional(
                            table,
                            current_ministry,
                            current_sector,
                        )

                        if parsed:
                            page_records.extend(parsed)

            # =================================================
            # SAVE PAGE RECORDS
            # =================================================

            for rec in page_records:

                rec["reporting_month"] = reporting_month

                if rec.get("ministry"):
                    current_ministry = rec["ministry"]

                if rec.get("sector"):
                    current_sector = rec["sector"]

                # Final normalization
                for key in [
                    "ministry",
                    "sector",
                    "project_name",
                    "agency",
                    "project_code",
                    "legacy_ocms_code",
                    "pmgid",
                    "state",
                    "approval_start_date",
                    "target_doc",
                    "revised_doc",
                    "original_cost_cr",
                    "revised_cost_cr",
                    "cumulative_expenditure_cr",
                    "physical_progress_pct",
                ]:
                    rec[key] = clean_text(rec.get(key))

                records.append(rec)

    df = pd.DataFrame(records)

    if df.empty:
        return df

    # Remove invalid project codes
    df = df[
        df["project_code"].notna()
        & (df["project_code"].astype(str).str.strip() != "")
    ]

    # IMPORTANT:
    # Same project should appear only once
    # inside one monthly PDF.
    df = df.drop_duplicates(
        subset=["project_code"],
        keep="first",
    )

    return df.reset_index(drop=True)


# ---------------------------------------------------------
# COMMAND LINE
# ---------------------------------------------------------

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "pdf_path"
    )

    parser.add_argument(
        "--month",
        required=True
    )

    parser.add_argument(
        "--out",
        required=True
    )

    args = parser.parse_args()

    extracted = extract_table6(
        args.pdf_path,
        args.month,
    )

    extracted.to_csv(
        args.out,
        index=False,
    )

    print(
        f"Successfully extracted "
        f"{len(extracted)} project rows "
        f"-> {args.out}"
    )