"""Generate "Report Inputs.xlsx" - the engineer-editable input workbook for the
R4M Aurora Power BI report (LCM coefficients + daily/monthly targets).

Prefills June 2026 targets from the PLAN sheet / REPORT sheet of
"Daily Report_Mining Production June.xlsx" when that file is present;
otherwise writes the metric skeleton with zeros.

Usage:  python build_inputs_workbook.py
Output: Report Inputs.xlsx (overwritten in place)
"""
import datetime as dt
import os
import warnings

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

HERE = os.path.dirname(os.path.abspath(__file__))
REF_XLSX = os.path.join(HERE, "Daily_Report_Erdene_Reference.xlsx")
# prefill source: the original June workbook if still around, else the reference copy
_CANDIDATES = [os.path.join(HERE, "Daily Report_Mining Production June.xlsx"), REF_XLSX]
SOURCE_XLSX = next((p for p in _CANDIDATES if os.path.exists(p)), _CANDIDATES[0])
OUT_XLSX = os.path.join(HERE, "Report Inputs.xlsx")

# Metric vocabulary. These exact strings are referenced by DAX measures in the
# semantic model - do not rename them here without renaming them there.
# value = PLAN sheet row holding the June daily targets (None -> prefill 0).
DAILY_METRICS = {
    "Total Movement (t)": 6,
    "Total Movement (m3)": 4,
    "Topsoil (t)": 10,
    "Waste (t)": 14,
    "Blasted Waste (t)": 16,
    "Freedig (t)": None,
    "Common Mineral (t)": None,
    "MinWaste (t)": 26,
    "Subgrade (t)": 28,
    "LG1 (t)": 30,
    "HG (t)": 34,
    "MG (t)": 36,
    "LG (t)": 38,
    "HG Au (g/t)": 52,
    "HG Ag (g/t)": 54,
    "MG Au (g/t)": 57,
    "MG Ag (g/t)": 59,
    "LG Au (g/t)": 62,
    "LG Ag (g/t)": 64,
    "LG1 Au (g/t)": None,
    "LG1 Ag (g/t)": None,
    "Subgrade Au (g/t)": None,
    "Subgrade Ag (g/t)": None,
    "MinWaste Au (g/t)": None,
    "MinWaste Ag (g/t)": None,
    "Ore Au (g/t)": 67,
    "Ore Ag (g/t)": None,
    "Engineering work (t)": 40,
    "IWF Spreading (lcm)": 107,
    "Tailings (t)": 109,
    "Mill Feed HG (t)": 77,
    "Mill Feed HG Au (g/t)": 78,
    "Mill Feed HG Ag (g/t)": 80,
    "Mill Feed MG (t)": 82,
    "Mill Feed MG Au (g/t)": 83,
    "Mill Feed MG Ag (g/t)": 85,
    "Mill Feed LG (t)": 87,
    "Mill Feed LG Au (g/t)": 88,
    "Mill Feed LG Ag (g/t)": 90,
    # the SOP's crushing plan ("6.1 Crushed Total Ore" by class) - Mobile Crusher chart tick
    "Crushed HG (t)": None,
    "Crushed MG (t)": None,
    "Crushed LG (t)": None,
    # flat excavator productivity targets, bcm per operating hour
    "EX212 (bcm/h)": None,
    "EX213 (bcm/h)": None,
    "EX214 (bcm/h)": None,
    "EX215 (bcm/h)": None,
    "EX216 (bcm/h)": None,
}
EXC_TARGET_DEFAULT = {"EX212 (bcm/h)": 140, "EX213 (bcm/h)": 330, "EX214 (bcm/h)": 330,
                      "EX215 (bcm/h)": 330, "EX216 (bcm/h)": 330}

