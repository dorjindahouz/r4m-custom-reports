#!/bin/bash
# Nightly refresh of the over-speed sheet, run by cron on the R4M app VM (installed by
# overspeed/server/install_server.py). Pulls the last 7 shift days from the C4M DB, rebuilds
# overspeed_report.html and swaps it into the folder nginx/R4M serves
# (https://r4m.example.local/r4m_custom_report/). Extra arguments go to fetch_overspeed.py.
set -euo pipefail
BASE="$HOME/r4m_overspeed"
WWW="/opt/R4M/storage/www/r4m_custom_report"
mkdir -p "$BASE/logs"
LOG="$BASE/logs/refresh_$(date +%Y%m%d).log"
exec >> "$LOG" 2>&1
echo "=== $(date '+%F %T') refresh start ($*)"
export C4M_DB_MODE=ssh PYTHONIOENCODING=utf-8
cd "$BASE/overspeed"
"$BASE/venv/bin/python" build_overspeed.py --fetch "$@"
cp overspeed_report.html "$WWW/overspeed_report.html.tmp"
chmod 644 "$WWW/overspeed_report.html.tmp"
mv -f "$WWW/overspeed_report.html.tmp" "$WWW/overspeed_report.html"      # atomic: readers never see a half file
echo "=== $(date '+%F %T') deployed $(stat -c %s "$WWW/overspeed_report.html") bytes -> $WWW/overspeed_report.html"
find "$BASE/logs" -name 'refresh_*.log' -mtime +30 -delete
