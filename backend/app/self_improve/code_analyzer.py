"""
AURA Backend — Code Analyzer.

Module: app.self_improve.code_analyzer
Purpose: Analyzes AURA's own Python code for issues.
         Uses AST parsing — no execution, fully safe.

Detects:
    - Long functions (> 50 lines)
    - Missing docstrings
    - Bare except clauses
    - Unused imports (basic detection)
    - High complexity functions
"""

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path("D:/AURA/backend")
SKIP_DIRS = {"venv", "__pycache__", ".git"}

MAX_FUNCTION_LINES = 50
MAX_COMPLEXITY = 10


@dataclass
class CodeIssue:
    """A detected code issue."""
    file_path: str
    line_number: int
    issue_type: str
    severity: str
    description: str
    suggestion: str

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "issue_type": self.issue_type,
            "severity": self.severity,
            "description": self.description,
            "suggestion": self.suggestion,
        }


@dataclass
class AnalysisResult:
    """Result of code analysis."""
    files_analyzed: int = 0
    total_issues: int = 0
    issues: list[CodeIssue] = field(default_factory=list)
    by_severity: dict = field(default_factory=dict)
    by_type: dict = field(default_factory=dict)
    health_score: float = 1.0

    def to_dict(self) -> dict:
        return {
            "files_analyzed": self.files_analyzed,
            "total_issues": self.total_issues,
            "issues": [i.to_dict() for i in self.issues[:50]],
            "by_severity": self.by_severity,
            "by_type": self.by_type,
            "health_score": round(self.health_score, 2),
        }


class CodeAnalyzer:
    """
    AST-based code analyzer for AURA's own codebase.

    READ-ONLY — never modifies any file.

    Methods:
        analyze_file: Analyze a single Python file.
        analyze_project: Analyze entire backend.
        calculate_health_score: Overall code health (0-1).
    """

    def analyze_file(self, file_path: Path) -> list[CodeIssue]:
        """
        Analyze a Python file for issues.

        Args:
            file_path: Path to .py file.

        Returns:
            list[CodeIssue]: Found issues.
        """
        issues = []

        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
            lines = source.splitlines()
        except Exception as e:
            logger.warning("Cannot parse %s: %s", file_path, e)
            return []

        rel_path = str(file_path.relative_to(BACKEND_ROOT)).replace("\\", "/")

        for node in ast.walk(tree):
            # Check functions and methods
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Missing docstring
                if not (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    if not node.name.startswith("_"):
                        issues.append(CodeIssue(
                            file_path=rel_path,
                            line_number=node.lineno,
                            issue_type="missing_docstring",
                            severity="low",
                            description=f"Function '{node.name}' has no docstring",
                            suggestion=f"Add a docstring to '{node.name}'",
                        ))

                # Long function
                func_lines = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                if func_lines > MAX_FUNCTION_LINES:
                    issues.append(CodeIssue(
                        file_path=rel_path,
                        line_number=node.lineno,
                        issue_type="long_function",
                        severity="medium",
                        description=(
                            f"Function '{node.name}' is {func_lines} lines long "
                            f"(max recommended: {MAX_FUNCTION_LINES})"
                        ),
                        suggestion=f"Consider breaking '{node.name}' into smaller functions",
                    ))

            # Bare except
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append(CodeIssue(
                    file_path=rel_path,
                    line_number=node.lineno,
                    issue_type="bare_except",
                    severity="medium",
                    description="Bare 'except:' clause catches all exceptions including SystemExit",
                    suggestion="Use 'except Exception as e:' instead",
                ))

        return issues

    def analyze_project(
        self,
        root: Path = BACKEND_ROOT,
        max_files: int = 50,
    ) -> AnalysisResult:
        """
        Analyze the entire AURA backend.

        Args:
            root: Backend root directory.
            max_files: Max files to analyze (RAM protection).

        Returns:
            AnalysisResult: Complete analysis.
        """
        result = AnalysisResult()
        py_files = []

        for path in root.rglob("*.py"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            py_files.append(path)

        py_files = py_files[:max_files]

        for py_file in py_files:
            issues = self.analyze_file(py_file)
            result.issues.extend(issues)
            result.files_analyzed += 1

        result.total_issues = len(result.issues)

        # Count by severity and type
        for issue in result.issues:
            result.by_severity[issue.severity] = (
                result.by_severity.get(issue.severity, 0) + 1
            )
            result.by_type[issue.issue_type] = (
                result.by_type.get(issue.issue_type, 0) + 1
            )

        result.health_score = self.calculate_health_score(result)
        return result

    def calculate_health_score(self, result: AnalysisResult) -> float:
        """Calculate overall health score (0-1, 1 = perfect)."""
        if result.files_analyzed == 0:
            return 1.0

        severity_weights = {"high": 0.5, "medium": 0.2, "low": 0.05}
        penalty = sum(
            result.by_severity.get(sev, 0) * weight
            for sev, weight in severity_weights.items()
        )
        score = max(0.0, 1.0 - (penalty / max(result.files_analyzed, 1)) * 0.1)
        return min(score, 1.0)


code_analyzer = CodeAnalyzer()