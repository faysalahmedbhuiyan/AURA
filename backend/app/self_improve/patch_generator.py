"""
AURA Backend — Patch Generator.

Module: app.self_improve.patch_generator
Purpose: Generates code improvement patches using Ollama LLM.
         Patches are NEVER applied automatically.
         Always shown to user for review and confirmation first.
"""

import logging
from dataclasses import dataclass

from app.self_improve.code_analyzer import CodeIssue

logger = logging.getLogger(__name__)

PATCH_SYSTEM_PROMPT = (
    "You are an expert Python code improver. "
    "Given code with an issue, provide the corrected version. "
    "Return ONLY the corrected code block, no explanation needed. "
    "Keep all existing functionality — only fix the reported issue. "
    "Maintain the same code style and conventions."
)


@dataclass
class CodePatch:
    """A suggested code improvement patch."""
    file_path: str
    line_number: int
    issue_type: str
    original_snippet: str
    improved_snippet: str
    description: str
    can_auto_apply: bool = False

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "issue_type": self.issue_type,
            "original_snippet": self.original_snippet,
            "improved_snippet": self.improved_snippet,
            "description": self.description,
            "can_auto_apply": self.can_auto_apply,
        }


class PatchGenerator:
    """
    LLM-powered code patch generator.

    Generates improvement suggestions for detected issues.
    NEVER applies patches automatically.

    Methods:
        generate_patch: Generate improvement for one issue.
        generate_patches: Generate improvements for multiple issues.
    """

    async def generate_patch(
        self,
        issue: CodeIssue,
        file_content: str,
    ) -> CodePatch | None:
        """
        Generate a patch for a specific issue.

        Args:
            issue: Detected code issue.
            file_content: Full file content.

        Returns:
            CodePatch | None: Suggested improvement.
        """
        try:
            from app.services.ollama_service import ollama_service

            # Extract relevant lines
            lines = file_content.splitlines()
            start = max(0, issue.line_number - 3)
            end = min(len(lines), issue.line_number + 20)
            snippet = "\n".join(lines[start:end])

            prompt = (
                f"Fix this Python code issue: {issue.description}\n\n"
                f"Issue type: {issue.issue_type}\n"
                f"Suggestion: {issue.suggestion}\n\n"
                f"Code snippet (line {issue.line_number}):\n"
                f"```python\n{snippet}\n```\n\n"
                f"Provide the improved version of the code snippet only."
            )

            improved = await ollama_service.chat(
                message=prompt,
                history=[],
                system_prompt=PATCH_SYSTEM_PROMPT,
            )

            # Clean code blocks
            import re
            improved = re.sub(r'^```python\s*', '', improved.strip())
            improved = re.sub(r'^```\s*', '', improved)
            improved = re.sub(r'\s*```$', '', improved).strip()

            return CodePatch(
                file_path=issue.file_path,
                line_number=issue.line_number,
                issue_type=issue.issue_type,
                original_snippet=snippet,
                improved_snippet=improved,
                description=issue.description,
                can_auto_apply=(issue.severity == "low"),
            )

        except Exception as e:
            logger.error("Patch generation failed: %s", e)
            return None

    async def generate_patches(
        self,
        issues: list[CodeIssue],
        max_patches: int = 5,
    ) -> list[CodePatch]:
        """
        Generate patches for multiple issues.

        Args:
            issues: List of detected issues.
            max_patches: Maximum patches to generate (RAM limit).

        Returns:
            list[CodePatch]: Generated patches.
        """
        from pathlib import Path

        patches = []
        # Sort by severity: high first
        priority_order = {"high": 0, "medium": 1, "low": 2}
        sorted_issues = sorted(
            issues[:max_patches],
            key=lambda i: priority_order.get(i.severity, 3),
        )

        for issue in sorted_issues:
            try:
                file_path = Path("D:/AURA/backend") / issue.file_path
                if not file_path.exists():
                    continue

                content = file_path.read_text(encoding="utf-8", errors="replace")
                patch = await self.generate_patch(issue, content)
                if patch:
                    patches.append(patch)

            except Exception as e:
                logger.warning("Skipping issue due to error: %s", e)

        return patches


patch_generator = PatchGenerator()