# Monthly targets: metric -> REPORT sheet cell (column K = Monthly Target).
MONTHLY_CELLS = {
    "Total Movement (t)": "K161",
    "Total Movement (m3)": "K162",
    "Topsoil (t)": "K163",
    "Waste (t)": "K164",
    "Blasted Waste (t)": "K165",
    "Freedig (t)": None,
    "Common Mineral (t)": "K167",
    "MinWaste (t)": "K171",
    "Subgrade (t)": "K170",
    "LG1 (t)": "K172",
    "HG (t)": "K182",
    "MG (t)": "K185",
    "LG (t)": "K188",
    "HG Au (g/t)": "K183",
    "HG Ag (g/t)": "K184",
    "MG Au (g/t)": "K186",
    "MG Ag (g/t)": "K187",
    "LG Au (g/t)": "K189",
    "LG Ag (g/t)": "K190",
    "LG1 Au (g/t)": None,
    "LG1 Ag (g/t)": None,
    "Subgrade Au (g/t)": None,
    "Subgrade Ag (g/t)": None,
    "MinWaste Au (g/t)": None,
    "MinWaste Ag (g/t)": None,
    "Ore Au (g/t)": "K180",
    "Ore Ag (g/t)": "K181",
    "Engineering work (t)": None,
    "IWF Spreading (lcm)": "K195",
    "Tailings (t)": "K196",
    "Mill Feed HG (t)": "K633",
    "Mill Feed HG Au (g/t)": "K634",
    "Mill Feed HG Ag (g/t)": "K635",
    "Mill Feed MG (t)": "K636",
    "Mill Feed MG Au (g/t)": "K637",
    "Mill Feed MG Ag (g/t)": "K638",
    "Mill Feed LG (t)": "K639",
    "Mill Feed LG Au (g/t)": "K640",
    "Mill Feed LG Ag (g/t)": "K641",
    "Crushed HG (t)": None,
    "Crushed MG (t)": None,
    "Crushed LG (t)": None,
}

# LCM / density coefficients per R4M Material Code.
# Density t/bcm from the Excel Parameters sheet (ore 2.64, waste 2.63, topsoil 1.6).
# Swell factor converts BCM -> LCM; engineers adjust these to their own values.
LCM_ROWS = [
    # code, name, density t/bcm, swell bcm->lcm
    ("HG", "High-Grade", 2.64, 1.0),
    ("MG", "Mid-Grade", 2.64, 1.0),
    ("LG1", "Low-Grade 0.45-0.7", 2.64, 1.0),
    ("LG2", "Low-Grade 0.7-2.0", 2.64, 1.0),
    ("SG", "Subgrade", 2.64, 1.0),
    ("MW", "MinWaste", 2.64, 1.0),
    ("W", "Blasted Waste", 2.63, 1.0),
    ("FD", "Freedig Waste", 2.63, 1.0),
    ("BAS", "Common Mineral", 2.63, 1.0),
    ("TS", "Topsoil", 1.6, 1.0),
    ("EW", "Road Base Material", 2.63, 1.0),
    ("TL", "Tailing", 1.6, 1.0),
    ("ROM", "Unidentified", 2.64, 1.0),
]

HEAD = Font(bold=True, color="FFFFFF")
HEAD_FILL = PatternFill("solid", fgColor="2F5496")
EDIT_FILL = PatternFill("solid", fgColor="FFF2CC")  # editable cells


def read_june_plan():
    """Return (dates, {plan_row: {date: value}}) from the June workbook, or (June dates, {})."""
    june = [dt.date(2026, 6, d) for d in range(1, 31)]
    if not os.path.exists(SOURCE_XLSX):
        print(f"WARNING: no PLAN source workbook found - daily targets prefill with ZEROS")
        return june, {}
    print(f"prefilling targets from {os.path.basename(SOURCE_XLSX)}")
    warnings.filterwarnings("ignore")
    wb = openpyxl.load_workbook(SOURCE_XLSX, read_only=True, data_only=True)
    ws = wb["PLAN"]
    grid = {rownum: [c.value for c in r]
            for rownum, r in enumerate(
                ws.iter_rows(min_row=1, max_row=115, max_col=40), start=1)}
    date_cols = {}  # date -> list index
    for i, v in enumerate(grid[3]):
        if isinstance(v, dt.datetime) and v.year == 2026 and v.month == 6:
            date_cols[v.date()] = i
    plan = {}
    rows_needed = {r for r in DAILY_METRICS.values() if r is not None}
    for r in rows_needed:
        vals = {}
        for d, i in date_cols.items():
            v = grid.get(r, [None] * 40)[i] if i < len(grid.get(r, [])) else None
            vals[d] = float(v) if isinstance(v, (int, float)) else 0.0
        plan[r] = vals
    monthly = {}
    ws2 = wb["REPORT"]
    for metric, cell in MONTHLY_CELLS.items():
        v = ws2[cell].value if cell else None
        monthly[metric] = float(v) if isinstance(v, (int, float)) else 0.0
    wb.close()
    return june, plan, monthly


