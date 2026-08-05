# AURA Security Monitor — Ubuntu Setup

## 1. Permissions needed

The security monitor needs elevated access for some operations:
- Reading `/var/log/auth.log` (SSH brute-force detection) — needs root
  or membership in the `adm` group.
- `ufw` (blocking IPs), `nmcli` (wifi off), `shutdown` — need root or
  a narrow sudoers rule.

**Recommended: run the whole AURA backend as a systemd service under
root**, rather than granting broad sudo to your normal user. This is
also what makes the "auto-start on boot" part work.

## 2. Passwordless sudo for the specific commands (if not running as root)

If you'd rather run AURA as your normal user, add a narrow sudoers
rule (`sudo visudo -f /etc/sudoers.d/aura-security`):

```
your_username ALL=(ALL) NOPASSWD: /usr/sbin/ufw, /usr/sbin/shutdown
```

(`nmcli radio wifi off` doesn't need root on most desktop setups —
test it directly first: `nmcli radio wifi off`)

## 3. systemd service (auto-start on boot)

Create `/etc/systemd/system/aura-security.service`:

```ini
[Unit]
Description=AURA Backend (with Security Monitor)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/path/to/AURA/backend
ExecStart=/path/to/AURA/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable aura-security
sudo systemctl start aura-security
sudo systemctl status aura-security
```

View logs:

```bash
sudo journalctl -u aura-security -f
```

## 4. Start the monitor loop itself

The systemd service starts the *backend*, but the monitor loop is
opt-in (so it doesn't start scanning before you're ready). Start it:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/security/start
```

Check status / recent alerts any time:

```bash
curl http://127.0.0.1:8000/api/v1/security/status
```

## 5. Tuning false positives

Thresholds live in `app/security/threat_detector.py`:
- `PORT_SCAN_THRESHOLD` (default 15 distinct ports)
- `CONNECTION_FLOOD_THRESHOLD` (default 40 connections)
- `SSH_FAILURE_THRESHOLD` (default 5 failed logins)

If you get false-positive HIGH/CRITICAL alerts (e.g. from normal
heavy browsing traffic), raise these numbers before trusting the
auto-shutdown behavior. **Test with `/security/status` and log
output for at least a few days before relying on auto-shutdown** —
a false-positive shutdown while you're mid-task is a real cost.

## 6. Testing safely

To test without risking an unwanted real shutdown:
1. Temporarily comment out the `firewall_controller.shutdown_system(...)`
   call in `alert_service.py`'s CRITICAL branch.
2. Trigger a test (e.g. `nmap` your own machine from another device
   to simulate a port scan) and confirm you see the desktop
   notification + alert log entry.
3. Once you trust the detection is accurate, re-enable the shutdown call.
