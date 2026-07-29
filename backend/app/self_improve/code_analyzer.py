"""
AURA Backend — Code Analyzer.

Module: app.self_improve.code_analyzer
Purpose: Analyzes AURA's codebase for issues.
         Supports: Python, JavaScript, JSX, CSS, TypeScript.
         Uses AST for Python, regex-based for JS/JSX/CSS.
         READ-ONLY — never modifies any file.

Detects:
    Python:
        - Long functions (> 50 lines)
        - Missing docstrings
        - Bare except clauses
        - TODO/FIXME comments

    JavaScript/JSX:
        - Console.log statements (debug leftovers)
        - TODO/FIXME comments
        - Long files (> 500 lines)
        - Missing prop-types or missing default export
        - Direct DOM manipulation in React

    CSS:
        - !important overuse
        - TODO comments
        - Duplicate selectors (basic detection)
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path("D:/AURA/backend")
FRONTEND_ROOT = Path("D:/AURA/frontend/src")
PROJECT_ROOT = Path("D:/AURA")

SKIP_DIRS = {"venv", "__pycache__", ".git", "node_modules", "dist", "build", ".vite"}

MAX_FUNCTION_LINES = 50
MAX_FILE_LINES_JS = 500
MAX_FILE_LINES_CSS = 300


@dataclass
class CodeIssue:
    """A detected code issue."""
    file_path: str
    line_number: int
    issue_type: str
    severity: str
    description: str
    suggestion: str
    language: str = "python"

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "issue_type": self.issue_type,
            "severity": self.severity,
            "description": self.description,
            "suggestion": self.suggestion,
            "language": self.language,
        }


@dataclass
class AnalysisResult:
    """Result of code analysis."""
    files_analyzed: int = 0
    total_issues: int = 0
    issues: list[CodeIssue] = field(default_factory=list)
    by_severity: dict = field(default_factory=dict)
    by_type: dict = field(default_factory=dict)
    by_language: dict = field(default_factory=dict)
    health_score: float = 1.0

    def to_dict(self) -> dict:
        return {
            "files_analyzed": self.files_analyzed,
            "total_issues": self.total_issues,
            "issues": [i.to_dict() for i in self.issues[:50]],
            "by_severity": self.by_severity,
            "by_type": self.by_type,
            "by_language": self.by_language,
            "health_score": round(self.health_score, 2),
        }


class CodeAnalyzer:
    """
    Multi-language code analyzer for AURA's codebase.

    Supports Python (AST), JavaScript/JSX (regex), CSS (regex).
    READ-ONLY — never modifies any file.

    Methods:
        analyze_file: Analyze a single file by extension.
        analyze_project: Analyze entire project (backend + frontend).
        calculate_health_score: Overall code health (0-1).
    """

    # ── Python analysis ───────────────────────────────────────────────────────

    def analyze_python(self, file_path: Path, root: Path) -> list[CodeIssue]:
        """Analyze a Python file using AST."""
        issues = []
        rel_path = str(file_path.relative_to(root)).replace("\\", "/")

        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
            lines = source.splitlines()
        except Exception as e:
            logger.warning("Cannot parse %s: %s", file_path, e)
            return []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Missing docstring on public functions
                has_docstring = (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                )
                if not has_docstring and not node.name.startswith("_"):
                    issues.append(CodeIssue(
                        file_path=rel_path,
                        line_number=node.lineno,
                        issue_type="missing_docstring",
                        severity="low",
                        description=f"Function '{node.name}' has no docstring",
                        suggestion=f"Add a docstring to '{node.name}'",
                        language="python",
                    ))

                # Long function
                if hasattr(node, "end_lineno"):
                    func_lines = node.end_lineno - node.lineno
                    if func_lines > MAX_FUNCTION_LINES:
                        issues.append(CodeIssue(
                            file_path=rel_path,
                            line_number=node.lineno,
                            issue_type="long_function",
                            severity="medium",
                            description=(
                                f"Function '{node.name}' is {func_lines} lines "
                                f"(max {MAX_FUNCTION_LINES})"
                            ),
                            suggestion=f"Split '{node.name}' into smaller functions",
                            language="python",
                        ))

            # Bare except
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append(CodeIssue(
                    file_path=rel_path,
                    line_number=node.lineno,
                    issue_type="bare_except",
                    severity="medium",
                    description="Bare 'except:' catches all exceptions including SystemExit",
                    suggestion="Use 'except Exception as e:' instead",
                    language="python",
                ))

        # TODO/FIXME comments
        for i, line in enumerate(lines, 1):
            if re.search(r'\b(TODO|FIXME|HACK|XXX)\b', line, re.IGNORECASE):
                issues.append(CodeIssue(
                    file_path=rel_path,
                    line_number=i,
                    issue_type="todo_comment",
                    severity="low",
                    description=f"TODO/FIXME found: {line.strip()[:80]}",
                    suggestion="Resolve or create a task for this item",
                    language="python",
                ))

        return issues

    # ── JavaScript / JSX analysis ─────────────────────────────────────────────

    def analyze_javascript(self, file_path: Path, root: Path) -> list[CodeIssue]:
        """Analyze a JS/JSX file using regex patterns."""
        issues = []
        rel_path = str(file_path.relative_to(root)).replace("\\", "/")
        lang = "jsx" if file_path.suffix == ".jsx" else "javascript"

        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
            lines = source.splitlines()
        except Exception as e:
            logger.warning("Cannot read %s: %s", file_path, e)
            return []

        # Long file
        if len(lines) > MAX_FILE_LINES_JS:
            issues.append(CodeIssue(
                file_path=rel_path,
                line_number=1,
                issue_type="long_file",
                severity="medium",
                description=f"File is {len(lines)} lines (max {MAX_FILE_LINES_JS})",
                suggestion="Consider splitting into smaller components/modules",
                language=lang,
            ))

        # Check for default export in JSX
        if file_path.suffix == ".jsx" and "export default" not in source:
            issues.append(CodeIssue(
                file_path=rel_path,
                line_number=1,
                issue_type="missing_default_export",
                severity="medium",
                description="JSX file has no default export",
                suggestion="Add 'export default' for the main component",
                language="jsx",
            ))

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # console.log debug statements
            if re.search(r'\bconsole\.(log|warn|error|debug)\s*\(', stripped):
                # Skip if it's in a comment
                if not stripped.startswith("//") and not stripped.startswith("*"):
                    issues.append(CodeIssue(
                        file_path=rel_path,
                        line_number=i,
                        issue_type="console_log",
                        severity="low",
                        description=f"Debug console statement: {stripped[:80]}",
                        suggestion="Remove console statements in production code",
                        language=lang,
                    ))

            # TODO/FIXME
            if re.search(r'\b(TODO|FIXME|HACK|XXX)\b', line, re.IGNORECASE):
                if not stripped.startswith("//") or "TODO" in stripped:
                    issues.append(CodeIssue(
                        file_path=rel_path,
                        line_number=i,
                        issue_type="todo_comment",
                        severity="low",
                        description=f"TODO/FIXME: {stripped[:80]}",
                        suggestion="Resolve or track this item",
                        language=lang,
                    ))

            # Direct DOM manipulation in React
            if file_path.suffix == ".jsx":
                if re.search(r'\bdocument\.(getElementById|querySelector|getElementsBy)', stripped):
                    issues.append(CodeIssue(
                        file_path=rel_path,
                        line_number=i,
                        issue_type="direct_dom",
                        severity="medium",
                        description="Direct DOM manipulation in React component",
                        suggestion="Use useRef() hook instead of direct DOM access",
                        language="jsx",
                    ))

            # Inline styles in JSX (discouraged)
            if file_path.suffix == ".jsx" and 'style={{' in stripped:
                issues.append(CodeIssue(
                    file_path=rel_path,
                    line_number=i,
                    issue_type="inline_style",
                    severity="low",
                    description="Inline style in JSX",
                    suggestion="Move styles to CSS file or use CSS variables",
                    language="jsx",
                ))

        return issues

    # ── CSS analysis ──────────────────────────────────────────────────────────

    def analyze_css(self, file_path: Path, root: Path) -> list[CodeIssue]:
        """Analyze a CSS file using regex patterns."""
        issues = []
        rel_path = str(file_path.relative_to(root)).replace("\\", "/")

        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
            lines = source.splitlines()
        except Exception as e:
            logger.warning("Cannot read %s: %s", file_path, e)
            return []

        # Long file
        if len(lines) > MAX_FILE_LINES_CSS:
            issues.append(CodeIssue(
                file_path=rel_path,
                line_number=1,
                issue_type="long_file",
                severity="low",
                description=f"CSS file is {len(lines)} lines (max {MAX_FILE_LINES_CSS})",
                suggestion="Consider splitting into multiple CSS modules",
                language="css",
            ))

        important_count = 0
        selectors = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # !important overuse
            if "!important" in stripped and not stripped.startswith("/*"):
                important_count += 1
                if important_count > 5:
                    issues.append(CodeIssue(
                        file_path=rel_path,
                        line_number=i,
                        issue_type="important_overuse",
                        severity="low",
                        description=f"Excessive use of !important (#{important_count})",
                        suggestion="Refactor CSS specificity instead of using !important",
                        language="css",
                    ))

            # TODO comments
            if re.search(r'/\*.*\b(TODO|FIXME)\b', stripped, re.IGNORECASE):
                issues.append(CodeIssue(
                    file_path=rel_path,
                    line_number=i,
                    issue_type="todo_comment",
                    severity="low",
                    description=f"TODO in CSS: {stripped[:80]}",
                    suggestion="Resolve this CSS TODO",
                    language="css",
                ))

            # Track selectors for duplicate detection (basic)
            selector_match = re.match(r'^([.#][\w-]+)\s*\{', stripped)
            if selector_match:
                selector = selector_match.group(1)
                if selector in selectors:
                    issues.append(CodeIssue(
                        file_path=rel_path,
                        line_number=i,
                        issue_type="duplicate_selector",
                        severity="medium",
                        description=f"Duplicate CSS selector: {selector}",
                        suggestion="Merge duplicate selectors to avoid specificity issues",
                        language="css",
                    ))
                else:
                    selectors.append(selector)

        return issues

    # ── File router ───────────────────────────────────────────────────────────

    def analyze_file(self, file_path: Path, root: Path) -> list[CodeIssue]:
        """Route to correct analyzer based on file extension."""
        ext = file_path.suffix.lower()
        if ext == ".py":
            return self.analyze_python(file_path, root)
        elif ext in (".js", ".jsx", ".ts", ".tsx"):
            return self.analyze_javascript(file_path, root)
        elif ext == ".css":
            return self.analyze_css(file_path, root)
        return []

    # ── Project analysis ──────────────────────────────────────────────────────

    def analyze_project(
        self,
        root: Path | None = None,
        max_files: int = 80,
        include_frontend: bool = True,
    ) -> AnalysisResult:
        """
        Analyze the entire AURA project.

        Scans backend (Python) + frontend (JS/JSX/CSS).

        Args:
            root: Override root (default: backend + frontend).
            max_files: Max files to analyze.
            include_frontend: Include frontend JS/JSX/CSS files.

        Returns:
            AnalysisResult: All issues found with health score.
        """
        result = AnalysisResult()
        all_files: list[tuple[Path, Path]] = []  # (file, root)

        # Backend Python files
        backend_files = [
            (f, BACKEND_ROOT)
            for f in BACKEND_ROOT.rglob("*.py")
            if not any(part in SKIP_DIRS for part in f.parts)
        ]
        all_files.extend(backend_files)

        # Frontend JS/JSX/CSS files
        if include_frontend and FRONTEND_ROOT.exists():
            for ext in ("*.js", "*.jsx", "*.css"):
                frontend_files = [
                    (f, Path("D:/AURA"))
                    for f in FRONTEND_ROOT.rglob(ext)
                    if not any(part in SKIP_DIRS for part in f.parts)
                ]
                all_files.extend(frontend_files)

        # Limit total files
        all_files = all_files[:max_files]

        for file_path, file_root in all_files:
            issues = self.analyze_file(file_path, file_root)
            result.issues.extend(issues)
            result.files_analyzed += 1

        result.total_issues = len(result.issues)

        # Stats by severity, type, language
        for issue in result.issues:
            result.by_severity[issue.severity] = (
                result.by_severity.get(issue.severity, 0) + 1
            )
            result.by_type[issue.issue_type] = (
                result.by_type.get(issue.issue_type, 0) + 1
            )
            result.by_language[issue.language] = (
                result.by_language.get(issue.language, 0) + 1
            )

        result.health_score = self.calculate_health_score(result)
        logger.info(
            "Analysis complete: %d files, %d issues, score=%.2f",
            result.files_analyzed,
            result.total_issues,
            result.health_score,
        )
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
        return round(min(score, 1.0), 3)


# ── Singleton ─────────────────────────────────────────────────────────────────
code_analyzer = CodeAnalyzer()