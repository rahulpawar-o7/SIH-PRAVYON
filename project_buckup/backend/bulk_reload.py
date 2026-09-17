import os
import math
import re
from datetime import datetime, timezone

import psycopg
from dotenv import load_dotenv

from extract_table6 import extract_table6


# ---------------------------------------------------------
# PDF -> REPORTING MONTH
# ---------------------------------------------------------

PDF_MONTH_MAP = {

    "FlashReport_April2026SIH.pdf": "2026-04",

    "FlashReport_August_2025.pdf": "2025-08",

    "FlashReport_December_2025.pdf": "2025-12",

    "FlashReport_February_2026.pdf": "2026-02",

    "FlashReport_January_2026.pdf": "2026-01",

    "FlashReport_July_2025.pdf": "2025-07",

    "FlashReport_July_2026SIH.pdf": "2026-07",

    "FlashReport_June_2026(1)SIH.pdf": "2026-06",

    "FlashReport_March_2026.pdf": "2026-03",

    "FlashReport_May2026(1)SIH.pdf": "2026-05",

    "FlashReport_November_2025.pdf": "2025-11",

    "FlashReport_October_2025.pdf": "2025-10",

    "FlashReport_September_2025.pdf": "2025-09",

    "FR_JUNE_2025.pdf": "2025-06",

    "FR_JUNE_2025_Copy.pdf": "2025-06",

    "FR_May2025.pdf": "2025-05",

    "FRApril2025.pdf": "2025-04",
}


# ---------------------------------------------------------
# ENV
# ---------------------------------------------------------

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is required"
    )


# ---------------------------------------------------------
# TEXT CLEANING
# ---------------------------------------------------------

def clean_text(value):

    if value is None:
        return None

    try:
        if isinstance(value, float) and math.isnan(value):
            return None
    except Exception:
        pass

    text = str(value).strip()

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

    return text


# ---------------------------------------------------------
# NUMBER CLEANING
# ---------------------------------------------------------

def clean_number(value, default=None):

    value = clean_text(value)

    if value is None:
        return default

    # Remove commas
    text = str(value).replace(",", "")

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        text
    )

    if not match:
        return default

    try:
        return float(match.group(0))
    except ValueError:
        return default


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

def db():

    return psycopg.connect(
        DATABASE_URL,
        row_factory=psycopg.rows.dict_row,
    )


# ---------------------------------------------------------
# LOAD ONE PDF
# ---------------------------------------------------------

def load_one(
    pdf_path: str,
    reporting_month: str,
):

    print(
        f"\nExtracting {pdf_path} "
        f"({reporting_month})..."
    )

    frame = extract_table6(
        pdf_path,
        reporting_month,
    )

    print(
        f"  -> {len(frame)} rows extracted"
    )

    if frame.empty:

        print(
            "  (nothing to insert, skipping)"
        )

        return 0

    project_rows = []
    history_rows = []

    now = datetime.now(timezone.utc)

    for _, row in frame.iterrows():

        code = clean_text(
            row.get("project_code")
        )

        if not code:
            continue

        original = clean_number(
            row.get(
                "original_cost_cr"
            ),
            default=0.0,
        )

        revised = clean_number(
            row.get(
                "revised_cost_cr"
            ),
            default=original,
        )

        project_name = (
            clean_text(
                row.get("project_name")
            )
            or "Infrastructure Project"
        )

        agency = clean_text(
            row.get("agency")
        )

        ministry = clean_text(
            row.get("ministry")
        )

        sector = clean_text(
            row.get("sector")
        )

        state = clean_text(
            row.get("state")
        )

        approval_start_date = clean_text(
            row.get("approval_start_date")
        )

        target_doc = clean_text(
            row.get("target_doc")
        )

        revised_doc = clean_text(
            row.get("revised_doc")
        )

        cumulative_expenditure = clean_number(
            row.get(
                "cumulative_expenditure_cr"
            ),
            default=0.0,
        )

        physical_progress = clean_number(
            row.get(
                "physical_progress_pct"
            ),
            default=0.0,
        )

        # ---------------------------------------------
        # MASTER PROJECT TABLE
        # ---------------------------------------------

        project_rows.append(
            (
                code,
                project_name,
                agency,
                ministry,
                sector,
                state,
                approval_start_date,
                target_doc,
                original,
            )
        )

        # ---------------------------------------------
        # MONTHLY HISTORY TABLE
        # ---------------------------------------------

        history_rows.append(
            (
                code,
                reporting_month,
                revised_doc,
                revised,
                cumulative_expenditure,
                physical_progress,
                now,
            )
        )

    # -----------------------------------------------------
    # DATABASE INSERT
    # -----------------------------------------------------

    with db() as conn:

        with conn.cursor() as cur:

            # ---------------------------------------------
            # PROJECTS
            # ---------------------------------------------

            cur.executemany(
                """
                INSERT INTO projects
                (
                    project_code,
                    project_name,
                    agency,
                    ministry,
                    sector,
                    state,
                    approval_start_date,
                    original_target_doc,
                    original_cost
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,%s
                )

                ON CONFLICT(project_code)
                DO UPDATE SET

                    project_name =
                        COALESCE(
                            EXCLUDED.project_name,
                            projects.project_name
                        ),

                    agency =
                        COALESCE(
                            EXCLUDED.agency,
                            projects.agency
                        ),

                    ministry =
                        COALESCE(
                            EXCLUDED.ministry,
                            projects.ministry
                        ),

                    sector =
                        COALESCE(
                            EXCLUDED.sector,
                            projects.sector
                        ),

                    state =
                        COALESCE(
                            EXCLUDED.state,
                            projects.state
                        ),

                    approval_start_date =
                        COALESCE(
                            EXCLUDED.approval_start_date,
                            projects.approval_start_date
                        ),

                    original_target_doc =
                        COALESCE(
                            EXCLUDED.original_target_doc,
                            projects.original_target_doc
                        ),

                    original_cost =
                        COALESCE(
                            EXCLUDED.original_cost,
                            projects.original_cost
                        )
                """,
                project_rows,
            )

            # ---------------------------------------------
            # MONTHLY HISTORY
            # ---------------------------------------------

            cur.executemany(
                """
                INSERT INTO project_monthly_history
                (
                    project_code,
                    reporting_month,
                    revised_doc,
                    revised_cost,
                    cumulative_expenditure,
                    physical_progress_pct,
                    created_at
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,%s,%s
                )

                ON CONFLICT(
                    project_code,
                    reporting_month
                )
                DO UPDATE SET

                    revised_doc =
                        EXCLUDED.revised_doc,

                    revised_cost =
                        EXCLUDED.revised_cost,

                    cumulative_expenditure =
                        EXCLUDED.cumulative_expenditure,

                    physical_progress_pct =
                        EXCLUDED.physical_progress_pct,

                    created_at =
                        EXCLUDED.created_at
                """,
                history_rows,
            )

        conn.commit()

    print(
        f"  -> Inserted/updated "
        f"{len(project_rows)} projects "
        f"for {reporting_month}"
    )

    return len(project_rows)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

if __name__ == "__main__":

    total = 0

    for filename, month in PDF_MONTH_MAP.items():

        if not os.path.exists(filename):

            print(
                f"\n[skip] {filename} "
                f"not found in current folder"
            )

            continue

        total += load_one(
            filename,
            month,
        )

    print(
        "\nDone."
    )

    print(
        f"Total project-month records "
        f"processed: {total}"
    )