"""Install (or update) the nightly daily-report rebuild on the R4M app VM.

What it does, over SSH/SFTP as the R4M_APP login from ../../.env:
  1. uploads the build code to ~/r4m_overspeed/daily_report/ (every daily_report/*.py, vendor
     scripts/fonts, logo, ../r4m-design-schema.css, ../Report Inputs.xlsx, server/refresh_daily_report.sh)
     - re-run after ANY change to the report code, or the nightly build reverts the page to the
     server's older copy
  2. seeds ~/r4m_overspeed/daily_report/data/ from the local data/ folder when it is missing
     (or --seed-data): the nightly fetch refreshes it from then on
  3. adds shapely / openpyxl / cryptography to the existing venv (pandas, pyarrow already there)
  4. runs one refresh now (unless --no-run) and shows the log tail
  5. installs the cron line (default 07:40 daily, after the 07:00 shift change)

The R4M login file (~/.config/r4m_custom_report/r4m_login) is NOT written by this script: the
account owner creates it on the server. Without it the job refreshes everything except the cube.

Run:  python install_daily_refresh.py [--cron "40 7 * * *"] [--no-run] [--seed-data] [--skip-pip]
"""
import argparse
import glob
import os
import sys

import paramiko

HERE = os.path.dirname(os.path.abspath(__file__))
DR = os.path.dirname(HERE)
ROOT = os.path.dirname(DR)
sys.path.insert(0, os.path.join(ROOT, "overspeed"))
import env  # noqa: E402

REMOTE = "r4m_overspeed"
SCRIPT = f"{REMOTE}/daily_report/server/refresh_daily_report.sh"
SKIP = {"render_pdf.py", "render_guide_pdf.py", "prepare_contour.py"}


def uploads():
    up = {}
    for p in glob.glob(os.path.join(DR, "*.py")):
        if os.path.basename(p) not in SKIP:
            up[p] = f"{REMOTE}/daily_report/{os.path.basename(p)}"
    for n in ("vendor_hyparquet.min.js", "vendor_three.min.js", "vendor_rubik.css", "erdene_logo.png"):
        up[os.path.join(DR, n)] = f"{REMOTE}/daily_report/{n}"
    up[os.path.join(ROOT, "r4m-design-schema.css")] = f"{REMOTE}/r4m-design-schema.css"
    up[os.path.join(ROOT, "Report Inputs.xlsx")] = f"{REMOTE}/Report Inputs.xlsx"
    up[os.path.join(HERE, "refresh_daily_report.sh")] = SCRIPT
    return up


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cron", default="40 7 * * *", help="cron schedule (server local time, UTC+8)")
    ap.add_argument("--no-run", action="store_true")
    ap.add_argument("--seed-data", action="store_true", help="overwrite the server's data/ with the local one")
    ap.add_argument("--skip-pip", action="store_true")
    a = ap.parse_args()
    s = env.server("R4M_APP")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(s["ip"], username=s["user"], password=s["password"], timeout=20, look_for_keys=False, allow_agent=False)

    def run(cmd, timeout=600):
        _, o, e = c.exec_command(cmd, timeout=timeout)
        out, err = o.read().decode(errors="replace"), e.read().decode(errors="replace")
        rc = o.channel.recv_exit_status()
        if out.strip():
            print(out.rstrip())
        if err.strip():
            print("  stderr:", err.strip()[-1500:])
        return rc, out, err

    sftp = c.open_sftp()
    home = sftp.normalize(".")
    print("1. uploading the build code")
    run(f"mkdir -p {REMOTE}/daily_report/server {REMOTE}/daily_report/data {REMOTE}/logs")
    for lp, rp in uploads().items():
        sftp.put(lp, f"{home}/{rp}")
    sftp.chmod(f"{home}/{SCRIPT}", 0o755)
    print(f"   {len(uploads())} files")

    rc, out, _ = run(f"ls {REMOTE}/daily_report/data/production.parquet 2>/dev/null | wc -l")
    if a.seed_data or out.strip() == "0":
        print("2. seeding data/ from the local cache")
        for lp in sorted(glob.glob(os.path.join(DR, "data", "*"))):
            if os.path.isfile(lp):
                sftp.put(lp, f"{home}/{REMOTE}/daily_report/data/{os.path.basename(lp)}")
        print("   done")
    else:
        print("2. server data/ present - kept (use --seed-data to overwrite)")
    sftp.close()

    if not a.skip_pip:
        print("3. venv packages")
        rc, _, _ = run(f"{REMOTE}/venv/bin/pip install -q --disable-pip-version-check shapely openpyxl cryptography", timeout=900)
        if rc:
            sys.exit("pip install failed - see above")
    run(f"{REMOTE}/venv/bin/python -c \"import pandas, pyarrow, shapely, openpyxl, cryptography; print('pandas', pandas.__version__, 'shapely', shapely.__version__, 'openpyxl', openpyxl.__version__, 'cryptography', cryptography.__version__)\"")
    rc, out, _ = run("test -f ~/.config/r4m_custom_report/r4m_login && echo 'R4M login file: present' || echo 'R4M login file: MISSING (cube not refreshed until it exists)'")

    if not a.no_run:
        print("4. one refresh now (~4-6 min)")
        rc, _, _ = run(f"bash {SCRIPT}; tail -25 {REMOTE}/logs/daily_report_$(date +%Y%m%d).log", timeout=1800)
    print(f"5. cron: {a.cron}")
    line = f"{a.cron} bash $HOME/{SCRIPT} # r4m daily report rebuild"
    run(f"(crontab -l 2>/dev/null | grep -v 'refresh_daily_report.sh'; echo '{line}') | crontab - && crontab -l | grep refresh_daily_report")
    c.close()


if __name__ == "__main__":
    main()
