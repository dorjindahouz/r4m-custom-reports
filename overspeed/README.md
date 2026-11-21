# C4M over-speed report

Standalone HTML report of over-speeding at the mine, read straight from the **C4M (FMS)
PostgreSQL database** (the `C4M_DB_*` server in the repo-root `.env`). Not the R4M cube.

```
C4M DB (ControlSenseDB) --ssh+psql--> fetch_overspeed.py --> data/*.parquet --> build_overspeed.py --> overspeed_report.html
```

## Run

```bash
cd overspeed
set C4M_DB_MODE=ssh                      # optional: skip the (refused) direct-login attempts
python build_overspeed.py --fetch        # all shift days since 2026-07-01 -> overspeed_report.html
python fetch_overspeed.py --help         # --limit-flat/--limit-steep, --steep-grades, --min-duration, --refresh-days, --force
```

**History since 1 July 2026, cached per day.** `fetch_overspeed.py` queries one shift date at a
time into `data/days/<date>/` and re-pulls only the missing days plus the newest `--refresh-days`
(2; telemetry lands late), then concatenates the period into `data/episodes_s<G>.parquet` (G = steep cut-off, default 10) and
`data/profile.parquet`. The first run takes ~15 min (≈9 s per day); a nightly run ~30 s. The page
embeds everything as dictionary-encoded column tables (≈3.7 MB per 8k events), opens on the last
7 days and has quick ranges (7 d / 30 d / all since 1 Jul) plus free date pickers. Above 20,000
events the map switches to a 40 m density grid (toggle "heat"/"dots").

Open `overspeed_report.html` in a browser (works offline; light/dark theme; CSV export;
**Export PDF** prints the current view to PDF — A4 landscape, first 200 table rows).

## What is in the page

**Mine policy: 40 km/h, 30 km/h on steep roads** (`--limit-flat`, `--limit-steep`). C4M itself is
still configured with 50/60 km/h segment limits, so its own alert register is empty; the events are
therefore derived from the 2-second GPS stream C4M records for every truck.

| Content | Source | Meaning |
|---|---|---|
| Over-speed events · limit 40 / 30 steep | `ta_datacamion_historic` | GPS speed above the policy limit; "steep" = GPS road grade ≥ 10 % by default (user, 2026-10-20; was 12 %) (`--steep-grades`, comma list → a selector in the page; profile bands support 6/8/10/12 %). Period runs to the shift date in progress (today's shift so far) |

C4M's own *Speed Limit Register* (`ta_speed_limits_exceeded`) was dropped from the page on
2026-10-10 (user: "suboptimal" — it only ever held a 16-row commissioning test). `sql/events.sql`
stays for reference; `fetch_overspeed.py --with-register` still pulls it to `data/events.parquet`.

Road grade is measured from the GPS track: elevation change over the horizontal distance travelled
in a ±10 s window (`--grade-window`); samples with < 15 m of travel count as flat. Consecutive
over-limit samples (gap ≤ 4 s, same limit) form one episode; the fetch caches every episode of
≥ 2 samples (`--min-duration` 4 s, zero tolerance). **Report rule (2026-10-16):** `build_overspeed.py`
embeds only episodes that last ≥ 8 s (`--min-duration`) *and* whose average speed is ≥ 2 km/h over
the limit (`--tolerance`); "over by" = average speed − limit. Peak 2-second samples are not shown
anywhere (they were not GPS noise — peak−avg is a median 0.3–1.7 km/h — but the 4–6 s "events" at
40–42 km/h were trucks cruising at the limit; the rule removes ~64 % of raw episodes and keeps 98 %
of the >50 km/h runs). "Highest sustained speed per truck" = the highest event average, flat vs steep,
against the dashed 40/30 lines. Filters: shift date, shift, truck, operator, crew, road type, steep cut-off,
load state, average excess over the limit, duration, free text.

Plus KPI tiles, events per day / road type / hour / truck / operator, an over-limit histogram, a
GPS **speed profile** (minutes above 30/35/40/45/50 km/h per day) and the event positions on the
pit contour map.

## Sheet 3 of the daily report + deployment

`daily_report/build_combined.py` adds an **Over-speed** tab to `daily_report_v3.html`: an iframe
that loads `overspeed_report.html?embed=1&theme=light` from the same folder the first time the tab
is opened (`daily_report/overspeed_sheet.py`). The combined build copies the latest over-speed page
next to the report. Both files live on the R4M app VM in `/opt/R4M/storage/www/r4m_custom_report/`
and are served at `https://r4m.example.local/r4m_custom_report/daily_report_v3.html` (deep link
`#overspeed`) and `.../overspeed_report.html`.

```bash
python deploy_r4m.py                   # upload both (backs up the server copies first)
python deploy_r4m.py --only overspeed  # nightly refresh: fetch + build + upload only this file
```

**Nightly refresh runs on the R4M app VM itself** (installed 2026-10-10 by
`server/install_server.py`): cron `30 10 * * *` (Asia/Ulaanbaatar) runs
`~/r4m_overspeed/overspeed/server/refresh_overspeed.sh`, which fetches the last 7 shift days from
the C4M DB (SSH + sudo psql with the C4M_DB_* values in `~/r4m_overspeed/.env`, mode 600), rebuilds
the page in a venv and swaps it into the served folder. Logs: `~/r4m_overspeed/logs/refresh_<date>.log`
(30 days kept). After editing any script or SQL here, re-run `python server/install_server.py`
(add `--no-run --skip-pip` to only re-upload + re-install the cron line). The daily report itself
is still deployed from this PC with `deploy_r4m.py --only daily`.

## Files

| File | Purpose |
|---|---|
| `env.py` | reads `../.env` (stdlib) |
| `db.py` | connection ladder: direct Postgres → SSH + `sudo -u postgres psql`; `run_query()` returns DataFrames |
| `discover_schema.py` | read-only schema exploration |
| `sql/events.sql` | the register query |
| `sql/telemetry_episodes.sql` | gaps-and-islands over the unnested GPS arrays → episodes |
| `sql/telemetry_profile.sql` | per day × shift × truck × load-state speed summary |
| `fetch_overspeed.py` | runs the SQL, writes `data/*.parquet|csv` + `meta.json` |
| `build_overspeed.py`, `overspeed_template.py` | assemble the HTML (CSS/JS inline, data embedded) |

