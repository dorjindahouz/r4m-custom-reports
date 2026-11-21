"""Pull operator checklists and KPI inputs from the C4M (FMS) database into operator_kpi/data/,
one shift date at a time (same cache model as overspeed/fetch_overspeed.py).

Per shift date, cached under data/days/<date>/:
  checklists.parquet       one row per pre-start checklist form (equipment, operator, status, counts)
  checklist_items.parquet  one row per item answer (is_ok, defect)
  loads.parquet            haul cycles rolled up per shift x equipment x operator (sums + counts per phase),
                           truck rows (role haul) and loader rows (role load)
  status.parquet           equipment status hours per shift x equipment x operator x status detail
  logins.parquet           operator login sessions (for over-speed attribution)
Once per run (dims): dim_checklist_items, dim_equipment, dim_workers, dim_status.
The cached days inside [--from, --to] are concatenated into data/<name>.parquet (+ .csv twins)
and data/meta.json. Review status of a form changes days after it is filed, so the newest
--refresh-days (default 7) are always re-pulled.

Run:  python fetch_operator_kpi.py [--from 2026-07-01] [--to YYYY-MM-DD] [--refresh-days 7] [--shift-start 7]
                                   [--form-shift-start 06:20]
Dates are SHIFT dates: shift day D runs from D 07:00 to D+1 07:00 (DS 07-19, NS 19-07). Checklists are
dated from 06:20 (DS 06:20-18:20, NS 18:20-06:20): operators file the pre-start form in the 20-40 min before the
shift, so a 06:50 form belongs to that day's day shift, not to the previous shift day (user, 2026-10-26).
Reuses ../overspeed/db.py (SSH + server-side psql) and ../overspeed/env.py (.env); never prints secrets.
"""
import argparse
import datetime as dt
import json
import os
import sys
import time

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "overspeed"))
import db  # noqa: E402

SQL = os.path.join(HERE, "sql")
DATA = os.path.join(HERE, "data")
HISTORY_START = "2026-07-01"

DAILY = ["checklists", "checklist_items", "loads", "status", "logins"]
FORMS = {"checklists", "checklist_items"}     # dated with --form-shift-start instead of --shift-start
SQL_OF = {"loads": "loads_by_operator_shift", "status": "status_by_operator_shift"}   # cache name -> sql file
DIMS = ["dim_checklist_items", "dim_equipment", "dim_workers", "dim_status"]
# columns that stay text; everything else is coerced to numbers (the SSH rung returns strings)
TEXT = {"created_ts", "shift_date", "shift", "equipment", "model", "fleet", "operator", "operator_login",
        "crew", "description", "form_status", "status_ts", "review_comment", "role", "login_ts",
        "logout_ts", "section", "item", "name_group", "status_name"}
BOOLS = {"is_ok", "is_struct", "deleted"}


def tidy(df):
    for c in df.columns:
        if c in BOOLS:
            df[c] = df[c].map({"t": True, "f": False, True: True, False: False})
        elif c not in TEXT:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def query(sql_name, params=None):
    sql = open(os.path.join(SQL, f"{SQL_OF.get(sql_name, sql_name)}.sql"), encoding="utf-8").read()
    return tidy(db.run_query(sql, params))


