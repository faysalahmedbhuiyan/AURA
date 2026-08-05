"""
AURA Backend — Firewall Controller (Tier 6, B4 — the "hands" of the
auto-response system).

Module: app.security.firewall_controller
Purpose: The ONLY module that actually executes system-level defensive
         actions (block an IP, disable wifi, shut down). Kept separate
         and small so it's easy to audit exactly what AURA is allowed
         to do to the machine.

Requires: AURA's backend process must run with sufficient privileges
          (root, or specific sudoers rules for `ufw`, `nmcli`,
          `shutdown`) on Ubuntu. Wire this up via systemd running as
          root, or a narrow sudoers file — NOT by running your whole
          dev session as root casually.
"""

import logging
import subprocess

logger = logging.getLogger(__name__)


class FirewallController:
    """Executes IP blocking, wifi disable, and shutdown. Ubuntu-only."""

    def block_ip(self, ip: str) -> dict:
        """Block a specific IP via ufw."""
        try:
            result = subprocess.run(
                ["sudo", "ufw", "deny", "from", ip],
                capture_output=True, text=True, timeout=10,
            )
            success = result.returncode == 0
            if success:
                logger.warning("Blocked IP via ufw: %s", ip)
            else:
                logger.error("Failed to block IP %s: %s", ip, result.stderr)
            return {"success": success, "ip": ip, "output": result.stdout or result.stderr}
        except Exception as e:
            logger.error("block_ip failed: %s", e)
            return {"success": False, "ip": ip, "error": str(e)}

    def disable_wifi(self) -> dict:
        """Turn off wifi via nmcli (NetworkManager, standard on Ubuntu desktop)."""
        try:
            result = subprocess.run(
                ["nmcli", "radio", "wifi", "off"],
                capture_output=True, text=True, timeout=10,
            )
            success = result.returncode == 0
            logger.critical("WIFI DISABLED by AURA security response. success=%s", success)
            return {"success": success, "output": result.stdout or result.stderr}
        except Exception as e:
            logger.error("disable_wifi failed: %s", e)
            return {"success": False, "error": str(e)}

    def shutdown_system(self, delay_seconds: int = 10) -> dict:
        """
        Shut down the machine. Delay gives a small window for the alert
        to actually reach the user before power-off — do not set this
        to 0 unless you have alerting confirmed working independently.
        """
        try:
            logger.critical(
                "SYSTEM SHUTDOWN triggered by AURA security response "
                "(in %ds).", delay_seconds,
            )
            result = subprocess.run(
                ["sudo", "shutdown", "-h", f"+{max(1, delay_seconds // 60) if delay_seconds >= 60 else 0}"]
                if delay_seconds >= 60 else
                ["sudo", "shutdown", "-h", "now"],
                capture_output=True, text=True, timeout=10,
            )
            return {"success": result.returncode == 0, "output": result.stdout or result.stderr}
        except Exception as e:
            logger.error("shutdown_system failed: %s", e)
            return {"success": False, "error": str(e)}

    def cancel_shutdown(self) -> dict:
        """Abort a pending scheduled shutdown (in case of false positive)."""
        try:
            result = subprocess.run(
                ["sudo", "shutdown", "-c"], capture_output=True, text=True, timeout=10,
            )
            return {"success": result.returncode == 0, "output": result.stdout or result.stderr}
        except Exception as e:
            return {"success": False, "error": str(e)}


firewall_controller = FirewallController()
