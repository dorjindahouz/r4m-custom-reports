# Operator KPI page (sheet 4 of the daily report)

`operator_kpi.html` — per-operator KPIs and the daily pre-start checklists from the C4M FMS
database, with CSV downloads. Same pipeline as the over-speed page:

    C4M DB (ControlSenseDB) --ssh+psql--> fetch_operator_kpi.py --> data/*.parquet --> build_operator_kpi.py --> operator_kpi.html

* `fetch_operator_kpi.py` — per shift date (07:00 → 07:00; checklists 06:20 → 06:20, DS 06:20–18:20 / NS 18:20–06:20,
  because forms are filed in the hour before the shift — user, 2026-10-26) cache in `data/days/<date>/`, up to and including
  the shift day running now (partial until the next refresh completes it):
  `checklists`, `checklist_items`, `loads` (haul cycles rolled up per shift × equipment × operator,
  truck rows + loader rows), `status` (equipment status hours per shift × equipment × operator ×
  status detail), `logins`; dimensions once per run. The newest 7 days are always re-pulled (a
  form's review status changes late). Reuses `../overspeed/db.py` and `env.py` (`.env` at the
  repo root; nothing is ever printed).
* `make_lookups.py` — `lookups/status_detail.json` from the R4M status dimension (C4M status ids
  → READY / DELAY / STANDBY / MANT. / OUTOFPLAN and Production / Planned / Unplanned). Re-run on
  the PC when R4M adds status details; the JSON is shipped with the build.
* `build_operator_kpi.py` — merges everything into one row per shift × equipment × operator
  (sums and counts only, so the page re-aggregates any date range exactly), adds the over-speed events of the
  Over-speed page and embeds the data in the page. Over-speed: the episode file the Over-speed page uses
  (`../overspeed/data/episodes_s<G>.parquet`, G = `steep_grades[0]` of its `meta.json`, else the newest file), the
  same report rule (`build_overspeed.apply_rule`: >= 8 s with an average >= limit + 2 km/h; never a peak speed),
  attributed to the operator logged in on the truck according to the truck's own telemetry (`operator_login` ->
  `dim_workers`; a login listed twice -> the id with a row on that truck in that shift, then the live row), with
  the name and the `at_worker_login` sessions as fallbacks (2026-10-30: 98.2 % by login, 0.1 % by session, 1.7 %
  without a login - counted, never ranked). Embedded as `osev` (one row per event) + per-row `os_n/os_s/os_max/os_steep`.
* `operator_kpi_template.py` — the page (same design grammar as the daily report).

## Page
* **01 Shift sheet** (the supervisors' daily page; its own Shift date / Shift / Crew bar, default = the last
  complete shift day, ‹ › to step): six tiles (operators on shift, loads, loads per productive hour and
  productive time with the change against the previous 30 shift days, checklists filed / machine-shifts
  worked, over-speed events), **Needs follow-up** grouped by reason (over-speed, no checklist, NOT-OK items incl.
  forms saved blank, productive time 15 points below the shift median, loading rate below 60 % of the median; on the PDF summary page only),
  then the truck and the loader operators **ranked within the shift** (Rank by; badges = rank in loads per
  productive hour [from 2 productive h], productive time, checklist, over-speed; no combined score; Δ = the
  operator against their own previous 30 shift days; ▸ opens the over-speed events). Click a name -> the
  **operator card** (tiles, operator vs fleet median vs own 30 days, ranks, events, checklists, top
  non-productive reasons; "Print this card").
* 02-04 Overview / Operator ranking / Trends follow the period and the filter bar (unchanged, plus
  rank `#` and badges, over-speed worst / steep / per 100 h columns, "Over-speed per 100 operated hours" and
  "Over-speed events" charts; a name opens the card for the period).
* **All KPIs** (2026-10-30): the shift tables have a Columns switch (Headline / All KPIs = every column of the operator CSV,
  grouped, with a median row); the shift KPI PDF adds an A4-landscape all-KPI table per shift after the summary page, and
  every operator card has an "All KPIs" block (operator · median of the shift · own previous 30 shift days, totals scaled to
  the same number of shifts).
* Section 03 "Operator ranking" (period charts, ranking table, operator CSV) was removed on 2026-10-30 (user); the page now has
  01 Shift sheet, 02 Overview, 03 Trends and no CSV download.
* The period "Pre-start checklists" section (charts, forms table, checklist CSVs) was removed on 2026-10-30 (user);
  checklists stay in the shift sheet (column, follow-ups, operator card, checklist PDF) and in the Overview/Trends compliance.

## KPIs
Activity (shifts, hours, equipment), time use (productive / breaks / delay / standby / maintenance
hours and %, shift-change minutes), trucks (loads, nominal tonnes, loads per productive hour, average
queue / spot / loading / haul / at-dump / dumping / travel-empty / cycle seconds), loaders (loads
loaded, loading and hang seconds, trucks served), compliance (checklists filed, compliance % = forms ÷
equipment-shifts worked, items NOT OK, rejected / not reviewed forms), safety (over-speed events).
Tonnes are nominal (52.8 t per truck load — the trucks have no payload scale). Cycle phases are the
C4M dispatch timestamps, verified to the second against the R4M cube's phase durations; the
loader's operator comes from the last login on the machine (99 % agreement with the R4M cube).

## Downloads
* **Shift KPI PDF** (shift sheet, "Export shift KPIs"): per shift of the selection one summary page (tiles,
  follow-ups, both ranked tables, every over-speed event, signature lines), then one A4 page per operator-shift
  (the operator card with signature lines), merged by the browser's print-to-PDF; suggested name
  `operator_kpis_<date>[_<shift>][_<crew>]` (`_partial` while the shift day is still running).
* **Bulk checklist PDF** (shift sheet, next to it): every form of the selected shift date / shift / crew becomes its
  own A4 page (header, items in C4M template order with OK / NOT OK, signature lines), merged into one file
  (suggested name `checklists_<date>[_<shift>][_<crew>]`). Only the shift-sheet selection applies.
* Test hooks: `window.__shiftPdf` / `window.__formsPdf` `{prepare, end, count}`, `window.__shiftSheet.summary(date, shift, crew)`.

## Run
    python fetch_operator_kpi.py --from 2026-07-01          # or: python build_operator_kpi.py --fetch
    python build_operator_kpi.py
    python ../daily_report/build_combined.py                 # copies operator_kpi.html next to the daily report (sheet 4)
    python ../overspeed/deploy_r4m.py --only opkpi daily     # upload to the R4M VM
Nightly on the R4M VM: `server/refresh_operator_kpi.sh` (cron 10:45, installed by
`../overspeed/server/install_server.py` together with the over-speed job; logs in `~/r4m_overspeed/logs/`).
**Refresh data** button (title block, only shown when the page is served from the R4M VM): runs the
same script now through the publish/refresh service (`../daily_report/server/publish_server.py`,
`POST /r4m_custom_report/refresh`), one run at a time, 10-minute cool-down, page reloads when done.
