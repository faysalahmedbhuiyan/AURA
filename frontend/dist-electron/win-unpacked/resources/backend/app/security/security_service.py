"""
AURA Backend — Security Service Orchestrator (Tier 6, B — main loop).

Module: app.security.security_service
Purpose: Ties connection_monitor + threat_detector + alert_service
         together into a periodic background loop. This is AURA's
         "security head" role — runs continuously, watching for
         intrusion attempts against this machine.
"""

import asyncio
import logging

from app.security.alert_service import alert_service
from app.security.connection_monitor import connection_monitor
from app.security.threat_detector import threat_detector

logger = logging.getLogger(__name__)

SCAN_INTERVAL_SECONDS = 15


class SecurityService:
    """Runs the connection-monitor -> threat-detector -> alert loop."""

    def __init__(self) -> None:
        self._running = False
        self._task: asyncio.Task | None = None

    async def _loop(self) -> None:
        logger.info("AURA security monitor started (scan every %ds).", SCAN_INTERVAL_SECONDS)
        while self._running:
            try:
                connection_monitor.snapshot()

                # Check connection-pattern threats per IP with recent activity
                for ip, events in connection_monitor.get_tracked_ips().items():
                    result = threat_detector.analyze_connection_history(ip, events)
                    if result["level"].value != "none":
                        await alert_service.handle_threat(ip, result["level"], result["reasons"])

                # Check SSH brute-force via auth log (independent of connection history)
                for finding in threat_detector.check_ssh_bruteforce():
                    await alert_service.handle_threat(
                        finding["ip"], finding["level"], finding["reasons"],
                    )

            except Exception as e:
                logger.error("Security scan iteration failed (continuing): %s", e)

            await asyncio.sleep(SCAN_INTERVAL_SECONDS)

    def start(self) -> bool:
        if self._running:
            return False
        self._running = True
        self._task = asyncio.create_task(self._loop())
        return True

    def stop(self) -> bool:
        if not self._running:
            return False
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("AURA security monitor stopped.")
        return True

    def status(self) -> dict:
        return {
            "running": self._running,
            "recent_alerts": alert_service.get_recent_alerts(limit=10),
        }


security_service = SecurityService()
