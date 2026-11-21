"""Connection to the C4M (FMS) PostgreSQL database.

Auth ladder (plan step 1):
  a. direct psycopg2 to <C4M_DB_IP>:5432 with the .env OS login as a Postgres role,
     trying a few likely database names (and C4M_DB_NAME / C4M_DB_USER /
     C4M_DB_PASSWORD_PG overrides from the environment or .env if the user adds them);
  b. SSH to the box as the OS user and run psql server-side as the `postgres` superuser
     (peer auth), streaming results back as TSV.
Whichever rung works is cached; `run_query(sql, params)` returns a DataFrame either way.
Secrets are never printed.

Run `python db.py` for a smoke test (server version, database, schemas).
"""
import io
import os
import re
import sys

import pandas as pd

import env

PORT = int(env.get("C4M_DB_PORT", "5432"))
DB_CANDIDATES = [n for n in [env.get("C4M_DB_NAME")] if n] + \
                ["ControlSenseDB", "c4m", "C4M", "ms4m", "postgres", "deploy"]

_conn = None          # psycopg2 connection when the direct rung works
_ssh = None           # paramiko client when the SSH rung works
_ssh_db = None        # database chosen on the SSH rung
_mode = None


def _log(msg):
    print(f"[db] {msg}", file=sys.stderr)


# --------------------------------------------------------------------------- #
# rung a: direct
# --------------------------------------------------------------------------- #
def _try_direct():
    import psycopg2
    srv = env.server("C4M_DB")
    users = [u for u in [env.get("C4M_DB_USER"), srv["user"], "postgres"] if u]
    pw = env.get("C4M_DB_PASSWORD_PG") or srv["password"]
    seen = set()
    for user in users:
        for dbname in DB_CANDIDATES:
            if (user, dbname) in seen:
                continue
            seen.add((user, dbname))
            try:
                c = psycopg2.connect(host=srv["ip"], port=PORT, user=user, password=pw,
                                     dbname=dbname, connect_timeout=5)
                c.set_session(readonly=True, autocommit=True)
                _log(f"direct user={user} db={dbname} -> ok")
                return c
            except Exception as e:  # noqa: BLE001
                reason = str(e).strip().splitlines()[0]
                _log(f"direct user={user} db={dbname} -> failed: {reason}")
    return None


# --------------------------------------------------------------------------- #
# rung b: ssh + server-side psql
# --------------------------------------------------------------------------- #
def _ssh_exec(cmd, timeout=120, sudo=False):
    """Run a remote command. With sudo=True the command must start with `sudo -S -p ''`
    and the OS password is written to its stdin (never on the command line)."""
    stdin, stdout, stderr = _ssh.exec_command(cmd, timeout=timeout)
    if sudo:
        stdin.write(env.server("C4M_DB")["password"] + "\n")
        stdin.flush()
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    rc = stdout.channel.recv_exit_status()
    return rc, out, err


_SUDO_PSQL = "sudo -S -p '' -u postgres psql -v ON_ERROR_STOP=1 -X -A --pset footer=off"


def _ssh_psql(sql, dbname, timeout=600):
    """Run SQL server-side as the postgres superuser; return (rc, tsv_out, err).
    The statement is uploaded to a temp file so no shell quoting is involved."""
    remote = f"/tmp/overspeed_{os.getpid()}.sql"
    sftp = _ssh.open_sftp()
    try:
        with sftp.open(remote, "w") as fh:
            fh.write(sql)
        sftp.chmod(remote, 0o644)
    finally:
        sftp.close()
    cmd = (f"{_SUDO_PSQL} -F \"$(printf '\t')\" -d {dbname} -f {remote}; "
           f"rc=$?; rm -f {remote}; exit $rc")
    return _ssh_exec(cmd, timeout=timeout, sudo=True)


