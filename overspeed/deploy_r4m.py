"""Deploy the daily report (+ its over-speed sheet) to the R4M app server.

Target: /opt/R4M/storage/www/r4m_custom_report/ on the R4M_APP server from ../.env, served at
https://r4m.example.local/r4m_custom_report/<file>. Every file that already exists on the server
is backed up next to itself as <name>.bak-<YYYYmmdd-HHMM> before it is overwritten.

Run:  python deploy_r4m.py                      # daily_report_v3.html + overspeed_report.html + operator_kpi.html
      python deploy_r4m.py --only overspeed     # just the over-speed snapshot
      python deploy_r4m.py --only opkpi daily   # the operator KPI page and the daily report
"""
import argparse
import datetime as dt
import os
import stat
import sys

import paramiko

import env

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REMOTE_DIR = "/opt/R4M/storage/www/r4m_custom_report"
URL = "https://r4m.example.local/r4m_custom_report/"
FILES = {
    "daily": os.path.join(ROOT, "daily_report", "daily_report_v3.html"),
    "overspeed": os.path.join(HERE, "overspeed_report.html"),
    "opkpi": os.path.join(ROOT, "operator_kpi", "operator_kpi.html"),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="+", choices=sorted(FILES), help="deploy only these files (daily, overspeed, opkpi)")
    a = ap.parse_args()
    todo = {k: v for k, v in FILES.items() if not a.only or k in a.only}
    for k, v in todo.items():
        if not os.path.exists(v):
            sys.exit(f"missing {v} - build it first")

    srv = env.server("R4M_APP")
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(srv["ip"], username=srv["user"], password=srv["password"], timeout=15,
                allow_agent=False, look_for_keys=False)
    sftp = cli.open_sftp()
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M")
    try:
        existing = set(sftp.listdir(REMOTE_DIR))
        for k, local in todo.items():
            name = os.path.basename(local)
            remote = f"{REMOTE_DIR}/{name}"
            if name in existing:
                bak = f"{remote}.bak-{stamp}"
                cli.exec_command(f"cp -p '{remote}' '{bak}'")[1].channel.recv_exit_status()
                print(f"  backed up {name} -> {os.path.basename(bak)}")
            tmp = remote + ".uploading"
            sftp.put(local, tmp)
            sftp.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
            sftp.posix_rename(tmp, remote)           # atomic swap: readers never see a half file
            size = sftp.stat(remote).st_size
            print(f"  uploaded {name}  ({size / 1e6:.1f} MB)")
            _, out, _ = cli.exec_command(f"curl -sk -o /dev/null -w '%{{http_code}} %{{size_download}}' {URL}{name}")
            code, dl = out.read().decode().split()
            ok = code == "200" and int(dl) == size
            print(f"  {URL}{name} -> HTTP {code}, {int(dl) / 1e6:.1f} MB {'OK' if ok else 'MISMATCH'}")
            if not ok:
                sys.exit(1)
    finally:
        sftp.close()
        cli.close()
    print("done")


if __name__ == "__main__":
    main()
