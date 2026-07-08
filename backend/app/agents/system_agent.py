"""
AURA Backend — System Agent.

Module: app.agents.system_agent
Purpose: Monitor and interact with the local system.
         CPU, RAM, disk usage, running processes, system info.
         Implements Constitution Rule 14 (AI Health Monitor).

Safety:
    - Read-only by default
    - Process termination requires confirmed=True
    - All actions logged
"""

import logging
import platform
import subprocess
from datetime import datetime, timezone

import psutil

from app.agents.base_agent import AgentResult, BaseAgent

logger = logging.getLogger(__name__)


class SystemAgent(BaseAgent):
    """
    System Monitoring Agent for AURA.

    Supported actions:
        ram     — RAM usage and availability
        cpu     — CPU usage and info
        disk    — Disk usage per drive
        health  — Full system health summary
        info    — System and OS information
        processes — Top processes by RAM/CPU
    """

    @property
    def name(self) -> str:
        return "SystemAgent"

    @property
    def description(self) -> str:
        return "Monitor system health: RAM, CPU, disk, and processes."

    async def execute(self, action: str, params: dict) -> AgentResult:
        """Execute a system monitoring action."""
        self.log_action(action, params)

        action_map = {
            "ram": self._get_ram,
            "cpu": self._get_cpu,
            "disk": self._get_disk,
            "health": self._get_health,
            "info": self._get_system_info,
            "processes": self._get_processes,
        }

        handler = action_map.get(action)
        if not handler:
            result = AgentResult(
                success=False,
                action=action,
                error=f"Unknown action: '{action}'. "
                      f"Available: {', '.join(action_map.keys())}",
            )
        else:
            try:
                result = await handler(params)
            except Exception as e:
                logger.error("SystemAgent error: %s", e)
                result = AgentResult(
                    success=False,
                    action=action,
                    error=str(e),
                )

        self.log_result(result)
        return result

    async def _get_ram(self, params: dict) -> AgentResult:
        """Get RAM usage information."""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return AgentResult(
            success=True,
            action="ram",
            data={
                "total_gb": round(mem.total / 1024**3, 2),
                "available_gb": round(mem.available / 1024**3, 2),
                "used_gb": round(mem.used / 1024**3, 2),
                "percent_used": mem.percent,
                "swap_total_gb": round(swap.total / 1024**3, 2),
                "swap_used_gb": round(swap.used / 1024**3, 2),
                "status": "critical" if mem.percent > 90
                          else "warning" if mem.percent > 75
                          else "ok",
            },
        )

    async def _get_cpu(self, params: dict) -> AgentResult:
        """Get CPU usage information."""
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_freq = psutil.cpu_freq()
        cpu_count = psutil.cpu_count()

        return AgentResult(
            success=True,
            action="cpu",
            data={
                "percent_used": cpu_percent,
                "cores_physical": psutil.cpu_count(logical=False),
                "cores_logical": cpu_count,
                "frequency_mhz": round(cpu_freq.current, 0) if cpu_freq else None,
                "status": "critical" if cpu_percent > 90
                          else "warning" if cpu_percent > 75
                          else "ok",
            },
        )

    async def _get_disk(self, params: dict) -> AgentResult:
        """Get disk usage information."""
        partitions = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                partitions.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "total_gb": round(usage.total / 1024**3, 2),
                    "used_gb": round(usage.used / 1024**3, 2),
                    "free_gb": round(usage.free / 1024**3, 2),
                    "percent_used": usage.percent,
                    "status": "critical" if usage.percent > 95
                              else "warning" if usage.percent > 85
                              else "ok",
                })
            except PermissionError:
                continue

        return AgentResult(
            success=True,
            action="disk",
            data={"partitions": partitions},
        )

    async def _get_health(self, params: dict) -> AgentResult:
        """Get full system health summary — implements AI Health Monitor."""
        mem = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.5)

        disk_ok = True
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                if usage.percent > 95:
                    disk_ok = False
            except PermissionError:
                continue

        ram_status = (
            "critical" if mem.percent > 90
            else "warning" if mem.percent > 75
            else "ok"
        )
        cpu_status = (
            "critical" if cpu_percent > 90
            else "warning" if cpu_percent > 75
            else "ok"
        )
        disk_status = "warning" if not disk_ok else "ok"

        overall = (
            "critical" if "critical" in [ram_status, cpu_status]
            else "warning" if "warning" in [ram_status, cpu_status, disk_status]
            else "ok"
        )

        return AgentResult(
            success=True,
            action="health",
            data={
                "overall": overall,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "ram": {
                    "status": ram_status,
                    "used_percent": mem.percent,
                    "available_gb": round(mem.available / 1024**3, 2),
                },
                "cpu": {
                    "status": cpu_status,
                    "used_percent": cpu_percent,
                },
                "disk": {
                    "status": disk_status,
                },
            },
        )

    async def _get_system_info(self, params: dict) -> AgentResult:
        """Get system and OS information."""
        uname = platform.uname()
        boot_time = datetime.fromtimestamp(psutil.boot_time())

        return AgentResult(
            success=True,
            action="info",
            data={
                "os": uname.system,
                "os_version": uname.version,
                "machine": uname.machine,
                "processor": uname.processor,
                "hostname": uname.node,
                "python_version": platform.python_version(),
                "boot_time": boot_time.isoformat(),
                "uptime_hours": round(
                    (datetime.now() - boot_time).total_seconds() / 3600, 1
                ),
            },
        )

    async def _get_processes(self, params: dict) -> AgentResult:
        """Get top processes by memory usage."""
        top_n = params.get("top_n", 10)
        sort_by = params.get("sort_by", "memory")

        processes = []
        for proc in psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_percent", "status"]
        ):
            try:
                info = proc.info
                processes.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "cpu_percent": round(info["cpu_percent"] or 0, 1),
                    "memory_percent": round(info["memory_percent"] or 0, 2),
                    "status": info["status"],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        sort_key = "memory_percent" if sort_by == "memory" else "cpu_percent"
        processes.sort(key=lambda x: x[sort_key], reverse=True)

        return AgentResult(
            success=True,
            action="processes",
            data={
                "top_n": top_n,
                "sort_by": sort_by,
                "processes": processes[:top_n],
            },
        )


# ── Singleton instance ────────────────────────────────────────────────────────
system_agent = SystemAgent()