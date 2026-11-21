"""Serve daily_report_v3.html with LIVE data on this machine.

The page fetches R4M with origin-relative URLs (/cube/..., /duckdb/...), so it
must be served from the same host as the R4M APIs. This script emulates that
locally: it serves this folder over HTTP and proxies /cube/* (parquet exports),
/duckdb/* (the R4M app's grades endpoint) and /dimensions/* (the HPGPS
backend: polygon boundaries, dig lines) to r4m.example.local (TLS verify off -
the cert is self-signed). You must be on the Erdene network.

Run:   python serve_local.py --login      (asks for your R4M username/password)
       python serve_local.py              (no login: the page shows its baked snapshot)
Open:  http://127.0.0.1:8123/daily_report_v3.html

Auth (since ~2026-09 every /cube/, /duckdb/, /dimensions/ path is 401 without
it). The R4M app logs in exactly like this script does:
  1. make a P-256 key pair; POST /auth/login {username, password, client_pubkey}
     where client_pubkey = base64 SPKI of the public key -> sets r4m_session;
  2. every request then carries that cookie PLUS a DPoP proof (RFC 9449): a JWT
     {typ: dpop+jwt, alg: ES256, jwk} . {jti, htm, htu, iat} signed with the
     private key - bound to method, full URL and time, so it is minted fresh
     per request and cannot be replayed.
The session is bound to this process's key, so a cookie copied from a browser
tab is useless here (and vice versa). The password is read with getpass (or
from R4M_PASSWORD for unattended runs) and kept in memory only, to log in again
if the session expires. R4M_USER skips the username prompt.

Test switches (env vars):
  FORCE_401=1    every proxied path returns 401   -> auth error path
  FAIL_GRADES=1  only /duckdb/* fails (503)        -> cube-only grades fallback
  FAIL_GEO=1     only /dimensions/* fails (503)    -> viewer without planned polygons
"""
import base64
import getpass
import http.cookiejar
import http.server
import json
import os
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid

DOCROOT = os.path.dirname(os.path.abspath(__file__))
UPSTREAM = "https://r4m.example.local"
PORT = int(os.environ.get("PORT", "8123"))
FORCE_401 = os.environ.get("FORCE_401") == "1"
FAIL_GRADES = os.environ.get("FAIL_GRADES") == "1"
FAIL_GEO = os.environ.get("FAIL_GEO") == "1"
PROXIED = ("/cube/", "/duckdb/", "/dimensions/")   # NB: R4M nginx routes only lowercase /duckdb/
# read-only passthrough for exploring other R4M endpoints through the same
# session: GET /r4m/<path> -> UPSTREAM/<path>  (GET only - nothing is written)
EXPLORE = "/r4m/"
PROBE = "/cube/dynamic/api/export?type=dimensions&name=material&format=parquet"

_ssl = ssl.create_default_context()
_ssl.check_hostname = False
_ssl.verify_mode = ssl.CERT_NONE


def _b64u(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


class R4MSession:
    """r4m_session cookie + per-request DPoP proofs, as the R4M Aurora SPA does."""

    def __init__(self, user, password):
        self.user, self._pw = user, password
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=_ssl),
            urllib.request.HTTPCookieProcessor(self.jar))
        self.lock = threading.Lock()
        self.key = None

    def _new_key(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        self.key = ec.generate_private_key(ec.SECP256R1())
        pub = self.key.public_key()
        n = pub.public_numbers()
        self.jwk = {"crv": "P-256", "kty": "EC",
                    "x": _b64u(n.x.to_bytes(32, "big")), "y": _b64u(n.y.to_bytes(32, "big"))}
        self.spki = base64.b64encode(pub.public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo)).decode()

    def proof(self, method, url):
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
        js = lambda o: json.dumps(o, separators=(",", ":")).encode()
        head = {"typ": "dpop+jwt", "alg": "ES256", "jwk": self.jwk}
        body = {"jti": str(uuid.uuid4()), "htm": method.upper(), "htu": url,
                "iat": int(time.time())}
        signing = _b64u(js(head)) + "." + _b64u(js(body))
        r, s = decode_dss_signature(self.key.sign(signing.encode(), ec.ECDSA(hashes.SHA256())))
        return signing + "." + _b64u(r.to_bytes(32, "big") + s.to_bytes(32, "big"))

    def login(self):
        """True on success; prints why not otherwise (never the password)."""
        self._new_key()
        self.jar.clear()
        url = UPSTREAM + "/auth/login"
        data = json.dumps({"username": self.user, "password": self._pw,
                           "client_pubkey": self.spki}).encode()
        rq = urllib.request.Request(url, data=data, method="POST", headers={
            "Content-Type": "application/json", "DPoP": self.proof("POST", url)})
        try:
            with self.opener.open(rq, timeout=60) as r:
                info = json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            msg = e.read()[:200].decode("utf-8", "replace").strip()
            wait = e.headers.get("Retry-After")
            print(f"R4M login as {self.user!r} failed: HTTP {e.code} {msg}"
                  + (f" (retry after {wait}s)" if wait else ""), flush=True)
            return False
        except Exception as e:
            print(f"R4M login: {UPSTREAM} unreachable ({type(e).__name__}: {e})", flush=True)
            return False
        got = [c.name for c in self.jar]
        print(f"R4M login as {self.user!r}: OK  (cookies: {', '.join(got) or 'none'})", flush=True)
        if info.get("must_change_password"):
            print("  NOTE: R4M says this account must change its password - do that in the R4M app.",
                  flush=True)
        return True

    def get(self, path, _retry=True):
        """(status, content_type, body) for an upstream GET; re-logs in once on 401."""
        url = UPSTREAM + path
        rq = urllib.request.Request(url, headers={"DPoP": self.proof("GET", url)})
        try:
            with self.opener.open(rq, timeout=300) as r:
                return r.status, r.headers.get("Content-Type"), r.read()
        except urllib.error.HTTPError as e:
            if e.code == 401 and _retry:
                with self.lock:
                    print("  session expired - logging in again", flush=True)
                    ok = self.login()
                if ok:
                    return self.get(path, _retry=False)
            raise


