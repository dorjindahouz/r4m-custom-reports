#!/bin/bash
# Nightly refresh of the Operator KPI sheet, run by cron on the R4M app VM (installed by
# overspeed/server/install_server.py next to the over-speed job). Pulls the missing shift days plus
# the newest --refresh-days (default 7: a form's review status changes days later) from the C4M DB,
# rebuilds operator_kpi.html and swaps it into the folder R4M serves
# (https://r4m.example.local/r4m_custom_report/). Extra arguments go to fetch_operator_kpi.py.
set -euo pipefail
BASE="$HOME/r4m_overspeed"
WWW="/opt/R4M/storage/www/r4m_custom_report"
mkdir -p "$BASE/logs"
LOG="$BASE/logs/refresh_opkpi_$(date +%Y%m%d).log"
exec >> "$LOG" 2>&1
echo "=== $(date '+%F %T') operator KPI refresh start ($*)"
export C4M_DB_MODE=ssh PYTHONIOENCODING=utf-8
cd "$BASE/operator_kpi"
"$BASE/venv/bin/python" build_operator_kpi.py --fetch "$@"
cp operator_kpi.html "$WWW/operator_kpi.html.tmp"
chmod 644 "$WWW/operator_kpi.html.tmp"
mv -f "$WWW/operator_kpi.html.tmp" "$WWW/operator_kpi.html"      # atomic: readers never see a half file
echo "=== $(date '+%F %T') deployed $(stat -c %s "$WWW/operator_kpi.html") bytes -> $WWW/operator_kpi.html"
find "$BASE/logs" -name 'refresh_opkpi_*.log' -mtime +30 -delete
