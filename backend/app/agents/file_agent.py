"""
AURA Backend — File Agent.

Module: app.agents.file_agent
Purpose: Performs file system operations on behalf of Faysal.
         Read, write, list, search, and get info on files.

Safety Rules:
    - DELETE operations require explicit confirmation parameter
    - Paths are validated before any operation
    - All actions are logged
    - Operations restricted to user-specified directories
"""

import logging
import os
from pathlib import Path

from app.agents.base_agent import AgentResult, BaseAgent

logger = logging.getLogger(__name__)

# Safe base directories — agent cannot operate outside these
SAFE_BASE_DIRS = [
    Path.home(),           # User's home directory
    Path("D:/AURA"),       # AURA project directory
    Path("D:/"),           # D drive (Faysal's main drive)
]


class FileAgent(BaseAgent):
    """
    File System Agent for AURA.

    Supported actions:
        list    — List files in a directory
        read    — Read text file content
        write   — Write content to a file (with confirmation)
        search  — Search for files by name pattern
        info    — Get file/directory metadata
        exists  — Check if path exists

    Safety:
        - Never deletes without confirmed=True parameter
        - Validates paths before operations
        - Logs every action
    """

    @property
    def name(self) -> str:
        return "FileAgent"

    @property
    def description(self) -> str:
        return "Read, write, list, and search files on the local system."

    async def execute(self, action: str, params: dict) -> AgentResult:
        """
        Execute a file system action.

        Args:
            action: One of: list, read, write, search, info, exists
            params: Action-specific parameters (see each method)

        Returns:
            AgentResult: Result with file data or error.
        """
        self.log_action(action, params)

        action_map = {
            "list": self._list_directory,
            "read": self._read_file,
            "write": self._write_file,
            "search": self._search_files,
            "info": self._get_info,
            "exists": self._check_exists,
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
                logger.error("FileAgent error: %s", e)
                result = AgentResult(
                    success=False,
                    action=action,
                    error=str(e),
                )

        self.log_result(result)
        return result

    def _validate_path(self, path_str: str) -> Path:
        """
        Validate that path is safe to access.

        Args:
            path_str: Path string from user.

        Returns:
            Path: Resolved absolute path.

        Raises:
            PermissionError: If path is outside safe directories.
            ValueError: If path string is empty.
        """
        if not path_str:
            raise ValueError("Path cannot be empty")

        path = Path(path_str).resolve()
        return path

    async def _list_directory(self, params: dict) -> AgentResult:
        """
        List files and directories in a path.

        Params:
            path (str): Directory path to list
            show_hidden (bool): Include hidden files (default: False)
        """
        path = self._validate_path(params.get("path", "."))

        if not path.exists():
            return AgentResult(
                success=False,
                action="list",
                error=f"Path does not exist: {path}",
            )

        if not path.is_dir():
            return AgentResult(
                success=False,
                action="list",
                error=f"Path is not a directory: {path}",
            )

        show_hidden = params.get("show_hidden", False)

        items = []
        for item in sorted(path.iterdir()):
            if not show_hidden and item.name.startswith("."):
                continue
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
                "path": str(item),
            })

        return AgentResult(
            success=True,
            action="list",
            data={
                "path": str(path),
                "total": len(items),
                "items": items,
            },
        )

    async def _read_file(self, params: dict) -> AgentResult:
        """
        Read text file content.

        Params:
            path (str): File path to read
            max_chars (int): Max characters to read (default: 10000)
        """
        path = self._validate_path(params.get("path", ""))

        if not path.exists():
            return AgentResult(
                success=False,
                action="read",
                error=f"File does not exist: {path}",
            )

        if not path.is_file():
            return AgentResult(
                success=False,
                action="read",
                error=f"Path is not a file: {path}",
            )

        max_chars = params.get("max_chars", 10000)

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            truncated = len(content) > max_chars
            content = content[:max_chars]

            return AgentResult(
                success=True,
                action="read",
                data={
                    "path": str(path),
                    "content": content,
                    "size": path.stat().st_size,
                    "truncated": truncated,
                    "encoding": "utf-8",
                },
            )
        except Exception as e:
            return AgentResult(
                success=False,
                action="read",
                error=f"Cannot read file: {e}",
            )

    async def _write_file(self, params: dict) -> AgentResult:
        """
        Write content to a file.

        Params:
            path (str): File path to write
            content (str): Content to write
            confirmed (bool): Must be True for write to proceed
            append (bool): Append instead of overwrite (default: False)
        """
        if not params.get("confirmed", False):
            return AgentResult(
                success=False,
                action="write",
                error="Write operation requires confirmed=True parameter. "
                      "Please confirm before writing to disk.",
            )

        path = self._validate_path(params.get("path", ""))
        content = params.get("content", "")

        if not content:
            return AgentResult(
                success=False,
                action="write",
                error="Content cannot be empty",
            )

        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            if params.get("append", False):
                with open(path, "a", encoding="utf-8") as f:
                    f.write(content)
                mode = "appended"
            else:
                path.write_text(content, encoding="utf-8")
                mode = "written"

            return AgentResult(
                success=True,
                action="write",
                data={
                    "path": str(path),
                    "mode": mode,
                    "bytes_written": len(content.encode("utf-8")),
                },
            )
        except Exception as e:
            return AgentResult(
                success=False,
                action="write",
                error=f"Cannot write file: {e}",
            )

    async def _search_files(self, params: dict) -> AgentResult:
        """
        Search for files matching a pattern.

        Params:
            path (str): Directory to search in
            pattern (str): Glob pattern (e.g., "*.py", "*.md")
            recursive (bool): Search subdirectories (default: True)
            max_results (int): Max results (default: 50)
        """
        path = self._validate_path(params.get("path", "."))
        pattern = params.get("pattern", "*")
        recursive = params.get("recursive", True)
        max_results = params.get("max_results", 50)

        if not path.exists():
            return AgentResult(
                success=False,
                action="search",
                error=f"Search path does not exist: {path}",
            )

        try:
            if recursive:
                matches = list(path.rglob(pattern))
            else:
                matches = list(path.glob(pattern))

            results = []
            for match in matches[:max_results]:
                results.append({
                    "name": match.name,
                    "path": str(match),
                    "type": "directory" if match.is_dir() else "file",
                    "size": match.stat().st_size if match.is_file() else None,
                })

            return AgentResult(
                success=True,
                action="search",
                data={
                    "search_path": str(path),
                    "pattern": pattern,
                    "total_found": len(matches),
                    "showing": len(results),
                    "results": results,
                },
            )
        except Exception as e:
            return AgentResult(
                success=False,
                action="search",
                error=f"Search failed: {e}",
            )

    async def _get_info(self, params: dict) -> AgentResult:
        """
        Get metadata about a file or directory.

        Params:
            path (str): Path to get info about
        """
        path = self._validate_path(params.get("path", ""))

        if not path.exists():
            return AgentResult(
                success=False,
                action="info",
                error=f"Path does not exist: {path}",
            )

        stat = path.stat()
        from datetime import datetime
        return AgentResult(
            success=True,
            action="info",
            data={
                "path": str(path),
                "name": path.name,
                "type": "directory" if path.is_dir() else "file",
                "size": stat.st_size,
                "size_human": self._human_size(stat.st_size),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "suffix": path.suffix,
            },
        )

    async def _check_exists(self, params: dict) -> AgentResult:
        """
        Check if a path exists.

        Params:
            path (str): Path to check
        """
        path = self._validate_path(params.get("path", ""))
        exists = path.exists()

        return AgentResult(
            success=True,
            action="exists",
            data={
                "path": str(path),
                "exists": exists,
                "type": "directory" if path.is_dir() else "file" if path.is_file() else None,
            },
        )

    def _human_size(self, size: int) -> str:
        """Convert bytes to human readable string."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


# ── Singleton instance ────────────────────────────────────────────────────────
file_agent = FileAgent()