SESSION = None   # R4MSession once --login succeeds; None = anonymous pass-through


def upstream_get(path):
    if SESSION:
        return SESSION.get(path)
    rq = urllib.request.Request(UPSTREAM + path)
    with urllib.request.urlopen(rq, context=_ssl, timeout=300) as r:
        return r.status, r.headers.get("Content-Type"), r.read()


PUBLISH_KEY = os.environ.get("PUBLISH_KEY", "local")   # stub of server/publish_server.py


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=DOCROOT, **kw)

    def log_message(self, *a):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        """POST /publish  (header X-Publish-Key)  -> writes published_inputs.json
        exactly like the real service; keeps a copy in plan_history/."""
        if self.path.split("?")[0] != "/publish":
            self._json(404, {"ok": False, "error": "not found"})
            return
        if self.headers.get("X-Publish-Key", "") != PUBLISH_KEY:
            self._json(403, {"ok": False, "error": "bad key"})
            return
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > 8 * 1024 * 1024:
            self._json(413, {"ok": False, "error": "size"})
            return
        try:
            plan = json.loads(self.rfile.read(n))
            assert isinstance(plan, dict) and "daily" in plan
        except Exception:
            self._json(400, {"ok": False, "error": "not a plan"})
            return
        plan["__publishedAt"] = time.strftime("%Y-%m-%d %H:%M")
        data = json.dumps(plan, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        hist = os.path.join(DOCROOT, "plan_history")
        os.makedirs(hist, exist_ok=True)
        with open(os.path.join(hist, "published_inputs_%s.json" % time.strftime("%Y%m%d_%H%M%S")), "wb") as fh:
            fh.write(data)
        tmp = os.path.join(DOCROOT, "published_inputs.json.tmp")
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, os.path.join(DOCROOT, "published_inputs.json"))
        print(f"  published plan: {len(data)} bytes at {plan['__publishedAt']}", flush=True)
        self._json(200, {"ok": True, "publishedAt": plan["__publishedAt"]})

    def do_GET(self):
        if self.path.split("?")[0] == "/published_inputs.json":
            p = os.path.join(DOCROOT, "published_inputs.json")
            if not os.path.exists(p):
                self._json(404, {"ok": False, "error": "nothing published yet"})
                return
            with open(p, "rb") as fh:
                body = fh.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith(EXPLORE):
            try:
                status, ctype, body = upstream_get(self.path[len(EXPLORE) - 1:])
                self.send_response(status)
                self.send_header("Content-Type", ctype or "application/octet-stream")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except urllib.error.HTTPError as e:
                body = e.read()
                self.send_response(e.code)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_response(502)
                self.end_headers()
                self.wfile.write(str(e).encode())
            return
        if self.path.startswith(PROXIED):
            if FORCE_401:
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b"unauthorized")
                return
            if FAIL_GRADES and self.path.startswith("/duckdb/sensor/"):
                self.send_response(503)
                self.end_headers()
                self.wfile.write(b"grades endpoint down (test)")
                return
            if FAIL_GEO and self.path.startswith("/dimensions/"):
                self.send_response(503)
                self.end_headers()
                self.wfile.write(b"geometry endpoint down (test)")
                return
            try:
                _, ctype, body = upstream_get(self.path)
                self.send_response(200)
                self.send_header("Content-Type", ctype or "application/octet-stream")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except urllib.error.HTTPError as e:
                # a 401 here is the whole failure mode: say so instead of
                # letting the page fall back to its snapshot silently
                print(f"  upstream {e.code} for {self.path[:90]}", flush=True)
                self.send_response(e.code)
                self.end_headers()
            except Exception as e:
                self.send_response(502)
                self.end_headers()
                self.wfile.write(str(e).encode())
            return
        super().do_GET()


def probe():
    """One export through the same code path, so auth problems surface at start."""
    who = f"logged in as {SESSION.user!r}" if SESSION else "anonymous"
    try:
        status, _, body = upstream_get(PROBE)
        print(f"upstream {UPSTREAM}: {status}, {len(body)} bytes, parquet={body[:4] == b'PAR1'}  [{who}]",
              flush=True)
    except urllib.error.HTTPError as e:
        print(f"upstream {UPSTREAM}: HTTP {e.code}  [{who}]", flush=True)
        if e.code in (401, 403):
            print("  -> R4M requires a login: restart with  python serve_local.py --login\n"
                  "     Until then the page shows its baked snapshot.", flush=True)
    except Exception as e:
        print(f"upstream {UPSTREAM}: unreachable ({type(e).__name__}: {e})  "
              "-> not on the Erdene network?", flush=True)


if __name__ == "__main__":
    if "--login" in sys.argv[1:] or os.environ.get("R4M_USER"):
        user = os.environ.get("R4M_USER") or input("R4M username: ").strip()
        pw = os.environ.get("R4M_PASSWORD") or getpass.getpass(f"R4M password for {user}: ")
        s = R4MSession(user, pw)
        if s.login():
            SESSION = s
        else:
            print("continuing without a session - the page will show its snapshot", flush=True)
    print(f"serving {DOCROOT} on :{PORT} (FORCE_401={FORCE_401} FAIL_GRADES={FAIL_GRADES} FAIL_GEO={FAIL_GEO})", flush=True)
    probe()
    print(f"open http://127.0.0.1:{PORT}/daily_report_v3.html", flush=True)
    http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
