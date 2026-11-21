"""Pull over-speed data from the C4M (FMS) database into overspeed/data/, one shift date at a time.

Each shift date is queried on its own and cached under data/days/<date>/ so a long history is
cheap to keep current: a run only queries the days that are missing plus the last
--refresh-days (telemetry lands 1-3 h late, so the newest days are re-pulled). The cached days
inside [--from, --to] are then concatenated into the files the page is built from:

  data/episodes_s<G>.parquet  over-speed episodes derived from raw 2 s GPS telemetry against the
                              MINE POLICY (--limit-flat on normal roads, --limit-steep on steep
                              roads), one file per steep-road definition G in --steep-grades
                              (|GPS grade| >= G %)
  data/profile.parquet        speed profile per shift date x shift x truck x load state x grade band
  data/events.parquet         (only with --with-register) C4M's own Speed Limit Register, for reference
plus .csv twins and meta.json (period, parameters, row counts, fetch time).

Run:  python fetch_overspeed.py [--from 2026-07-01] [--to YYYY-MM-DD] [--refresh-days 3]
                                [--limit-flat 40] [--limit-steep 30] [--steep-grades 12]
                                [--min-duration 4] [--grade-window 5] [--shift-start 7]
Default period = HISTORY_START (2026-07-01) .. the shift date running NOW (07:00 -> 07:00), so a refresh
shows today's shift so far (telemetry lags 1-3 h); the newest --refresh-days are re-pulled every run,
which completes the open day later (3, so a morning refresh's half night shift is completed too).
Dates are SHIFT dates: shift day D runs from D 07:00 to D+1 07:00 (DS 07-19, NS 19-07).
"""
import argparse
import datetime as dt
import json
import os
import sys
import time

import pandas as pd

import db

HERE = os.path.dirname(os.path.abspath(__file__))
SQL = os.path.join(HERE, "sql")
DATA = os.path.join(HERE, "data")
DAYS = os.path.join(DATA, "days")
HISTORY_START = "2026-07-01"

NUM_EVENTS = ["id", "id_segment", "limit_kmh", "speed_kmh", "avg_speed_kmh", "over_kmh",
              "duration_s", "id_cycle", "x", "y", "z", "segment_pct_start", "segment_pct_end"]
NUM_EPISODES = ["id_segment", "grade_pct", "limit_kmh", "speed_kmh", "avg_speed_kmh", "over_kmh",
                "duration_s", "x", "y", "z"]
NUM_PROFILE = ["grade_band", "sec_total", "sec_moving", "max_kmh", "p99_kmh", "avg_moving_kmh",
               "sec_gt30", "sec_gt35", "sec_gt40", "sec_gt45", "sec_gt50"]
BOOLS = ["is_loaded", "acknowledged"]


def tidy(df, numeric):
    """The SSH rung returns everything as text; coerce to proper dtypes."""
    for c in numeric:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in BOOLS:
        if c in df:
            df[c] = df[c].map({"t": True, "f": False, True: True, False: False})
    return df


def query(sql_name, params, numeric):
    sql = open(os.path.join(SQL, f"{sql_name}.sql"), encoding="utf-8").read()
    return tidy(db.run_query(sql, params), numeric)


def daterange(a, b):
    d = dt.date.fromisoformat(a)
    while d <= dt.date.fromisoformat(b):
        yield d.isoformat()
        d += dt.timedelta(days=1)