def _try_ssh():
    import paramiko
    global _ssh, _ssh_db
    srv = env.server("C4M_DB")
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        cli.connect(srv["ip"], username=srv["user"], password=srv["password"], timeout=10,
                    allow_agent=False, look_for_keys=False)
    except Exception as e:  # noqa: BLE001
        _log(f"ssh {srv['user']}@{srv['ip']} -> failed: {e}")
        return False
    _ssh = cli
    _log(f"ssh {srv['user']}@{srv['ip']} -> ok")
    rc, out, err = _ssh_exec(_SUDO_PSQL + ' -t -c "select datname from pg_database where not datistemplate"', sudo=True)
    if rc != 0:
        tail = err.strip().splitlines()[-1] if err.strip() else rc
        _log(f"server-side psql as postgres -> failed: {tail}")
        return False
    dbs = [d for d in out.split() if d]
    _log(f"databases on server: {dbs}")
    pref = [n for n in DB_CANDIDATES if n in dbs]
    _ssh_db = pref[0] if pref else next((d for d in dbs if d != "postgres"), dbs[0])
    _log(f"ssh rung using db={_ssh_db}")
    return True


# --------------------------------------------------------------------------- #
# public
# --------------------------------------------------------------------------- #
def connect():
    global _conn, _mode
    if _mode:
        return _mode
    # C4M_DB_MODE=ssh skips the direct rung (saves ~10 s when you know it is refused)
    _conn = None if env.get("C4M_DB_MODE") == "ssh" else _try_direct()
    if _conn is not None:
        _mode = "direct"
        return _mode
    if _try_ssh():
        _mode = "ssh"
        return _mode
    raise RuntimeError("Could not reach the C4M database: direct Postgres login and SSH "
                       "fallback both failed (see [db] lines above). Ask IT for a read-only "
                       "Postgres role and put it in .env as C4M_DB_USER / C4M_DB_PASSWORD_PG / "
                       "C4M_DB_NAME.")


def mode():
    return connect()


def current_db():
    connect()
    return _conn.get_dsn_parameters()["dbname"] if _mode == "direct" else _ssh_db


def run_query(sql, params=None):
    """Run a SELECT and return a DataFrame. params: dict for %(name)s placeholders."""
    connect()
    if _mode == "direct":
        return pd.read_sql_query(sql, _conn, params=params)
    # ssh rung: inline the parameters as SQL literals (read-only, values are dates/ints)
    if params:
        def lit(v):
            if v is None:
                return "NULL"
            if isinstance(v, (int, float)):
                return repr(v)
            return "'" + str(v).replace("'", "''") + "'"
        sql = re.sub(r"%\((\w+)\)s", lambda m: lit(params[m.group(1)]), sql)
    rc, out, err = _ssh_psql(sql, _ssh_db)
    if rc != 0:
        raise RuntimeError(f"psql failed: {err.strip()}")
    if not out.strip():
        return pd.DataFrame()
    return pd.read_csv(io.StringIO(out), sep="\t", dtype=str, keep_default_na=False,
                       na_values=[""])


def switch_db(dbname):
    """Point subsequent queries at another database (same server)."""
    global _conn, _ssh_db
    connect()
    if _mode == "direct":
        import psycopg2
        p = _conn.get_dsn_parameters()
        pw = env.get("C4M_DB_PASSWORD_PG") or env.server("C4M_DB")["password"]
        _conn = psycopg2.connect(host=p["host"], port=p["port"], user=p["user"],
                                 password=pw, dbname=dbname, connect_timeout=5)
        _conn.set_session(readonly=True, autocommit=True)
    else:
        _ssh_db = dbname


if __name__ == "__main__":
    print("mode:", connect())
    print("database:", current_db())
    print(run_query("select version() as v").iloc[0, 0])
    print(run_query("select datname from pg_database where not datistemplate order by 1"))
    print(run_query("select schema_name from information_schema.schemata "
                    "where schema_name not in ('pg_catalog','information_schema','pg_toast') order by 1"))
