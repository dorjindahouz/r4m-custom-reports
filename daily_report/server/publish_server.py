#!/usr/bin/env python3
"""Publish + refresh service for the custom report pages on the R4M app server.

Two jobs, both tiny, standard library only, listening on the docker-host address so only
R4M's gateway container reaches it:

1. PUBLISH (daily report plan): accept the plan the page POSTs and write it as
   published_inputs.json in the report folder, so the next reload of the report (any browser,
   any user) picks it up. Gated by a key (header X-Publish-Key) read from --key-file; every
   publish is also kept in <www>/plan_history/.
   Closed months are locked (Erdene, 2026-10-29): a publish that changes any value dated in a
   month before the running one (or a "YYYY" value of a past year) is refused with 423 unless
   the same key is also sent as X-Closed-Unlock, which the page only does after the user has
   typed the password for that publish. One universal password (user).

2. REFRESH (Operator KPI / Over-speed snapshots): run the same scripts the nightly cron runs,
   on demand, from the page's "Refresh data" button. One run at a time, a cool-down between
   runs, SELECT-only against C4M, so no key is needed. The scripts log into
   <jobs-base>/logs/ themselves; this service only tracks state.

Gateway routes (R4M gateway manager, service custom_report_publish -> 172.18.0.1:8790):
    exact        /r4m_custom_report/publish      (client max body 8m)
    prefix_stop  /r4m_custom_report/refresh      (-> /refresh, /refresh/status)

    python3 publish_server.py --www /opt/R4M/storage/www/r4m_custom_report \\
        --key-file ~/.config/r4m_custom_report/publish.key --jobs-base ~/r4m_overspeed \\
        --port 8790 --bind 172.18.0.1
"""
import argparse
import http.server
import json
import os
import re
import subprocess
import sys
import threading
import time

MAX_BODY = 8 * 1024 * 1024
REQUIRED = ("daily",)           # the page always sends these top-level blocks

# refresh jobs: name -> (script relative to --jobs-base, log prefix, page file)
JOBS = {
    "opkpi":     ("operator_kpi/server/refresh_operator_kpi.sh", "refresh_opkpi_", "operator_kpi.html"),
    "overspeed": ("overspeed/server/refresh_overspeed.sh",       "refresh_",       "overspeed_report.html"),
}
STATE = {}                      # job -> dict(running, started, finished, rc, pid)
LOCK = threading.Lock()


