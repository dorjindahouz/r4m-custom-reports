"""Build the C4M over-speed report as one self-contained HTML page.

Data flow:
  fetch_overspeed.py  ->  data/episodes_s<G>.parquet, data/profile.parquet, meta.json (per-day cache in data/days/)
  this script         ->  overspeed_report.html  (all data embedded as compact column tables; filtering,
                          charts, table, map and CSV export run client-side; works offline)

Run:  python build_overspeed.py [--min-duration 8] [--tolerance 2] [--no-map] [--out PATH] [--fetch [fetch args...]]
      e.g.  python build_overspeed.py --fetch --from 2026-07-01      (everything after --fetch goes to the fetch)

Report rule (user, 2026-10-16): the fetch caches every run of >= 2 over-limit samples (4 s, zero
tolerance) so the rule can change without re-pulling 100+ days; the page embeds only the events that
last >= MIN_DURATION_S and whose AVERAGE speed is >= TOLERANCE_KMH over the limit. The peak 2 s sample
is not shown anywhere any more: the 4-6 s "events" at 40-42 km/h were trucks cruising at the limit,
not speeding, and the real peaks (60+ km/h) are all long runs that survive the rule anyway.
"Over by" = average speed during the event minus the limit.
"""
import argparse
import base64
import json
import math
import os
import subprocess
import sys

import pandas as pd

from overspeed_template import CSS, HTML, JS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(HERE, "data")
DAILY = os.path.join(ROOT, "daily_report")
OUT = os.path.join(HERE, "overspeed_report.html")

MIN_DURATION_S = 8         # an event must last >= 4 consecutive 2 s samples over the limit (user: 10 -> 8, 2026-10-16)
TOLERANCE_KMH = 2.0        # ... and its average speed must exceed the limit by at least this

# columns kept on disk (parquet/csv) but not embedded in the page: ids/duplicates to keep the HTML
# small, plus every peak-sample figure (speed_kmh = event peak, max_kmh/p99_kmh = profile peaks)
DROP = ["fleet", "model", "operator_login", "id_segment", "event_end_ts", "id_cycle",
        "segment_pct_start", "segment_pct_end", "speed_kmh", "max_kmh", "p99_kmh"]
ROUND1 = ("x", "y", "z", "over_kmh", "grade_pct", "avg_speed_kmh", "avg_moving_kmh")


def apply_rule(df, rule):
    """Report rule on a cached episode frame: over_kmh = average speed - limit; keep events that
    last >= rule[0] s with over_kmh >= rule[1] km/h."""
    df = df.copy()
    df["over_kmh"] = (df["avg_speed_kmh"] - df["limit_kmh"]).round(1)
    return df[(df["duration_s"] >= rule[0]) & (df["over_kmh"] >= rule[1])].reset_index(drop=True)


def table(name, rule=None):
    """Parquet -> compact column table: {"cols": [...], "data": {col: [...]}, "dict": {col: [uniques]}}.
    Text columns are dictionary-encoded (the page decodes them back into row objects).
    `rule` = (min_duration_s, tolerance_kmh) for episode tables (see apply_rule)."""
    p = os.path.join(DATA, f"{name}.parquet")
    if not os.path.exists(p):
        return None
    df = pd.read_parquet(p)
    if rule and "avg_speed_kmh" in df.columns:
        df = apply_rule(df, rule)
    df = df.drop(columns=[c for c in DROP if c in df.columns])
    for c in ROUND1:
        if c in df:
            df[c] = df[c].round(1)
    out = {"cols": list(df.columns), "data": {}, "dict": {}}
    for c in df.columns:
        s = df[c]
        if s.dtype == object or str(s.dtype) in ("string", "str"):
            codes, uniques = pd.factorize(s, use_na_sentinel=True)
            out["dict"][c] = [None if (isinstance(u, float) and math.isnan(u)) else u for u in uniques.tolist()]
            out["data"][c] = [None if k < 0 else int(k) for k in codes.tolist()]
        elif s.dtype == bool:
            out["data"][c] = [bool(v) for v in s.tolist()]
        else:
            vals = s.tolist()
            out["data"][c] = [None if (v is None or (isinstance(v, float) and math.isnan(v))) else (v.item() if hasattr(v, "item") else v) for v in vals]
            if str(s.dtype).startswith("int") or all(v is None or float(v).is_integer() for v in out["data"][c]):
                out["data"][c] = [None if v is None else int(v) for v in out["data"][c]]
    return out


