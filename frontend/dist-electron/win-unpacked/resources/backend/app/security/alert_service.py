"""
AURA Backend — Alert Service (Tier 6, B3).

Module: app.security.alert_service
Purpose: Turns a ThreatLevel into an actual response — desktop
         notification, log entry, and (for HIGH/CRITICAL) calls into
         firewall_controller. Has a cooldown per IP so a single
         ongoing attack doesn't trigger shutdown over and over.
"""

import logging
import subprocess
import time

from app.security.threat_detector import ThreatLevel

logger = logging.getLogger(__name__)

# Don't re-trigger the SAME action for the SAME ip within this window.
_ACTION_COOLDOWN_SECONDS = 600  # 10 minutes

# In-memory alert log — recent alerts, for a "security status" chat command.
_RECENT_ALERTS: list[dict] = []
_MAX_ALERTS_KEPT = 100
_last_action_time: dict = {}  # (ip, action) -> timestamp


class AlertService:
    """Decides on and executes a response for a detected threat."""

    def notify_desktop(self, title: str, message: str) -> None:
        """Ubuntu desktop notification (visible immediately, no extra setup)."""
        try:
            subprocess.run(
                ["notify-send", "-u", "critical", title, message],
                capture_output=True, timeout=5,
            )
        except Exception as e:
            logger.warning("Desktop notification failed (non-critical): %s", e)

    def _cooldown_ok(self, ip: str, action: str) -> bool:
        key = f"{ip}:{action}"
        last = _last_action_time.get(key, 0)
        if time.time() - last < _ACTION_COOLDOWN_SECONDS:
            return False
        _last_action_time[key] = time.time()
        return True

    def _log_alert(self, ip: str, level: ThreatLevel, reasons: list[str], actions_taken: list[str]) -> None:
        entry = {
            "timestamp": time.time(),
            "ip": ip,
            "level": level.value,
            "reasons": reasons,
            "actions_taken": actions_taken,
        }
        _RECENT_ALERTS.append(entry)
        if len(_RECENT_ALERTS) > _MAX_ALERTS_KEPT:
            _RECENT_ALERTS.pop(0)
        logger.warning("SECURITY ALERT [%s] ip=%s reasons=%s actions=%s",
                        level.value, ip, reasons, actions_taken)

    async def handle_threat(self, ip: str, level: ThreatLevel, reasons: list[str]) -> dict:
        """Respond to a detected threat according to its level."""
        from app.security.firewall_controller import firewall_controller

        if level == ThreatLevel.NONE:
            return {"handled": False}

        actions_taken = []
        reason_text = "; ".join(reasons)

        if level == ThreatLevel.LOW:
            actions_taken.append("logged")

        elif level == ThreatLevel.MEDIUM:
            self.notify_desktop("AURA Security Alert", f"Suspicious activity from {ip}: {reason_text}")
            actions_taken.append("desktop_alert")

        elif level == ThreatLevel.HIGH:
            self.notify_desktop("⚠️ AURA Security — HIGH THREAT", f"{ip}: {reason_text}\nBlocking IP + disabling wifi.")
            actions_taken.append("desktop_alert")
            if self._cooldown_ok(ip, "block"):
                block_result = firewall_controller.block_ip(ip)
                actions_taken.append(f"block_ip:{block_result.get('success')}")
            if self._cooldown_ok(ip, "wifi_off"):
                wifi_result = firewall_controller.disable_wifi()
                actions_taken.append(f"wifi_off:{wifi_result.get('success')}")

        elif level == ThreatLevel.CRITICAL:
            self.notify_desktop(
                "🚨 AURA Security — CRITICAL THREAT",
                f"{ip}: {reason_text}\nShutting down in 10 seconds. Run cancel_shutdown to abort.",
            )
            actions_taken.append("desktop_alert")
            if self._cooldown_ok(ip, "block"):
                firewall_controller.block_ip(ip)
                actions_taken.append("block_ip")
            if self._cooldown_ok(ip, "wifi_off"):
                firewall_controller.disable_wifi()
                actions_taken.append("wifi_off")
            if self._cooldown_ok(ip, "shutdown"):
                firewall_controller.shutdown_system(delay_seconds=10)
                actions_taken.append("shutdown_scheduled")

        self._log_alert(ip, level, reasons, actions_taken)
        return {"handled": True, "ip": ip, "level": level.value, "actions_taken": actions_taken}

    def get_recent_alerts(self, limit: int = 20) -> list[dict]:
        return list(reversed(_RECENT_ALERTS[-limit:]))


alert_service = AlertService()