def read_pp_reference():
    """Process-plant actuals + Mill-Feed-YTD monthly history from the reference workbook.

    Returns (pp_daily = {date: {"t":…, "au":…}}, mill_monthly = [(month, bt, mt, pt, bg, fg, pg)]).
    """
    pp_daily, mill_monthly = {}, []
    if not os.path.exists(REF_XLSX):
        print(f"NOTE: {REF_XLSX} not found; PP Actuals / Mill Monthly start empty")
        return pp_daily, mill_monthly
    warnings.filterwarnings("ignore")
    wb = openpyxl.load_workbook(REF_XLSX, read_only=True, data_only=True)

    ws = wb["PP"]
    for r in ws.iter_rows(min_row=2, max_col=15, values_only=True):
        d, typ, ton = r[0], r[2], r[3]
        if isinstance(d, dt.datetime) and str(typ).strip() == "Process Plant" \
                and isinstance(ton, (int, float)):
            key = d.strftime("%Y-%m-%d")
            pp_daily.setdefault(key, {"t": 0.0, "au": None})
            pp_daily[key]["t"] += float(ton)
        gd, gv = r[8], r[14]                       # cols I (date) and O ("(Mill)" grade)
        if isinstance(gd, dt.datetime) and isinstance(gv, (int, float)):
            key = gd.strftime("%Y-%m-%d")
            pp_daily.setdefault(key, {"t": 0.0, "au": None})
            pp_daily[key]["au"] = round(float(gv), 3)

    ws = wb["GRAPH DATA"]
    rows = {rn: r for rn, r in enumerate(
        ws.iter_rows(min_row=182, max_row=191, max_col=20, values_only=True), start=182)}
    months = rows[182]
    for i in range(1, len(months)):
        m = months[i]
        if not isinstance(m, dt.datetime):
            break
        vals = [rows[rn][i] for rn in (184, 185, 186, 189, 190, 191)]
        mill_monthly.append((m.strftime("%Y-%m"),
                             *[round(float(v), 3) if isinstance(v, (int, float)) else 0.0
                               for v in vals]))
    wb.close()
    return pp_daily, mill_monthly


