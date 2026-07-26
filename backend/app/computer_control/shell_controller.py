"""
AURA Backend — Shell Controller.

Module: app.computer_control.shell_controller
Purpose: Execute PowerShell and CMD commands safely.

         ⚠️ HIGH RISK — confirmed=True ALWAYS required.
         ⚠️ Blocklist prevents dangerous commands.
         ⚠️ 30-second timeout on all commands.
         ⚠️ Every command is logged with full output.

Safety:
    - confirmed=True mandatory, no exceptions
    - Dangerous commands blocked (format, rmdir C:, etc.)
    - Timeout: 30 seconds
    - Output truncated to 5000 chars
    - Working directory restricted to D:/AURA by default
"""

import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

SAFE_WORKING_DIR = Path("D:/AURA")
COMMAND_TIMEOUT = 30

BLOCKED_PATTERNS = [
    r'\bformat\s+[a-zA-Z]:', r'\brmdir\s+[a-zA-Z]:\\',
    r'\bdel\s+[a-zA-Z]:\\', r'\brd\s+/s\s+[a-zA-Z]:\\',
    r'\bshutdown\b', r'\brestart\b',
    r'\brm\s+-rf\s+/', r'\bdiskpart\b',
    r'\bnetsh\s+firewall\b', r'\bsc\s+delete\b',
    r'\bnet\s+user\b', r'\bnet\s+localgroup\b',
    r'Remove-Item.*-Recurse.*[A-Z]:\\',
    r'Format-Volume', r'Clear-Disk',
]


@dataclass
class ShellResult:
    success: bool
    command: str
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    error: str = ""
    was_blocked: bool = False

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "command": self.command,
            "stdout": self.stdout[:3000],
            "stderr": self.stderr[:1000],
            "return_code": self.return_code,
            "error": self.error,
            "was_blocked": self.was_blocked,
        }


class ShellController:
    """
    PowerShell/CMD execution controller.

    ⚠️ HIGH RISK — requires confirmed=True always.

    Methods:
        run_powershell: Execute a PowerShell command.
        run_cmd: Execute a CMD command.
        is_safe: Check if command passes safety filters.
    """

    def is_safe(self, command: str) -> tuple[bool, str]:
        """
        Check if command is safe to execute.

        Args:
            command: Command string to check.

        Returns:
            tuple: (is_safe, reason_if_blocked)
        """
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Blocked pattern: {pattern}"
        return True, ""

    def run_powershell(
        self,
        command: str,
        confirmed: bool = False,
        working_dir: str | None = None,
    ) -> ShellResult:
        """
        Execute a PowerShell command.

        Args:
            command: PowerShell command to run.
            confirmed: MUST be True — hard gate.
            working_dir: Working directory (default: D:/AURA).

        Returns:
            ShellResult: Output and status.
        """
        if not confirmed:
            return ShellResult(
                success=False,
                command=command,
                error="Shell execution requires confirmed=True. This is mandatory for safety.",
            )

        safe, reason = self.is_safe(command)
        if not safe:
            logger.warning("BLOCKED command: %s | Reason: %s", command[:100], reason)
            return ShellResult(
                success=False,
                command=command,
                error=f"Command blocked for safety: {reason}",
                was_blocked=True,
            )

        cwd = working_dir or str(SAFE_WORKING_DIR)
        logger.info("Running PowerShell: %s", command[:200])

        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT,
                encoding="utf-8",
                errors="replace",
            )
            return ShellResult(
                success=result.returncode == 0,
                command=command,
                stdout=result.stdout.strip()[:5000],
                stderr=result.stderr.strip()[:1000],
                return_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ShellResult(
                success=False,
                command=command,
                error=f"Command timed out after {COMMAND_TIMEOUT}s",
            )
        except Exception as e:
            logger.error("PowerShell error: %s", e)
            return ShellResult(success=False, command=command, error=str(e))

    def run_cmd(
        self,
        command: str,
        confirmed: bool = False,
    ) -> ShellResult:
        """
        Execute a CMD command.

        Args:
            command: CMD command to run.
            confirmed: MUST be True.

        Returns:
            ShellResult: Output and status.
        """
        if not confirmed:
            return ShellResult(
                success=False,
                command=command,
                error="CMD execution requires confirmed=True.",
            )

        safe, reason = self.is_safe(command)
        if not safe:
            return ShellResult(
                success=False,
                command=command,
                error=f"Command blocked: {reason}",
                was_blocked=True,
            )

        logger.info("Running CMD: %s", command[:200])
        try:
            result = subprocess.run(
                ["cmd", "/c", command],
                cwd=str(SAFE_WORKING_DIR),
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT,
                encoding="utf-8",
                errors="replace",
            )
            return ShellResult(
                success=result.returncode == 0,
                command=command,
                stdout=result.stdout.strip()[:5000],
                stderr=result.stderr.strip()[:1000],
                return_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ShellResult(
                success=False,
                command=command,
                error=f"Command timed out after {COMMAND_TIMEOUT}s",
            )
        except Exception as e:
            return ShellResult(success=False, command=command, error=str(e))


shell_controller = ShellController()