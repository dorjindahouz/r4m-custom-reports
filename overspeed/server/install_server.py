"""Install (or update) the nightly over-speed refresh on the R4M app VM.

What it does, over SSH/SFTP as the R4M_APP login from ../../.env:
  1. uploads the build inputs to ~/r4m_overspeed/  (overspeed/ scripts + sql, the design CSS,
     the logo/font, the contour map)  - re-run after editing any of them
  2. writes ~/r4m_overspeed/.env (mode 600) with ONLY the C4M_DB_* values the fetch needs
  3. creates a venv and installs pandas / pyarrow / paramiko (needs PyPI access from the VM)
  4. runs one refresh now (fetch -> build -> copy into the served folder) and shows its log
  5. installs the cron line (default 10:30 daily, Asia/Ulaanbaatar - after the night shift's
     telemetry has landed; the DB lags 1-3 h)

Run:  python install_server.py [--cron "30 10 * * *"] [--no-run] [--skip-pip]
"""
import argparse
import os
import stat
import sys

import paramiko

HERE = os.path.dirname(os.path.abspath(__file__))
OVERSPEED = os.path.dirname(HERE)
ROOT = os.path.dirname(OVERSPEED)
sys.path.insert(0, OVERSPEED)
import env  # noqa: E402

REMOTE = "r4m_overspeed"                     # relative to the login's home
SCRIPT = f"{REMOTE}/overspeed/server/refresh_overspeed.sh"
OPKPI = os.path.join(ROOT, "operator_kpi")
SCRIPT2 = f"{REMOTE}/operator_kpi/server/refresh_operator_kpi.sh"
UPLOADS = {                                  # local path -> remote path (under home)
    os.path.join(ROOT, "r4m-design-schema.css"):                  f"{REMOTE}/r4m-design-schema.css",
    os.path.join(ROOT, "daily_report", "erdene_logo.png"):        f"{REMOTE}/daily_report/erdene_logo.png",
    os.path.join(ROOT, "daily_report", "vendor_rubik.css"):       f"{REMOTE}/daily_report/vendor_rubik.css",
    os.path.join(ROOT, "daily_report", "data", "contour_bg.json"): f"{REMOTE}/daily_report/data/contour_bg.json",
    os.path.join(ROOT, "daily_report", "data", "contour_bg.png"):  f"{REMOTE}/daily_report/data/contour_bg.png",
    os.path.join(OVERSPEED, "env.py"):                            f"{REMOTE}/overspeed/env.py",
    os.path.join(OVERSPEED, "db.py"):                             f"{REMOTE}/overspeed/db.py",
    os.path.join(OVERSPEED, "fetch_overspeed.py"):                f"{REMOTE}/overspeed/fetch_overspeed.py",
    os.path.join(OVERSPEED, "build_overspeed.py"):                f"{REMOTE}/overspeed/build_overspeed.py",
    os.path.join(OVERSPEED, "overspeed_template.py"):             f"{REMOTE}/overspeed/overspeed_template.py",
    os.path.join(OVERSPEED, "sql", "events.sql"):                 f"{REMOTE}/overspeed/sql/events.sql",
    os.path.join(OVERSPEED, "sql", "telemetry_episodes.sql"):     f"{REMOTE}/overspeed/sql/telemetry_episodes.sql",
    os.path.join(OVERSPEED, "sql", "telemetry_profile.sql"):      f"{REMOTE}/overspeed/sql/telemetry_profile.sql",
    os.path.join(HERE, "refresh_overspeed.sh"):                   SCRIPT,
    os.path.join(OPKPI, "fetch_operator_kpi.py"):                 f"{REMOTE}/operator_kpi/fetch_operator_kpi.py",
    os.path.join(OPKPI, "build_operator_kpi.py"):                 f"{REMOTE}/operator_kpi/build_operator_kpi.py",
    os.path.join(OPKPI, "operator_kpi_template.py"):              f"{REMOTE}/operator_kpi/operator_kpi_template.py",
    os.path.join(OPKPI, "lookups", "status_detail.json"):         f"{REMOTE}/operator_kpi/lookups/status_detail.json",
    os.path.join(OPKPI, "server", "refresh_operator_kpi.sh"):     SCRIPT2,
    os.path.join(OPKPI, "sql", "checklists.sql"):                       f"{REMOTE}/operator_kpi/sql/checklists.sql",
    os.path.join(OPKPI, "sql", "checklist_items.sql"):                  f"{REMOTE}/operator_kpi/sql/checklist_items.sql",
    os.path.join(OPKPI, "sql", "dim_checklist_items.sql"):              f"{REMOTE}/operator_kpi/sql/dim_checklist_items.sql",
    os.path.join(OPKPI, "sql", "dim_equipment.sql"):                    f"{REMOTE}/operator_kpi/sql/dim_equipment.sql",
    os.path.join(OPKPI, "sql", "dim_status.sql"):                       f"{REMOTE}/operator_kpi/sql/dim_status.sql",
    os.path.join(OPKPI, "sql", "dim_workers.sql"):                      f"{REMOTE}/operator_kpi/sql/dim_workers.sql",
    os.path.join(OPKPI, "sql", "loads_by_operator_shift.sql"):          f"{REMOTE}/operator_kpi/sql/loads_by_operator_shift.sql",
    os.path.join(OPKPI, "sql", "logins.sql"):                           f"{REMOTE}/operator_kpi/sql/logins.sql",
    os.path.join(OPKPI, "sql", "status_by_operator_shift.sql"):         f"{REMOTE}/operator_kpi/sql/status_by_operator_shift.sql",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cron", default="30 10 * * *", help="cron schedule for the over-speed refresh (server local time)")
    ap.add_argument("--cron-opkpi", default="45 10 * * *", help="cron schedule for the operator KPI refresh")
    ap.add_argument("--no-run", action="store_true", help="install only, do not run a refresh now")
    ap.add_argument("--skip-pip", action="store_true", help="venv already has the packages")
    ap.add_argument("--seed-cache", action="store_true", help="upload data/days/* (the per-day cache) to the server")
    a = ap.parse_args()

    srv = env.server("R4M_APP")
    c4m = env.server("C4M_DB")
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(srv["ip"], username=srv["user"], password=srv["password"], timeout=15,
                allow_agent=False, look_for_keys=False)

    def run(cmd, timeout=120, show=True):
        _, out, err = cli.exec_command(cmd, timeout=timeout)
        o = out.read().decode("utf-8", "replace"); e = err.read().decode("utf-8", "replace")
        rc = out.channel.recv_exit_status()
        if show and (o.strip() or e.strip()):
            print("   ", (o + e).strip().replace("\n", "\n    ")[-3000:])
        return rc, o, e

    print("1. uploading build inputs")
    sftp = cli.open_sftp()
    dirs = sorted({os.path.dirname(r) for r in UPLOADS.values()} | {f"{REMOTE}/overspeed/data", f"{REMOTE}/operator_kpi/data", f"{REMOTE}/logs"})
    run("mkdir -p " + " ".join(dirs), show=False)
    for local, remote in UPLOADS.items():
        sftp.put(local, remote)
        print(f"    {remote}")
    sftp.chmod(SCRIPT, 0o755)
    sftp.chmod(SCRIPT2, 0o755)

    if a.seed_cache:
        src = os.path.join(OVERSPEED, "data", "days")
        days = sorted(d for d in os.listdir(src)) if os.path.isdir(src) else []
        print(f"1b. seeding the per-day cache ({len(days)} days) so the first server run is short")
        _, existing, _ = run(f"ls {REMOTE}/overspeed/data/days 2>/dev/null", show=False)
        have = set(existing.split())
        for d in days:
            if d in have and d not in days[-3:]:
                continue
            run(f"mkdir -p {REMOTE}/overspeed/data/days/{d}", show=False)
            for fn in os.listdir(os.path.join(src, d)):
                sftp.put(os.path.join(src, d, fn), f"{REMOTE}/overspeed/data/days/{d}/{fn}")
        print(f"    done ({len(days) - len([d for d in days if d in have and d not in days[-3:]])} days uploaded)")
        src2 = os.path.join(OPKPI, "data", "days")
        days2 = sorted(os.listdir(src2)) if os.path.isdir(src2) else []
        _, existing2, _ = run(f"ls {REMOTE}/operator_kpi/data/days 2>/dev/null", show=False)
        have2 = set(existing2.split())
        n2 = 0
        for d in days2:
            if d in have2 and d not in days2[-7:]:
                continue
            run(f"mkdir -p {REMOTE}/operator_kpi/data/days/{d}", show=False)
            for fn in os.listdir(os.path.join(src2, d)):
                sftp.put(os.path.join(src2, d, fn), f"{REMOTE}/operator_kpi/data/days/{d}/{fn}")
            n2 += 1
        print(f"    operator KPI cache: {n2} of {len(days2)} days uploaded")

    print("2. writing .env (C4M_DB_* only, mode 600)")
    with sftp.open(f"{REMOTE}/.env", "w") as fh:
        fh.write("# written by overspeed/server/install_server.py - only what the fetch needs\n"
                 f"C4M_DB_IP_ADDRESS='{c4m['ip']}'\nC4M_DB_USERNAME='{c4m['user']}'\n"
                 f"C4M_DB_PASSWORD='{c4m['password']}'\nC4M_DB_MODE='ssh'\n")
    sftp.chmod(f"{REMOTE}/.env", stat.S_IRUSR | stat.S_IWUSR)
    sftp.close()

    print("3. python venv + packages")
    rc, _, _ = run(f"test -x {REMOTE}/venv/bin/python || python3 -m venv {REMOTE}/venv", timeout=300)
    if rc != 0:
        print("    venv with pip failed - bootstrapping pip manually")
        run(f"python3 -m venv --without-pip {REMOTE}/venv && curl -sS https://bootstrap.pypa.io/get-pip.py | {REMOTE}/venv/bin/python", timeout=300)
    if not a.skip_pip:
        rc, _, _ = run(f"{REMOTE}/venv/bin/pip install -q --disable-pip-version-check pandas pyarrow paramiko", timeout=900)
        if rc != 0:
            sys.exit("pip install failed - see above")
    run(f"{REMOTE}/venv/bin/python -c \"import pandas, pyarrow, paramiko; print('pandas', pandas.__version__, 'pyarrow', pyarrow.__version__, 'paramiko', paramiko.__version__)\"")

    if not a.no_run:
        print("4. running one refresh now (fetch + build + deploy; ~2-3 min)")
        rc, _, _ = run(f"bash {SCRIPT}", timeout=1500, show=False)
        run(f"tail -n 25 $(ls -t {REMOTE}/logs/refresh_*.log | head -1)")
        if rc != 0:
            sys.exit(f"refresh exited {rc} - cron NOT installed")
        print("4b. running one operator KPI refresh now (fetch + build + deploy)")
        rc, _, _ = run(f"bash {SCRIPT2}", timeout=2400, show=False)
        run(f"tail -n 12 $(ls -t {REMOTE}/logs/refresh_opkpi_*.log | head -1)")
        if rc != 0:
            sys.exit(f"operator KPI refresh exited {rc} - cron NOT installed")

    print(f"5. cron: {a.cron} (over-speed), {a.cron_opkpi} (operator KPI)")
    line = f"{a.cron} $HOME/{SCRIPT}".replace("$HOME", "/home/" + srv["user"])
    line2 = f"{a.cron_opkpi} $HOME/{SCRIPT2}".replace("$HOME", "/home/" + srv["user"])
    run("(crontab -l 2>/dev/null | grep -v -e refresh_overspeed.sh -e refresh_operator_kpi.sh; echo '" + line + "'; echo '" + line2 + "') | crontab -", show=False)
    run("crontab -l")
    cli.close()
    print("done")


if __name__ == "__main__":
    main()