def main():
    res = read_june_plan()
    if len(res) == 3:
        dates, plan, monthly = res
    else:
        dates, plan = res
        monthly = {m: 0.0 for m in MONTHLY_CELLS}

    out = openpyxl.Workbook()

    # --- ReadMe ---
    ws = out.active
    ws.title = "ReadMe"
    lines = [
        "R4M Aurora Power BI report - input workbook",
        "",
        "How to use:",
        "1. Edit the yellow cells only. Do not rename sheets, the 'Metric' column values,",
        "   or the Material Code values - the Power BI model matches on those exact names.",
        "2. 'Daily Targets': one column per date. For a new month, replace the date row",
        "   with the new month's dates and enter the plan (copy from your PLAN sheet).",
        "   Extra date columns are fine; the model unpivots whatever dates are present.",
        "3. 'Monthly Targets': one row per metric per month (add rows for new months).",
        "4. 'LCM': density (t/bcm) and swell factor (bcm->lcm) per R4M material code.",
        "   Volume m3 = tonnes / density.  LCM = m3 x swell factor.",
        "5. Save this file, then in Power BI: Home > Refresh.",
        "",
        "This file is read by the semantic model via the InputsPath parameter",
        "(Transform data > Edit parameters) - update that if you move this file.",
        "Regenerate a fresh copy any time with:  python build_inputs_workbook.py",
    ]
    for i, line in enumerate(lines, 1):
        ws.cell(row=i, column=1, value=line)
        if i == 1:
            ws.cell(row=i, column=1).font = Font(bold=True, size=14)
    ws.column_dimensions["A"].width = 95

    # --- Daily Targets ---
    ws = out.create_sheet("Daily Targets")
    ws.cell(row=1, column=1, value="Metric").font = HEAD
    ws.cell(row=1, column=1).fill = HEAD_FILL
    for j, d in enumerate(dates, start=2):
        c = ws.cell(row=1, column=j, value=d)
        c.font, c.fill = HEAD, HEAD_FILL
        c.number_format = "yyyy-mm-dd"
        c.alignment = Alignment(horizontal="center")
        ws.column_dimensions[c.column_letter].width = 11
    for i, (metric, prow) in enumerate(DAILY_METRICS.items(), start=2):
        ws.cell(row=i, column=1, value=metric).font = Font(bold=True)
        for j, d in enumerate(dates, start=2):
            if prow:
                v = plan.get(prow, {}).get(d, 0.0)
            else:
                v = EXC_TARGET_DEFAULT.get(metric, 0.0)
            c = ws.cell(row=i, column=j, value=round(v, 4))
            c.fill = EDIT_FILL
    ws.column_dimensions["A"].width = 26
    ws.freeze_panes = "B2"

    # --- Monthly Targets ---
    ws = out.create_sheet("Monthly Targets")
    for j, h in enumerate(["Metric", "Month", "Target"], start=1):
        c = ws.cell(row=1, column=j, value=h)
        c.font, c.fill = HEAD, HEAD_FILL
    for i, metric in enumerate(MONTHLY_CELLS, start=2):
        ws.cell(row=i, column=1, value=metric).font = Font(bold=True)
        m = ws.cell(row=i, column=2, value=dt.date(2026, 6, 1))
        m.number_format = "yyyy-mm-dd"
        m.fill = EDIT_FILL
        t = ws.cell(row=i, column=3, value=round(monthly.get(metric, 0.0), 4))
        t.fill = EDIT_FILL
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 14
    ws.freeze_panes = "A2"

    # --- PP Actuals + Mill Monthly (process-plant side, prefilled from reference) ---
    pp_daily, mill_monthly = read_pp_reference()

    ws = out.create_sheet("PP Actuals")
    pp_dates = sorted(pp_daily)
    ws.cell(row=1, column=1, value="Metric").font = HEAD
    ws.cell(row=1, column=1).fill = HEAD_FILL
    for j, d in enumerate(pp_dates, start=2):
        c = ws.cell(row=1, column=j, value=dt.datetime.strptime(d, "%Y-%m-%d").date())
        c.font, c.fill = HEAD, HEAD_FILL
        c.number_format = "yyyy-mm-dd"
        ws.column_dimensions[c.column_letter].width = 11
    for i, (metric, key) in enumerate(
            [("PP throughput (t)", "t"), ("PP head grade Au (g/t)", "au")], start=2):
        ws.cell(row=i, column=1, value=metric).font = Font(bold=True)
        for j, d in enumerate(pp_dates, start=2):
            v = pp_daily[d].get(key)
            c = ws.cell(row=i, column=j, value=round(v, 3) if isinstance(v, (int, float)) else None)
            c.fill = EDIT_FILL
    ws.column_dimensions["A"].width = 24
    ws.freeze_panes = "B2"

    ws = out.create_sheet("Mill Monthly")
    heads = ["Month", "Monthly Plan throughput (t)", "Mine throughput (t)", "PP throughput (t)",
             "Monthly Plan head grade Au (g/t)", "Feed head grade Au (g/t)", "PP head grade Au (g/t)"]
    for j, h in enumerate(heads, start=1):
        c = ws.cell(row=1, column=j, value=h)
        c.font, c.fill = HEAD, HEAD_FILL
        ws.column_dimensions[c.column_letter].width = 18 if j > 1 else 10
    for i, row in enumerate(mill_monthly, start=2):
        ws.cell(row=i, column=1, value=row[0]).font = Font(bold=True)
        for j, v in enumerate(row[1:], start=2):
            c = ws.cell(row=i, column=j, value=v)
            c.fill = EDIT_FILL
    ws.freeze_panes = "A2"

    # --- LCM ---
    ws = out.create_sheet("LCM")
    headers = ["Material Code", "Material Name", "Density t/bcm", "Swell Factor"]
    for j, h in enumerate(headers, start=1):
        c = ws.cell(row=1, column=j, value=h)
        c.font, c.fill = HEAD, HEAD_FILL
        ws.column_dimensions[c.column_letter].width = 16
    for i, (code, name, dens, swell) in enumerate(LCM_ROWS, start=2):
        ws.cell(row=i, column=1, value=code).font = Font(bold=True)
        ws.cell(row=i, column=2, value=name)
        d = ws.cell(row=i, column=3, value=dens)
        s = ws.cell(row=i, column=4, value=swell)
        d.fill = EDIT_FILL
        s.fill = EDIT_FILL
    ws.column_dimensions["B"].width = 20
    ws.freeze_panes = "A2"

    out.save(OUT_XLSX)
    print(f"wrote {OUT_XLSX}")


if __name__ == "__main__":
    main()
