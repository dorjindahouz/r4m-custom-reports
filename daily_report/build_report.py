"""Build the Erdene daily mining production report as a standalone HTML page.

Replicates the REPORT tab of "Daily Report_Mining Production June.xlsx" (the
R4M-sourceable sections, in the Master Report order: MINING, ROM INVENTORIES, MILL FEEDING)
directly from the R4M cube API data - no Power BI involved.

Data flow:
  fetch_data.py            ->  data/*.parquet + data/r4m_grades.json  (--fetch refreshes;
                               everything comes from r4m.example.local)
  Report Inputs.xlsx       ->  default LCM coefficients + daily/monthly targets
  this script              ->  daily_report.html  (self-contained; the page
                               recomputes everything client-side, and the LCM /
                               target inputs are editable in the browser with
                               localStorage persistence)

Run:  python build_report.py [--fetch]
"""
import argparse
import base64
import datetime as dt
import json
import os
import re
import subprocess
import sys

import numpy as np
import pandas as pd

from customize_template import CUSTOM_CSS, CUSTOM_JS
from manual_template import (AUX_TYPES, MANUAL_CSS, MANUAL_INPUTS_HTML,
                             MANUAL_JS, MANUAL_SECTION_HTML, merge_defs, seed_manual)
from master_template import (MASTER_CSS, MASTER_INPUTS_HTML, MASTER_SECTION_HTML,
                             MRSET_DEFAULT, master_js)
from notes_template import NOTES_CSS, NOTES_JS, NOTES_SECTION_HTML
from xlsx_template import INPUTS_XLSX_JS, XLSX_CSS, XLSX_JS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(HERE, "data")
INPUTS_XLSX = os.path.join(ROOT, "Report Inputs.xlsx")
# The PUBLISHED plan: written by the page's "Publish inputs" button and baked
# into every build on top of the workbook defaults, so everyone who opens the
# report sees the same targets. See apply_published().
PUBLISHED_JSON = os.path.join(HERE, "published_inputs.json")
OUT = os.path.join(HERE, "daily_report.html")
LOGO_B64 = base64.b64encode(
    open(os.path.join(HERE, "erdene_logo.png"), "rb").read()).decode("ascii")

SHIFT_NAME = {"A": "DS", "B": "NS"}


# --------------------------------------------------------------------------- #
# Data preparation
# --------------------------------------------------------------------------- #
def load_joined():
    f = lambda n: pd.read_parquet(os.path.join(DATA, f"{n}.parquet"))
    prod = f("production")
    prod = prod[prod["It is reportable for production"] == True]  # noqa: E712

    mat = f("material")[["Id Material", "Material Code"]]
    dump = f("location_dump")[["Id Location Dump", "Location Dump", "Region"]]
    grades = f("polygon_grades").copy()
    grades["gname"] = grades["Polygon Grade Name"].str.strip()
    gp = (grades.pivot_table(index="Id Polygon", columns="gname",
                             values="Polygon Grade Value", aggfunc="max")
                .rename(columns={"Gold grade": "Au", "Silver grade": "Ag"}))
    for c in ("Au", "Ag"):
        if c not in gp:
            gp[c] = np.nan

    # Overlay the R4M app's polygon grades (data/r4m_grades.json, from
    # /duckdb/sensor/getGradeBlockAndPolygonData/): the cube's polygon_grades
    # export carries only ONE grade per polygon (almost always Ag) while the
    # app endpoint carries both Au and Ag. R4M app grades win where present;
    # the cube export only fills Ag for polygons the endpoint never lists
    # (polygons with no Au registered).
    r4m = load_r4m_grades()
    if r4m:
        gdf = pd.DataFrame.from_dict(r4m, orient="index", columns=["Au_r4m", "Ag_r4m"])
        gdf.index.name = "Id Polygon"
        gp = gp.join(gdf, how="outer")
        gp["Au"] = gp["Au_r4m"].combine_first(gp["Au"])
        gp["Ag"] = gp["Ag_r4m"].combine_first(gp["Ag"])
        gp = gp.drop(columns=["Au_r4m", "Ag_r4m"])

    df = (prod.merge(mat, on="Id Material", how="left")
              .merge(dump, on="Id Location Dump", how="left")
              .merge(gp[["Au", "Ag"]], on="Id Polygon", how="left"))
    df["date"] = df["Date Cube Hauling"].astype(str).str[:10]
    df["shift"] = df["Hauling Shift"].map(SHIFT_NAME).fillna(df["Hauling Shift"])
    df["code"] = df["Material Code"].fillna("?")
    df["t"] = df["Dry Tonnes"].fillna(0.0)
    df["au_g"] = df["t"] * df["Au"].fillna(0.0)
    df["ag_g"] = df["t"] * df["Ag"].fillna(0.0)
    # "dump_crushed" (a test dump of crushed waste) is not the crusher pad
    df["is_crush"] = (df["Location Dump"].str.contains(MILL_FEED_RE, case=False, na=False, regex=True)
                      & ~df["Location Dump"].str.match(r"dump", case=False, na=False))
    df["is_iwf"] = df["Region"].eq("IWF")
    df["is_rom"] = df["Region"].eq("ROM Pad")
    # reclaim: cycles LOADED from a ROM-pad location. R4M books part of the
    # reclaim against the pile itself (SMG-1-6_C, SL_21_1 ...), the rest
    # against feed points (F1..F4, FINGER*) that match no pile.
    ll_path = os.path.join(DATA, "location_load.parquet")
    if os.path.exists(ll_path):
        ll = (pd.read_parquet(ll_path)[["Id Location Load", "Location Load", "Region", "Zone"]]
                .rename(columns={"Region": "Load Region", "Zone": "Load Zone"}))
        df = df.merge(ll, on="Id Location Load", how="left")
    else:
        df["Location Load"], df["Load Region"], df["Load Zone"] = None, None, None
    df["is_rom_load"] = df["Load Region"].eq("ROM Pad")
    # REHANDLE = loaded from a stockpile or a dump, not from the pit: reclaim off
    # the ROM pad ("StockPile Zone") and waste re-moved off IWF / min-waste /
    # topsoil ("Dumping Zone"). Pit loads are "Loading Zone" + "Zonas Tajo".
    # Mine-production rows exclude rehandle (it was mined when it first left
    # the pit); Mill Feeding counts crusher deliveries whether direct or
    # reclaimed. The two are independent measures. Same rule in LIVE_JS.
    # Since 2026-10-19 (Erdene change pack, item 1) a crusher delivery that was
    # NOT loaded in the pit ("Loading Zone") is rehandle too: feed points such as
    # Finger-2 / Scat_1 sit in "Zonas Tajo", and the mill feed must never be
    # counted again as mine production. Total Movement = mined only (sum of rows).
    df["is_reh"] = (df["Load Zone"].isin(REHANDLE_ZONES)
                    | (df["is_crush"] & df["Load Zone"].ne("Loading Zone")))

    # grade coverage: share of tonnage whose source polygon has a grade at all
    t = df["t"].sum()
    df.attrs["au_cov"] = (df.loc[df["Au"].notna(), "t"].sum() / t * 100) if t else 0
    df.attrs["ag_cov"] = (df.loc[df["Ag"].notna(), "t"].sum() / t * 100) if t else 0
    return df


def build_cube(df):
    """cube[date][shift][code] = [t, au_g, ag_g, t_crush, au_crush, ag_crush, t_iwf,
                                   t_reh, au_reh, ag_reh, t_crush_with_au, t_crush_with_ag]
    (reh = rehandle loads; the last two = crusher tonnes whose source polygon has
    an Au / Ag grade registered - the denominators of the mill-feed head grade)"""
    g = df.groupby(["date", "shift", "code"])
    agg = g.apply(lambda s: pd.Series({
        "t": s["t"].sum(),
        "au": s["au_g"].sum(),
        "ag": s["ag_g"].sum(),
        "tc": s.loc[s["is_crush"], "t"].sum(),
        "auc": s.loc[s["is_crush"], "au_g"].sum(),
        "agc": s.loc[s["is_crush"], "ag_g"].sum(),
        "tw": s.loc[s["is_iwf"], "t"].sum(),
        "tr": s.loc[s["is_reh"], "t"].sum(),
        "aur": s.loc[s["is_reh"], "au_g"].sum(),
        "agr": s.loc[s["is_reh"], "ag_g"].sum(),
        "tca": s.loc[s["is_crush"] & s["Au"].notna(), "t"].sum(),
        "tcg": s.loc[s["is_crush"] & s["Ag"].notna(), "t"].sum(),
    }), include_groups=False)
    cube = {}
    for (date, shift, code), row in agg.iterrows():
        cube.setdefault(date, {}).setdefault(shift, {})[code] = [
            round(row.t, 2), round(row.au, 1), round(row.ag, 1),
            round(row.tc, 2), round(row.auc, 1), round(row.agc, 1),
            round(row.tw, 2),
            round(row.tr, 2), round(row.aur, 1), round(row.agr, 1),
            round(row.tca, 2), round(row.tcg, 2),
        ]
    return cube


EXCLUDE_EQUIP = {"EX127"}   # deleted test units still present in the equipment dim

# Mill feed = cycles dumped at the crusher. The dump location was called
# "Crusher"/"CRUSHER" until 2026-08-25 and "Үйлдвэр" (Mongolian: plant) from
# that day on - both are the same crusher pad. Same regex in the page's live
# rebuild (build_combined LIVE_JS) - keep the two in sync.
MILL_FEED_RE = r"crush|үйлдвэр"
REHANDLE_ZONES = ("StockPile Zone", "Dumping Zone")   # location_load.Zone values that are not the pit

# Active stockpiles for the atlas ore inventory (a build-time snapshot): R4M has
# no open/closed status for ROM-pad dump locations, so a pile counts as ACTIVE
# when it received material within this many days of the latest data. The
# report's ROM table (renderROM) instead follows the selected period: a pile is
# listed only when R4M logged a receipt onto it or a reclaim load from it
# between the start and end dates.
ACTIVE_PILE_DAYS = 30


def load_r4m_grades():
    """{Id Polygon: (Au, Ag)} from data/r4m_grades.json ({} if missing)."""
    path = os.path.join(DATA, "r4m_grades.json")
    if not os.path.exists(path):
        return {}
    raw = json.load(open(path, encoding="utf-8")).get("polygon") or {}
    out = {}
    for pid, (au, ag) in raw.items():
        out[int(pid)] = (np.nan if au is None else float(au),
                         np.nan if ag is None else float(ag))
    return out


def build_exh(df, lcm):
    """exh[equipment][date][shift] = [24 hourly bcm], for excavators (EX*).

    Shift-keyed so the report's day/night filter reaches the excavator charts;
    the shift comes from the cycle row, never from the clock hour."""
    eq_path = os.path.join(DATA, "equipment.parquet")
    if not os.path.exists(eq_path):
        print("NOTE: equipment.parquet not cached yet (run --fetch); excavator charts will be empty")
        return {}
    eq = pd.read_parquet(eq_path)[["Id Equipment", "Equipment"]]
    eq = eq[~eq["Equipment"].isin(EXCLUDE_EQUIP)]
    d = df.merge(eq, left_on="Id Equipment Loading", right_on="Id Equipment", how="left")
    d = d[d["Equipment"].astype(str).str.upper().str.startswith("EX")].copy()
    dens = {k: v.get("density", 2.64) for k, v in (lcm or {}).items()}
    d["bcm"] = d["t"] / d["code"].map(dens).fillna(2.64)
    d["hour"] = pd.to_numeric(d["Hauling Hour"], errors="coerce")
    d = d[d["hour"].between(0, 23)]
    exh = {}
    for (e, date, sh, h), v in d.groupby(["Equipment", "date", "shift", "hour"])["bcm"].sum().items():
        (exh.setdefault(e, {}).setdefault(date, {})
            .setdefault(str(sh), [0.0] * 24))[int(h)] = round(float(v), 1)
    return exh


def build_rom(df):
    """rom[pile][date] = [t, au_g, ag_g] (received onto ROM Pad piles)."""
    r = df[df["is_rom"]]
    g = r.groupby(["Location Dump", "date"])[["t", "au_g", "ag_g"]].sum()
    rom = {}
    for (pile, date), row in g.iterrows():
        rom.setdefault(pile, {})[date] = [round(row["t"], 2),
                                          round(row["au_g"], 1),
                                          round(row["ag_g"], 1)]
    return rom


def build_romout(df):
    """romout[pile][date] = t loaded OUT of a ROM-pad location (reclaim)."""
    if "is_rom_load" not in df:
        return {}
    r = df[df["is_rom_load"]]
    out = {}
    for (pile, date), t in r.groupby(["Location Load", "date"])["t"].sum().items():
        if t > 0:
            out.setdefault(pile, {})[date] = round(float(t), 2)
    return out


def build_romcls(df):
    """romcls[pile][material code] = t received (R4M material codes; the ROM
    table's Class column shows the dominant code per pile)."""
    r = df[df["is_rom"]]
    out = {}
    for (pile, code), t in r.groupby(["Location Dump", "code"])["t"].sum().items():
        if t > 0:
            out.setdefault(pile, {})[code] = round(float(t), 1)
    return out


# Metric vocabulary the page's rows and importers rely on (mirrors
# build_inputs_workbook.DAILY_METRICS / MONTHLY_CELLS). Every name is guaranteed
# to exist in DEFAULTS.daily / DEFAULTS.monthly even when the workbook on disk
# predates it, so the grids list it and the Excel / SOP imports accept it.
CANON_DAILY = [
    "Total Movement (t)", "Total Movement (m3)", "Topsoil (t)", "Waste (t)", "Blasted Waste (t)",
    "Freedig (t)", "Common Mineral (t)", "MinWaste (t)", "Subgrade (t)", "LG1 (t)", "HG (t)", "MG (t)",
    "LG (t)", "HG Au (g/t)", "HG Ag (g/t)", "MG Au (g/t)", "MG Ag (g/t)", "LG Au (g/t)", "LG Ag (g/t)",
    "LG1 Au (g/t)", "LG1 Ag (g/t)", "Subgrade Au (g/t)", "Subgrade Ag (g/t)", "MinWaste Au (g/t)",
    "MinWaste Ag (g/t)", "Ore Au (g/t)", "Ore Ag (g/t)", "Engineering work (t)", "IWF Spreading (lcm)",
    "Tailings (t)", "Mill Feed HG (t)", "Mill Feed HG Au (g/t)", "Mill Feed HG Ag (g/t)", "Mill Feed MG (t)",
    "Mill Feed MG Au (g/t)", "Mill Feed MG Ag (g/t)", "Mill Feed LG (t)", "Mill Feed LG Au (g/t)",
    "Mill Feed LG Ag (g/t)", "Crushed HG (t)", "Crushed MG (t)", "Crushed LG (t)",
    "EX212 (bcm/h)", "EX213 (bcm/h)", "EX214 (bcm/h)", "EX215 (bcm/h)", "EX216 (bcm/h)",
]
CANON_MONTHLY = [m for m in CANON_DAILY if not m.startswith("EX")]


def read_inputs():
    """Defaults from Report Inputs.xlsx -> {lcm, daily, monthly, pp, millmon,
    manual, aux}. The last two are the manual-data store (requests 04/05/09);
    they start empty of values but pre-seeded with the survey rows."""
    import openpyxl
    lcm, daily, monthly = {}, {}, {}
    if not os.path.exists(INPUTS_XLSX):
        print(f"WARNING: {INPUTS_XLSX} not found; inputs default to zeros")
        return {"lcm": lcm, "daily": daily, "monthly": monthly,
                "manual": seed_manual(lcm), "aux": {"machines": []},
                "budget": {}, "mrset": dict(MRSET_DEFAULT)}
    wb = openpyxl.load_workbook(INPUTS_XLSX, read_only=True, data_only=True)

    ws = wb["LCM"]
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or not row[0]:
            continue
        code, name, dens, swell = row[0], row[1], row[2], row[3]
        lcm[str(code)] = {"name": str(name or ""),
                          "density": float(dens or 2.64),
                          "swell": float(swell or 1.0)}

    ws = wb["Daily Targets"]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    date_cols = {}
    for i, v in enumerate(header):
        if isinstance(v, (dt.datetime, dt.date)):
            date_cols[i] = v.strftime("%Y-%m-%d")
    for row in rows[1:]:
        if not row or not row[0]:
            continue
        metric = str(row[0])
        vals = {}
        for i, key in date_cols.items():
            v = row[i] if i < len(row) else None
            if isinstance(v, (int, float)):
                vals[key] = round(float(v), 4)
        daily[metric] = vals

    ws = wb["Monthly Targets"]
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or not row[0]:
            continue
        metric, month, target = row[0], row[1], row[2]
        if isinstance(month, (dt.datetime, dt.date)):
            mk = month.strftime("%Y-%m")
        else:
            mk = str(month)[:7]
        monthly.setdefault(str(metric), {})[mk] = round(float(target or 0.0), 4)
    pp = {"t": {}, "au": {}}
    if "PP Actuals" in wb.sheetnames:
        rows_ = list(wb["PP Actuals"].iter_rows(values_only=True))
        dcols = {i: v.strftime("%Y-%m-%d") for i, v in enumerate(rows_[0])
                 if isinstance(v, (dt.datetime, dt.date))}
        keymap = {"PP throughput (t)": "t", "PP head grade Au (g/t)": "au"}
        for row in rows_[1:]:
            k = keymap.get(str(row[0]) if row else "")
            if not k:
                continue
            for i, dk in dcols.items():
                v = row[i] if i < len(row) else None
                if isinstance(v, (int, float)):
                    pp[k][dk] = round(float(v), 3)

    millmon = {}
    if "Mill Monthly" in wb.sheetnames:
        for row in wb["Mill Monthly"].iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue
            keys = ["bt", "mt", "pt", "bg", "fg", "pg"]
            millmon[str(row[0])[:7]] = {
                k: (round(float(v), 3) if isinstance(v, (int, float)) else 0.0)
                for k, v in zip(keys, row[1:7])}

    wb.close()
    for m in CANON_DAILY:
        daily.setdefault(m, {})
    for m in CANON_MONTHLY:
        monthly.setdefault(m, {})
    return {"lcm": lcm, "daily": daily, "monthly": monthly, "pp": pp, "millmon": millmon,
            "manual": seed_manual(lcm), "aux": {"machines": []},
            "budget": {}, "mrset": dict(MRSET_DEFAULT)}


def apply_published(defaults):
    """Overlay daily_report/published_inputs.json on the workbook defaults
    (same merge rules as the page's loadInputs) and stamp DEFAULTS.__pub, the
    version the page compares browser-local edits against."""
    pub = {"at": None, "src": "Report Inputs.xlsx"}
    if os.path.exists(PUBLISHED_JSON):
        with open(PUBLISHED_JSON, encoding="utf-8") as fh:
            p = json.load(fh)
        for k in ("lcm", "daily", "monthly", "pp", "millmon"):
            for a, v in (p.get(k) or {}).items():
                if isinstance(v, dict):
                    defaults.setdefault(k, {}).setdefault(a, {}).update(v)
        man = p.get("manual") or {}
        if isinstance(man.get("defs"), list) and man["defs"]:
            seeded = defaults.setdefault("manual", {}).get("defs") or []
            defaults["manual"]["defs"] = merge_defs(man["defs"], seeded)
        for a, v in (man.get("vals") or {}).items():
            defaults.setdefault("manual", {}).setdefault("vals", {}).setdefault(a, {}).update(v)
        if isinstance((p.get("aux") or {}).get("machines"), list):
            defaults["aux"] = {"machines": p["aux"]["machines"]}
        if isinstance(p.get("romadj"), list):
            defaults["romadj"] = p["romadj"]
        if isinstance(p.get("sopraw"), dict):
            defaults.setdefault("sopraw", {}).update(p["sopraw"])
        if isinstance(p.get("budget"), dict):        # the Master Report budget (Work_Order), whole
            defaults["budget"] = p["budget"]
        if isinstance(p.get("mrset"), dict):
            defaults.setdefault("mrset", {}).update(p["mrset"])
        pub = {"at": p.get("__publishedAt") or dt.datetime.fromtimestamp(
                   os.path.getmtime(PUBLISHED_JSON)).strftime("%Y-%m-%d %H:%M"),
               "src": "published_inputs.json"}
        n_d = sum(len(v) for v in (p.get("daily") or {}).values())
        print(f"published plan: {PUBLISHED_JSON} (published {pub['at']}, {n_d} daily target cells)")
    else:
        print("published plan: none yet - workbook defaults only")
    defaults.setdefault("romadj", [])   # ROM balance adjustments [{pile, date, bal, note}]
    defaults.setdefault("sopraw", {})   # the SOP sheet per month as last imported (export hands it back)
    defaults.setdefault("budget", {})   # Master Report plan columns: {row id: {"YYYY-MM": v, "YYYY": total}}
    defaults.setdefault("mrset", dict(MRSET_DEFAULT))
    defaults["__pub"] = pub
    return defaults