def read_key(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read().strip()


PERIOD_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
SHIFT_H = 7                     # the shift day starts at 07:00


def is_closed(period, now=None):
    """'YYYY-MM-DD' / 'YYYY-MM' closed = before the running month; 'YYYY' = before the running year."""
    t = time.localtime((now or time.time()) - SHIFT_H * 3600)
    if len(period) == 4:
        return int(period) < t.tm_year
    return period[:7] < "%04d-%02d" % (t.tm_year, t.tm_mon)


def closed_cells(obj, path="", period=None, out=None):
    """{path: value} of every leaf that belongs to a closed period. The period is the first
    date-like key on the path; items of a list carry their own `date`."""
    if out is None:
        out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.startswith("__"):
                continue
            p = period or (k if PERIOD_RE.match(k) else None)
            closed_cells(v, path + "/" + k, p, out)
    elif isinstance(obj, list):
        for v in obj:
            d = v.get("date") if isinstance(v, dict) else None
            p = period or (d[:10] if isinstance(d, str) and PERIOD_RE.match(d[:10]) else None)
            if p:                    # list items have no stable index: keyed by their content
                out[path + "[]" + json.dumps(v, sort_keys=True)] = (p, True)
    elif period and obj is not None and obj != "" and is_closed(period):
        out[path] = (period, obj)
    if not path:
        return {k: v for k, v in out.items() if is_closed(v[0])}
    return out


def closed_changes(old, new):
    """Sorted list of the closed periods whose values differ between two plans."""
    a, b = closed_cells(old), closed_cells(new)
    months = set()
    for k in set(a) | set(b):
        va, vb = a.get(k), b.get(k)
        if va is None or vb is None:
            months.add((va or vb)[0][:7])
        elif va[1] != vb[1] and not (isinstance(va[1], (int, float)) and isinstance(vb[1], (int, float))
                                     and abs(va[1] - vb[1]) < 1e-9):
            months.add(va[0][:7])
    return sorted(months)


def strip_prefix(path):
    p = path.split("?")[0]
    if p.startswith("/r4m_custom_report/"):
        p = p[len("/r4m_custom_report"):]
    return p


def query(path):
    q = {}
    if "?" in path:
        for kv in path.split("?", 1)[1].split("&"):
            if "=" in kv:
                k, v = kv.split("=", 1)
                q[k] = v
    return q


class H(http.server.BaseHTTPRequestHandler):
    server_version = "r4m-custom-report-publish/2"
    www = key_file = jobs_base = None
    cooldown = 600

    def log_message(self, fmt, *a):     # one line per request, to journald via stdout
        sys.stdout.write("%s %s\n" % (self.address_string(), fmt % a))
        sys.stdout.flush()

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---- refresh ---------------------------------------------------------------------------
    def _job_status(self, job):
        script, logpre, page = JOBS[job]
        st = dict(STATE.get(job) or {})
        st.pop("pid", None)
        now = time.time()
        st["job"] = job
        st["running"] = bool(st.get("running"))
        st["elapsed"] = round(now - st["started"]) if st.get("running") and st.get("started") else None
        st["cooldownLeft"] = max(0, round(self.cooldown - (now - st["finished"]))) if st.get("finished") else 0
        p = os.path.join(self.www, page)
        st["pageAt"] = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(p))) if os.path.exists(p) else None
        st["available"] = os.path.exists(os.path.join(self.jobs_base, script)) if self.jobs_base else False
        logs = sorted(f for f in os.listdir(os.path.join(self.jobs_base, "logs")) if f.startswith(logpre)) if self.jobs_base and os.path.isdir(os.path.join(self.jobs_base, "logs")) else []
        if logs:
            try:
                with open(os.path.join(self.jobs_base, "logs", logs[-1]), encoding="utf-8", errors="replace") as fh:
                    lines = [l.rstrip() for l in fh.read().splitlines() if l.strip()]
                st["log"] = lines[-3:]
            except Exception:
                st["log"] = []
        for k in ("started", "finished"):
            if st.get(k):
                st[k] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st[k]))
        return st

    def _start_job(self, job):
        script = os.path.join(self.jobs_base, JOBS[job][0])
        env = dict(os.environ)
        env.setdefault("HOME", os.path.expanduser("~"))
        env["PYTHONIOENCODING"] = "utf-8"
        p = subprocess.Popen(["bash", script], cwd=os.path.dirname(script), env=env,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        STATE[job] = {"running": True, "started": time.time(), "finished": None, "rc": None, "pid": p.pid}

        def wait():
            rc = p.wait()
            with LOCK:
                STATE[job].update(running=False, finished=time.time(), rc=rc)
            sys.stdout.write("refresh %s finished rc=%s\n" % (job, rc))
            sys.stdout.flush()
        threading.Thread(target=wait, daemon=True).start()

    def do_GET(self):
        p = strip_prefix(self.path)
        if p in ("/publish/health", "/health", "/publish"):
            f = os.path.join(self.www, "published_inputs.json")
            at = None
            if os.path.exists(f):
                try:
                    with open(f, encoding="utf-8") as fh:
                        at = json.load(fh).get("__publishedAt")
                except Exception:
                    at = "unreadable"
            self._json(200, {"ok": True, "publishedAt": at})
            return
        if p in ("/refresh/status", "/refresh"):
            job = query(self.path).get("job", "opkpi")
            if job not in JOBS:
                self._json(400, {"ok": False, "error": "unknown job"})
                return
            with LOCK:
                self._json(200, dict(ok=True, **self._job_status(job)))
            return
        self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        p = strip_prefix(self.path)
        if p == "/refresh":
            self._post_refresh()
            return
        if p != "/publish":
            self._json(404, {"ok": False, "error": "not found"})
            return
        try:
            key = read_key(self.key_file)
        except Exception:
            self._json(500, {"ok": False, "error": "key file missing"})
            return
        if not key or self.headers.get("X-Publish-Key", "").strip() != key:
            self._json(403, {"ok": False, "error": "bad key"})
            return
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX_BODY:
            self._json(413, {"ok": False, "error": "body size"})
            return
        try:
            plan = json.loads(self.rfile.read(n).decode("utf-8"))
            assert isinstance(plan, dict) and all(k in plan for k in REQUIRED)
        except Exception:
            self._json(400, {"ok": False, "error": "not a plan"})
            return
        plan.pop("__notes", None)                      # photos never go to the shared plan
        cur = {}
        try:
            with open(os.path.join(self.www, "published_inputs.json"), encoding="utf-8") as fh:
                cur = json.load(fh)
        except FileNotFoundError:
            pass
        except Exception:
            self._json(500, {"ok": False, "error": "published plan unreadable"})
            return
        locked = closed_changes(cur, plan)
        if locked and self.headers.get("X-Closed-Unlock", "").strip() != key:
            self._json(423, {"ok": False, "error": "closed months locked", "months": locked})
            return
        plan["__publishedAt"] = time.strftime("%Y-%m-%d %H:%M")
        plan["__publishedFrom"] = self.address_string()
        data = json.dumps(plan, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        hist = os.path.join(self.www, "plan_history")
        os.makedirs(hist, exist_ok=True)
        with open(os.path.join(hist, "published_inputs_%s.json" % time.strftime("%Y%m%d_%H%M%S")), "wb") as fh:
            fh.write(data)
        tmp = os.path.join(self.www, "published_inputs.json.tmp")
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, os.path.join(self.www, "published_inputs.json"))   # atomic swap
        self._json(200, {"ok": True, "publishedAt": plan["__publishedAt"], "bytes": len(data)})

    def _post_refresh(self):
        n = int(self.headers.get("Content-Length") or 0)
        job = "opkpi"
        if 0 < n <= 4096:
            try:
                job = json.loads(self.rfile.read(n).decode("utf-8")).get("job", "opkpi")
            except Exception:
                pass
        else:
            job = query(self.path).get("job", job)
        if job not in JOBS:
            self._json(400, {"ok": False, "error": "unknown job"})
            return
        if not self.jobs_base or not os.path.exists(os.path.join(self.jobs_base, JOBS[job][0])):
            self._json(503, {"ok": False, "error": "refresh script not installed on this server"})
            return
        with LOCK:
            st = STATE.get(job) or {}
            if st.get("running"):
                self._json(409, dict(ok=False, error="already running", **self._job_status(job)))
                return
            left = self.cooldown - (time.time() - st["finished"]) if st.get("finished") else 0
            if left > 0:
                self._json(429, dict(ok=False, error="cool-down", **self._job_status(job)))
                return
            self._start_job(job)
            sys.stdout.write("refresh %s started by %s\n" % (job, self.address_string()))
            self._json(202, dict(ok=True, **self._job_status(job)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--www", required=True, help="report folder (where published_inputs.json is written)")
    ap.add_argument("--key-file", required=True, help="file holding the publish key")
    ap.add_argument("--jobs-base", default="", help="folder holding the nightly refresh jobs (~/r4m_overspeed); empty = refresh disabled")
    ap.add_argument("--refresh-cooldown", type=int, default=600, help="seconds between two on-demand refreshes of the same job")
    ap.add_argument("--port", type=int, default=8790)
    ap.add_argument("--bind", default="127.0.0.1")
    a = ap.parse_args()
    if not os.path.isdir(a.www):
        sys.exit("not a directory: " + a.www)
    H.www, H.key_file = a.www, a.key_file
    H.jobs_base = os.path.expanduser(a.jobs_base) if a.jobs_base else None
    H.cooldown = a.refresh_cooldown
    print("publish service: www=%s key=%s jobs=%s on %s:%d" % (a.www, a.key_file, H.jobs_base, a.bind, a.port), flush=True)
    http.server.ThreadingHTTPServer((a.bind, a.port), H).serve_forever()


if __name__ == "__main__":
    main()
