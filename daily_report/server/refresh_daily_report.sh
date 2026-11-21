#!/bin/bash
# Nightly rebuild of the daily report (daily_report_v3.html) on the R4M app VM, run by cron
# (installed by daily_report/server/install_daily_refresh.py):
#   1. C4M polygon lifetimes / versions, dump areas and stockpile links (read-only SELECTs)
#   2. R4M cube snapshot with the signed R4M login in ~/.config/r4m_custom_report/r4m_login
#      (two lines, username + password, mode 600, written by the account owner; skipped when absent)
#   3. build_combined.py with the published plan currently served
#   4. sanity checks, then swap into the served folder (previous page kept as .bak-<stamp>-nightly,
#      the last 7 kept). Any failure leaves the served page untouched.
set -uo pipefail
BASE="$HOME/r4m_overspeed"
DR="$BASE/daily_report"
WWW="/opt/R4M/storage/www/r4m_custom_report"
LOGIN="$HOME/.config/r4m_custom_report/r4m_login"
mkdir -p "$BASE/logs"
LOG="$BASE/logs/daily_report_$(date +%Y%m%d).log"
exec >> "$LOG" 2>&1
exec 9>"$BASE/logs/daily_report.lock"
flock -n 9 || { echo "=== $(date '+%F %T') another refresh is running - skipped"; exit 0; }
echo "=== $(date '+%F %T') daily report refresh start"
export C4M_DB_MODE=ssh PYTHONIOENCODING=utf-8
PY="$BASE/venv/bin/python"
cd "$DR" || exit 1

"$PY" fetch_c4m_polygon_versions.py || echo "WARN: C4M polygon/stockpile fetch failed - previous file kept"
if [ -f "$LOGIN" ]; then
  "$PY" fetch_data.py --login-file "$LOGIN" || echo "WARN: R4M fetch incomplete - the cached files are used for what failed"
else
  echo "NOTE: no $LOGIN - R4M cube snapshot not refreshed"
fi
cp -p "$WWW/published_inputs.json" "$DR/published_inputs.json" 2>/dev/null || echo "NOTE: no published plan on the server"

"$PY" build_combined.py || { echo "FAIL: build exited non-zero - served page unchanged"; exit 1; }
OUT="$DR/daily_report_v3.html"
SZ=$(stat -c %s "$OUT")
[ "$SZ" -gt 3000000 ] || { echo "FAIL: page only $SZ bytes - not deployed"; exit 1; }
grep -q "window.ATL" "$OUT" || { echo "FAIL: atlas half missing - not deployed"; exit 1; }
if grep -o "__[A-Z][A-Z0-9_]*__" "$OUT" | grep -v "^__THREE" | grep -q .; then
  echo "FAIL: unreplaced build tokens - not deployed"; exit 1
fi

STAMP=$(date +%Y%m%d-%H%M)
cp -p "$WWW/daily_report_v3.html" "$WWW/daily_report_v3.html.bak-$STAMP-nightly"
cp "$OUT" "$WWW/daily_report_v3.html.tmp"
chmod 644 "$WWW/daily_report_v3.html.tmp"
mv -f "$WWW/daily_report_v3.html.tmp" "$WWW/daily_report_v3.html"     # atomic: readers never see a half file
ls -1t "$WWW"/daily_report_v3.html.bak-*-nightly 2>/dev/null | tail -n +8 | xargs -r rm -f
echo "=== $(date '+%F %T') deployed $SZ bytes -> $WWW/daily_report_v3.html (backup .bak-$STAMP-nightly)"
find "$BASE/logs" -name 'daily_report_*.log' -mtime +30 -delete
