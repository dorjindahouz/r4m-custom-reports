# Publishing the plan automatically on r4m.example.local (+ on-demand data refresh)

`publish_server.py` now has a second job (2026-10-11): the **Refresh data** button on the
Operator KPI page POSTs `/r4m_custom_report/refresh` (`{"job":"opkpi"}`) and polls
`/r4m_custom_report/refresh/status?job=opkpi`. The service runs the same script the nightly
cron runs (`~/r4m_overspeed/operator_kpi/server/refresh_operator_kpi.sh`, SELECT-only against
C4M, ≈1–2 min), one run at a time, with a 10-minute cool-down between runs; the page reloads
itself when the run finishes. No key: the job cannot change anything but the snapshot page.
Gateway route: `prefix_stop /r4m_custom_report/refresh` → service `custom_report_publish`
(route id 19, config revision 4; DB backup `~/server/nginxDB_backup_20261011_185128/`). Unit
ExecStart gained `--jobs-base %h/r4m_overspeed --refresh-cooldown 600`. `job=overspeed` is
also accepted (no button for it yet).


The report (`/opt/R4M/storage/www/r4m_custom_report/daily_report_v3.html`) reads
`published_inputs.json` from its own folder on load and overlays it on the baked
defaults. The **Publish inputs** button POSTs the plan to `publish` in the same
folder. `publish_server.py` (standard library, ~100 lines) is the service behind
that POST; R4M's own backend serves the JSON file as a static file like the HTML.

## What is deployed on the R4M app server (192.0.2.18) — 2026-10-10

| Piece | Where | Notes |
|---|---|---|
| Service | `~deploy/server/publish_server.py` | runs as `deploy` (the report folder's owner); listens on 172.18.0.1:8790 (the docker-host address on the `r4m` bridge network) |
| Unit | `~deploy/.config/systemd/user/r4m-custom-report-publish.service` | user-level systemd unit, linger enabled → survives logout and reboot |
| Publish key | `~deploy/.config/r4m_custom_report/publish.key` (mode 600) | read it on the box: `cat ~/.config/r4m_custom_report/publish.key` |
| nginx route | **R4M gateway manager** (its DB `/opt/R4M/storage/nginxDB/config.db`: upstream_host `172.18.0.1`, service `custom_report_publish`, route exact `/r4m_custom_report/publish`, requires_auth 0) | applied as config revision 3 on 2026-10-10; the manager renders, validates and applies nginx config itself and reverts hand edits; a backup of the DB before the change is in `~deploy/server/nginxDB_backup_20261010_212436/` |
| Firewall | ufw rule `8790/tcp ALLOW 172.18.0.0/16` | containers on the `r4m` docker network may reach the service; nothing else |
| Published plan | `/opt/R4M/storage/www/r4m_custom_report/published_inputs.json` | written atomically on each publish |
| History | `/opt/R4M/storage/www/r4m_custom_report/plan_history/published_inputs_<stamp>.json` | one file per publish |

Operate it as `deploy`:

```sh
systemctl --user status r4m-custom-report-publish      # running?
systemctl --user restart r4m-custom-report-publish     # after replacing publish_server.py
journalctl --user -u r4m-custom-report-publish -n 50   # log (one line per request)
curl -s http://127.0.0.1:8790/health                   # {"ok": true, "publishedAt": "..."}
```

## Install / update

1. `scp -r daily_report/server deploy@192.0.2.18:~/` (the service file and scripts).
2. First time, as deploy (no sudo): create the key, enable the user unit, enable linger —
   i.e.:
   ```sh
   mkdir -p ~/.config/r4m_custom_report ~/.config/systemd/user
   python3 -c "import secrets; print(secrets.token_urlsafe(18))" > ~/.config/r4m_custom_report/publish.key; chmod 600 ~/.config/r4m_custom_report/publish.key
   # unit file as in the table above, then:
   systemctl --user daemon-reload && systemctl --user enable --now r4m-custom-report-publish && loginctl enable-linger deploy
   ```
3. Firewall, once, with sudo (ufw is on and blocks container→host ports):
   `sudo ufw allow from 172.18.0.0/16 to any port 8790 proto tcp comment 'r4m custom report publish'`
4. Route, once, in the R4M gateway admin panel (the one that manages certificates) — do NOT edit
   nginx files by hand, the manager reconciles them from its database within seconds:
   - Upstream host: name `172.18.0.1`, scheme http (the docker host as seen from the `r4m` network)
   - Service: slug `custom_report_publish`, upstream host `172.18.0.1`, port `8790`
   - Route: path `/r4m_custom_report/publish`, match `exact`, kind `proxy`, service `custom_report_publish`,
     strip prefix off, client max body 8m, requires auth **on** (publishing then also needs an R4M login)
   - Apply the configuration (config → apply). Check: `curl -sk -o /dev/null -w '%{http_code}' -X POST https://r4m.example.local/r4m_custom_report/publish -H 'X-Publish-Key: wrong' -d '{}'` → 403 (or 401 without an R4M session)
5. Copy the new `daily_report_v3.html` into the report folder (keep a `.bak_<date>` copy).


## Checks

```sh
curl -sk https://r4m.example.local/r4m_custom_report/published_inputs.json      # 404 until the first publish
curl -sk -o /dev/null -w "%{http_code}\n" -X POST https://r4m.example.local/r4m_custom_report/publish -H 'X-Publish-Key: wrong' -d '{}'   # 403
```

In the report: Inputs panel → edit a target → **Publish inputs** → enter the key →
the bar turns green with the publish time. Reload in another browser: same numbers.
Every viewer gets the new plan on their next reload; no rebuild, no upload.

## Rollback / history

Copy one of the `plan_history/` files over `published_inputs.json` (as deploy).

## Giving or revoking publish rights

Give someone the key. To revoke it for everyone, write a new key into the key
file — it is read on every request, no restart needed. The report folder is
served without the R4M login, so the key is the only gate on publishing.
