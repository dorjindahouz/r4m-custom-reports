"""Minimal .env reader (stdlib only, no python-dotenv).

Reads ../.env (repo root) which holds the VM/OS logins transcribed from IT's server
sheet. Values are single-quoted; hostnames contain spaces, so callers must use the
*_IP_ADDRESS keys. Nothing here ever prints a value.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(os.path.dirname(HERE), ".env")

_cache = None


def load(path=ENV_PATH):
    global _cache
    if _cache is not None and path == ENV_PATH:
        return _cache
    vals = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                v = v.strip()
                if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
                    v = v[1:-1]
                vals[k.strip()] = v
    if path == ENV_PATH:
        _cache = vals
    return vals


def get(key, default=None):
    """Environment variable wins over the .env file (lets you override at run time)."""
    return os.environ.get(key) or load().get(key, default)


def server(prefix="C4M_DB"):
    """Return {ip, user, password} for one of the server blocks in .env."""
    return {
        "ip": get(f"{prefix}_IP_ADDRESS"),
        "user": get(f"{prefix}_USERNAME"),
        "password": get(f"{prefix}_PASSWORD"),
    }