# --------------------------------------------------------------------------- #
# HTML template
# --------------------------------------------------------------------------- #
TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Daily Report - Mining Production</title>
<style>
  :root{
    --gold:#c9a227; --gold-deep:#9a7b17; --gold-hi:#d7b23a;
    --graphite:#262c31; --banner:#c9a227; --head:#f6efdb; --headM:#ecd9a0;
    --grid:#454b50; --ink:#1b1e21; --ink2:#5c6166;
    --display:Bahnschrift,'Segoe UI Semibold','Segoe UI',Arial,sans-serif;
  }
  *{box-sizing:border-box}
  body{font-family:Calibri,'Segoe UI',Arial,sans-serif;color:var(--ink);
       background:#f1efe9;margin:0;padding:18px 0 60px}
  .sheet{width:1280px;max-width:96vw;margin:0 auto;background:#fff;border-radius:6px;
         padding:26px 30px 40px;box-shadow:0 2px 14px rgba(16,24,32,.14)}
  /* title block */
  .titleblock{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;
              background:var(--graphite);color:#fff;margin:-26px -30px 20px;
              padding:24px 30px 18px;border-radius:6px 6px 0 0;
              border-bottom:3px solid var(--gold)}
  .titleblock h1{font-size:23px;margin:0;font-weight:700;letter-spacing:1.2px;
                 font-family:var(--display);color:#fff}
  .titleblock .sub{font-size:11px;font-weight:700;margin-top:5px;color:var(--gold-hi);
                   letter-spacing:2.5px;text-transform:uppercase}
  .brand{display:flex;align-items:center;gap:18px;min-width:0}
  .brandlogo{height:56px;width:auto;flex:none;background:#fff;padding:7px 12px;border-radius:6px}
  .period{font-size:13.5px;font-weight:700;white-space:nowrap;text-align:right;color:#cfd4d8}
  .period select{font:inherit;font-weight:700;padding:4px 10px;margin-left:6px;
                 border:1px solid var(--gold);border-radius:4px;background:#fff;color:var(--ink)}
  .period .perto{margin-left:6px;color:var(--gold-hi)}
  .period .pershift{margin-left:16px}
  .shiftnote{font-size:11px;color:var(--gold-hi);font-weight:400;margin-top:5px;
             white-space:normal;max-width:560px;text-align:right;margin-left:auto}
  table.rep td.num.dimtgt{color:#9aa1a7}
  .meta{font-size:11px;color:#9aa1a7;font-weight:400;margin-top:4px}
  /* big cross-navigation button */
  .bigbtn{display:inline-flex;align-items:center;gap:9px;background:linear-gradient(180deg,var(--gold-hi),var(--gold-deep));
          color:var(--ink) !important;font-weight:700;font-size:15px;letter-spacing:.8px;
          font-family:var(--display);
          padding:11px 24px;border-radius:6px;text-decoration:none;margin-top:10px;
          box-shadow:0 2px 7px rgba(154,123,23,.5);border:1px solid #8a6e10}
  .bigbtn:hover{background:linear-gradient(180deg,var(--gold),#84690e)}
  .bigbtn .glyph{font-size:19px;line-height:1}
  /* section banner */
  body{counter-reset:sec}
  .banner{background:var(--graphite);color:#fff;font-weight:700;font-size:14.5px;
          font-family:var(--display);
          text-align:left;padding:7px 12px 7px 14px;letter-spacing:1.8px;margin-top:28px;
          border:1px solid var(--grid);border-left:5px solid var(--gold);
          counter-increment:sec;box-shadow:0 1px 3px rgba(16,24,32,.18)}
  .banner::before{content:"0" counter(sec) "  ·  ";color:var(--gold-hi);letter-spacing:2px}
  /* report tables */
  table.rep{border-collapse:collapse;width:100%;font-size:12.5px}
  table.rep th,table.rep td{border:1px solid var(--grid);padding:3px 8px}
  table.rep thead th{background:var(--head);font-weight:700;text-align:center;font-size:12.5px}
  table.rep thead th.mon{background:var(--headM)}
  table.rep td.lbl{font-weight:700;text-align:left;white-space:nowrap}
  table.rep td.lbl.ind{padding-left:34px}
  table.rep td.lbl.ind2{padding-left:58px}
  table.rep tr.sub td.lbl{font-weight:400}
  /* ore-class rows (Erdene 2026-10-17): light tint + class-coloured left edge */
  table.rep tr.grp td{background:#f3f5f7}
  table.rep tr.hg td{background:#fdece4}  table.rep tr.hg.sub td{background:#fef6f2}
  table.rep tr.mg td{background:#e6effd}  table.rep tr.mg.sub td{background:#f3f7fe}
  table.rep tr.lg2 td{background:#edf6e6} table.rep tr.lg2.sub td{background:#f6fbf3}
  table.rep tr.lg1 td{background:#f3f5e3} table.rep tr.lg1.sub td{background:#f9faf1}
  table.rep tr.hg td.lbl{border-left:4px solid #f06b32}
  table.rep tr.mg td.lbl{border-left:4px solid #005aed}
  table.rep tr.lg2 td.lbl{border-left:4px solid #55a630}
  table.rep tr.lg1 td.lbl{border-left:4px solid #8c9b2e}
  table.rep tr.grp td.lbl{border-left:4px solid #6b747b}
  table.rep tr td{-webkit-print-color-adjust:exact;print-color-adjust:exact}
  table.rep td.num{text-align:right;font-variant-numeric:tabular-nums;min-width:86px}
  table.rep td.neg{color:#b00000}
  /* inputs panel */
  details.inputs{margin-top:30px;border:1px solid #bbb;background:#fbfbfb}
  details.inputs>summary{cursor:pointer;font-weight:700;font-size:14px;padding:8px 12px;
        background:#eef3f3;list-style:revert}
  .pubbar{margin:4px 0 8px;padding:7px 10px;border-radius:4px;font-size:12.5px;line-height:1.5;background:#eef6ee;border:1px solid #b9d9b9;color:#1f4d1f}
.pubbar.local{background:#fff6dd;border-color:#e6c766;color:#5c4500}
.pubbar.prev{background:#fdeeee;border-color:#e3aaaa;color:#6b1c1c}
.pubbar button{margin-left:8px}
.pwdlg{border:1px solid #c9d3dc;border-radius:6px;padding:16px 18px;max-width:420px;font-size:13px;box-shadow:0 8px 30px rgba(0,0,0,.25)}
.pwdlg::backdrop{background:rgba(16,54,68,.35)}
.pwdlg p{margin:0 0 10px;line-height:1.45}
.pwdlg input{width:100%;box-sizing:border-box;padding:6px 8px;font-size:13px}
.pwdlg .pwbtn{margin-top:12px;text-align:right}
.pubbtn{font-weight:700}
  .inputs-body{padding:12px 14px 18px}
  .inputs-body h3{font-size:13px;margin:16px 0 6px}
  .inputs-body .hint{font-size:11.5px;color:#555;margin:2px 0 10px}
  table.edit{border-collapse:collapse;font-size:12px}
  table.edit th,table.edit td{border:1px solid #999;padding:1px 4px;text-align:center}
  table.edit thead th{background:var(--head);font-weight:700;white-space:nowrap}
  table.edit td.lbl{font-weight:700;text-align:left;white-space:nowrap;background:#fff}
  table.edit input{width:74px;border:none;background:transparent;font:inherit;
                   text-align:right;padding:2px 2px}
  table.edit input:focus{outline:2px solid var(--banner);background:#fffbe6}
  .scrollx{overflow-x:auto;max-width:100%}
  .btnrow{margin:10px 0 2px;display:flex;gap:8px;flex-wrap:wrap}
  .btnrow .inmon{display:flex;align-items:center;gap:6px;font-size:12px;font-weight:700}
  .btnrow .inmon select{font:inherit;font-weight:700;padding:4px 6px;border:1px solid #1B7F8F;border-radius:3px;background:#fff}
  .btnrow button{font:inherit;font-size:12px;padding:5px 12px;cursor:pointer;
                 border:1px solid #888;background:#fff}
  .btnrow button:hover{background:#eef7f7}
  .note{font-size:11.5px;color:#555;margin-top:6px;font-style:italic}
  /* KPI strip */
  .kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:14px 0 4px}
  .kpi{border:none;border-left:4px solid var(--gold);border-radius:6px;position:relative;
       padding:10px 13px 11px;background:var(--graphite);box-shadow:0 2px 6px rgba(16,24,32,.22);overflow:hidden}
  .kpi .k{font-size:10px;color:#aeb5bb;font-weight:700;letter-spacing:1.1px;text-transform:uppercase}
  .kpi .v{font-size:27px;font-weight:700;margin-top:3px;color:var(--gold-hi);font-family:var(--display)}
  .kpi .s{font-size:11px;color:#9aa1a7;margin-top:4px;position:relative;z-index:1}
  .kpi .s b{display:inline-block;padding:1px 7px;border-radius:9px;font-size:10.5px}
  .kpi .s b.up{color:#8fe3ab;background:#12351f} .kpi .s b.dn{color:#ff9d9d;background:#46191b}
  .kpi svg.spark{position:absolute;right:8px;bottom:6px;opacity:.85}
  table.rep td.num.vpos{color:#0a7a33}
  table.rep td.num.vneg{color:#b00000}
  table.edit td.fillrow{white-space:nowrap;padding:0 3px}
  table.edit td.fillrow button{font:inherit;font-size:11px;line-height:1;cursor:pointer;padding:2px 5px;
        border:1px solid #cdd4d9;background:#fff;border-radius:3px;color:#4a5257}
  table.edit td.fillrow button:hover{background:#eef2f5}
  .tablectl{font-size:11.5px;color:#555;margin:6px 0 2px}
  .tablectl label{cursor:pointer}
__MANUAL_CSS__
__NOTES_CSS__
__XLSX_CSS__
__CUSTOM_CSS__
__MASTER_CSS__
  /* charts */
  /* one chart per row, full page width (Erdene, 2026-10-27: like their Master Report) */
  .charts,.charts.three{display:grid;grid-template-columns:1fr;gap:18px;margin-top:16px}
  .chart{border:1px solid #e2e7ea;border-radius:6px;padding:12px 14px 6px;background:#fff;
         break-inside:avoid;box-shadow:0 1px 3px rgba(16,24,32,.08)}
  .chart h4{margin:0 0 7px;font-size:13px;font-weight:600;letter-spacing:.2px;position:relative;padding-bottom:6px}
  .chart h4::after{content:"";position:absolute;left:0;bottom:0;width:34px;height:2px;background:#1CA3A6}
  .chart svg{width:100%;height:auto;display:block}
  .clegend{display:flex;flex-wrap:wrap;gap:3px 14px;font-size:11px;color:#444;margin:1px 0 5px}
  .clegend span{display:inline-flex;align-items:center;gap:5px}
  .clegend i{width:11px;height:11px;display:inline-block;border-radius:2px}
  .clegend i.line{height:3px;border-radius:1px}
  .clegend i.out{background:#fff !important;border:1.6px solid #7f8a92}
  .clegend i.dash{width:13px;height:0;border-top:2.6px solid #1b1e21;border-radius:0;background:transparent !important}
  @media print{
    body{background:#fff;padding:0}
    .titleblock{background:#fff;color:#111;border-bottom:3px solid #111;margin:0 0 14px;padding:0 0 10px}
    .titleblock h1{color:#111}
    .titleblock .sub{color:#7a6210}
    .titleblock .meta,.period{color:#555}
    .kpi{background:#fff;border:1px solid #999;box-shadow:none}
    .kpi .v{color:#111} .kpi .k,.kpi .s{color:#555}
    .sheet{box-shadow:none;width:100%;max-width:none;padding:10px 12px}
    details.inputs,.noprint{display:none !important}
    .banner{-webkit-print-color-adjust:exact;print-color-adjust:exact}
    table.rep thead th{-webkit-print-color-adjust:exact;print-color-adjust:exact}
    tr,table{break-inside:avoid}
  }
</style>
</head>
<body>
__MASTER_SECTION_HTML__
<div class="sheet">
  <div class="titleblock">
    <div class="brand">
      <img class="brandlogo" src="data:image/png;base64,__LOGO_B64__" alt="Erdene Mongol LLC">
      <div>
      <h1>OPERATIONAL MINING REPORT BY ERDENE MONGOL LLC AT THE BAYANKHUNDII GOLD MINE</h1>
      <div class="sub">Shinejinst soum, Bayankhongor province</div>
      <div class="meta">Source: R4M cube API &middot; data through <span id="dataThrough"></span> &middot; built __BUILT_AT__</div>
      <div class="meta">__GRADE_COV__</div>
      </div>
    </div>
    <div class="period">
      Reporting Period:<select id="startSel"></select><span class="perto">&rarr;</span><select id="dateSel"></select>
      <span class="pershift">Shift:<select id="shiftSel"><option value="">Both</option><option value="DS">Day (DS)</option><option value="NS">Night (NS)</option></select></span>
      <div class="meta noprint">STD = start-to-date, i.e. the whole selected period</div>
      <div class="meta shiftnote" id="shiftNote" hidden></div>
      <div class="noprint"><a class="bigbtn" href="mine_atlas.html"><span class="glyph">&#128506;</span> OPEN MINE ATLAS &rarr;</a></div>
    </div>
  </div>

  <div class="kpis" id="kpis"></div>

  <div class="banner">MINING</div>
  <div class="tablectl noprint"><label><input type="checkbox" id="showHelpers"> Show Excel helper rows (SUMPRODUCT)</label></div>
  <table class="rep" id="tblMP">
    <thead>
      <tr>
        <th rowspan="2" data-c="lbl">Material type</th>
        <th colspan="2" data-c="today">Today</th>
        <th rowspan="2" data-c="dt">Daily Target</th>
        <th rowspan="2" data-c="da">Daily Actual</th>
        <th rowspan="2" data-c="mt">STD Target</th>
        <th rowspan="2" data-c="ma">STD Actual</th>
        <th rowspan="2" data-c="mv">STD Variance</th>
        <th rowspan="2" class="mon" data-c="mo">Monthly Target</th>
      </tr>
      <tr><th data-c="ds">DS</th><th data-c="ns">NS</th></tr>
    </thead>
    <tbody></tbody>
  </table>
  <div class="note">Mine production = material <b>loaded in the pit</b>. Targets come from the published plan (Inputs &rarr; Import Site Operation Plan). Rehandle &mdash; loads taken off a stockpile or a dump, and every crusher delivery that was not loaded in the pit &mdash; is excluded from every row, Total Movement included (crusher deliveries are reported under Mill Feeding). Total Ore = Non-Rom ore (Subgrade + MinWaste) + Rom ore (HG + MG + LG2 + LG1). Hover a strip-ratio label for its formula.</div>
  <div class="charts" id="chartsMP"></div>
  <div id="chartsEXC"></div>

  <div class="banner">ROM INVENTORIES (received on C4M ROM Pad)</div>
  <table class="rep" id="tblROM">
    <thead>
      <tr>
        <th data-c="pile">Stock id</th><th data-c="cls">Class</th>
        <th data-c="t">Received to date</th>
        <th data-c="bal">Balance, t</th>
        <th data-c="per">Received in period</th>
        <th data-c="out">Reclaimed in period</th>
        <th data-c="au">Avg Au g/t</th><th data-c="ag">Avg Ag g/t</th>
        <th data-c="aug">Au in balance, g</th><th data-c="agg">Ag in balance, g</th>
        <th data-c="last">Last activity</th><th data-c="idle">Days idle</th>
      </tr>
    </thead>
    <tbody></tbody>
  </table>
  <div class="note"><b>Piles active in the selected period only</b> &mdash; a ROM-pad pile is listed when R4M logged at least one cycle dumped onto it or loaded out of it between the start and end dates, or when its balance was adjusted in the period. <b>Balance</b> = everything dumped onto the pile up to the end date &minus; everything loaded out of it (R4M load location with the pile&rsquo;s name, or its &ldquo;-1C-&rdquo; alias, e.g. SMG-1C-21 &rarr; SMG-1-21), starting from the last <b>manual adjustment</b> (&#9998;) when there is one. <i>Received / Reclaimed in period</i> are the flows inside the start&ndash;end window, not split by shift. A pile that has been fed out but still shows tonnes, or a negative balance, needs an adjustment: <a href="#tblRomAdj" data-open="inputsPanel" class="noprint">&#9998; set a pile&rsquo;s balance (e.g. to 0) on a date</a>. Grades are the average of what the pile received.</div>
  <div class="note" id="romUnmatched"></div>

  <div class="banner">MILL FEEDING</div>
  <table class="rep" id="tblMF">
    <thead>
      <tr>
        <th rowspan="2" data-c="lbl">Material type</th>
        <th colspan="2" data-c="today">Today</th>
        <th rowspan="2" data-c="dt">Daily Target</th>
        <th rowspan="2" data-c="da">Daily Actual</th>
        <th rowspan="2" data-c="mt">STD Target</th>
        <th rowspan="2" data-c="ma">STD Actual</th>
        <th rowspan="2" data-c="mv">STD Variance</th>
        <th rowspan="2" class="mon" data-c="mo">Monthly Target</th>
      </tr>
      <tr><th data-c="ds">DS</th><th data-c="ns">NS</th></tr>
    </thead>
    <tbody></tbody>
  </table>
  <div class="note">Mill Feed = cycles dumped at the crusher in R4M (dump location <i>Crusher</i> up to 2026-08-25, <i>Үйлдвэр</i> since). Au/Ag are the source polygon's grades registered in R4M (the polygon grades behind the R4M Aurora &ldquo;Grades&rdquo; report &mdash; both metals; the cube's polygon_grades export only fills Ag for polygons with no Au registered), not plant lab assays. Many stock / finger polygons are registered without grades: their tonnes take the average grade of the same material class over the same dates (the &ldquo;Feed with Au grade registered&rdquo; row shows how much of the feed carried a grade), so they no longer pull the head grade down to 0. Classes follow the R4M material code of the cycle; codes outside HG/MG/LG2/LG1 are shown as Other / unclassified.</div>
  <div class="tablectl noprint"><a href="#tblPP" data-open="inputsPanel">&#9998; Enter Process Plant actuals (PP throughput &amp; head grade)</a> &middot; <a href="#btnXlsxIn" data-open="inputsPanel">&#9998; Load the Monthly Plan (import the SOP workbook, or type the Mill Feed daily targets)</a></div>
  <div class="charts" id="chartsMF"></div>
  <div class="note">Mobile Crusher Production and the blend charts are the R4M crusher-delivery cycles (dump location <i>Үйлдвэр</i> / <i>Crusher</i>), split by the material code of each cycle; the crusher unit CH01 itself logs no tonnage. A wrong cycle is corrected at the source (C4M dispatch or the DQ app) and the page picks it up on the next load. The Monthly Plan and the Process Plant figures are inputs: Inputs panel &rarr; Daily targets / Process Plant actuals &rarr; Publish.</div>

__NOTES_SECTION_HTML__
__MANUAL_SECTION_HTML__

  <details class="inputs noprint" id="customPanel">
    <summary>LAYOUT &mdash; show or hide charts and table columns (saved in this browser)</summary>
    <div class="inputs-body">
      <div class="btnrow">
        <button type="button" id="tcShowAll">Show all charts</button>
        <button type="button" id="tcResetAll">Reset layout</button>
        <span class="hint" id="tcHiddenCount"></span>
      </div>
      <div class="hint">Every chart has &#10530; (full page) and &#10005; (hide) in its top-right corner; table headers have a gear. Anything hidden here is also absent from the printed PDF. Saved separately from the input parameters, so importing someone else&rsquo;s targets never disturbs your layout.</div>
      <div id="tcChartList"></div>
      <div id="tcTableList"></div>
    </div>
  </details>

  <details class="inputs noprint" id="inputsPanel">
    <summary>INPUTS &mdash; LCM coefficients &amp; targets (<span id="pubSummary">published plan</span>)</summary>
    <div class="inputs-body">
      <div class="pubbar" id="pubBar"></div>
      <div class="btnrow">
        <button id="btnPublish" class="pubbtn">&#10515; Publish inputs (for everyone)</button>
        <button id="btnReset">Discard my edits</button>
        <label class="inmon">Month <select id="inMonSel" title="the month the input tables and the downloaded workbook show"></select></label>
        <button id="btnXlsx">&#10515; Download workbook</button>
        <button id="btnXlsxIn" class="pubbtn">&#10514; Import workbook</button>
        <input type="file" id="fileXlsx" accept=".xlsx,.xlsm" style="display:none">
      </div>
      <h3>Loose Cubic Meter coefficients (per R4M material code)</h3>
      <div class="scrollx"><table class="edit" id="tblLCM"></table></div>
      <h3>Daily targets &mdash; <span id="dailyMonthLbl"></span></h3>
      <div class="btnrow"><button type="button" id="btnCopyMon">Copy this month &rarr; next month</button></div>
      <div class="scrollx"><table class="edit" id="tblDaily"></table></div>
      <h3>Process Plant actuals &mdash; <span id="ppMonthLbl"></span></h3>
      <div class="scrollx"><table class="edit" id="tblPP"></table></div>
      <h3>Mill Feed monthly history (YTD chart)</h3>
      <div class="scrollx"><table class="edit" id="tblMillMon"></table></div>
      <h3>ROM stockpile balance adjustments</h3>
      <div class="scrollx"><table class="edit romadj" id="tblRomAdj"></table></div>
      <h3>Monthly targets &mdash; <span id="monthLbl"></span></h3>
      <div class="scrollx"><table class="edit" id="tblMonthly"></table></div>
__MANUAL_INPUTS_HTML__
__MASTER_INPUTS_HTML__
    </div>
  </details>
  <div style="margin-top:36px;padding-top:10px;border-top:1px solid #e4e1d6;font-size:10.5px;color:#8a9097;display:flex;justify-content:space-between">
    <span>ERDENE MONGOL LLC &middot; BAYANKHUNDII GOLD MINE &middot; generated from the R4M dispatch cube</span>
    <span>built __BUILT_AT__</span>
  </div>
</div>

<script>
"use strict";
/* ------------------------------------------------------------------ data */
const CUBE = __CUBE__;      /* cube[date][shift][code] = [t,au,ag,tc,auc,agc,tiwf,treh,aureh,agreh,tcau,tcag] */
const ROM  = __ROM__;       /* rom[pile][date] = [t,au,ag] */
const ROMCLS = __ROMCLS__;  /* romcls[pile][R4M material code] = t received */
const ROMOUT = __ROMOUT__;  /* romout[pile][date] = t loaded out of the pile (reclaim) */
const EXH  = __EXH__;       /* exh[equipment][date][shift] = [24 hourly bcm] */
const DEFAULTS = __DEFAULTS__; /* {lcm:{code:{name,density,swell}}, daily:{metric:{date:v}}, monthly:{metric:{month:v}}} */

const DATES = Object.keys(CUBE).sort();
const LS_KEY = "erd_daily_report_inputs_v1";
const LS_PREV = LS_KEY + "_setaside";     /* local edits made against an older published plan */
/* the published plan this page was built with; local edits remember which one
   they were made against (__base) and are only applied on top of that same one */
let PUB = DEFAULTS.__pub || {at: null, src: "Report Inputs.xlsx"};
delete DEFAULTS.__pub;
let PUB_ID = PUB.at || "workbook";
let pubSetAside = false;
/* The published plan is a file NEXT TO THE PAGE on the server
   (published_inputs.json, written by POST publish - see server/publish_server.py).
   It is fetched before the first render and overlaid on the baked defaults, so
   everyone sees the same targets without a rebuild. Where there is no server
   (file://, an old host) the baked copy is what you get. */
// the service answers under /r4m_custom_report/ only; the R4M menu embeds this page under /fronts/r4m_custom_report/,
// so the POST target is made origin-absolute (local serve: /publish)
const PUB_URL = "published_inputs.json", PUB_POST = location.protocol === "file:" ? "publish" : location.pathname.replace(/^\/fronts(?=\/)/, "").replace(/[^/]*$/, "") + "publish", PUB_KEY_LS = "erd_report_publish_key";
function applyPublishedJS(p){           /* same merge as build_report.apply_published */
  for (const k of ["lcm", "daily", "monthly", "pp", "millmon"]){
    if (!DEFAULTS[k]) DEFAULTS[k] = {};
    for (const a in (p[k] || {}))
      if (p[k][a] && typeof p[k][a] === "object") DEFAULTS[k][a] = Object.assign(DEFAULTS[k][a] || {}, p[k][a]);
  }
  const man = p.manual || {};
  if (!DEFAULTS.manual) DEFAULTS.manual = {defs: [], vals: {}};
  if (Array.isArray(man.defs) && man.defs.length) DEFAULTS.manual.defs = mergeDefs(man.defs, DEFAULTS.manual.defs);
  for (const a in (man.vals || {})) DEFAULTS.manual.vals[a] = Object.assign(DEFAULTS.manual.vals[a] || {}, man.vals[a]);
  if (p.aux && Array.isArray(p.aux.machines)) DEFAULTS.aux = {machines: p.aux.machines};
  if (Array.isArray(p.romadj)) DEFAULTS.romadj = p.romadj;
  if (p.sopraw && typeof p.sopraw === "object") DEFAULTS.sopraw = Object.assign(DEFAULTS.sopraw || {}, p.sopraw);
  if (p.budget && typeof p.budget === "object") DEFAULTS.budget = p.budget;     /* Master Report plan, whole */
  if (p.mrset && typeof p.mrset === "object") DEFAULTS.mrset = Object.assign(DEFAULTS.mrset || {}, p.mrset);
}
async function fetchPublished(){
  if (location.protocol === "file:") return false;
  try{
    const r = await fetch(PUB_URL + "?t=" + Date.now(), {cache: "no-store", credentials: "same-origin"});
    if (!r.ok) return false;
    const p = await r.json();
    if (!p || typeof p !== "object") return false;
    applyPublishedJS(p);
    PUB = {at: p.__publishedAt || null, src: "server"};
    PUB_ID = PUB.at || "server";
    return true;
  }catch(e){ console.warn("published plan not fetched:", e); return false; }
}
/* closed-month lock: the same rule as server/publish_server.py closed_changes() */
const PUB_PERIOD_RE = /^\d{4}(-\d{2}(-\d{2})?)?$/;
function pubIsClosed(p){
  const t = new Date(Date.now() - 7 * 3600e3), y = t.getFullYear(), m = String(t.getMonth() + 1).padStart(2, "0");
  return p.length === 4 ? +p < y : p.slice(0, 7) < y + "-" + m;
}
function pubClosedCells(obj, path, period, out){
  if (obj && typeof obj === "object" && !Array.isArray(obj)){
    for (const k in obj){
      if (k.startsWith("__")) continue;
      pubClosedCells(obj[k], path + "/" + k, period || (PUB_PERIOD_RE.test(k) ? k : null), out);
    }
  } else if (Array.isArray(obj)){
    for (const v of obj){
      const d = v && typeof v === "object" && !Array.isArray(v) && typeof v.date === "string" ? v.date.slice(0, 10) : null;
      const p = period || (d && PUB_PERIOD_RE.test(d) ? d : null);
      if (p && pubIsClosed(p)) out[path + "[]" + JSON.stringify(v)] = [p, true];
    }
  } else if (period && obj !== null && obj !== undefined && obj !== "" && pubIsClosed(period)) out[path] = [period, obj];
  return out;
}
function pubClosedChanges(oldP, newP){
  const a = pubClosedCells(oldP, "", null, {}), b = pubClosedCells(newP, "", null, {}), ms = new Set();
  for (const k of new Set([...Object.keys(a), ...Object.keys(b)])){
    const va = a[k], vb = b[k];
    if (!va || !vb) ms.add((va || vb)[0].slice(0, 7));
    else if (va[1] !== vb[1] && !(typeof va[1] === "number" && typeof vb[1] === "number" && Math.abs(va[1] - vb[1]) < 1e-9)
             && String(va[1]) !== String(vb[1])) ms.add(va[0].slice(0, 7));
  }
  return [...ms].sort();
}
function pubAskPassword(msg){            /* resolves to the typed password, or null */
  return new Promise(res => {
    const dl = document.createElement("dialog");
    dl.className = "pwdlg";
    dl.innerHTML = '<form method="dialog"><p></p><input type="password" autocomplete="off" placeholder="Password">' +
      '<div class="pwbtn"><button value="cancel" type="button">Cancel</button> <button value="ok" class="pri">Unlock and publish</button></div></form>';
    dl.querySelector("p").textContent = msg;
    const inp = dl.querySelector("input");
    dl.querySelector('button[value="cancel"]').addEventListener("click", () => dl.close("cancel"));
    dl.addEventListener("close", () => { const v = dl.returnValue === "ok" ? inp.value.trim() : ""; dl.remove(); res(v || null); });
    document.body.appendChild(dl);
    dl.showModal(); inp.focus();
  });
}
const noTags = s => String(s == null ? "" : s).replace(/[<>&]/g, "");
const T=0, AU=1, AG=2, TC=3, AUC=4, AGC=5, TIWF=6, TR=7, AUR=8, AGR=9;   /* TR.. = rehandle loads */
const TCAU=10, TCAG=11;   /* crusher tonnes whose source polygon has an Au / Ag grade registered */
const NSLOT = 12;

let inputs = loadInputs();

/* ---------------------------------------------------- the reporting period
   The report covers a date RANGE (start..end) and optionally a single shift.
   Everywhere below D ("the report date") == PERIOD.end, and the cumulative
   columns run from PERIOD.start to D.  PERIOD is written only by refresh().  */
const PERIOD = {start: null, end: null, shift: null};   /* shift: null = both */
const SS = () => PERIOD.shift ? [PERIOD.shift] : null;  /* -> shifts arg of agg()/row.v() */
const stdDates = () => DATES.filter(d => d >= PERIOD.start && d <= PERIOD.end);
/* every calendar day in the range, including days with no cycles (they plot as 0) */
/* 24 hourly bcm for one excavator-day, honouring the shift filter */
function exhHours(eq, d){
  const rec = (EXH[eq] || {})[d];
  if (!rec) return null;
  if (PERIOD.shift) return rec[PERIOD.shift] || null;
  const a = rec.DS, b = rec.NS;
  if (!a && !b) return null;
  const out = new Array(24).fill(0);
  for (let h = 0; h < 24; h++) out[h] = (a ? a[h] : 0) + (b ? b[h] : 0);
  return out;
}
function rangeDays(){
  const out = [];
  for (let t = Date.parse(PERIOD.start); t <= Date.parse(PERIOD.end); t += 86400000)
    out.push(new Date(t).toISOString().slice(0, 10));
  return out;
}
/* Monthly roll-up charts follow the END date only: they are history views, so
   the start date must not truncate them (documented in the reader's guide). */
const endMon = () => PERIOD.end.slice(0, 7);
/* the month the Inputs panel works on: follows the report period until the user picks one in its
   Month box (any month, also ones without R4M data yet, e.g. next month's plan) */
let IN_MON = null;
const inMon = () => IN_MON || PERIOD.end.slice(0, 7);
const monAdd = (m, n) => { const [y, mo] = m.split("-").map(Number); return new Date(Date.UTC(y, mo - 1 + n, 1)).toISOString().slice(0, 7); };
function renderInMon(){
  const sel = document.getElementById("inMonSel"); if (!sel) return;
  const cur = inMon(), run = new Date(Date.now() - 7 * 3600e3).toISOString().slice(0, 7);
  let lo = DATES[0].slice(0, 7);
  for (const k of ["daily", "pp"]) for (const m in inputs[k]) for (const d in inputs[k][m] || {}) if (/^\d{4}-\d{2}/.test(d) && d.slice(0, 7) < lo) lo = d.slice(0, 7);
  const hi = monAdd(run, 12) > cur ? monAdd(run, 12) : cur;
  if (cur < lo) lo = cur;
  lo = lo.slice(0, 4) + "-01";                      /* from January of the earliest year with data */
  const ms = []; for (let m = lo; m <= hi; m = monAdd(m, 1)) ms.push(m);
  sel.innerHTML = ms.reverse().map(m => '<option value="' + m + '"' + (m === cur ? " selected" : "") + ">" +
    new Date(Date.parse(m + "-01T00:00:00")).toLocaleDateString("en-US", {month: "long", year: "numeric"}) + "</option>").join("");
}
const monthsUpto = list => list.filter(m => m <= endMon());

function deepCopy(o){ return JSON.parse(JSON.stringify(o)); }
function loadInputs(saved){
  const base = deepCopy(DEFAULTS);
  if (!base.manual) base.manual = {defs: [], vals: {}};
  if (!base.aux) base.aux = {machines: []};
  if (!Array.isArray(base.romadj)) base.romadj = [];
  if (!base.sopraw || typeof base.sopraw !== "object") base.sopraw = {};
  if (!base.budget || typeof base.budget !== "object") base.budget = {};
  if (!base.mrset || typeof base.mrset !== "object") base.mrset = {};
  try{
    if (saved === undefined){
      saved = JSON.parse(localStorage.getItem(LS_KEY) || "null");
      /* local edits identical to the published plan (e.g. the publisher's own,
         after the rebuild) are not edits any more: drop them silently */
      if (saved){
        const pub = JSON.stringify(loadInputs(null)), mine = JSON.stringify(loadInputs(saved));
        if (pub === mine){ localStorage.removeItem(LS_KEY); saved = null; }
      }
      /* edits made against an older published plan must not hide the new one:
         set them aside (restorable) and show everyone the published numbers */
      if (saved && saved.__base !== PUB_ID){
        try{ localStorage.setItem(LS_PREV, JSON.stringify(saved)); }catch(e){}
        localStorage.removeItem(LS_KEY);
        pubSetAside = true;
        saved = null;
      }
    }
    if (saved){
      for (const k of ["lcm","daily","monthly","pp","millmon"]){
        if (!saved[k]) continue;
        for (const a in saved[k]){
          base[k][a] = Object.assign(base[k][a] || {}, saved[k][a]);
        }
      }
      /* the manual store holds ARRAYS, which Object.assign would merge by index:
         the user's series list replaces the seeded one wholesale, values merge */
      if (saved.manual){
        if (Array.isArray(saved.manual.defs) && saved.manual.defs.length)
          base.manual.defs = mergeDefs(saved.manual.defs, base.manual.defs);
        for (const a in (saved.manual.vals || {}))
          base.manual.vals[a] = Object.assign(base.manual.vals[a] || {}, saved.manual.vals[a]);
      }
      if (saved.aux && Array.isArray(saved.aux.machines)) base.aux.machines = saved.aux.machines;
      if (Array.isArray(saved.romadj)) base.romadj = saved.romadj;
      if (saved.sopraw && typeof saved.sopraw === "object") Object.assign(base.sopraw, saved.sopraw);
      /* saved = the whole inputs object, so its budget is complete (a budget import may have dropped lines) */
      if (saved.budget && typeof saved.budget === "object") base.budget = saved.budget;
      if (saved.mrset && typeof saved.mrset === "object") Object.assign(base.mrset, saved.mrset);
    }
  }catch(e){ console.warn("inputs load failed", e); }
  return base;
}
function saveInputs(){
  localStorage.setItem(LS_KEY, JSON.stringify(Object.assign({}, inputs, {__base: PUB_ID})));
  renderPubBar();
}
function hasLocalEdits(){ try{ return !!localStorage.getItem(LS_KEY); }catch(e){ return false; } }
function renderPubBar(){
  const bar = document.getElementById("pubBar"), sum = document.getElementById("pubSummary");
  if (!bar) return;
  const pubTxt = PUB.at ? `published ${noTags(PUB.at)}` : "workbook defaults (nothing published yet)";
  let prev = null;
  try{ prev = localStorage.getItem(LS_PREV); }catch(e){}
  if (hasLocalEdits()){
    bar.className = "pubbar local";
    bar.innerHTML = `<b>You have unpublished edits</b> &mdash; only this browser sees them. Everyone else sees the plan ${pubTxt}. Press <b>Publish inputs</b> to share them.`;
    sum.textContent = "unpublished edits in this browser";
  } else if (prev && pubSetAside){
    bar.className = "pubbar prev";
    bar.innerHTML = `A newer plan was published (${pubTxt}), so the edits this browser had made against the old one were set aside. ` +
      `<button type="button" id="btnRestorePrev">Restore my old edits</button><button type="button" id="btnDropPrev">Forget them</button>`;
    sum.textContent = "published plan";
    document.getElementById("btnRestorePrev").onclick = () => {
      inputs = loadInputs(JSON.parse(prev)); localStorage.removeItem(LS_PREV); pubSetAside = false;
      saveInputs(); refresh(true);
    };
    document.getElementById("btnDropPrev").onclick = () => {
      localStorage.removeItem(LS_PREV); pubSetAside = false; renderPubBar();
    };
  } else {
    bar.className = "pubbar";
    bar.innerHTML = `Showing the <b>published plan</b> (${pubTxt}) &mdash; the same numbers everyone sees.`;
    sum.textContent = "published plan";
  }
}

/* -------------------------------------------------------------- helpers */
function dens(code){ const l = inputs.lcm[code]; return l && l.density > 0 ? l.density : 2.64; }
function swell(code){ const l = inputs.lcm[code]; return l && l.swell > 0 ? l.swell : 1.0; }

/* Sum a cube slot over dates x shifts x codes. codes=null -> all codes. */
function agg(dates, shifts, codes){
  const out = {}; /* code -> [NSLOT slots] */
  for (const d of dates){
    const day = CUBE[d]; if (!day) continue;
    for (const s in day){
      if (shifts && !shifts.includes(s)) continue;
      for (const c in day[s]){
        if (codes && !codes.includes(c)) continue;
        const v = day[s][c];
        const o = out[c] || (out[c] = new Array(NSLOT).fill(0));
        for (let i = 0; i < NSLOT; i++) o[i] += v[i] || 0;
      }
    }
  }
  return out;
}
function slot(o, i){ let x = 0; for (const c in o) x += o[c][i]; return x; }
/* "mined" = loaded from the pit: everything hauled minus REHANDLE (loads taken
   off a stockpile or a dump, and every crusher delivery not loaded in the pit's
   "Loading Zone"). Ore hauled straight from the pit to the crusher was mined
   today; ore reclaimed to it was mined when it first left the pit. Every Mine
   Production row - Total Movement included - is mined only (Erdene 2026-10-17:
   mill feed must not inflate mine production). Mill Feeding (TC..) is an
   independent measure. */
function expitT(o){ return slot(o,T) - slot(o,TR); }
function expitAu(o){ return slot(o,AU) - slot(o,AUR); }
function expitAg(o){ return slot(o,AG) - slot(o,AGR); }

/* targets */
function tD(metric, date){
  const m = inputs.daily[metric]; if (!m) return null;
  const v = m[date]; return (v === undefined || v === null) ? null : +v;
}
function tRange(metric, D){    /* target summed over the selected period */
  const m = inputs.daily[metric]; if (!m) return null;
  let x = 0, any = false;
  for (const d in m){ if (d >= PERIOD.start && d <= D){ x += +m[d]; any = true; } }
  return any ? x : null;
}
function tSumprod(tMetric, gMetric, D){   /* sum over the period's dates of t*g */
  const tm = inputs.daily[tMetric], gm = inputs.daily[gMetric];
  if (!tm || !gm) return null;
  let x = 0;
  for (const d in tm){ if (d >= PERIOD.start && d <= D) x += (+tm[d]) * (+(gm[d] || 0)); }
  return x;
}
function tDprod(tMetric, gMetric, D){    /* single day t*g */
  const t = tD(tMetric, D), g = tD(gMetric, D);
  return (t === null) ? null : t * (g || 0);
}
function tM(metric, mon){
  const m = inputs.monthly[metric]; if (!m) return null;
  const v = m[mon]; return (v === undefined || v === null) ? null : +v;
}
const div = (a, b) => (b ? a / b : (a ? null : 0));

/* -------------------------------------------------- row value functions */
/* Each row: {label, ind, fmt, v(dates,shifts), td(D), tr(D), tm(mon)}     */
const ORE = ["HG","MG","LG2","LG1"], SMW = ["SG","MW"], WASTE = ["W","FD"];   /* ORE = ROM ore (>0.45 g/t) */
const ALLORE = ["SG","MW","HG","MG","LG2","LG1"];                                 /* Total Ore = Non-ROM + ROM */
const FEED_LG = ["LG1","LG2"];
const FEED_CLS = ["HG","MG","LG1","LG2"];

function volT(o){ let x = 0; for (const c in o) x += (o[c][T] - o[c][TR]) / dens(c); return x; }

function classT(codes){ return (dd, ss) => expitT(agg(dd, ss, codes)); }
function classAu(codes){ return (dd, ss) => { const o = agg(dd, ss, codes); return div(expitAu(o), expitT(o)); }; }
function classAg(codes){ return (dd, ss) => { const o = agg(dd, ss, codes); return div(expitAg(o), expitT(o)); }; }
function tdSum(metrics){ return D => metrics.reduce((a, m) => a + (tD(m, D) || 0), 0); }
function trSum(metrics){ return D => metrics.reduce((a, m) => a + (tRange(m, D) || 0), 0); }
function tmSum(metrics){ return mon => metrics.reduce((a, m) => a + (tM(m, mon) || 0), 0); }
/* weighted target grade from class (t,g) metric pairs */
function tdWG(pairs){ return D => { let n = 0, d = 0; for (const [t, g] of pairs){ const tv = tD(t, D) || 0; n += tv * (tD(g, D) || 0); d += tv; } return div(n, d); }; }
function trWG(pairs){ return D => { let n = 0, d = 0; for (const [t, g] of pairs){ n += tSumprod(t, g, D) || 0; d += tRange(t, D) || 0; } return div(n, d); }; }

/* weighted target grades over class (t, g/t) pairs; a pair whose grade metric
   has NO value for the day / in the range is left out of both numerator and
   denominator (plans entered by hand carry HG / MG / LG grades only; the SOP
   import also fills LG1 / Subgrade / MinWaste) */
function tdWGx(pairs){ return D => { let n = 0, d = 0; for (const [t, g] of pairs){ const gv = tD(g, D); if (gv === null) continue;
  const tv = tD(t, D) || 0; n += tv * gv; d += tv; } return div(n, d); }; }
function trWGx(pairs){ return D => { let n = 0, d = 0; for (const [t, g] of pairs){ if (tRange(g, D) === null) continue;
  n += tSumprod(t, g, D) || 0; d += tRange(t, D) || 0; } return div(n, d); }; }
const ROMP = [["HG (t)","HG Au (g/t)"],["MG (t)","MG Au (g/t)"],["LG (t)","LG Au (g/t)"],["LG1 (t)","LG1 Au (g/t)"]];
const ROMPAG = [["HG (t)","HG Ag (g/t)"],["MG (t)","MG Ag (g/t)"],["LG (t)","LG Ag (g/t)"],["LG1 (t)","LG1 Ag (g/t)"]];
const OREP = ROMP.concat([["Subgrade (t)","Subgrade Au (g/t)"],["MinWaste (t)","MinWaste Au (g/t)"]]);
const OREPAG = ROMPAG.concat([["Subgrade (t)","Subgrade Ag (g/t)"],["MinWaste (t)","MinWaste Ag (g/t)"]]);
const FEEDP = [["Mill Feed HG (t)","Mill Feed HG Au (g/t)"],["Mill Feed MG (t)","Mill Feed MG Au (g/t)"],["Mill Feed LG (t)","Mill Feed LG Au (g/t)"]];
const FEEDPAG = [["Mill Feed HG (t)","Mill Feed HG Ag (g/t)"],["Mill Feed MG (t)","Mill Feed MG Ag (g/t)"],["Mill Feed LG (t)","Mill Feed LG Ag (g/t)"]];
const FEEDT = ["Mill Feed HG (t)","Mill Feed MG (t)","Mill Feed LG (t)"];
const ROM_T = ["HG (t)","MG (t)","LG (t)","LG1 (t)"], NONROM_T = ["Subgrade (t)","MinWaste (t)"];
const ALLORE_T = NONROM_T.concat(ROM_T);
const NOTGT = {td: () => null, tr: () => null, tm: () => null};
const tgt1 = name => ({td: D => tD(name, D), tr: D => tRange(name, D), tm: m => tM(name, m)});
/* a class's pair of grade rows; targets only where a grade metric exists.
   Trailing spaces keep the labels distinct for the layout customiser's row keys. */
let _gpad = 0;
function gradeRows(id, codes, cls, ind, tAu, tAg, tMet){
  const gt = g => g ? {td: D => tD(g, D), tr: trWG([[tMet, g]]), tm: m => tM(g, m)} : NOTGT;
  const pad = " ".repeat(++_gpad);
  return [
    Object.assign({id: id + ".au", label: "Au grade, g/t" + pad, ind, fmt: "d2", cls, g: 1, v: classAu(codes)}, gt(tAu)),
    Object.assign({id: id + ".ag", label: "Ag grade, g/t" + pad, ind, fmt: "d2", cls, g: 1, v: classAg(codes)}, gt(tAg)),
  ];
}
/* strip ratios as defined in Erdene's Site Operation Plan (SOP) workbook:
   "total ore" = Waste / Total ore (Non-ROM + ROM); "ore to ROM" = (Waste + Non-ROM ore) / ROM ore */
const SR_TIP_TOTAL = "Strip ratio total ore = Waste \u00f7 Total ore (Non-Rom + Rom), t/t";
const SR_TIP_ROM = "Strip ratio ore to ROM = (Waste + Non-Rom ore) \u00f7 Rom ore, t/t";
const srTotal = (w, s, o) => (o + s) > 0 ? w / (o + s) : 0;   /* Excel shows 0 on a zero denominator */
const srRom = (w, s, o) => o > 0 ? (w + s) / o : 0;
function srRow(id, label, tip, f){
  return {id, label, tip, fmt: "d1",
    v: (dd, ss) => f(expitT(agg(dd, ss, WASTE)), expitT(agg(dd, ss, SMW)), expitT(agg(dd, ss, ORE))),
    td: D => { const w = tD("Waste (t)", D) || 0, s = tdSum(NONROM_T)(D), o = tdSum(ROM_T)(D); return (o + s) ? f(w, s, o) : null; },
    tr: D => { const w = tRange("Waste (t)", D) || 0, s = trSum(NONROM_T)(D), o = trSum(ROM_T)(D); return (o + s) ? f(w, s, o) : null; },
    tm: m => { const w = tM("Waste (t)", m) || 0, s = tmSum(NONROM_T)(m), o = tmSum(ROM_T)(m); return (o + s) ? f(w, s, o) : null; }};
}

/* Mine Production. Row = {id, label, ind, fmt, cls, g, tip, v(dates,shifts), td(D), tr(D), tm(mon)}.
   Structure per Erdene's change pack of 2026-10-17: Total Ore = Non-ROM ore
   (Subgrade + MinWaste) + ROM ore (>0.45 g/t = HG + MG + LG2 + LG1). */
const MP_ROWS = [
  Object.assign({id: "tm_t", label: "Total Movement, t", fmt: "int",
   v: (dd, ss) => expitT(agg(dd, ss, null))}, tgt1("Total Movement (t)")),
  Object.assign({id: "tm_m3", label: "Total Movement, m3", fmt: "int",
   v: (dd, ss) => volT(agg(dd, ss, null))}, tgt1("Total Movement (m3)")),
  Object.assign({id: "ts", label: "Topsoil, t", fmt: "int", v: classT(["TS"])}, tgt1("Topsoil (t)")),
  Object.assign({id: "waste", label: "Waste, t", fmt: "int", v: classT(WASTE)}, tgt1("Waste (t)")),
  Object.assign({id: "bw", label: "Blasted Waste, t", ind: 1, fmt: "int", v: classT(["W"])}, tgt1("Blasted Waste (t)")),
  Object.assign({id: "fd", label: "Freedig, t", ind: 1, fmt: "int", v: classT(["FD"])}, tgt1("Freedig (t)")),
  Object.assign({id: "cm_t", label: "Common Mineral, t", fmt: "int", v: classT(["BAS"])}, tgt1("Common Mineral (t)")),
  {id: "cm_m3", label: "Common Mineral, m3", fmt: "int",
   v: (dd, ss) => expitT(agg(dd, ss, ["BAS"])) / dens("BAS"),
   td: D => div(tD("Common Mineral (t)", D), dens("BAS")),
   tr: D => div(tRange("Common Mineral (t)", D), dens("BAS")),
   tm: m => div(tM("Common Mineral (t)", m), dens("BAS"))},
  {label:"SUMPRODUCT HG Au/t*t", fmt:"d1", v:(dd,ss)=>expitAu(agg(dd,ss,["HG"])),
   td:()=>null, tr:D=>tSumprod("HG (t)","HG Au (g/t)",D), tm:()=>null},
  {label:"SUMPRODUCT HG Ag/t*t", fmt:"d1", v:(dd,ss)=>expitAg(agg(dd,ss,["HG"])),
   td:()=>null, tr:D=>tSumprod("HG (t)","HG Ag (g/t)",D), tm:()=>null},
  {label:"SUMPRODUCT MG Au/t*t", fmt:"d1", v:(dd,ss)=>expitAu(agg(dd,ss,["MG"])),
   td:()=>null, tr:D=>tSumprod("MG (t)","MG Au (g/t)",D), tm:()=>null},
  {label:"SUMPRODUCT MG Ag/t*t", fmt:"d1", v:(dd,ss)=>expitAg(agg(dd,ss,["MG"])),
   td:()=>null, tr:D=>tSumprod("MG (t)","MG Ag (g/t)",D), tm:()=>null},
  {label:"SUMPRODUCT LG Au/t*t", fmt:"d1", v:(dd,ss)=>expitAu(agg(dd,ss,["LG2"])),
   td:()=>null, tr:D=>tSumprod("LG (t)","LG Au (g/t)",D), tm:()=>null},
  {label:"SUMPRODUCT LG Ag/t*t", fmt:"d1", v:(dd,ss)=>expitAg(agg(dd,ss,["LG2"])),
   td:()=>null, tr:D=>tSumprod("LG (t)","LG Ag (g/t)",D), tm:()=>null},
  {id: "ore_all", label: "Total Ore, t", fmt: "int", cls: "grp", v: classT(ALLORE),
   td: tdSum(ALLORE_T), tr: trSum(ALLORE_T), tm: tmSum(ALLORE_T)},
  {id: "ore_all.au", label: "Au grade, g/t", ind: 1, fmt: "d2", g: 1, v: classAu(ALLORE),
   td: tdWGx(OREP), tr: trWGx(OREP), tm: m => { const n = OREP.reduce((a, [t, g]) => a + (tM(t, m) || 0) * (tM(g, m) || 0), 0), d = tmSum(OREP.map(p => p[0]))(m); return d ? n / d : null; }},
  {id: "ore_all.ag", label: "Ag grade, g/t", ind: 1, fmt: "d2", g: 1, v: classAg(ALLORE),
   td: tdWGx(OREPAG), tr: trWGx(OREPAG), tm: m => { const n = OREPAG.reduce((a, [t, g]) => a + (tM(t, m) || 0) * (tM(g, m) || 0), 0), d = tmSum(OREPAG.map(p => p[0]))(m); return d ? n / d : null; }},
  {id: "nonrom", label: "Non-Rom Ore, t", fmt: "int", cls: "grp", v: classT(SMW),
   td: tdSum(NONROM_T), tr: trSum(NONROM_T), tm: tmSum(NONROM_T)},
  Object.assign({id: "sg", label: "Subgrade (0.35-0.45 g/t), t", ind: 1, fmt: "int", v: classT(["SG"])}, tgt1("Subgrade (t)")),
  ...gradeRows("sg", ["SG"], "", 2, "Subgrade Au (g/t)", "Subgrade Ag (g/t)", "Subgrade (t)"),
  Object.assign({id: "mw", label: "MinWaste (0.1-0.35 g/t), t", ind: 1, fmt: "int", v: classT(["MW"])}, tgt1("MinWaste (t)")),
  ...gradeRows("mw", ["MW"], "", 2, "MinWaste Au (g/t)", "MinWaste Ag (g/t)", "MinWaste (t)"),
  {id: "ore", label: "Rom Ore, (>0.45 g/t), t", fmt: "int", cls: "grp", v: classT(ORE),
   td: tdSum(ROM_T), tr: trSum(ROM_T), tm: tmSum(ROM_T)},
  {id: "ore.au", label: "Au grade, g/t", ind: 1, fmt: "d2", g: 1, v: classAu(ORE),
   td: D => tD("Ore Au (g/t)", D) ?? tdWGx(ROMP)(D), tr: trWGx(ROMP), tm: m => tM("Ore Au (g/t)", m)},
  {id: "ore.ag", label: "Ag grade, g/t", ind: 1, fmt: "d2", g: 1, v: classAg(ORE),
   td: D => tD("Ore Ag (g/t)", D) ?? tdWGx(ROMPAG)(D), tr: trWGx(ROMPAG), tm: m => tM("Ore Ag (g/t)", m)},
  Object.assign({id: "hg", label: "High-Grade ore (>6.0 g/t), t", ind: 1, fmt: "int", cls: "hg", v: classT(["HG"])}, tgt1("HG (t)")),
  ...gradeRows("hg", ["HG"], "hg", 2, "HG Au (g/t)", "HG Ag (g/t)", "HG (t)"),
  Object.assign({id: "mg", label: "Mid-Grade ore (2.0-6.0 g/t), t", ind: 1, fmt: "int", cls: "mg", v: classT(["MG"])}, tgt1("MG (t)")),
  ...gradeRows("mg", ["MG"], "mg", 2, "MG Au (g/t)", "MG Ag (g/t)", "MG (t)"),
  Object.assign({id: "lg2", label: "Low-Grade2 ore (0.7-2.0 g/t), t", ind: 1, fmt: "int", cls: "lg2", v: classT(["LG2"])}, tgt1("LG (t)")),
  ...gradeRows("lg2", ["LG2"], "lg2", 2, "LG Au (g/t)", "LG Ag (g/t)", "LG (t)"),
  Object.assign({id: "lg1", label: "Low-Grade1 ore (0.45-0.7 g/t), t", ind: 1, fmt: "int", cls: "lg1", v: classT(["LG1"])}, tgt1("LG1 (t)")),
  ...gradeRows("lg1", ["LG1"], "lg1", 2, "LG1 Au (g/t)", "LG1 Ag (g/t)", "LG1 (t)"),
  srRow("sr_total", "Strip ratio total ore, t/t", SR_TIP_TOTAL, srTotal),
  srRow("sr_rom", "Strip ratio ore to ROM, t/t", SR_TIP_ROM, srRom),
  {id: "tmpstock", label: "Temporary Stockpile (t)", fmt: "int", v: () => 0, td: () => 0, tr: () => 0, tm: () => 0},
  Object.assign({id: "ew", label: "Engineering work, t", fmt: "int", v: classT(["EW"])}, tgt1("Engineering work (t)")),
  Object.assign({id: "tl", label: "Mill tailings transport (t)", fmt: "int", v: classT(["TL"])}, tgt1("Tailings (t)")),
];

/* ------------------------------------------------------------ mill feeding
   Crusher deliveries (TC..) by the cycle's R4M material code. Head grades use
   only the tonnes whose source polygon HAS a registered grade (TCAU/TCAG): many
   stock / finger polygons are registered without grades, and counting them as
   0 g/t used to drag the head grade towards zero. Per material code, ungraded
   tonnes take that code's graded average over the same dates; contained metal =
   head grade x all tonnes; a code with no graded tonnes at all is left out of
   the head grade, and its tonnes take the overall head grade. */
function feedT(codes){ return (dd,ss)=>slot(agg(dd,ss,codes),TC); }
function feedGrade(o, MS, DEN){       /* grade or null */
  let n = 0, d = 0;
  for (const c in o){ const v = o[c]; if (v[DEN] > 0 && v[TC] > 0){ n += v[TC] * v[MS] / v[DEN]; d += v[TC]; } }
  return d ? n / d : null;
}
function feedAu(codes){ return (dd,ss)=>feedGrade(agg(dd,ss,codes), AUC, TCAU); }
function feedAg(codes){ return (dd,ss)=>feedGrade(agg(dd,ss,codes), AGC, TCAG); }
function feedKg(MS, DEN){ return (dd,ss)=>{ const o = agg(dd,ss,null), g = feedGrade(o, MS, DEN);
  return g === null ? (slot(o,TC) ? null : 0) : g * slot(o,TC) / 1000; }; }
function feedOtherT(dd,ss){ return Math.max(0, slot(agg(dd,ss,null),TC) - slot(agg(dd,ss,FEED_CLS),TC)); }
function feedPct(codes){ return (dd,ss)=>{const o=agg(dd,ss,null); return div(slot(agg(dd,ss,codes),TC), slot(o,TC));}; }
/* share of crusher tonnes whose source polygon has an Au grade registered */
function feedAuCov(dd,ss){ const o = agg(dd,ss,null); return slot(o,TC) ? slot(o,TCAU) / slot(o,TC) : null; }

const MF_ROWS = [
  {id:"feed", label:"Total Ore Feed, t", fmt:"d1", v:feedT(null),
   td:tdSum(FEEDT), tr:trSum(FEEDT), tm:tmSum(FEEDT)},
  {id:"feed.au", label:"Feed Head Grade Au g/t", fmt:"d2", v:feedAu(null),
   td:tdWG(FEEDP), tr:trWG(FEEDP),
   tm:m=>{let n=0,d=0; for(const [t,g] of FEEDP){const tv=tM(t,m)||0; n+=tv*(tM(g,m)||0); d+=tv;} return div(n,d);}},
  {id:"feed.aukg", label:"Contained Gold, kg", fmt:"d2", v:feedKg(AUC, TCAU),
   td:D=>{let x=0; for(const [t,g] of FEEDP) x+=(tDprod(t,g,D)||0); return x/1000;},
   tr:D=>{let x=0; for(const [t,g] of FEEDP) x+=(tSumprod(t,g,D)||0); return x/1000;},
   tm:m=>{let x=0; for(const [t,g] of FEEDP) x+=(tM(t,m)||0)*(tM(g,m)||0); return x/1000;}},
  {id:"feed.ag", label:"Feed Head Grade Ag g/t", fmt:"d2", v:feedAg(null),
   td:tdWG(FEEDPAG), tr:trWG(FEEDPAG),
   tm:m=>{let n=0,d=0; for(const [t,g] of FEEDPAG){const tv=tM(t,m)||0; n+=tv*(tM(g,m)||0); d+=tv;} return div(n,d);}},
  {id:"feed.agkg", label:"Contained Silver, kg", fmt:"d2", v:feedKg(AGC, TCAG),
   td:D=>{let x=0; for(const [t,g] of FEEDPAG) x+=(tDprod(t,g,D)||0); return x/1000;},
   tr:D=>{let x=0; for(const [t,g] of FEEDPAG) x+=(tSumprod(t,g,D)||0); return x/1000;},
   tm:m=>{let x=0; for(const [t,g] of FEEDPAG) x+=(tM(t,m)||0)*(tM(g,m)||0); return x/1000;}},
  {id:"feed.aucov", label:"Feed with Au grade registered, %", ind:1, fmt:"pct", g:1, v:feedAuCov,
   td:()=>null, tr:()=>null, tm:()=>null,
   tip:"Share of crusher tonnes whose source polygon has an Au grade in R4M; the rest take their class's average grade"},
  {id:"feed.hg", label:"High-Grade ore (>6.0 g/t), t", fmt:"d1", cls:"hg", v:feedT(["HG"]),
   td:D=>tD("Mill Feed HG (t)",D), tr:D=>tRange("Mill Feed HG (t)",D), tm:m=>tM("Mill Feed HG (t)",m)},
  {id:"feed.hg.au", label:"High-Grade ore Au grade, g/t", ind:1, fmt:"d2", cls:"hg", g:1, v:feedAu(["HG"]),
   td:D=>tD("Mill Feed HG Au (g/t)",D), tr:trWG([["Mill Feed HG (t)","Mill Feed HG Au (g/t)"]]), tm:m=>tM("Mill Feed HG Au (g/t)",m)},
  {id:"feed.hg.ag", label:"High-Grade ore Ag grade, g/t", ind:1, fmt:"d2", cls:"hg", g:1, v:feedAg(["HG"]),
   td:D=>tD("Mill Feed HG Ag (g/t)",D), tr:trWG([["Mill Feed HG (t)","Mill Feed HG Ag (g/t)"]]), tm:m=>tM("Mill Feed HG Ag (g/t)",m)},
  {id:"feed.mg", label:"Mid-Grade ore (2.0-6.0 g/t), t", fmt:"d1", cls:"mg", v:feedT(["MG"]),
   td:D=>tD("Mill Feed MG (t)",D), tr:D=>tRange("Mill Feed MG (t)",D), tm:m=>tM("Mill Feed MG (t)",m)},
  {id:"feed.mg.au", label:"Mid-Grade ore Au grade, g/t", ind:1, fmt:"d2", cls:"mg", g:1, v:feedAu(["MG"]),
   td:D=>tD("Mill Feed MG Au (g/t)",D), tr:trWG([["Mill Feed MG (t)","Mill Feed MG Au (g/t)"]]), tm:m=>tM("Mill Feed MG Au (g/t)",m)},
  {id:"feed.mg.ag", label:"Mid-Grade ore Ag grade, g/t", ind:1, fmt:"d2", cls:"mg", g:1, v:feedAg(["MG"]),
   td:D=>tD("Mill Feed MG Ag (g/t)",D), tr:trWG([["Mill Feed MG (t)","Mill Feed MG Ag (g/t)"]]), tm:m=>tM("Mill Feed MG Ag (g/t)",m)},
  {id:"feed.lg", label:"Low-Grade2 ore (0.7-2.0 g/t), t", fmt:"d1", cls:"lg2", v:feedT(FEED_LG),
   td:D=>tD("Mill Feed LG (t)",D), tr:D=>tRange("Mill Feed LG (t)",D), tm:m=>tM("Mill Feed LG (t)",m)},
  {id:"feed.lg.au", label:"Low-Grade2 Au grade, g/t", ind:1, fmt:"d2", cls:"lg2", g:1, v:feedAu(FEED_LG),
   td:D=>tD("Mill Feed LG Au (g/t)",D), tr:trWG([["Mill Feed LG (t)","Mill Feed LG Au (g/t)"]]), tm:m=>tM("Mill Feed LG Au (g/t)",m)},
  {id:"feed.lg.ag", label:"Low-Grade2 Ag grade, g/t", ind:1, fmt:"d2", cls:"lg2", g:1, v:feedAg(FEED_LG),
   td:D=>tD("Mill Feed LG Ag (g/t)",D), tr:trWG([["Mill Feed LG (t)","Mill Feed LG Ag (g/t)"]]), tm:m=>tM("Mill Feed LG Ag (g/t)",m)},
  {id:"feed.oth", label:"Other / unclassified feed, t", fmt:"d1", v:feedOtherT,
   td:()=>null, tr:()=>null, tm:()=>null,
   tip:"Crusher deliveries whose R4M material code is not HG / MG / LG2 / LG1 (e.g. ROM 'Unidentified', waste codes)"},
  {id:"feed.blend", label:"Blend ratio, %", fmt:"pct", v:(dd,ss)=>{const t=slot(agg(dd,ss,null),TC); return t?1:null;},
   td:D=>1, tr:D=>1, tm:m=>1},
  {id:"feed.hg.pct", label:"High-Grade ore (>6.0 g/t), %", ind:1, fmt:"pct", cls:"hg", v:feedPct(["HG"]),
   td:D=>div(tD("Mill Feed HG (t)",D)||0, tdSum(FEEDT)(D)),
   tr:D=>div(tRange("Mill Feed HG (t)",D)||0, trSum(FEEDT)(D)),
   tm:m=>div(tM("Mill Feed HG (t)",m)||0, tmSum(FEEDT)(m))},
  {id:"feed.mg.pct", label:"Mid-Grade ore (2.0-6.0 g/t), %", ind:1, fmt:"pct", cls:"mg", v:feedPct(["MG"]),
   td:D=>div(tD("Mill Feed MG (t)",D)||0, tdSum(FEEDT)(D)),
   tr:D=>div(tRange("Mill Feed MG (t)",D)||0, trSum(FEEDT)(D)),
   tm:m=>div(tM("Mill Feed MG (t)",m)||0, tmSum(FEEDT)(m))},
  {id:"feed.lg.pct", label:"Low-Grade2 ore (0.7-2.0 g/t), %", ind:1, fmt:"pct", cls:"lg2", v:feedPct(FEED_LG),
   td:D=>div(tD("Mill Feed LG (t)",D)||0, tdSum(FEEDT)(D)),
   tr:D=>div(tRange("Mill Feed LG (t)",D)||0, trSum(FEEDT)(D)),
   tm:m=>div(tM("Mill Feed LG (t)",m)||0, tmSum(FEEDT)(m))},
  {id:"feed.oth.pct", label:"Other / unclassified feed, %", ind:1, fmt:"pct",
   v:(dd,ss)=>div(feedOtherT(dd,ss), slot(agg(dd,ss,null),TC)), td:()=>null, tr:()=>null, tm:()=>null},
];
const rowById = id => MP_ROWS.find(r => r.id === id) || MF_ROWS.find(r => r.id === id);

/* ------------------------------------------------------------ formatting */
const FMT = {
  int: v => v.toLocaleString("en-US", {maximumFractionDigits: 0}),
  d1:  v => v.toLocaleString("en-US", {minimumFractionDigits: 1, maximumFractionDigits: 1}),
  d2:  v => v.toLocaleString("en-US", {minimumFractionDigits: 2, maximumFractionDigits: 2}),
  pct: v => (v * 100).toLocaleString("en-US", {maximumFractionDigits: 0}) + "%",
};
function cell(v, fmt){
  if (v === null || v === undefined || !isFinite(v)) return ["", false];
  return [FMT[fmt](v), v < -1e-9];
}

/* --------------------------------------------------------------- render */
function renderKPIs(D){
  const stdD = stdDates();
  const row = rowById;
  const feedRow = row("feed");
  const tiles = [
    ["Today movement", row("tm_t").v([D], SS()), row("tm_t").td(D), "t"],
    ["STD movement", row("tm_t").v(stdD, SS()), row("tm_t").tr(D), "t"],
    ["STD ROM ore", row("ore").v(stdD, SS()), row("ore").tr(D), "t"],
    ["STD mill feed", feedRow.v(stdD, SS()), feedRow.tr(D), "t"],
    ["STD strip ratio", row("sr_rom").v(stdD, SS()), row("sr_rom").tr(D), ""],
  ];
  const host = document.getElementById("kpis");
  host.innerHTML = "";
  const sparkDays = DATES.filter(d => d <= D).slice(-14);
  const sparkRows = [row("tm_t"), row("tm_t"), row("ore"), feedRow, row("sr_rom")];
  tiles.forEach(([k, v, tgt, unit], ti) => {
    const big = (v === null || !isFinite(v)) ? "–" :
      unit === "t" ? v.toLocaleString("en-US", {maximumFractionDigits: 0}) : FMT.d2(v);
    let sub = "no target";
    if (tgt !== null && isFinite(tgt) && tgt > 0){
      const pct = v / tgt * 100;
      const cls = unit === "t" ? (pct >= 100 ? "up" : "dn") : (pct <= 100 ? "up" : "dn");
      sub = `target ${unit === "t" ? FMT.int(tgt) : FMT.d2(tgt)} · <b class="${cls}">${pct.toFixed(0)}%</b>`;
    }
    /* 14-day sparkline of the tile's daily series */
    const sr = sparkRows[ti];
    const vals = sparkDays.map(d => sr.v([d], SS()) || 0);
    const mx = Math.max(1e-9, ...vals);
    const pts = vals.map((sv, i) => `${(i / Math.max(vals.length - 1, 1) * 86 + 2).toFixed(1)},${(22 - sv / mx * 20).toFixed(1)}`).join(" ");
    const spark = `<svg class="spark" width="90" height="24" viewBox="0 0 90 24"><polyline points="${pts}" fill="none" stroke="#d7b23a" stroke-width="1.6" stroke-linejoin="round"/></svg>`;
    host.innerHTML += `<div class="kpi"><div class="k">${k}</div><div class="v">${big}${unit ? "&thinsp;" + unit : ""}</div><div class="s">${sub}</div>${spark}</div>`;
  });
}

const SEC_COLS = ["ds", "ns", "dt", "da", "mt", "ma", "mv", "mo"];
/* stable per-row key for the layout customiser; labels that differ only by
   trailing spaces ("Au grade, g/t" / "Au grade, g/t ") must not collide */
const _rkSeen = {};
function rowKey(r){
  if (r.__rk) return r.__rk;
  const base = r.label.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
  const n = (_rkSeen[base] = (_rkSeen[base] || 0) + 1);
  return (r.__rk = n > 1 ? base + "_" + n : base);
}
function renderSection(tbodySel, rows, D){
  const mon = D.slice(0,7);
  const sh = PERIOD.shift;                          /* null | "DS" | "NS" */
  const showHelpers = document.getElementById("showHelpers").checked;
  const tb = document.querySelector(tbodySel);
  tb.innerHTML = "";
  for (const r of rows){
    if (!showHelpers && r.label.startsWith("SUMPRODUCT")) continue;
    const ds = r.v([D], ["DS"]), ns = r.v([D], ["NS"]), da = r.v([D], SS());
    const dt = r.td(D);
    const ma = r.v(stdDates(), SS()), mt = r.tr(D);
    /* targets are set per DAY, never per shift, so a variance against a single
       shift's actual is meaningless: blank it and dim the target cells */
    const mv = (sh || ma === null || mt === null || !isFinite(ma) || !isFinite(mt)) ? null : ma - mt;
    const mo = r.tm(mon);
    const tr = document.createElement("tr");
    tr.dataset.rk = rowKey(r);
    if (r.cls || r.g) tr.className = ((r.cls || "") + (r.g ? " sub" : "")).trim();
    const lbl = document.createElement("td");
    lbl.className = "lbl" + (r.ind === 2 ? " ind2" : r.ind ? " ind" : "");
    lbl.dataset.c = "lbl";
    lbl.textContent = r.label.trim();
    if (r.tip) lbl.title = r.tip;
    tr.appendChild(lbl);
    [ds, ns, dt, da, mt, ma, mv, mo].forEach((v, ci) => {
      const td = document.createElement("td");
      const [txt, neg] = cell(v, r.fmt);
      td.className = "num";
      td.dataset.c = SEC_COLS[ci];
      if (ci === 6 && txt !== ""){                  /* STD Variance: green/red ink */
        td.className += v >= 0 ? " vpos" : " vneg";
      } else if (neg){
        td.className += " neg";
      }
      if (sh){
        if (ci === 2 || ci === 4 || ci === 7){
          td.className += " dimtgt";
          td.title = "Targets are set per day, not per shift - this is the whole-day figure";
        } else if ((ci === 0 && sh === "NS") || (ci === 1 && sh === "DS")){
          td.className += " dimtgt";                /* the shift filtered out */
        }
      }
      td.textContent = txt;
      tr.appendChild(td);
    });
    tb.appendChild(tr);
  }
}

/* material class of a ROM pile = the R4M material code that dominates what was
   dumped onto it; falls back to the dump-location name (SM_29_1 / SMG-1-6 /
   1237_MG1 -> MG, SL_21_3 / SLG2-3-1 -> LG, SHG-1-4 -> HG, ST_51 -> TS, S_5 -> LG-1) */
function pileClass(p){
  const byCode = ROMCLS[p];
  if (byCode){
    let best = "", bt = 0;
    for (const c in byCode) if (byCode[c] > bt){ bt = byCode[c]; best = c; }
    if (best) return best;
  }
  const u = String(p).toUpperCase().replace(/^1237[_ ]/, "");
  let m = u.match(/^S?(HG|MG|LG|TS)/);
  if (m) return m[1];
  m = u.match(/^S([HMLT])[_\-\d]/);
  if (m) return {H: "HG", M: "MG", L: "LG", T: "TS"}[m[1]];
  if (/^S_\d/.test(u)) return "LG-1";
  m = u.match(/(?:^|[^A-Z])(HG|MG|LG)(?:[^A-Z]|$)/);
  return m ? m[1] : "";
}
/* R4M has no open/closed status for ROM-pad piles: a pile is listed when R4M
   logged a cycle dumped onto it or loaded out of it between PERIOD.start and
   the end date D. (The atlas ore inventory keeps its own build-time 30-day
   rule, build_report.ACTIVE_PILE_DAYS.) */
let ROM_ACTIVE = [];      /* last renderROM rows (RPT.romActive): the ROM table's active dump areas */
/* reclaim -> pile: an R4M load location carries the pile's own name (SMG-1-16)
   or its "-1C-" alias (load SMG-1C-21 = dump area SMG-1-21); anything else
   (F1..F4, fingers, LO215 ...) cannot be tied to a pile and is not netted */
const romNorm = k => String(k).trim().replace(/-(\d+)C-/i, "-$1-");
function romOutPile(k){ return ROM[k] ? k : (ROM[romNorm(k)] ? romNorm(k) : null); }
function romAdjFor(pile, D){       /* latest manual balance reset on or before D */
  let a = null;
  for (const x of (inputs.romadj || []))
    if (x && x.pile === pile && x.date && x.date <= D && (!a || x.date >= a.date)) a = x;
  return a;
}
/* every pile's balance as of D: received - matched reclaim since the latest manual
   adjustment; flows inside [S, D] drive `active` (the ROM table lists active piles
   only; the Master Report sums all of them by class) */
function romState(D, S){
  const rows = [];
  const outBy = {};
  let unmatched = 0;
  const unmatchedBy = {};
  for (const k in ROMOUT){
    const p = romOutPile(k);
    for (const d in ROMOUT[k]){
      const v = ROMOUT[k][d];
      if (!(v > 0) || d > D) continue;
      if (p) (outBy[p] = outBy[p] || {})[d] = (outBy[p][d] || 0) + v;
      else if (d >= S){ unmatched += v; unmatchedBy[k] = (unmatchedBy[k] || 0) + v; }
    }
  }
  for (const pile in ROM){
    const adj = romAdjFor(pile, D);
    let t = 0, au = 0, ag = 0, per = 0, out = 0, outAll = 0, last = null;
    let bal = adj ? (+adj.bal || 0) : 0;
    for (const d in ROM[pile]){
      if (d <= D && ROM[pile][d][0] > 0){
        const v = ROM[pile][d]; t += v[0]; au += v[1]; ag += v[2];
        if (d >= S) per += v[0];        /* flow: received inside the period */
        if (!adj || d > adj.date) bal += v[0];
        if (last === null || d > last) last = d;
      }
    }
    const rc = outBy[pile] || {};
    for (const d in rc){
      outAll += rc[d];
      if (d >= S) out += rc[d];         /* flow: reclaimed inside the period */
      if (!adj || d > adj.date) bal -= rc[d];
      if (last === null || d > last) last = d;
    }
    const adjIn = !!(adj && adj.date >= S);
    if (t > 0.01)
      rows.push({pile, t, au, ag, per, out, outAll, bal, adj, last, active: per > 0.01 || out > 0.01 || adjIn});
  }
  return {rows, unmatched, unmatchedBy};
}
function renderROM(D){
  const tb = document.querySelector("#tblROM tbody");
  tb.innerHTML = "";
  const dayMs = 86400000, Dms = Date.parse(D);
  const st = romState(D, PERIOD.start), unmatched = st.unmatched, unmatchedBy = st.unmatchedBy;
  const rows = st.rows.filter(r => r.active);
  rows.sort((a, b) => b.bal - a.bal || b.t - a.t);
  ROM_ACTIVE = rows;
  let T_ = 0, B_ = 0, AU_ = 0, AG_ = 0, PER_ = 0, OUT_ = 0;
  for (const r of rows){
    const gAu = div(r.au, r.t) ?? 0, gAg = div(r.ag, r.t) ?? 0;
    const bAu = Math.max(r.bal, 0) * gAu, bAg = Math.max(r.bal, 0) * gAg;
    T_ += r.t; B_ += r.bal; AU_ += bAu; AG_ += bAg; PER_ += r.per; OUT_ += r.out;
    const idle = r.last ? Math.round((Dms - Date.parse(r.last)) / dayMs) : null;
    const idleTxt = idle === null ? "" : (idle === 0 ? "today" : idle);
    const tip = (r.adj ? `set to ${FMT.d1(+r.adj.bal || 0)} t on ${r.adj.date}${r.adj.note ? " (" + noTags(r.adj.note) + ")" : ""}, then ` : "") +
                `received ${FMT.d1(r.t)} t to date, reclaimed ${FMT.d1(r.outAll)} t to date` +
                (r.bal < -0.05 ? " - reclaim exceeds receipts: set an adjustment" : "");
    const tr = document.createElement("tr");
    tr.innerHTML =
      `<td class="lbl" data-c="pile">${noTags(r.pile)}</td><td data-c="cls" style="text-align:center">${pileClass(r.pile)}</td>` +
      `<td class="num" data-c="t">${FMT.d1(r.t)}</td>` +
      `<td class="num${r.bal < -0.05 ? " neg" : ""}" data-c="bal" title="${tip}" style="font-weight:700">${FMT.d1(r.bal)}${r.adj ? ' <span title="manual adjustment">&#9998;</span>' : ""}</td>` +
      `<td class="num" data-c="per">${r.per > 0.01 ? FMT.d1(r.per) : ""}</td>` +
      `<td class="num" data-c="out">${r.out > 0.01 ? FMT.d1(r.out) : ""}</td>` +
      `<td class="num" data-c="au">${FMT.d2(gAu)}</td>` +
      `<td class="num" data-c="ag">${FMT.d2(gAg)}</td>` +
      `<td class="num" data-c="aug">${FMT.d1(bAu)}</td><td class="num" data-c="agg">${FMT.d1(bAg)}</td>` +
      `<td class="num" data-c="last">${r.last ?? ""}</td>` +
      `<td class="num" data-c="idle"${idle > 30 ? ' style="color:#b00000;font-weight:700"' : ""}>${idleTxt}</td>`;
    tb.appendChild(tr);
  }
  const tr = document.createElement("tr");
  tr.style.fontWeight = "700";
  tr.innerHTML =
    `<td class="lbl" data-c="pile">Total</td><td data-c="cls"></td><td class="num" data-c="t">${FMT.d1(T_)}</td>` +
    `<td class="num" data-c="bal">${FMT.d1(B_)}</td>` +
    `<td class="num" data-c="per">${FMT.d1(PER_)}</td>` +
    `<td class="num" data-c="out">${FMT.d1(OUT_)}</td>` +
    `<td class="num" data-c="au">${FMT.d2(div(AU_, Math.max(B_, 0)) ?? 0)}</td><td class="num" data-c="ag">${FMT.d2(div(AG_, Math.max(B_, 0)) ?? 0)}</td>` +
    `<td class="num" data-c="aug">${FMT.d1(AU_)}</td><td class="num" data-c="agg">${FMT.d1(AG_)}</td>` +
    `<td data-c="last"></td><td data-c="idle"></td>`;
  tb.appendChild(tr);
  const un = document.getElementById("romUnmatched");
  if (un){
    const top = Object.entries(unmatchedBy).sort((a, b) => b[1] - a[1]).slice(0, 6)
      .map(([k, v]) => `${noTags(k)} ${FMT.int(v)} t`).join(", ");
    un.innerHTML = unmatched > 0.5
      ? `Reclaim in the period booked at load locations that match no pile (not netted off any balance): <b>${FMT.int(unmatched)} t</b> &mdash; ${top}.`
      : "";
  }
}

/* ROM balance adjustments editor (Inputs panel). inputs.romadj = [{pile, date, bal, note}] */
function renderRomAdj(){
  const t = document.getElementById("tblRomAdj");
  if (!t) return;
  if (!Array.isArray(inputs.romadj)) inputs.romadj = [];
  const piles = Object.keys(ROM).sort();
  t.innerHTML = "<thead><tr><th>Pile (C4M dump area)</th><th>Date</th><th>Balance, t</th><th>Note</th><th></th></tr></thead>";
  const tb = document.createElement("tbody");
  const list = inputs.romadj.map((x, i) => [x, i]).sort((a, b) => String(b[0].date).localeCompare(String(a[0].date)));
  for (const [x, i] of list){
    const tr = document.createElement("tr");
    tr.innerHTML = `<td class="lbl">${noTags(x.pile)}</td><td>${noTags(x.date)}</td>` +
      `<td style="text-align:right">${FMT.d1(+x.bal || 0)}</td><td class="lbl" style="font-weight:400">${noTags(x.note || "")}</td>` +
      `<td><button type="button" title="Remove this adjustment">&times;</button></td>`;
    tr.querySelector("button").addEventListener("click", () => {
      inputs.romadj.splice(i, 1); saveInputs(); refresh(true);
    });
    tb.appendChild(tr);
  }
  const add = document.createElement("tr");
  add.innerHTML =
    `<td><input type="text" list="romPileList" placeholder="pile" style="width:130px;text-align:left"><datalist id="romPileList">` +
    piles.map(p => `<option value="${noTags(p)}">`).join("") + `</datalist></td>` +
    `<td><input type="date" style="width:130px" value="${PERIOD.end || ""}"></td>` +
    `<td><input type="number" step="any" value="0"></td>` +
    `<td><input type="text" placeholder="e.g. fed out / survey" style="width:200px;text-align:left"></td>` +
    `<td><button type="button">Add</button></td>`;
  const [ip, idt, ib, inote] = add.querySelectorAll("input");
  add.querySelector("button").addEventListener("click", () => {
    const pile = ip.value.trim(), date = idt.value, bal = parseFloat(ib.value);
    if (!pile || !date || !isFinite(bal)){ alert("Pick a pile, a date and a balance (t)."); return; }
    if (!ROM[pile] && !confirm('"' + pile + '" is not a ROM-pad dump area R4M knows. Add it anyway?')) return;
    inputs.romadj.push({pile, date, bal, note: inote.value.trim()});
    saveInputs(); refresh(true);
  });
  tb.appendChild(add);
  t.appendChild(tb);
}
/* links that open a collapsed panel and scroll to a grid (PP actuals, plan, ROM adjustments) */
function wireOpenLinks(){
  document.querySelectorAll("a[data-open]").forEach(a => {
    if (a.__wired) return; a.__wired = 1;
    a.addEventListener("click", ev => {
      const det = document.getElementById(a.dataset.open), tgt = document.querySelector(a.getAttribute("href"));
      if (!det || !tgt) return;
      ev.preventDefault();
      det.open = true;
      setTimeout(() => tgt.scrollIntoView({behavior: "smooth", block: "center"}), 30);
    });
  });
}

/* --------------------------------------------------- PP / mill helpers */
const PP_FACTOR = 1.0;   /* reference monthly history already moisture-factored */
function ppT(d){ const v = inputs.pp.t[d]; return (v === undefined || v === null) ? null : +v; }
function ppAu(d){ const v = inputs.pp.au[d]; return (v === undefined || v === null) ? null : +v; }
function monthsAll(){
  const set = new Set(Object.keys(inputs.millmon));
  for (const d of DATES) set.add(d.slice(0, 7));
  return [...set].sort();
}
function monthDates(mon){ return DATES.filter(d => d.slice(0, 7) === mon); }
function cumWeighted(tArr, gArr){
  let num = 0, den = 0;
  return tArr.map((t, i) => {
    const g = gArr[i];
    if (t !== null && t !== undefined && g !== null && g !== undefined && isFinite(g)){
      num += t * g; den += t;
    }
    return den > 0 ? num / den : null;
  });
}

/* ------------------------------------------------------------- charting */
/* Excel-replica combo charts: daily Actual/Target bars (left axis) +
   cumulative STD lines (right axis), grade lines in g/t, stacked blends. */
const C_ACT = "#2a78d6", C_TGT = "#b7bfc6", C_CUM = "#1baf7a",
      C_CUMT = "#8a8f94", C_AU = "#c9a227",
      C_HG = "#eb6834", C_MG = "#2a78d6", C_LG = "#1baf7a";
const C_LG1 = "#8c9b2e", C_OTH = "#7f8c99";   /* LG1 olive (Erdene's colour), unclassified grey (never #b7bfc6 = target tick) */

function niceMax(v){
  if (!isFinite(v) || v <= 0) return 1;
  const p = Math.pow(10, Math.floor(Math.log10(v))), n = v / p;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * p;
}
const fmtAxis = v => Math.abs(v) >= 1e6 ? (Math.round(v/1e4)/100) + "M" : Math.abs(v) >= 1e3 ? Math.round(v/1e2)/10 + "k" : "" + Math.round(v*100)/100;
const esc = s => String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;");

/* cfg: {title, cats, bars:[{name,color,values,stack}], lines:[{name,color,values,right,dash}], pct} */
function drawChart(host, cfg){
  /* chart language v3: bullet-tick targets, capped gradient bars, slot hover
     tooltip, month separators, area wash under cumulative lines, end badges */
  /* size is a contract: cfg.W/H/fs let the same cfg be re-drawn full-page.
     Label density is width-aware - with 16 seven-character month labels in a
     620-unit chart the old fixed n/16 rule overlapped every one of them. */
  const W=cfg.W||1220,H=cfg.H||300,ml=48,mt=14,anyR=(cfg.lines||[]).some(l=>l.right),mr=anyR?46:10,
        cats=cfg.cats,n=cats.length,
        FS=cfg.fs||9.5, FZ=FS/9.5, fz=v=>+(v*FZ).toFixed(1),
        catW=Math.max(1,...cats.map(c=>String(c).length))*FS*0.57+6,
        slot0=(W-ml-mr)/Math.max(n,1),
        rot=(catW>slot0&&n<=40)?-40:0,
        step=rot?1:Math.max(1,Math.ceil(catW/slot0)),
        mb=cfg.mb||(rot?Math.min(52,catW*0.72+12):22),
        pw=W-ml-mr,ph=H-mt-mb;
  const INK="#1b1e21";
  const allBars=cfg.bars||[], lines=cfg.lines||[];
  const isTgt=b=>b.tgt||b.color==="#b7bfc6";
  const ticks=allBars.filter(isTgt), bars=allBars.filter(b=>!isTgt(b));
  const groups=[];
  for (const b of bars){ const key=b.stack===undefined?"g"+groups.length:b.stack;
    let g_=groups.find(x=>x.key===key); if(!g_){g_={key,members:[]};groups.push(g_);} g_.members.push(b); }
  let lMax=cfg.lMax||0;
  for(let i=0;i<n;i++){
    for(const g_ of groups){ let s=0; for(const b of g_.members) s+=Math.max(0,b.values[i]||0); lMax=Math.max(lMax,s); }
    for(const tk of ticks) lMax=Math.max(lMax,tk.values[i]||0);
    for(const l of lines) if(!l.right) lMax=Math.max(lMax,l.values[i]||0);
  }
  lMax=cfg.pct?1:(cfg.lMax||niceMax(lMax));
  let rMax=0; for(const l of lines) if(l.right) for(const v of l.values) rMax=Math.max(rMax,v||0);
  rMax=niceMax(rMax);
  const x=i=>ml+pw*(i+0.5)/n, slotW=pw/n, yL=v=>mt+ph*(1-v/lMax), yR=v=>mt+ph*(1-v/rMax);
  const dark=c=>{const m=c.match(/^#(..)(..)(..)$/); if(!m) return c;
    return "#"+m.slice(1).map(h=>Math.max(0,Math.round(parseInt(h,16)*0.86)).toString(16).padStart(2,"0")).join("");};
  const gid=c=>"g"+c.replace("#","");
  let defs="", seen={};
  for(const b of bars) if(!seen[b.color]){ seen[b.color]=1;
    defs+=`<linearGradient id="${gid(b.color)}" x1="0" y1="0" x2="0" y2="1">`+
          `<stop offset="0" stop-color="${b.color}"/><stop offset="1" stop-color="${dark(b.color)}"/></linearGradient>`; }
  let s=`<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg"><defs>${defs}</defs>`;
  /* grid + axis labels */
  for(let g_=0;g_<=4;g_++){ const yy=mt+ph*g_/4, lv=lMax*(1-g_/4);
    s+=`<line x1="${ml}" y1="${yy}" x2="${ml+pw}" y2="${yy}" stroke="#e9ecef"/>`;
    s+=`<text x="${ml-4}" y="${yy+3.5}" text-anchor="end" font-size="${fz(9)}" fill="#5c6166">${cfg.pct?Math.round(lv*100)+"%":fmtAxis(lv)}</text>`;
    if(anyR) s+=`<text x="${ml+pw+4}" y="${yy+3.5}" font-size="${fz(9)}" fill="#5c6166">${fmtAxis(rMax*(1-g_/4))}</text>`; }
  /* unit caption from title tail (", t" / ", %", " min/cycle" ...) */
  const um=(cfg.title||"").match(/,\s*([\w³·\/%&; ]{1,14})$/);
  if(um) s+=`<text x="${ml}" y="${mt-4}" font-size="${fz(9)}" fill="#8a9097" font-style="italic">${esc(um[1])}</text>`;
  /* month separators when cats look like MM-DD */
  const isDates=typeof cats[0]==="string"&&/^\d{2}-\d{2}$/.test(cats[0]);
  if(isDates){
    for(let i=1;i<n;i++){
      if(cats[i].slice(0,2)!==cats[i-1].slice(0,2)){
        const xx=ml+pw*i/n;
        s+=`<line x1="${xx}" y1="${mt-2}" x2="${xx}" y2="${mt+ph}" stroke="#c9ccd0" stroke-width="1"/>`;
        s+=`<text x="${xx+3}" y="${mt+7}" font-size="${fz(8.5)}" fill="#8a9097" font-weight="700">M${+cats[i].slice(0,2)}</text>`;
      }
    }
  }
  /* thin, or tilt, so labels never collide; the last category is always shown,
     and the regular label before it is dropped when it would sit too close */
  const axIdx=[];
  for(let i=0;i<n;i+=step) axIdx.push(i);
  if(n && axIdx[axIdx.length-1]!==n-1){
    if(n-1-axIdx[axIdx.length-1] < step) axIdx.pop();
    axIdx.push(n-1);
  }
  for(const i of axIdx){
    const xx=x(i).toFixed(1);
    s += rot
      ? `<text class="axl" x="${xx}" y="${(mt+ph+11).toFixed(1)}" text-anchor="end" font-size="${fz(9.5)}" fill="#5c6166" transform="rotate(${rot} ${xx} ${(mt+ph+11).toFixed(1)})">${esc(cats[i])}</text>`
      : `<text class="axl" x="${xx}" y="${(mt+ph+16).toFixed(1)}" text-anchor="middle" font-size="${fz(9.5)}" fill="#5c6166">${esc(cats[i])}</text>`;
  }
  /* area wash under cumulative-looking lines */
  for(const l of lines){
    if(!(l.area||/^(STD|MTD|Cum)/i.test(l.name))) continue;
    const yf=l.right?yR:yL; let pts=[];
    for(let i=0;i<n;i++){ const v=l.values[i];
      if(v===null||v===undefined||!isFinite(v)) continue;
      pts.push([x(i),yf(v)]); }
    if(pts.length>1){
      s+=`<path d="M${pts[0][0].toFixed(1)} ${(mt+ph).toFixed(1)} `+
         pts.map(p=>`L${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" ")+
         ` L${pts[pts.length-1][0].toFixed(1)} ${(mt+ph).toFixed(1)} Z" fill="${l.color}" fill-opacity="0.09"/>`;
    }
  }
  /* bars: capped width, rounded top, square base, gradient fill */
  const nG=Math.max(groups.length,1), bw=Math.min(24,Math.max(3,slotW*0.64/nG-1));
  for(let i=0;i<n;i++){
    groups.forEach((g_,gi)=>{ let base=0, stackSum=0;   /* pct: each group is its own 100% stack */
      if(cfg.pct) for(const b of g_.members) stackSum+=Math.max(0,b.values[i]||0);
      const bx=x(i)-(nG*(bw+1))/2+gi*(bw+1)+0.5;
      for(const b of g_.members){ let v=Math.max(0,b.values[i]||0);
        if(cfg.pct) v=stackSum?v/stackSum:0; if(v<=0) continue;
        const y1=yL(base+v), hh=Math.max(yL(base)-yL(base+v),0.6);
        const r=Math.min(4,bw/2,hh), isTop=true;
        if(b.outline){     /* plan / target stacks: white fill, class-coloured outline */
          s+=`<rect x="${(bx+0.7).toFixed(1)}" y="${(y1+0.7).toFixed(1)}" width="${Math.max(bw-1.4,0.5).toFixed(1)}" height="${Math.max(hh-1.4,0.4).toFixed(1)}" fill="#fff" stroke="${b.color}" stroke-width="1.4"/>`;
        } else if(base===0&&r>0.5){
          s+=`<path d="M${bx} ${(y1+hh).toFixed(1)} L${bx} ${(y1+r).toFixed(1)} Q${bx} ${y1.toFixed(1)} ${(bx+r).toFixed(1)} ${y1.toFixed(1)} L${(bx+bw-r).toFixed(1)} ${y1.toFixed(1)} Q${(bx+bw).toFixed(1)} ${y1.toFixed(1)} ${(bx+bw).toFixed(1)} ${(y1+r).toFixed(1)} L${(bx+bw).toFixed(1)} ${(y1+hh).toFixed(1)} Z" fill="url(#${gid(b.color)})"/>`;
        } else {
          s+=`<rect x="${bx}" y="${y1.toFixed(1)}" width="${bw}" height="${hh.toFixed(1)}" fill="url(#${gid(b.color)})"/>`;
          s+=`<line x1="${bx}" y1="${y1.toFixed(1)}" x2="${(bx+bw).toFixed(1)}" y2="${y1.toFixed(1)}" stroke="#fff" stroke-width="1.6"/>`;
        }
        base+=v; } }); }
  /* bullet ticks for targets */
  for(const tk of ticks){
    for(let i=0;i<n;i++){ const v=tk.values[i];
      if(v===null||v===undefined||!isFinite(v)||v<=0) continue;
      const yy=yL(Math.min(v,lMax)), half=slotW*0.31;
      s+=`<line x1="${(x(i)-half).toFixed(1)}" y1="${yy.toFixed(1)}" x2="${(x(i)+half).toFixed(1)}" y2="${yy.toFixed(1)}" stroke="${INK}" stroke-width="2.4"/>`;
    }
  }
  /* lines + ringed points + end badges */
  const badge=[];
  for(const l of lines){ const yf=l.right?yR:yL; let path="",pts="",started=false,lastIdx=-1;
    for(let i=0;i<n;i++){ const v=l.values[i];
      if(v===null||v===undefined||!isFinite(v)){started=false;continue;}
      path+=(started?"L":"M")+x(i).toFixed(1)+" "+yf(v).toFixed(1)+" "; started=true; lastIdx=i;
      pts+=`<circle cx="${x(i).toFixed(1)}" cy="${yf(v).toFixed(1)}" r="2.4" fill="${l.color}" stroke="#fff" stroke-width="1.4"/>`; }
    s+=`<path d="${path}" fill="none" stroke="${l.color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"${l.dash?' stroke-dasharray="5 4"':""}/>`+pts;
    const finite=l.values.filter(v=>v!==null&&v!==undefined&&isFinite(v));
    const flat=finite.length>1&&finite.every(v=>v===finite[0]);
    if(lastIdx>=0&&lines.length<=3&&!flat){
      const v=l.values[lastIdx];
      const clip=x(lastIdx)+35>W;  /* anchor end at the plot edge instead of spilling out */
      badge.push(`<text x="${(x(lastIdx)+(clip?-5:5)).toFixed(1)}" y="${(yf(v)-5).toFixed(1)}"${clip?' text-anchor="end"':""} font-size="${fz(9.5)}" font-weight="700" fill="${INK}" stroke="#fff" stroke-width="3" paint-order="stroke">${fmtAxis(v)}</text>`);
    }
  }
  s+=badge.join("");
  s+=`<line x1="${ml}" y1="${mt+ph}" x2="${ml+pw}" y2="${mt+ph}" stroke="#6b747b" stroke-width="1.2"/>`;
  /* slot hover: band highlight + combined tooltip */
  s+=`<rect class="hoverband" x="0" y="${mt}" width="0" height="${ph}" fill="#1b1e21" fill-opacity="0.05" style="display:none"/>`;
  for(let i=0;i<n;i++){
    s+=`<rect class="hit" data-i="${i}" x="${(ml+pw*i/n).toFixed(1)}" y="${mt}" width="${slotW.toFixed(2)}" height="${ph}" fill="transparent"/>`;
  }
  s+=`</svg>`;
  let leg='<div class="clegend">';
  for(const b of bars) leg+=b.outline?`<span><i class="out" style="border-color:${b.color}"></i>${esc(b.name)}</span>`:`<span><i style="background:${b.color}"></i>${esc(b.name)}</span>`;
  for(const tk of ticks) leg+=`<span><i class="dash"></i>${esc(tk.name)}</span>`;
  for(const l of lines) leg+=`<span><i class="line" style="background:${l.color}"></i>${esc(l.name)}${l.right?" (right)":""}</span>`;
  leg+="</div>";
  const div=document.createElement("div"); div.className="chart";
  div.innerHTML=`<h4>${esc(cfg.title)}</h4>${leg}${s}`;
  /* identity + renderer travel with the node, so the full-page view re-draws
     the same cfg through the drawChart of whichever half owns this chart */
  /* an untitled sub-chart (the polygon detail panel draws one) still needs a
     stable key, so fall back to the host it is drawn into */
  div.dataset.ck = cfg.key || String(cfg.title||"").toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_|_$/g,"")
                   || ((host && host.id) ? host.id + ".c" : "");
  div.__cfg = cfg; div.__draw = drawChart;
  host.appendChild(div);
  /* window.TC, never a bare TC: build_report's cube-slot const TC=3 shadows it */
  if (window.TC) window.TC.registerChart(div);
  /* interactivity */
  const svg=div.querySelector("svg"), band=svg.querySelector(".hoverband");
  const fmtV=v=>(v==null||!isFinite(v))?"–":(cfg.pct?Math.round(v*1000)/10+"%":v.toLocaleString("en-US",{maximumFractionDigits:Math.abs(v)<10?2:1}));
  /* a pct chart's tooltip shows each bar's share of its own stack, not raw tonnes */
  const pctOf=b=>{ if(!cfg.pct) return b.values; const g_=groups.find(g=>g.members.includes(b));
    return b.values.map((v,i)=>{ let tt=0; for(const m of g_.members) tt+=Math.max(0,m.values[i]||0); return tt?Math.max(0,v||0)/tt:null; }); };
  const series=[...bars.map(b=>({n:b.name,c:b.color,v:pctOf(b)})),
                ...ticks.map(t=>({n:t.name,c:"#1b1e21",v:t.values})),
                ...lines.map(l=>({n:l.name,c:l.color,v:l.values}))];
  svg.querySelectorAll(".hit").forEach(hit=>{
    hit.addEventListener("mousemove",ev=>{
      const i=+hit.dataset.i;
      band.setAttribute("x",(ml+pw*i/n).toFixed(1));
      band.setAttribute("width",slotW.toFixed(2));
      band.style.display="";
      let h=`<b>${esc(String(cats[i]))}</b>`;
      for(const sr of series){
        const v=sr.v[i];
        if(v===null||v===undefined||(!v&&v!==0)) continue;
        h+=`<br><span style="color:${sr.c}">&#9632;</span> ${esc(sr.n)}: <b>${fmtV(v)}</b>`;
      }
      ctipShow(ev,h);
    });
    hit.addEventListener("mouseleave",()=>{ band.style.display="none"; ctipHide(); });
  });
  return div;
}
function ctipEl(){
  let t=document.getElementById("ctip");
  if(!t){ t=document.createElement("div"); t.id="ctip";
    t.style.cssText="position:fixed;pointer-events:none;background:rgba(27,30,33,.94);color:#fff;font-size:11.5px;padding:7px 10px;border-radius:4px;max-width:280px;display:none;z-index:60;line-height:1.5";
    document.body.appendChild(t); }
  return t;
}
function ctipShow(ev,html){ const t=ctipEl(); t.innerHTML=html; t.style.display="block";
  t.style.left=Math.min(ev.clientX+14,innerWidth-300)+"px"; t.style.top=(ev.clientY+12)+"px"; }
function ctipHide(){ ctipEl().style.display="none"; }


function rowByLabel(rows, label){ return rows.find(r => r.label === label); }
const LASTD = () => DATES[DATES.length - 1];

function dSeries(fn, days){    /* daily values; null after last data date */
  const last = LASTD();
  return days.map(d => d > last ? null : (CUBE[d] ? fn(d) : 0));
}
function cumOf(vals){
  let s = 0;
  return vals.map(v => { if (v === null || v === undefined) return null; s += v; return s; });
}
function tgtSeries(row, days){ return days.map(d => row.td(d)); }

function stdCombo(host, title, row, days, cats){
  const act = dSeries(d => row.v([d], SS()) || 0, days);
  const tgt = tgtSeries(row, days);
  drawChart(host, {title, cats,
    bars: [{name: "Daily Actual", color: C_ACT, values: act},
           {name: "Daily Target", color: C_TGT, values: tgt.map(v => v || 0)}],
    lines: [{name: "STD Actual", color: C_CUM, right: true, values: cumOf(act)},
            {name: "STD Target", color: C_CUMT, right: true, dash: true, values: cumOf(tgt.map(v => v || 0))}]});
}

function monthsInData(){
  const set = new Set(DATES.map(d => d.slice(0, 7)));
  return [...set].sort();
}
function monthDates(mon){ return DATES.filter(d => d.slice(0, 7) === mon); }

/* dates of month `m` that fall inside the reporting period (end-clipped) */
const monDatesR = m => monthDates(m).filter(d => d <= PERIOD.end);
const partialMon = m => monDatesR(m).length !== monthDates(m).length;

function buildCharts(D){
  const mon = D.slice(0, 7);
  const days = rangeDays();
  const multiMon = PERIOD.start.slice(0, 7) !== mon;
  const cats = days.map(d => multiMon ? d.slice(5) : +d.slice(8));
  const perLabel = multiMon ? PERIOD.start + " \u2192 " + D : mon;
  const mp = document.getElementById("chartsMP");
  const mf = document.getElementById("chartsMF");
  const ex = document.getElementById("chartsEXC");
  mp.innerHTML = mf.innerHTML = ex.innerHTML = "";

  stdCombo(mp, "Total Movement, t", rowById("tm_t"), days, cats);
  stdCombo(mp, "Topsoil, t", rowById("ts"), days, cats);
  stdCombo(mp, "Waste, t", rowById("waste"), days, cats);

  /* Non-ROM ore: Subgrade + MinWaste stacked */
  const sgA = dSeries(d => expitT(agg([d], SS(), ["SG"])), days);
  const mwA = dSeries(d => expitT(agg([d], SS(), ["MW"])), days);
  const smwRow = rowById("nonrom");
  const smwT = tgtSeries(smwRow, days).map(v => v || 0);
  drawChart(mp, {title: "Non-Rom Ore (Subgrade + MinWaste), t", cats,
    bars: [{name: "Subgrade", color: C_AU, values: sgA, stack: "a"},
           {name: "MinWaste", color: C_OTH, values: mwA, stack: "a"},
           {name: "Daily Target", color: C_TGT, values: smwT}],
    lines: [{name: "STD Actual", color: C_CUM, right: true,
             values: cumOf(days.map((d, i) => sgA[i] === null ? null : (sgA[i] + mwA[i])))},
            {name: "STD Target", color: C_CUMT, right: true, dash: true, values: cumOf(smwT)},
            {name: "Subgrade STD", color: C_AU, right: true, values: cumOf(sgA)},
            {name: "MinWaste STD", color: C_OTH, right: true, values: cumOf(mwA)}]});

  /* ROM ore mining tonnage by class (stacked HG / MG / LG2 / LG1) + Au grade */
  const oreRow = rowById("ore");
  const auRow = rowById("ore.au");
  const last_ = LASTD();
  const clsA = c => dSeries(d => expitT(agg([d], SS(), [c])), days);
  drawChart(mp, {title: "Ore Mining, t  &  Au g/t", cats,
    bars: [{name: "HG", color: C_HG, values: clsA("HG"), stack: "o"},
           {name: "MG", color: C_MG, values: clsA("MG"), stack: "o"},
           {name: "LG2", color: C_LG, values: clsA("LG2"), stack: "o"},
           {name: "LG1", color: C_LG1, values: clsA("LG1"), stack: "o"},
           {name: "ROM Ore Daily Target, t", color: C_TGT, values: tgtSeries(oreRow, days).map(v => v || 0)}],
    lines: [{name: "Au g/t daily actual", color: "#e07b39", right: true,
             values: dSeries(d => auRow.v([d], SS()) || null, days)},
            {name: "Au g/t daily target", color: "#e07b39", right: true, dash: true,
             values: days.map(d => auRow.td(d))},
            {name: "Au g/t STD actual", color: C_AU, right: true,
             values: days.map(d => d > last_ ? null : auRow.v(days.filter(x => x <= d), SS()) || null)},
            {name: "Au g/t cum target", color: "#1b1e21", right: true, dash: true,
             values: days.map(d => trWGx(ROMP)(d))}]});

  stdCombo(mp, "Common Mineral Production, m3", rowById("cm_m3"), days, cats);
  stdCombo(mp, "Mill tailings transport, t", rowById("tl"), days, cats);

  /* Common Mineral by month */
  const mons = monthsUpto(monthsInData());
  const cmRow = rowById("cm_m3");
  const cmM = mons.map(m => cmRow.v(monDatesR(m), SS()) || 0);
  const cmT = mons.map(m => cmRow.tm(m) || 0);
  drawChart(mp, {title: "Start To Date Common Mineral Production, m3", cats: mons,
    bars: [{name: "Monthly Actual", color: C_ACT, values: cmM},
           {name: "Monthly Target", color: C_TGT, values: cmT}],
    lines: [{name: "Cumulative Actual", color: C_CUM, right: true, values: cumOf(cmM)},
            {name: "Cumulative Target", color: C_CUMT, right: true, dash: true, values: cumOf(cmT)}]});

  /* Contained silver & Ag grade by month (mined ore, ex-rehandle) */
  const agO = mons.map(m => agg(monDatesR(m), SS(), ORE));
  const agKg = agO.map(o => expitAg(o) / 1000);
  const agTkg = mons.map(m => ROMPAG.reduce((a, [t, g]) => a + (tM(t, m) || 0) * (tM(g, m) || 0), 0) / 1000);
  const agGt = agO.map(o => div(expitAg(o), expitT(o)) || null);
  const agTgt = mons.map(m => { let nn = 0, dd = 0; for (const [t, g] of ROMPAG){
      const tv = tM(t, m) || 0; nn += tv * (tM(g, m) || 0); dd += tv; } return dd ? nn / dd : null; });
  drawChart(mp, {title: "Contained Silver, kg  &  Ag g/t", cats: mons,
    bars: [{name: "Contained Ag Actual, kg", color: C_ACT, values: agKg},
           {name: "Contained Ag Target, kg", color: C_TGT, values: agTkg}],
    lines: [{name: "Ag g/t actual", color: "#5b7fa6", right: true, values: agGt},
            {name: "Ag g/t target", color: "#1b1e21", right: true, dash: true, values: agTgt}]});

  /* Excavator performance: toggle between hourly (report day) and daily bcm/h (month) */
  const exctl = document.createElement("div");
  exctl.className = "tablectl noprint";
  exctl.innerHTML = `<label>Excavator view:
    <select id="exGran">
      <option value="hour">Hourly — report day</option>
      <option value="day">Daily bcm/h — full month</option>
    </select></label>`;
  ex.appendChild(exctl);
  const exhost = document.createElement("div");
  exhost.className = "charts three";
  ex.appendChild(exhost);
  function drawExcavators(){
    exhost.innerHTML = "";
    const eqs = Object.keys(EXH).sort();
    if ((window.__exGran || "hour") === "day"){
      const last = LASTD();
      for (const eq of eqs){
        const vals = days.map(d => { if (d > last) return null;
          const hh = exhHours(eq, d); if (!hh) return 0;
          let s = 0, c = 0; for (const v of hh){ if (v > 0){ s += v; c++; } }
          return c ? s / c : 0; });
        const tgt = days.map(d => tD(`${eq} (bcm/h)`, d) ?? (eq === "EX212" ? 140 : 330));
        drawChart(exhost, {title: `${eq} performance — bcm per hour by day, ${perLabel}`, cats,
          bars: [{name: "Actual bcm/h", color: C_ACT, values: vals}],
          lines: [{name: "Target bcm/h", color: "#1b1e21", dash: true, values: tgt}]});
      }
    } else {
      const hcats = Array.from({length: 24}, (_, h) => String(h).padStart(2, "0"));
      for (const eq of eqs){
        const vals = exhHours(eq, D) || Array(24).fill(0);
        const tgtV = tD(`${eq} (bcm/h)`, D) ?? (eq === "EX212" ? 140 : 330);
        drawChart(exhost, {title: `${eq} performance — bcm per hour, ${D}`, cats: hcats,
          bars: [{name: "Actual bcm/h", color: C_ACT, values: vals},
                 {name: "Target bcm/h", color: C_TGT, values: Array(24).fill(tgtV)}]});
      }
    }
  }
  const exSel = exctl.querySelector("#exGran");
  exSel.value = window.__exGran || "hour";
  exSel.addEventListener("change", () => { window.__exGran = exSel.value; drawExcavators(); });
  drawExcavators();

  /* ---- mill feeding charts: Monthly Plan vs Mine vs Process Plant ---- */
  const fHG = dSeries(d => slot(agg([d], SS(), ["HG"]), TC), days);
  const fMG = dSeries(d => slot(agg([d], SS(), ["MG"]), TC), days);
  const fLG = dSeries(d => slot(agg([d], SS(), FEED_LG), TC), days);
  const fL2 = dSeries(d => slot(agg([d], SS(), ["LG2"]), TC), days);
  const fL1 = dSeries(d => slot(agg([d], SS(), ["LG1"]), TC), days);
  const fOth = dSeries(d => feedOtherT([d], SS()), days);
  const feedRow = MF_ROWS[0], feedAuRow = MF_ROWS[1];
  const fT = tgtSeries(feedRow, days).map(v => v || 0);
  const mineT = dSeries(d => feedRow.v([d], SS()) || 0, days);
  const ppTs = days.map(d => ppT(d));
  const mineG = dSeries(d => { const g = feedAuRow.v([d], SS()); return g || null; }, days);
  const ppGs = days.map(d => ppAu(d));
  const budG = days.map(d => tdWG(FEEDP)(d));
  drawChart(mf, {title: "Daily Mill throughput — Monthly Plan vs Mine vs Process Plant, t & Au g/t", cats,
    bars: [{name: "Mine feed (R4M)", color: C_ACT, values: mineT},
           {name: "PP throughput", color: "#7a4dd8", values: ppTs.map(v => v ?? 0)},
           {name: "Monthly Plan", color: C_TGT, values: fT}],
    lines: [{name: "Feed head grade Au", color: C_AU, right: true, values: mineG},
            {name: "PP head grade Au", color: "#7a4dd8", right: true, dash: true, values: ppGs},
            {name: "Monthly Plan head grade Au", color: "#1b1e21", right: true, dash: true, values: budG}]});

  const budGd = days.map(d => tdWG(FEEDP)(d));
  drawChart(mf, {title: "STD Mill throughput & head grades — Monthly Plan vs Mine vs PP", cats,
    bars: [],
    lines: [{name: "Cum Mine feed, t", color: C_ACT, values: cumOf(mineT)},
            {name: "Cum PP, t", color: "#7a4dd8", values: cumOf(ppTs.map(v => v ?? 0))},
            {name: "Cum Monthly Plan, t", color: C_CUMT, dash: true, values: cumOf(fT)},
            {name: "Cum Feed grade Au", color: C_AU, right: true, values: cumWeighted(mineT, mineG)},
            {name: "Cum PP grade Au", color: "#b39ddb", right: true, dash: true, values: cumWeighted(ppTs.map(v => v ?? 0), ppGs)},
            {name: "Cum Monthly Plan grade Au", color: "#8a8f94", right: true, dash: true, values: cumWeighted(fT, budGd)}]});

  /* Mill Feed YTD by month: history from Mill Monthly inputs, live months computed */
  const ytdMons = monthsUpto(monthsAll());
  const mm = m => inputs.millmon[m] || {};
  /* the baked monthly history is a WHOLE-month figure: never use it for a month
     the reporting period only partly covers, or for a single-shift view */
  const liveOr = (m, k, fn) => { const v = mm(m)[k];
    return (!partialMon(m) && !PERIOD.shift && v !== undefined && v !== 0) ? v : fn(); };
  const ytd = ytdMons.map(m => {
    const md = monDatesR(m);
    const mt_ = () => feedRow.v(md, SS()) || 0;
    const pt_ = () => md.reduce((a, d) => a + (ppT(d) || 0), 0);
    const bt_ = () => tmSum(FEEDT)(m) || 0;
    const fg_ = () => feedAuRow.v(md, SS()) || 0;
    const pg_ = () => { let n = 0, dn = 0; for (const d of md){ const t = ppT(d), g = ppAu(d);
        if (t && g){ n += t * g; dn += t; } } return dn ? n / dn : 0; };
    const bg_ = () => { let n = 0, dn = 0; for (const [t, g] of FEEDP){ const tv = tM(t, m) || 0;
        n += tv * (tM(g, m) || 0); dn += tv; } return dn ? n / dn : 0; };
    return {bt: liveOr(m, "bt", bt_), mt: liveOr(m, "mt", mt_), pt: liveOr(m, "pt", pt_),
            bg: liveOr(m, "bg", bg_), fg: liveOr(m, "fg", fg_), pg: liveOr(m, "pg", pg_)};
  });
  drawChart(mf, {title: "Mill Feed YTD — Monthly Plan vs Mine vs PP by month, t & Au g/t", cats: ytdMons,
    bars: [{name: "Mine throughput", color: C_ACT, values: ytd.map(y => y.mt)},
           {name: "PP throughput", color: "#7a4dd8", values: ytd.map(y => y.pt)},
           {name: "Monthly Plan", color: C_TGT, values: ytd.map(y => y.bt)}],
    lines: [{name: "Feed grade Au", color: C_AU, right: true, values: ytd.map(y => y.fg || null)},
            {name: "PP grade Au", color: "#b39ddb", right: true, dash: true, values: ytd.map(y => y.pg || null)},
            {name: "Monthly Plan grade Au", color: "#1b1e21", right: true, dash: true, values: ytd.map(y => y.bg || null)}]});

  /* Start-To-Date crusher production by month: monthly bars + cumulative lines */
  drawChart(mf, {title: "Start To Date Mobile Crusher Production, t", cats: ytdMons,
    bars: [{name: "Monthly Actual", color: C_ACT, values: ytd.map(y => y.mt)},
           {name: "Monthly Plan", color: C_TGT, values: ytd.map(y => y.bt)}],
    lines: [{name: "Cum Actual", color: C_CUM, right: true, values: cumOf(ytd.map(y => y.mt))},
            {name: "Cum Monthly Plan", color: C_CUMT, right: true, dash: true, values: cumOf(ytd.map(y => y.bt))}]});

  /* Mobile Crusher Production: daily crusher deliveries stacked by R4M material
     code (LG1 / LG2 / MG / HG / other) + the Monthly Plan tick + cumulative lines */
  /* plan tick = the SOP's crushing plan ("6.1 Crushed Total Ore") when the period
     has one, else the mill-feed plan */
  const CRUSHT = ["Crushed HG (t)", "Crushed MG (t)", "Crushed LG (t)"];
  const crPlan = days.map(d => tdSum(CRUSHT)(d));
  const hasCr = days.some(d => CRUSHT.some(m => tD(m, d) !== null));
  const crT = hasCr ? crPlan : fT;
  drawChart(mf, {title: "Mobile Crusher Production, t", cats,
    bars: [{name: "LG1", color: C_LG1, values: fL1, stack: "c"},
           {name: "LG2", color: C_LG, values: fL2, stack: "c"},
           {name: "MG", color: C_MG, values: fMG, stack: "c"},
           {name: "HG", color: C_HG, values: fHG, stack: "c"},
           {name: "Other / unclassified", color: C_OTH, values: fOth, stack: "c"},
           {name: hasCr ? "Crushing plan (daily)" : "Monthly Plan (daily)", color: C_TGT, values: crT}],
    lines: [{name: "Cum Actual", color: C_CUM, right: true, values: cumOf(mineT)},
            {name: hasCr ? "Cum crushing plan" : "Cum Monthly Plan", color: C_CUMT, right: true, dash: true, values: cumOf(crT)}]});

  /* blend ratio %: per day the Monthly Plan stack (outlined, left) next to the
     actual stack (filled, right), each its own 100% - Erdene's Excel layout */
  drawChart(mf, {title: "Blend Ratio — Monthly Plan vs Actual, %", cats, pct: true,
    bars: [{name: "Plan HG", color: C_HG, outline: true, values: days.map(d => tD("Mill Feed HG (t)", d) || 0), stack: "p"},
           {name: "Plan MG", color: C_MG, outline: true, values: days.map(d => tD("Mill Feed MG (t)", d) || 0), stack: "p"},
           {name: "Plan LG", color: C_LG, outline: true, values: days.map(d => tD("Mill Feed LG (t)", d) || 0), stack: "p"},
           {name: "Actual HG", color: C_HG, values: fHG, stack: "a"},
           {name: "Actual MG", color: C_MG, values: fMG, stack: "a"},
           {name: "Actual LG", color: C_LG, values: fLG, stack: "a"},
           {name: "Actual other", color: C_OTH, values: fOth, stack: "a"}]});
}

/* ------------------------------------------------------- inputs editors */
const DAILY_METRICS = Object.keys(DEFAULTS.daily);
const MONTHLY_METRICS = Object.keys(DEFAULTS.monthly);

function monthDays(mon){
  const [y, m] = mon.split("-").map(Number);
  const n = new Date(y, m, 0).getDate();
  return Array.from({length: n}, (_, i) => `${mon}-${String(i + 1).padStart(2, "0")}`);
}
function numInput(value, oninput){
  const inp = document.createElement("input");
  inp.type = "number"; inp.step = "any";
  inp.value = (value === null || value === undefined) ? "" : value;
  inp.addEventListener("change", () => {
    oninput(inp.value === "" ? 0 : parseFloat(inp.value));
    saveInputs();
    if (!window.__pasting) refresh(false);    /* a pasted block refreshes once, at the end */
  });
  return inp;
}
function renderLCM(){
  const t = document.getElementById("tblLCM");
  t.innerHTML = "<thead><tr><th>Material Code</th><th>Material Name</th><th>Density t/bcm</th><th>Swell Factor</th></tr></thead>";
  const tb = document.createElement("tbody");
  for (const code of Object.keys(inputs.lcm)){
    const l = inputs.lcm[code];
    const tr = document.createElement("tr");
    tr.innerHTML = `<td class="lbl">${code}</td><td class="lbl" style="font-weight:400">${l.name || ""}</td>`;
    const td1 = document.createElement("td"); td1.appendChild(numInput(l.density, v => l.density = v));
    const td2 = document.createElement("td"); td2.appendChild(numInput(l.swell, v => l.swell = v));
    tr.appendChild(td1); tr.appendChild(td2);
    tb.appendChild(tr);
  }
  t.appendChild(tb);
}
function renderDailyGrid(mon){
  document.getElementById("dailyMonthLbl").textContent = mon;
  const days = monthDays(mon);
  const t = document.getElementById("tblDaily");
  let head = '<thead><tr><th>Metric</th><th title="Fill helpers">fill</th>';
  for (const d of days) head += `<th>${d.slice(8)}</th>`;
  t.innerHTML = head + "</tr></thead>";
  const tb = document.createElement("tbody");
  for (const metric of DAILY_METRICS){
    const tr = document.createElement("tr");
    const lbl = document.createElement("td"); lbl.className = "lbl"; lbl.textContent = metric;
    tr.appendChild(lbl);
    /* "unclear how to enter the plan numbers" (request 03): one number across the
       whole month, or a monthly total spread evenly over its days */
    const tools = document.createElement("td");
    tools.className = "fillrow";
    tools.innerHTML = '<button type="button" title="Set every day of the month to one value">=</button>' +
                      '<button type="button" title="Spread a monthly total evenly over the days">&#931;</button>';
    const fb = tools.querySelectorAll("button");
    fb[0].addEventListener("click", () => fillDaily(metric, mon, "flat"));
    fb[1].addEventListener("click", () => fillDaily(metric, mon, "spread"));
    tr.appendChild(tools);
    for (const d of days){
      const td = document.createElement("td");
      const cur = inputs.daily[metric] ? inputs.daily[metric][d] : undefined;
      td.appendChild(numInput(cur === undefined ? null : cur, v => {
        (inputs.daily[metric] = inputs.daily[metric] || {})[d] = v;
      }));
      tr.appendChild(td);
    }
    tb.appendChild(tr);
  }
  t.appendChild(tb);
}
function fillDaily(metric, mon, how){
  const days = monthDays(mon);
  const q = how === "flat"
    ? prompt('Set "' + metric + '" to this value on every day of ' + mon + ":", "")
    : prompt('Monthly total for "' + metric + '" in ' + mon + " — spread evenly over " +
             days.length + " days:", "");
  if (q === null || String(q).trim() === "") return;
  const v = parseFloat(String(q).replace(/[, ]/g, ""));
  if (!isFinite(v)){ alert("That is not a number."); return; }
  const per = how === "flat" ? v : v / days.length;
  const m = (inputs.daily[metric] = inputs.daily[metric] || {});
  for (const d of days) m[d] = Math.round(per * 1000) / 1000;
  saveInputs(); refresh(true);
}
function renderPPGrid(mon){
  document.getElementById("ppMonthLbl").textContent = mon;
  const days = monthDays(mon);
  const t = document.getElementById("tblPP");
  let head = "<thead><tr><th>Metric</th>";
  for (const d of days) head += `<th>${d.slice(8)}</th>`;
  t.innerHTML = head + "</tr></thead>";
  const tb = document.createElement("tbody");
  for (const [label, key] of [["PP throughput (t)", "t"], ["PP head grade Au (g/t)", "au"]]){
    const tr = document.createElement("tr");
    const lbl = document.createElement("td"); lbl.className = "lbl"; lbl.textContent = label;
    tr.appendChild(lbl);
    for (const d of days){
      const td = document.createElement("td");
      const cur = inputs.pp[key][d];
      td.appendChild(numInput(cur === undefined ? null : cur, v => { inputs.pp[key][d] = v; }));
      tr.appendChild(td);
    }
    tb.appendChild(tr);
  }
  t.appendChild(tb);
}
function renderMillMon(){
  const t = document.getElementById("tblMillMon");
  const mons_ = monthsAll();
  const cols = [["bt","Monthly Plan t"],["mt","Mine t"],["pt","PP t"],["bg","Monthly Plan Au"],["fg","Feed Au"],["pg","PP Au"]];
  t.innerHTML = "<thead><tr><th>Month</th>" + cols.map(c => `<th>${c[1]}</th>`).join("") + "</tr></thead>";
  const tb = document.createElement("tbody");
  for (const m of mons_){
    const tr = document.createElement("tr");
    const lbl = document.createElement("td"); lbl.className = "lbl"; lbl.textContent = m;
    tr.appendChild(lbl);
    for (const [k] of cols){
      const td = document.createElement("td");
      const cur = (inputs.millmon[m] || {})[k];
      td.appendChild(numInput(cur === undefined ? null : cur, v => {
        (inputs.millmon[m] = inputs.millmon[m] || {})[k] = v;
      }));
      tr.appendChild(td);
    }
    tb.appendChild(tr);
  }
  t.appendChild(tb);
}
function renderMonthlyGrid(mon){
  document.getElementById("monthLbl").textContent = mon;
  const t = document.getElementById("tblMonthly");
  t.innerHTML = "<thead><tr><th>Metric</th><th>Target</th></tr></thead>";
  const tb = document.createElement("tbody");
  for (const metric of MONTHLY_METRICS){
    const tr = document.createElement("tr");
    const lbl = document.createElement("td"); lbl.className = "lbl"; lbl.textContent = metric;
    tr.appendChild(lbl);
    const td = document.createElement("td");
    const cur = inputs.monthly[metric] ? inputs.monthly[metric][mon] : undefined;
    td.appendChild(numInput(cur === undefined ? null : cur, v => {
      (inputs.monthly[metric] = inputs.monthly[metric] || {})[mon] = v;
    }));
    tr.appendChild(td);
    tb.appendChild(tr);
  }
  t.appendChild(tb);
}

__MANUAL_JS__
__NOTES_JS__
__INPUTS_XLSX_JS__
__MASTER_JS__

/* --------------------------------------------------------------- wiring */
let lastMonth = null;
/* the shift filter reaches R4M cycle actuals only - say so rather than let a
   half-day actual sit silently next to a whole-day target */
function updateShiftNote(){
  const el = document.getElementById("shiftNote");
  if (!el) return;
  if (!PERIOD.shift){ el.hidden = true; el.innerHTML = ""; return; }
  el.hidden = false;
  el.innerHTML = (PERIOD.shift === "DS" ? "Day shift (DS) only" : "Night shift (NS) only") +
    " &mdash; filters R4M cycle actuals. Targets, plant actuals, ROM inventory and the " +
    "analytics sections below remain whole-day.";
}
/* Courtesy only: when the report period sits inside one calendar month, point the
   mine map's own Period control at that month. The atlas payload is pre-aggregated
   per month / ISO week / day at build time and carries no shift dimension, so an
   arbitrary range (or a single shift) cannot drive it - it stays independent. */
function syncMapPeriod(){
  const sel = document.getElementById("periodSel");     /* atlas half only */
  if (!sel || PERIOD.start.slice(0, 7) !== PERIOD.end.slice(0, 7)) return;
  const m = PERIOD.end.slice(0, 7);
  if (sel.value === m || ![...sel.options].some(o => o.value === m)) return;
  sel.value = m;
  sel.dispatchEvent(new Event("change"));
}
function refresh(rebuildInputs){
  const endEl = document.getElementById("dateSel"), stEl = document.getElementById("startSel");
  const D = endEl.value;
  if (stEl.value > D) stEl.value = D;               /* clamp an inverted range */
  PERIOD.start = stEl.value;
  PERIOD.end = D;
  PERIOD.shift = document.getElementById("shiftSel").value || null;
  const mon = inMon();
  updateShiftNote();
  renderKPIs(D);
  renderSection("#tblMP tbody", MP_ROWS, D);
  renderSection("#tblMF tbody", MF_ROWS, D);
  renderROM(D);
  buildCharts(D);
  renderManual();
  ndRender();
  mrRenderIfShown();
  if (window.TC) window.TC.sweep();
  if (rebuildInputs || mon !== lastMonth){
    renderLCM(); renderDailyGrid(mon); renderMonthlyGrid(mon);
    renderPPGrid(mon); renderMillMon(); renderRomAdj();
    renderManualGrids(mon);
    wirePasteGrids();
    renderInMon();
    lastMonth = mon;
  }
  syncMapPeriod();
  if (window.ATL && window.ATL.refreshInv) window.ATL.refreshInv();
  /* the atlas analytics charts follow the report period too (Erdene 2026-10-17) */
  if (window.ATL && window.ATL.redrawCharts) window.ATL.redrawCharts();
}

function init(){
  const sel = document.getElementById("dateSel");
  const stSel = document.getElementById("startSel");
  const shSel = document.getElementById("shiftSel");
  sel.innerHTML = stSel.innerHTML = "";
  for (const d of DATES){
    const o = document.createElement("option");
    o.value = d; o.textContent = d;
    sel.appendChild(o);
    const o2 = document.createElement("option");
    o2.value = d; o2.textContent = d;
    stSel.appendChild(o2);
  }
  const lastD = DATES[DATES.length - 1];
  sel.value = lastD;
  /* default period = the end date's month, i.e. exactly the old month-to-date window */
  stSel.value = DATES.find(d => d.slice(0,7) === lastD.slice(0,7)) || DATES[0];
  sel.addEventListener("change", () => refresh(false));
  stSel.addEventListener("change", () => refresh(false));
  shSel.addEventListener("change", () => refresh(false));
  document.getElementById("showHelpers").addEventListener("change", () => refresh(false));
  document.getElementById("dataThrough").textContent = DATES[DATES.length - 1];

  document.getElementById("btnReset").addEventListener("click", () => {
    if (!confirm("Discard your unpublished edits and go back to the published plan?")) return;
    localStorage.removeItem(LS_KEY);
    inputs = loadInputs();
    refresh(true);
    renderPubBar();
  });
  document.getElementById("btnPublish").addEventListener("click", async () => {
    /* the plan only (no engineering notes/photos). POSTed to the publish
       service next to the page; where there is none, downloaded as a file for
       the manual route (copy into daily_report, rebuild, upload). */
    const now = new Date(), p2 = n => String(n).padStart(2, "0");
    const stamp = `${now.getFullYear()}-${p2(now.getMonth() + 1)}-${p2(now.getDate())} ${p2(now.getHours())}:${p2(now.getMinutes())}`;
    const out = Object.assign({}, inputs, {__publishedAt: stamp});
    delete out.__base;
    const body = JSON.stringify(out);
    const bar = document.getElementById("pubBar");
    let key = null;
    try{ key = localStorage.getItem(PUB_KEY_LS); }catch(e){}
    if (location.protocol !== "file:"){
      if (!key){
        key = prompt("Publish key (ask the report owner; this browser remembers it):");
        if (!key) return;
        key = key.trim();
      }
      /* closed months (before the running one) are locked: changing them needs the password typed
         for this publish (never remembered); the service checks it again (423 = locked) */
      let unlock = null;
      const post = async () => {
        try{
          const hd = {"Content-Type": "application/json", "X-Publish-Key": key};
          if (unlock) hd["X-Closed-Unlock"] = unlock;
          return await fetch(PUB_POST, {method: "POST", credentials: "same-origin", headers: hd, body});
        }catch(e){ return null; }
      };
      const askUnlock = async months => {
        unlock = await pubAskPassword("This publish changes closed month" + (months.length > 1 ? "s " : " ") +
          months.join(", ") + ". Closed months are locked \u2014 enter the password to publish the change.");
        return !!unlock;
      };
      const closedNow = pubClosedChanges(DEFAULTS, out);
      if (closedNow.length && !(await askUnlock(closedNow))){
        bar.className = "pubbar prev"; bar.textContent = "Not published \u2014 closed months stay locked. Your edits are kept in this browser.";
        return;
      }
      bar.className = "pubbar local"; bar.textContent = "Publishing\u2026";
      let resp = await post();
      if (resp && resp.status === 423 && !unlock){          /* the server saw closed changes this page did not */
        let months = [];
        try{ months = (await resp.json()).months || []; }catch(e){}
        if (!(await askUnlock(months))){
          bar.className = "pubbar prev"; bar.textContent = "Not published \u2014 closed months stay locked. Your edits are kept in this browser.";
          return;
        }
        resp = await post();
      }
      if (resp && resp.status === 423){
        bar.className = "pubbar prev"; bar.textContent = "Password rejected \u2014 closed months stay locked; nothing was published. Your edits are kept in this browser.";
        return;
      }
      if (resp && resp.ok){
        try{ localStorage.setItem(PUB_KEY_LS, key); }catch(e){}
        localStorage.removeItem(LS_KEY); localStorage.removeItem(LS_PREV); pubSetAside = false;
        await fetchPublished();              /* re-read exactly what the server holds now */
        inputs = loadInputs(); refresh(true); renderPubBar();
        bar.className = "pubbar";
        bar.innerHTML = `<b>Published ${noTags(PUB.at || stamp)}.</b> Everyone sees these numbers from their next reload of the report.`;
        return;
      }
      if (resp && (resp.status === 401 || resp.status === 403)){
        try{ localStorage.removeItem(PUB_KEY_LS); }catch(e){}
        bar.className = "pubbar prev";
        bar.textContent = "Publish key rejected \u2014 press Publish again and re-enter it.";
        return;
      }
      if (resp && resp.status !== 404 && resp.status !== 405){
        bar.className = "pubbar prev";
        bar.textContent = `Publish failed (HTTP ${resp.status}) \u2014 nothing changed; try again or tell the report owner.`;
        return;
      }
    }
    const blob = new Blob([body], {type: "application/json"});
    const aEl = document.createElement("a");
    aEl.href = URL.createObjectURL(blob);
    aEl.download = "published_inputs.json";
    aEl.click();
    bar.className = "pubbar local";
    bar.innerHTML = `<b>No publish service on this copy of the report \u2014 saved published_inputs.json (${stamp}) instead.</b> Copy it into the report&rsquo;s <code>daily_report</code> folder, run <code>python build_combined.py</code>, and upload the new <code>daily_report_v3.html</code>. Until then only this browser sees these numbers.`;
  });
  wireManual();
  wireNotes();
  wireOpenLinks();
  renderPubBar();
  document.getElementById("inMonSel").addEventListener("change", e => { IN_MON = e.target.value; refresh(true); });
  document.getElementById("btnCopyMon").addEventListener("click", () => {
    const mon = inMon();
    const [y, m] = mon.split("-").map(Number);
    const nxt = new Date(Date.UTC(y, m, 1)).toISOString().slice(0, 7);
    let n = 0;
    for (const metric in inputs.daily){
      const src = inputs.daily[metric];
      for (const d of monthDays(mon)){
        if (src[d] === undefined || src[d] === null) continue;
        src[nxt + d.slice(7)] = src[d];
        n++;
      }
    }
    saveInputs(); refresh(true);
    alert(n ? ("Copied " + n + " target value(s) from " + mon + " to " + nxt + ".")
            : ("Nothing to copy: " + mon + " has no daily targets yet."));
  });
  document.getElementById("btnXlsx").addEventListener("click", xlDownloadTemplate);
  document.getElementById("btnXlsxIn").addEventListener("click",
    () => document.getElementById("fileXlsx").click());
  document.getElementById("fileXlsx").addEventListener("change", ev => {
    const f = ev.target.files[0];
    ev.target.value = "";
    if (f) xlImportFile(f);
  });
  wireMaster();

  refresh(true);
}
/* Automation surface. The report's own state lives inside an IIFE in the combined
   build, so anything that has to be driven from outside - the PDF renderer, the
   host application, the Playwright checks - goes through here. build_combined
   extends this object rather than replacing it. */
function start(){ fetchPublished().finally(() => { inputs = loadInputs(); init(); }); }
window.RPT = {
  refresh: refresh,
  cube: () => CUBE, dates: () => DATES, inputs: () => inputs, save: saveInputs,
  period: () => ({start: PERIOD.start, end: PERIOD.end, shift: PERIOD.shift}),
  romActive: () => ROM_ACTIVE,
  setPeriod: (start, end, shift) => {
    if (end) document.getElementById("dateSel").value = end;
    if (start) document.getElementById("startSel").value = start;
    if (shift !== undefined) document.getElementById("shiftSel").value = shift || "";
    refresh(false);
  },
  md: {get: mdGet, set: mdSet, auxKey: auxKey, defs: mdDefs, dates: mdDates,
       machines: auxMachines},
  notes: {render: ndRender, add: ndAddNote, accept: ndAcceptFiles, tx: ndTx},
  master: {render: renderMaster, show: mrShow, setDate: mrSetDate, date: () => MR_D,
           periods: () => (MR_P || mrPeriods(MR_D || mrDefaultDate())),
           value: (id, wk) => { if (!MR_P) renderMaster(); return mrVal(id, wk); },
           plan: (id, key) => mrPlan(MR_BY_ID[id], key), rows: () => MR_SPEC,
           preparePrint: mrPreparePrint, endPrint: mrEndPrint, fit: mrFit, defaultDate: mrDefaultDate,
           printHtml: mrPrintHtml, print: mrPrint}
};
start();
</script>
<script>
__XLSX_JS__
</script>
<script>
__CUSTOM_JS__
</script>
</body>
</html>
"""

# One source for both build paths: build_combined cuts TEMPLATE at the first
# <script>, so the CSS above travels with the report stylesheet while the
# trailing <script> block is dropped and re-emitted by build_combined itself.
TEMPLATE = (TEMPLATE
            .replace("__MANUAL_CSS__", MANUAL_CSS)
            .replace("__MANUAL_SECTION_HTML__", MANUAL_SECTION_HTML)
            .replace("__MANUAL_INPUTS_HTML__", MANUAL_INPUTS_HTML)
            .replace("__MANUAL_JS__", MANUAL_JS.replace("__AUX_TYPES__", json.dumps(AUX_TYPES)))
            .replace("__INPUTS_XLSX_JS__", INPUTS_XLSX_JS)
            .replace("__NOTES_CSS__", NOTES_CSS)
            .replace("__NOTES_SECTION_HTML__", NOTES_SECTION_HTML)
            .replace("__NOTES_JS__", NOTES_JS)
            .replace("__XLSX_CSS__", XLSX_CSS)
            .replace("__XLSX_JS__", XLSX_JS)
            .replace("__CUSTOM_CSS__", CUSTOM_CSS)
            .replace("__CUSTOM_JS__", CUSTOM_JS)
            .replace("__MASTER_CSS__", MASTER_CSS)
            .replace("__MASTER_SECTION_HTML__", MASTER_SECTION_HTML)
            .replace("__MASTER_INPUTS_HTML__", MASTER_INPUTS_HTML)
            .replace("__MASTER_JS__", master_js()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true",
                    help="refresh dashboard/data from the R4M API first")
    args = ap.parse_args()

    if args.fetch:
        print("fetching from R4M API ...")
        rc = subprocess.call([sys.executable,
                              os.path.join(HERE, "fetch_data.py")])
        if rc != 0:
            print("fetch failed - building from cached parquet", file=sys.stderr)

    df = load_joined()
    cube = build_cube(df)
    rom = build_rom(df)
    defaults = apply_published(read_inputs())
    exh = build_exh(df, defaults.get("lcm"))

    dates = sorted(cube)
    au_cov, ag_cov = df.attrs["au_cov"], df.attrs["ag_cov"]
    grade_note = (f"Polygon grade coverage of hauled tonnage: Au {au_cov:.0f}% / Ag {ag_cov:.0f}% "
                  f"&mdash; Au/Ag cells read low where the cube's polygons carry no grade")
    if au_cov < 50:
        grade_note = ('<b style="display:inline-block;background:#fbe7e7;color:#a30f0f;'
                      'padding:2px 9px;border-radius:4px;margin-top:4px;font-weight:600">&#9888; ' + grade_note +
                      " (most polygons currently have NO gold grade in R4M &mdash; ask geology to populate polygon_grades)</b>")
    print(f"cycles: {len(df):,}   dates: {dates[0]} .. {dates[-1]}   "
          f"ROM piles: {len(rom)}   Au coverage: {au_cov:.0f}%   Ag coverage: {ag_cov:.0f}%")

    j = lambda o: json.dumps(o, separators=(",", ":"), ensure_ascii=False)
    html = (TEMPLATE
            .replace("__CUBE__", j(cube))
            .replace("__ROM__", j(rom))
            .replace("__ROMCLS__", j(build_romcls(df)))
            .replace("__ROMOUT__", j(build_romout(df)))
            .replace("__EXH__", j(exh))
            .replace("__DEFAULTS__", j(defaults))
            .replace("__BUILT_AT__", dt.datetime.now().strftime("%Y-%m-%d %H:%M"))
            .replace("__LOGO_B64__", LOGO_B64)
            .replace("__GRADE_COV__", grade_note))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"wrote {OUT}  ({os.path.getsize(OUT)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
