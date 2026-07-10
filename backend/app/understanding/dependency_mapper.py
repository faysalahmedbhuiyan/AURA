"""
AURA Backend — Dependency Mapper.

Module: app.understanding.dependency_mapper
Purpose: Builds a Python import dependency graph for the AURA backend.
         Shows which modules import which other modules.
         Helps AURA understand "if I change X, what else breaks?"

READ-ONLY — never modifies any file.
Uses AST parsing for accurate import extraction.
"""

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

SKIP_DIRS = {
    "venv", "__pycache__", "node_modules", ".git",
    "dist", "build", ".aura",
}


@dataclass
class ModuleNode:
    """A single Python module in the dependency graph."""
    module_id: str          # e.g. "app.services.ollama_service"
    file_path: str
    imports: list[str]      # other AURA modules this imports
    imported_by: list[str]  # modules that import this
    external_imports: list[str]  # third-party/stdlib imports
    line_count: int

    def to_dict(self) -> dict:
        return {
            "module_id": self.module_id,
            "file_path": self.file_path,
            "imports": self.imports,
            "imported_by": self.imported_by,
            "external_imports": self.external_imports,
            "line_count": self.line_count,
        }


@dataclass
class DependencyGraph:
    """Complete module dependency graph."""
    modules: dict[str, ModuleNode] = field(default_factory=dict)
    total_modules: int = 0
    most_imported: list[dict] = field(default_factory=list)
    most_dependencies: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_modules": self.total_modules,
            "most_imported": self.most_imported[:10],
            "most_dependencies": self.most_dependencies[:10],
            "modules": {k: v.to_dict() for k, v in self.modules.items()},
        }


class DependencyMapper:
    """
    Builds Python module import dependency graph.

    Methods:
        build_graph: Analyze all .py files and build dependency graph.
        get_dependents: Find all modules that depend on a given module.
        get_dependencies: Find all modules a given module depends on.
    """

    def build_graph(
        self,
        backend_root: Path,
    ) -> DependencyGraph:
        """
        Build complete dependency graph for the Python backend.

        Args:
            backend_root: Path to backend/ directory.

        Returns:
            DependencyGraph: Full import graph.
        """
        graph = DependencyGraph()
        py_files = self._collect_py_files(backend_root)

        # First pass — parse all imports
        for py_file in py_files:
            module_id = self._path_to_module_id(py_file, backend_root)
            imports, externals, line_count = self._parse_imports(py_file, backend_root)

            graph.modules[module_id] = ModuleNode(
                module_id=module_id,
                file_path=str(py_file),
                imports=imports,
                imported_by=[],
                external_imports=externals,
                line_count=line_count,
            )

        # Second pass — build reverse deps (imported_by)
        for module_id, node in graph.modules.items():
            for dep in node.imports:
                if dep in graph.modules:
                    graph.modules[dep].imported_by.append(module_id)

        graph.total_modules = len(graph.modules)

        # Most imported
        by_imports = sorted(
            graph.modules.values(),
            key=lambda m: len(m.imported_by),
            reverse=True,
        )
        graph.most_imported = [
            {"module": m.module_id, "imported_by_count": len(m.imported_by)}
            for m in by_imports[:10] if m.imported_by
        ]

        # Most dependencies
        by_deps = sorted(
            graph.modules.values(),
            key=lambda m: len(m.imports),
            reverse=True,
        )
        graph.most_dependencies = [
            {"module": m.module_id, "dependency_count": len(m.imports)}
            for m in by_deps[:10] if m.imports
        ]

        logger.info("Dependency graph built: %d modules", graph.total_modules)
        return graph

    def _collect_py_files(self, root: Path) -> list[Path]:
        """Collect all .py files, skipping irrelevant dirs."""
        files = []
        for path in root.rglob("*.py"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            files.append(path)
        return files

    def _path_to_module_id(self, path: Path, root: Path) -> str:
        """Convert file path to dotted module ID."""
        try:
            rel = path.relative_to(root)
            parts = list(rel.with_suffix("").parts)
            return ".".join(parts)
        except ValueError:
            return path.stem

    def _parse_imports(
        self,
        path: Path,
        root: Path,
    ) -> tuple[list[str], list[str], int]:
        """
        Parse Python file for imports using AST.

        Returns:
            tuple: (aura_imports, external_imports, line_count)
        """
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except Exception:
            return [], [], 0

        line_count = source.count("\n") + 1
        aura_imports: list[str] = []
        external_imports: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if name.startswith("app."):
                        aura_imports.append(name)
                    else:
                        external_imports.append(name.split(".")[0])

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    if node.module.startswith("app."):
                        aura_imports.append(node.module)
                    elif node.level == 0:
                        external_imports.append(node.module.split(".")[0])

        return (
            sorted(set(aura_imports)),
            sorted(set(external_imports)),
            line_count,
        )

    def get_dependents(
        self,
        module_id: str,
        graph: DependencyGraph,
        transitive: bool = False,
    ) -> list[str]:
        """
        Find all modules that depend on a given module.

        Args:
            module_id: Target module.
            graph: Built dependency graph.
            transitive: Include transitive deps (depth-first).

        Returns:
            list[str]: Module IDs that import target.
        """
        if module_id not in graph.modules:
            return []

        direct = graph.modules[module_id].imported_by

        if not transitive:
            return direct

        visited = set()
        queue = list(direct)
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            if current in graph.modules:
                queue.extend(graph.modules[current].imported_by)

        return list(visited)


# ── Singleton ─────────────────────────────────────────────────────────────────
dependency_mapper = DependencyMapper()