import sys
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

PROJECTS = [
    ("MINISTRY OF ROAD TRANSPORT AND HIGHWAYS", "Roads and Highways", [
        ("1", "Six Laning of Chennai-Bengaluru NH-48 Corridor\n(National Highways Authority of India)\n(NH-48-CB-2024)\n(OCMS-4471)(PMG-2210)", "Tamil Nadu", "2021-06-15\n(2022-01-10)", "2025-12-31\n(2027-06-30)", "4,250.00\n(4,890.50)"),
        ("2", "Zojila Tunnel Approach Road Package II\n(NHIDCL)\n(ZJT-AR-P2)", "Ladakh", "2020-10-01\n(-)", "2026-09-30\n(2028-03-31)", "2,680.00\n(3,120.00)"),
    ]),
    ("MINISTRY OF RAILWAYS", "Railways", [
        ("3", "Rishikesh-Karnprayag Broad Gauge Rail Link\n(Rail Vikas Nigam Limited)\n(RVNL-RK-BG-19)\n(OCMS-3320)(-)", "Uttarakhand", "2019-03-01\n(-)", "2025-03-31\n(2026-12-31)", "16,216.00\n(24,659.00)"),
    ]),
]

MONTH_DATA = {
    "2026-04": {"NH-48-CB-2024": ("2,105.40", "48.20"), "ZJT-AR-P2": ("1,240.00", "39.50"), "RVNL-RK-BG-19": ("14,890.00", "61.00")},
    "2026-05": {"NH-48-CB-2024": ("2,297.80", "52.60"), "ZJT-AR-P2": ("1,318.75", "41.20"), "RVNL-RK-BG-19": ("15,410.30", "63.80")},
}


def build(month, out_path):
    data = MONTH_DATA[month]
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(out_path, pagesize=landscape(A4), topMargin=12 * mm)
    header = ["Sl.No", "Project Name\n(Implementing Agency)\n(Project Code)", "State", "Approval/\nStart Date", "Original/Revised\nTarget DOC", "Original/Revised\nCost (Rs. Cr)", "Cumulative\nExpenditure (Rs. Cr)", "Physical\nProgress (%)"]
    rows = [header]
    for ministry, sector, projects in PROJECTS:
        rows.append(["", ministry, "", "", "", "", "", ""])
        rows.append(["", sector, "", "", "", "", "", ""])
        for sl, name_cell, state, start, doc_dates, cost in projects:
            code = name_cell.split("\n")[2].strip("()")
            exp, prog = data[code]
            rows.append([sl, name_cell, state, start, doc_dates, cost, exp, prog])
    table = Table(rows, colWidths=[14 * mm, 84 * mm, 26 * mm, 28 * mm, 32 * mm, 32 * mm, 32 * mm, 24 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
    ]))
    doc.build([Paragraph(f"Table 6: All Ongoing Projects — Flash Report {month}", styles["Title"]), Spacer(1, 6), table])
    print(f"wrote {out_path}")


if __name__ == "__main__":
    month = sys.argv[1]
    build(month, sys.argv[2])
