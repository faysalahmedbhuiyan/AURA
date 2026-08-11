"""
AURA Backend — Connection Monitor (Tier 6, B1).

Module: app.security.connection_monitor
Purpose: Snapshot and track active network connections on this machine.
         Pure observation — no blocking/response logic here (that's
         threat_detector.py + firewall_controller.py). Cross-platform
         via psutil, but designed/tested for Ubuntu (the target OS).
"""

import logging
import time
from collections import defaultdict, deque

import psutil

logger = logging.getLogger(__name__)

# How many recent connection events to keep per remote IP, for the
# threat detector to look for patterns (e.g. many ports hit quickly).
_HISTORY_WINDOW_SECONDS = 300  # 5 minutes


class ConnectionMonitor:
    """Tracks active connections and recent per-IP connection history."""

    def __init__(self) -> None:
        # ip -> deque[(timestamp, port, status)]
        self._history: dict[str, deque] = defaultdict(lambda: deque(maxlen=200))

    def snapshot(self) -> list[dict]:
        """
        Take a snapshot of current network connections.

        Returns:
            list[dict]: each with local/remote address, port, status,
            and the owning process name (if permission allows).
        """
        results = []
        try:
            connections = psutil.net_connections(kind="inet")
        except (psutil.AccessDenied, PermissionError):
            logger.warning(
                "Insufficient permission to list all connections — "
                "run with elevated privileges (e.g. via systemd as root) "
                "for full visibility."
            )
            return results

        now = time.time()
        for c in connections:
            if not c.raddr:  # skip connections with no remote address (listening sockets)
                continue

            remote_ip = c.raddr.ip
            remote_port = c.raddr.port
            proc_name = None
            if c.pid:
                try:
                    proc_name = psutil.Process(c.pid).name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    proc_name = None

            entry = {
                "remote_ip": remote_ip,
                "remote_port": remote_port,
                "local_port": c.laddr.port if c.laddr else None,
                "status": c.status,
                "pid": c.pid,
                "process": proc_name,
                "timestamp": now,
            }
            results.append(entry)
            self._history[remote_ip].append((now, remote_port, c.status))

        self._prune_old_history(now)
        return results

    def get_recent_activity(self, ip: str) -> list[tuple]:
        """All recorded (timestamp, port, status) events for an IP within the window."""
        return list(self._history.get(ip, []))

    def get_tracked_ips(self) -> dict[str, list[tuple]]:
        """All IPs currently being tracked, with their recent event history."""
        return {ip: list(events) for ip, events in self._history.items()}

    def _prune_old_history(self, now: float) -> None:
        cutoff = now - _HISTORY_WINDOW_SECONDS
        for ip, events in list(self._history.items()):
            while events and events[0][0] < cutoff:
                events.popleft()
            if not events:
                del self._history[ip]


connection_monitor = ConnectionMonitor()
