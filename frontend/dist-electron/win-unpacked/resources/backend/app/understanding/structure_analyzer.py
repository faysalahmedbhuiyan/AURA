"""
AURA Backend — Structure Analyzer.

Module: app.understanding.structure_analyzer
Purpose: Builds a complete map of the AURA project structure.
         Analyzes folders, files, sizes, types, and counts.
         READ-ONLY — never modifies any file.

Output helps AURA answer:
  "What files are in the backend?"
  "How big is the project?"
  "What modules exist?"
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

SKIP_DIRS = {
    "venv", "__pycache__", "node_modules", ".git",
    "dist", "build", ".vite", "chroma", ".aura",
}

SKIP_EXTENSIONS = {".pyc", ".pyo", ".pyd", ".exe", ".dll", ".so"}

FILE_TYPE_MAP = {
    ".py": "python",
    ".jsx": "react",
    ".js": "javascript",
    ".css": "stylesheet",
    ".md": "markdown",
    ".json": "json",
    ".env": "config",
    ".toml": "config",
    ".txt": "text",
    ".html": "html",
    ".onnx": "model",
    ".wav": "audio",
}


@dataclass
class FileInfo:
    """Metadata about a single file."""
    path: str
    name: str
    extension: str
    file_type: str
    size_bytes: int
    relative_path: str

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "name": self.name,
            "extension": self.extension,
            "file_type": self.file_type,
            "size_bytes": self.size_bytes,
            "relative_path": self.relative_path,
        }


@dataclass
class FolderInfo:
    """Metadata about a folder."""
    path: str
    name: str
    relative_path: str
    file_count: int
    total_size_bytes: int
    subfolders: list[str] = field(default_factory=list)
    files: list[FileInfo] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "name": self.name,
            "relative_path": self.relative_path,
            "file_count": self.file_count,
            "total_size_bytes": self.total_size_bytes,
            "subfolders": self.subfolders,
        }


@dataclass
class ProjectStructure:
    """Complete project structure summary."""
    root: str
    total_files: int
    total_size_bytes: int
    file_type_counts: dict[str, int]
    largest_files: list[dict]
    folders: list[FolderInfo]
    all_files: list[FileInfo]

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "total_files": self.total_files,
            "total_size_bytes": self.total_size_bytes,
            "total_size_human": self._human_size(self.total_size_bytes),
            "file_type_counts": self.file_type_counts,
            "largest_files": self.largest_files[:10],
            "folder_count": len(self.folders),
            "folders": [f.to_dict() for f in self.folders],
        }

    def _human_size(self, size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size //= 1024
        return f"{size:.1f} TB"


class StructureAnalyzer:
    """
    Analyzes the AURA project file and folder structure.

    Methods:
        analyze: Build complete project structure map.
        get_folder: Get detailed info about a specific folder.
        get_file_types: Summary of file types in project.
    """

    def analyze(
        self,
        project_root: Path,
        max_depth: int = 6,
    ) -> ProjectStructure:
        """
        Build complete project structure.

        Args:
            project_root: Root directory to analyze.
            max_depth: Maximum folder depth to traverse.

        Returns:
            ProjectStructure: Complete structure with all files/folders.
        """
        all_files: list[FileInfo] = []
        folders: list[FolderInfo] = []
        file_type_counts: dict[str, int] = {}

        self._traverse(
            project_root,
            project_root,
            0,
            max_depth,
            all_files,
            folders,
            file_type_counts,
        )

        total_size = sum(f.size_bytes for f in all_files)

        largest = sorted(all_files, key=lambda f: f.size_bytes, reverse=True)
        largest_dicts = [f.to_dict() for f in largest[:10]]

        return ProjectStructure(
            root=str(project_root),
            total_files=len(all_files),
            total_size_bytes=total_size,
            file_type_counts=file_type_counts,
            largest_files=largest_dicts,
            folders=folders,
            all_files=all_files,
        )

    def _traverse(
        self,
        path: Path,
        root: Path,
        depth: int,
        max_depth: int,
        all_files: list,
        folders: list,
        type_counts: dict,
    ) -> tuple[int, int]:
        """Recursively traverse directory. Returns (file_count, total_size)."""
        if depth > max_depth:
            return 0, 0

        if any(part in SKIP_DIRS for part in path.parts):
            return 0, 0

        file_count = 0
        total_size = 0
        folder_files: list[FileInfo] = []
        subfolders: list[str] = []

        try:
            for item in sorted(path.iterdir()):
                if item.name.startswith(".") and item.name not in {".env.example"}:
                    continue

                if item.is_dir():
                    if item.name in SKIP_DIRS:
                        continue
                    subfolders.append(item.name)
                    fc, ts = self._traverse(
                        item, root, depth + 1, max_depth,
                        all_files, folders, type_counts,
                    )
                    file_count += fc
                    total_size += ts

                elif item.is_file():
                    if item.suffix in SKIP_EXTENSIONS:
                        continue

                    try:
                        size = item.stat().st_size
                    except OSError:
                        size = 0

                    file_type = FILE_TYPE_MAP.get(item.suffix.lower(), "other")
                    rel_path = str(item.relative_to(root)).replace("\\", "/")

                    fi = FileInfo(
                        path=str(item),
                        name=item.name,
                        extension=item.suffix,
                        file_type=file_type,
                        size_bytes=size,
                        relative_path=rel_path,
                    )
                    all_files.append(fi)
                    folder_files.append(fi)
                    file_count += 1
                    total_size += size
                    type_counts[file_type] = type_counts.get(file_type, 0) + 1

        except PermissionError:
            pass

        rel = str(path.relative_to(root)).replace("\\", "/") if path != root else "."
        folders.append(FolderInfo(
            path=str(path),
            name=path.name,
            relative_path=rel,
            file_count=file_count,
            total_size_bytes=total_size,
            subfolders=subfolders,
            files=folder_files,
        ))

        return file_count, total_size


# ── Singleton ─────────────────────────────────────────────────────────────────
structure_analyzer = StructureAnalyzer()