def contour():
    """Pit contour background shared with the daily report (optional)."""
    j = os.path.join(DAILY, "data", "contour_bg.json")
    png = os.path.join(DAILY, "data", "contour_bg.png")
    if not (os.path.exists(j) and os.path.exists(png)):
        return None
    meta = json.load(open(j))
    meta["png"] = base64.b64encode(open(png, "rb").read()).decode("ascii")
    return meta


def read(path, default=""):
    return open(path, encoding="utf-8").read() if os.path.exists(path) else default


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fetch", nargs=argparse.REMAINDER, help="run fetch_overspeed.py first (remaining args are passed to it)")
    ap.add_argument("--no-map", action="store_true", help="omit the contour map (smaller file)")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--min-duration", type=int, default=MIN_DURATION_S, help="report only events lasting >= N s")
    ap.add_argument("--tolerance", type=float, default=TOLERANCE_KMH,
                    help="report only events whose average speed is >= limit + X km/h")
    a = ap.parse_args()

    if a.fetch is not None:
        cmd = [sys.executable, os.path.join(HERE, "fetch_overspeed.py")] + a.fetch
        print("fetching:", " ".join(cmd[1:]))
        subprocess.run(cmd, check=True, cwd=HERE)

    meta = json.load(open(os.path.join(DATA, "meta.json"), encoding="utf-8"))
    rule = (a.min_duration, a.tolerance)
    meta["fetch_min_duration_s"] = meta.get("min_duration_s")      # what the day cache holds (4 s, no tolerance)
    meta["min_duration_s"] = a.min_duration                         # what the page reports
    meta["tolerance_kmh"] = a.tolerance
    policy = {str(g): table(f"episodes_s{g}", rule) for g in meta.get("steep_grades", [])}
    data = {
        "meta": meta,
        "policy": {g: t for g, t in policy.items() if t},
        "profile": table("profile"),
        "contour": None if a.no_map else contour(),
    }
    logo = base64.b64encode(open(os.path.join(DAILY, "erdene_logo.png"), "rb").read()).decode("ascii")

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Over-speed report · {meta['date_from']} → {meta['date_to']}</title>
<style>
{read(os.path.join(DAILY, 'vendor_rubik.css'))}
{read(os.path.join(ROOT, 'r4m-design-schema.css'))}
{CSS}
</style>
</head>
<body>
{HTML.replace('__LOGO__', logo)}
<script>
{JS.replace('__DATA__', json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))}
</script>
</body>
</html>
"""
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(page)
    n = {f"policy_s{g}": len(t["data"][t["cols"][0]]) for g, t in data["policy"].items()}
    n["profile"] = len(data["profile"]["data"]["shift_date"]) if data["profile"] else 0
    print(f"wrote {a.out}  ({os.path.getsize(a.out) / 1e6:.1f} MB)  rows: {n}  period {meta['date_from']}..{meta['date_to']}")

    # console cross-check of the headline numbers the page should show for the whole period
    lf, ls = meta["limit_flat"], meta["limit_steep"]
    prof = pd.read_parquet(os.path.join(DATA, "profile.parquet"))
    for g in data["policy"]:
        raw = pd.read_parquet(os.path.join(DATA, f"episodes_s{g}.parquet"))
        df = apply_rule(raw, rule)
        steep = prof.grade_band >= {"6": 1, "8": 2, "10": 3, "12": 4}.get(g, 2)
        over = (prof.loc[steep, f"sec_gt{int(ls)}"].sum() + prof.loc[~steep, f"sec_gt{int(lf)}"].sum()) / 60
        print(f"check steep>={g}%: {len(df)} events of {len(raw)} cached (rule >= {rule[0]} s, avg >= +{rule[1]:g} km/h), "
              f"{(df.road == 'steep').sum()} steep, {df.equipment.nunique()} trucks, {df.operator.nunique()} operators, "
              f"worst avg excess +{df.over_kmh.max():.1f} km/h, longest {df.duration_s.max()} s, "
              f"total {df.duration_s.sum() / 60:.1f} min | GPS over policy {over:.1f} min, moving {prof.sec_moving.sum() / 3600:.1f} h")


if __name__ == "__main__":
    main()
