"""
AURA Backend — Code Analyzer.

Module: app.review.code_analyzer
Purpose: AST-based static analysis of Python source files.
         Detects structural issues without executing any code.
         READ-ONLY — never modifies the analyzed files.
"""

import ast
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_FUNCTION_LINES = 50
MAX_FILE_LINES = 500
MAX_PARAMETERS = 5
MAX_NESTING_DEPTH = 4


class CodeIssue:
    """A single detected issue in a source file."""

    def __init__(
        self,
        file_path: str,
        line: int,
        category: str,
        severity: str,
        message: str,
    ) -> None:
        self.file_path = file_path
        self.line = line
        self.category = category
        self.severity = severity  # low | medium | high
        self.message = message

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "line": self.line,
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
        }


class CodeAnalyzer:
    """
    Analyzes a single Python file using the ast module.

    Methods:
        analyze_file: Parse a file and return a list of CodeIssue.
    """

    def analyze_file(self, path: Path) -> list[CodeIssue]:
        """
        Run all checks on a single Python file.

        Args:
            path: Path to a .py file.

        Returns:
            list[CodeIssue]: Issues found, empty list if file is clean
                              or unreadable/unparsable.
        """
        issues: list[CodeIssue] = []

        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning("Could not read %s: %s", path, e)
            return issues

        file_str = str(path)
        lines = source.splitlines()

        # File length check
        if len(lines) > MAX_FILE_LINES:
            issues.append(CodeIssue(
                file_str, 1, "file_length", "medium",
                f"File has {len(lines)} lines (threshold: {MAX_FILE_LINES}). "
                "Consider splitting into smaller modules.",
            ))

        # TODO/FIXME scan (plain text, doesn't need AST)
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#") and (
                "TODO" in stripped or "FIXME" in stripped
            ):
                issues.append(CodeIssue(
                    file_str, i, "todo_comment", "low",
                    f"Unresolved marker: {stripped.lstrip('#').strip()}",
                ))

        try:
            tree = ast.parse(source, filename=file_str)
        except SyntaxError as e:
            issues.append(CodeIssue(
                file_str, e.lineno or 1, "syntax_error", "high",
                f"File could not be parsed: {e.msg}",
            ))
            return issues

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                issues.extend(self._check_function(file_str, node))
            elif isinstance(node, ast.ClassDef):
                issues.extend(self._check_class(file_str, node))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                pass  # unused-import check done separately below

        issues.extend(self._check_unused_imports(file_str, tree, source))

        return issues

    def _check_function(
        self, file_str: str, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> list[CodeIssue]:
        """Check a single function for length, docstring, params, nesting."""
        issues: list[CodeIssue] = []

        # Function length
        if node.end_lineno and node.lineno:
            func_len = node.end_lineno - node.lineno
            if func_len > MAX_FUNCTION_LINES:
                issues.append(CodeIssue(
                    file_str, node.lineno, "long_function", "medium",
                    f"Function '{node.name}' is {func_len} lines "
                    f"(threshold: {MAX_FUNCTION_LINES}). "
                    "Consider breaking it into smaller functions.",
                ))

        # Missing docstring (skip dunder/private methods for noise reduction)
        if not ast.get_docstring(node) and not node.name.startswith("_"):
            issues.append(CodeIssue(
                file_str, node.lineno, "missing_docstring", "low",
                f"Function '{node.name}' has no docstring.",
            ))

        # Too many parameters
        total_params = len(node.args.args) + len(node.args.kwonlyargs)
        if total_params > MAX_PARAMETERS:
            issues.append(CodeIssue(
                file_str, node.lineno, "too_many_params", "medium",
                f"Function '{node.name}' has {total_params} parameters "
                f"(threshold: {MAX_PARAMETERS}). Consider a config object.",
            ))

        # Nesting depth
        depth = self._max_nesting_depth(node)
        if depth > MAX_NESTING_DEPTH:
            issues.append(CodeIssue(
                file_str, node.lineno, "deep_nesting", "medium",
                f"Function '{node.name}' has nesting depth {depth} "
                f"(threshold: {MAX_NESTING_DEPTH}). Consider early returns.",
            ))

        return issues

    def _check_class(self, file_str: str, node: ast.ClassDef) -> list[CodeIssue]:
        """Check a class for missing docstring."""
        issues: list[CodeIssue] = []
        if not ast.get_docstring(node):
            issues.append(CodeIssue(
                file_str, node.lineno, "missing_docstring", "low",
                f"Class '{node.name}' has no docstring.",
            ))
        return issues

    def _check_unused_imports(
        self, file_str: str, tree: ast.AST, source: str
    ) -> list[CodeIssue]:
        """
        Heuristic unused-import check.

        Not 100% accurate (doesn't handle __all__, re-exports, or
        string-based dynamic references) but catches the common case.
        """
        issues: list[CodeIssue] = []
        imported_names: dict[str, int] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[0]
                    imported_names[name] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    name = alias.asname or alias.name
                    imported_names[name] = node.lineno

        for name, line in imported_names.items():
            # Count occurrences of the name outside the import line itself
            occurrences = source.count(name)
            if occurrences <= 1:
                issues.append(CodeIssue(
                    file_str, line, "unused_import", "low",
                    f"Import '{name}' appears unused.",
                ))

        return issues

    def _max_nesting_depth(self, node: ast.AST, current: int = 0) -> int:
        """Recursively compute the maximum nesting depth in a function body."""
        max_depth = current
        nesting_nodes = (ast.If, ast.For, ast.While, ast.Try, ast.With)

        for child in ast.iter_child_nodes(node):
            if isinstance(child, nesting_nodes):
                child_depth = self._max_nesting_depth(child, current + 1)
            else:
                child_depth = self._max_nesting_depth(child, current)
            max_depth = max(max_depth, child_depth)

        return max_depth


# ── Singleton instance ────────────────────────────────────────────────────────
code_analyzer = CodeAnalyzer()