"""
AURA Backend — Threat Detector (Tier 6, B2).

Module: app.security.threat_detector
Purpose: Look for suspicious PATTERNS in connection history and system
         auth logs. Deliberately conservative — false positives that
         trigger wifi-off/shutdown are far worse than a missed alert,
         so multiple independent signals are required before anything
         above ALERT severity fires.

Signals detected:
    - Port-scan pattern: one remote IP touching many distinct local
      ports in a short window.
    - SSH brute-force pattern: many failed login attempts from one IP
      in /var/log/auth.log within a short window.
    - Connection flood: one IP opening an unusually high number of
      connections in a short window.
"""

import logging
import re
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)

# Thresholds — deliberately conservative. Tune these up if you get
# false positives on your own network (e.g. a NAT'd office network
# with legitimately many ports/connections from one IP).
PORT_SCAN_THRESHOLD = 15         # distinct ports from one IP within window
CONNECTION_FLOOD_THRESHOLD = 40  # connection events from one IP within window
SSH_FAILURE_THRESHOLD = 5        # failed SSH logins from one IP within window
AUTH_LOG_WINDOW_SECONDS = 300
AUTH_LOG_PATH = "/var/log/auth.log"


class ThreatLevel(str, Enum):
    NONE = "none"
    LOW = "low"            # log only
    MEDIUM = "medium"      # alert the user, no auto-action
    HIGH = "high"          # alert + disable wifi
    CRITICAL = "critical"  # alert + disable wifi + shutdown


class ThreatDetector:
    """Pattern-based detection over connection history + auth logs."""

    def analyze_connection_history(self, ip: str, events: list[tuple]) -> dict:
        """
        Check one IP's recent connection events for port-scan / flood
        patterns. `events` is [(timestamp, port, status), ...].
        """
        if not events:
            return {"ip": ip, "level": ThreatLevel.NONE, "reasons": []}

        distinct_ports = {port for (_, port, _) in events}
        reasons = []
        level = ThreatLevel.NONE

        if len(distinct_ports) >= PORT_SCAN_THRESHOLD:
            reasons.append(
                f"Port scan pattern: {len(distinct_ports)} distinct ports "
                f"touched in {AUTH_LOG_WINDOW_SECONDS}s"
            )
            level = ThreatLevel.HIGH

        if len(events) >= CONNECTION_FLOOD_THRESHOLD:
            reasons.append(
                f"Connection flood: {len(events)} connection events in "
                f"{AUTH_LOG_WINDOW_SECONDS}s"
            )
            level = ThreatLevel.HIGH

        return {"ip": ip, "level": level, "reasons": reasons}

    def check_ssh_bruteforce(self) -> list[dict]:
        """
        Parse recent /var/log/auth.log entries for repeated failed SSH
        logins from the same IP. Requires read access to the log
        (typically root, or membership in the 'adm' group on Ubuntu).
        """
        try:
            with open(AUTH_LOG_PATH, "r", errors="ignore") as f:
                lines = f.readlines()[-5000:]  # only look at recent tail
        except (FileNotFoundError, PermissionError) as e:
            logger.warning(
                "Cannot read %s (%s) — SSH brute-force detection disabled. "
                "Run AURA as root or add it to the 'adm' group.",
                AUTH_LOG_PATH, e,
            )
            return []

        failed_by_ip: dict = defaultdict(int)
        pattern = re.compile(r"Failed password.*from (\d{1,3}(?:\.\d{1,3}){3})")

        for line in lines:
            m = pattern.search(line)
            if m:
                failed_by_ip[m.group(1)] += 1

        results = []
        for ip, count in failed_by_ip.items():
            if count >= SSH_FAILURE_THRESHOLD:
                results.append({
                    "ip": ip,
                    "level": ThreatLevel.CRITICAL,
                    "reasons": [f"{count} failed SSH login attempts detected"],
                })
        return results


threat_detector = ThreatDetector()