def main():
    current_shift_date = (dt.datetime.now() - dt.timedelta(hours=7)).date()   # shift day = 07:00 -> 07:00
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="date_from", default=HISTORY_START)
    ap.add_argument("--to", dest="date_to", default=current_shift_date.isoformat(), help="last shift date (default: the one running now)")
    ap.add_argument("--refresh-days", type=int, default=3, help="re-pull the newest N shift dates even if cached")
    ap.add_argument("--limit-flat", type=float, default=40.0, help="policy limit on normal roads, km/h")
    ap.add_argument("--limit-steep", type=float, default=30.0, help="policy limit on steep roads, km/h")
    ap.add_argument("--steep-grades", default="10",
                    help="comma list of |grade| %% values that define a steep road; one episode file each")
    ap.add_argument("--min-duration", type=int, default=4, help="drop telemetry episodes shorter than N s")
    ap.add_argument("--grade-window", type=int, default=5, help="half-window in samples (x2 s) for the GPS grade")
    ap.add_argument("--shift-start", type=int, default=7, help="hour the day shift starts")
    ap.add_argument("--with-register", action="store_true", help="also pull C4M's own Speed Limit Register (events.parquet)")
    ap.add_argument("--force", action="store_true", help="ignore the cache and re-pull every day")
    ap.add_argument("--out", default=DATA, help="output directory (default overspeed/data)")
    a = ap.parse_args()

    out_dir = a.out
    days_dir = os.path.join(out_dir, "days")
    os.makedirs(days_dir, exist_ok=True)
    grades = [int(g) for g in a.steep_grades.split(",") if g.strip()]
    base = {"shift_start": a.shift_start, "limit_flat": a.limit_flat, "limit_steep": a.limit_steep,
            "min_dur": a.min_duration, "grade_window": a.grade_window}
    days = list(daterange(a.date_from, a.date_to))
    refresh = set(days[-a.refresh_days:]) if a.refresh_days > 0 else set()
    names = [f"episodes_s{g}" for g in grades] + ["profile"]
    print(f"C4M over-speed fetch  shift dates {a.date_from} .. {a.date_to} ({len(days)} days)  "
          f"policy {a.limit_flat:g}/{a.limit_steep:g} km/h, steep >= {grades} %")

    todo = [d for d in days if a.force or d in refresh
            or not all(os.path.exists(os.path.join(days_dir, d, f"{n}.parquet")) for n in names)]
    print(f"  cached: {len(days) - len(todo)} days   to pull: {len(todo)} days")
    if todo or a.with_register:
        print(f"  connection: {db.connect()} -> {db.current_db()}")
        db.switch_db("ControlSenseDB")
    t_all = time.time()
    for i, d in enumerate(todo, 1):
        ddir = os.path.join(days_dir, d)
        os.makedirs(ddir, exist_ok=True)
        t = time.time()
        params = dict(base, date_from=d, date_to=d)
        n = {}
        for g in grades:
            df = query("telemetry_episodes", dict(params, steep_pct=g), NUM_EPISODES)
            df.to_parquet(os.path.join(ddir, f"episodes_s{g}.parquet"), index=False)
            n[f"s{g}"] = len(df)
        df = query("telemetry_profile", params, NUM_PROFILE)
        df.to_parquet(os.path.join(ddir, "profile.parquet"), index=False)
        n["profile"] = len(df)
        print(f"  [{i:>3}/{len(todo)}] {d}  {n}  ({time.time() - t:4.1f} s)")
    if todo:
        print(f"  pulled {len(todo)} days in {(time.time() - t_all) / 60:.1f} min")

    # concatenate the cached days of the period into the files the page is built from
    counts = {}
    for n in names:
        parts = [pd.read_parquet(os.path.join(days_dir, d, f"{n}.parquet")) for d in days
                 if os.path.exists(os.path.join(days_dir, d, f"{n}.parquet"))]
        df = pd.concat([p for p in parts if len(p)], ignore_index=True) if any(len(p) for p in parts) else parts[0]
        df.to_parquet(os.path.join(out_dir, f"{n}.parquet"), index=False)
        df.to_csv(os.path.join(out_dir, f"{n}.csv"), index=False, encoding="utf-8-sig")
        counts[n] = len(df)
        print(f"  {n:<14} {len(df):>7} rows  ({len(parts)} days)")

    if a.with_register:          # C4M's own Speed Limit Register - not shown in the page, kept for reference
        df = query("events", dict(base, date_from=a.date_from, date_to=a.date_to), NUM_EVENTS)
        df.to_parquet(os.path.join(out_dir, "events.parquet"), index=False)
        df.to_csv(os.path.join(out_dir, "events.csv"), index=False, encoding="utf-8-sig")
        counts["events"] = len(df)
        print(f"  {'events':<14} {len(df):>7} rows")

    meta = {"date_from": a.date_from, "date_to": a.date_to, "shift_start": a.shift_start,
            "limit_flat": a.limit_flat, "limit_steep": a.limit_steep, "steep_grades": grades,
            "min_duration_s": a.min_duration, "grade_window_s": a.grade_window * 2, "rows": counts,
            "days": len(days), "pulled_now": todo,
            "fetched_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source": "C4M ControlSenseDB @ " + (db.env.get("C4M_DB_IP_ADDRESS") or "?")}
    json.dump(meta, open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8"), indent=2)
    print("  meta.json written")


if __name__ == "__main__":
    sys.exit(main())
