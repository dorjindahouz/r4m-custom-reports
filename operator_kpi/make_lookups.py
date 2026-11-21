"""Build lookups/status_detail.json from the R4M cube's status dimension (PC only; commit the JSON).

C4M's tp_estados.id_detal_estado ids are the same ids as R4M's `Id Status Detail`, and R4M already
classifies every one of them into Main Status (READY / DELAY / STANDBY / MANT. / OUTOFPLAN) and
Type (Production / Planned / Unplanned ...). The nightly job on the R4M VM has no cube access,
so the mapping is shipped as a static file.

Run:  python make_lookups.py        (reads ../daily_report/data/status_detail.parquet)
"""
import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "daily_report", "data", "status_detail.parquet")
OUT = os.path.join(HERE, "lookups", "status_detail.json")


def main():
    df = pd.read_parquet(SRC)
    m = {}
    for r in df.itertuples(index=False):
        m[str(int(r._0))] = [str(r._3).strip(), str(r._4).strip(), str(r._5).strip()]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(m, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    mains = sorted({v[0] for v in m.values()})
    print(f"wrote {OUT}: {len(m)} status details, main statuses {mains}")


if __name__ == "__main__":
    main()