def daterange(a, b):
    d = dt.date.fromisoformat(a)
    while d <= dt.date.fromisoformat(b):
        yield d.isoformat()
        d += dt.timedelta(days=1)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="date_from", default=HISTORY_START)
    ap.add_argument("--to", dest="date_to", default=None, help="last shift date (default: the one running now)")
    ap.add_argument("--refresh-days", type=int, default=7, help="re-pull the newest N shift dates even if cached")
    ap.add_argument("--shift-start", type=int, default=7, help="hour the day shift starts")
    ap.add_argument("--form-shift-start", default="06:20", help="HH:MM the checklist day starts (forms are filed before the shift)")
    ap.add_argument("--force", action="store_true", help="ignore the cache and re-pull every day")
    ap.add_argument("--out", default=DATA, help="output directory (default operator_kpi/data)")
    a = ap.parse_args()
    # default --to = the shift date running NOW (from the earlier of the two day starts), so today's forms are
    # on the page as soon as a refresh runs; the newest --refresh-days are always re-pulled, which completes it later
    hh, _, mm = a.form_shift_start.partition(":")
    form_min = int(hh) * 60 + int(mm or 0)
    if a.date_to is None:
        start = min(a.shift_start * 60, form_min)
        a.date_to = (dt.datetime.now() - dt.timedelta(minutes=start)).date().isoformat()

    out_dir = a.out
    days_dir = os.path.join(out_dir, "days")
    os.makedirs(days_dir, exist_ok=True)
    base = {"shift_start": a.shift_start}
    days = list(daterange(a.date_from, a.date_to))
    refresh = set(days[-a.refresh_days:]) if a.refresh_days > 0 else set()
    print(f"C4M operator KPI fetch  shift dates {a.date_from} .. {a.date_to} ({len(days)} days)")

    todo = [d for d in days if a.force or d in refresh
            or not all(os.path.exists(os.path.join(days_dir, d, f"{n}.parquet")) for n in DAILY)]
    print(f"  cached: {len(days) - len(todo)} days   to pull: {len(todo)} days   + dimensions")
    print(f"  connection: {db.connect()} -> {db.current_db()}")
    db.switch_db("ControlSenseDB")
    t_all = time.time()
    for i, d in enumerate(todo, 1):
        ddir = os.path.join(days_dir, d)
        os.makedirs(ddir, exist_ok=True)
        t = time.time()
        params = dict(base, date_from=d, date_to=d)
        n = {}
        for name in DAILY:
            df = query(name, dict(params, day_start_min=form_min) if name in FORMS else params)
            df.to_parquet(os.path.join(ddir, f"{name}.parquet"), index=False)
            n[name] = len(df)
        print(f"  [{i:>3}/{len(todo)}] {d}  {n}  ({time.time() - t:4.1f} s)")
    if todo:
        print(f"  pulled {len(todo)} days in {(time.time() - t_all) / 60:.1f} min")

    counts = {}
    for name in DIMS:                       # dimensions: always fresh, small
        df = query(name)
        df.to_parquet(os.path.join(out_dir, f"{name}.parquet"), index=False)
        counts[name] = len(df)
    print(f"  dimensions: { {k: v for k, v in counts.items()} }")

    for name in DAILY:                      # concatenate the cached days of the period
        parts = [pd.read_parquet(os.path.join(days_dir, d, f"{name}.parquet")) for d in days
                 if os.path.exists(os.path.join(days_dir, d, f"{name}.parquet"))]
        nonempty = [p for p in parts if len(p)]
        df = pd.concat(nonempty, ignore_index=True) if nonempty else (parts[0] if parts else pd.DataFrame())
        if name == "logins" and len(df):     # the per-day margin re-selects sessions: keep one copy
            df = df.drop_duplicates(subset=["id_worker", "id_equipo", "login_ts"], keep="last")
        df.to_parquet(os.path.join(out_dir, f"{name}.parquet"), index=False)
        df.to_csv(os.path.join(out_dir, f"{name}.csv"), index=False, encoding="utf-8-sig")
        counts[name] = len(df)
        print(f"  {name:<16} {len(df):>7} rows  ({len(parts)} days)")

    meta = {"date_from": a.date_from, "date_to": a.date_to, "shift_start": a.shift_start,
            "form_shift_start": a.form_shift_start, "rows": counts, "days": len(days), "pulled_now": todo,
            "fetched_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source": "C4M ControlSenseDB @ " + (db.env.get("C4M_DB_IP_ADDRESS") or "?")}
    json.dump(meta, open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8"), indent=2)
    print("  meta.json written")


if __name__ == "__main__":
    sys.exit(main())
