"""
AURA Backend — Code Explainer.

Module: app.mentor.code_explainer
Purpose: Explains a Python file's structure and behavior in plain
         language. Combines AST-based structure extraction with an
         LLM-generated explanation. READ-ONLY.
"""

import ast
import logging
from pathlib import Path

from app.services.ollama_service import ollama_service

logger = logging.getLogger(__name__)

MAX_SOURCE_CHARS = 6000  # RAM-aware cap for the LLM prompt

TEACHER_SYSTEM_PROMPT = (
    "You are a patient, clear coding mentor. You explain code to someone "
    "learning to program. You are NOT AURA and you are not having a "
    "conversation — you only explain the code you are given. "
    "Use simple language, explain WHY the code is written this way (not "
    "just what it does), and use short examples where it helps. "
    "Never ask for confirmation or offer to remember anything. "
    "Respond in the requested language."
)


class CodeExplainer:
    """
    Explains a Python file's structure and purpose.

    Methods:
        explain_file: Full pipeline — structure extraction + LLM explanation.
    """

    async def explain_file(self, path: Path, language: str = "en") -> dict:
        """
        Explain a single Python file.

        Args:
            path: Path to a .py file.
            language: Response language code.

        Returns:
            dict: {
                "file": str,
                "structure": list[dict],  # functions/classes with line ranges
                "explanation": str,       # LLM-generated plain-language explanation
            }
        """
        source = path.read_text(encoding="utf-8", errors="replace")
        structure = self._extract_structure(source)

        truncated_source = source[:MAX_SOURCE_CHARS]
        prompt = (
            f"Explain what this Python file does, in language code "
            f"'{language}'. Cover: (1) the overall purpose of the file, "
            f"(2) what each function/class does, (3) any non-obvious "
            f"design decisions. Keep it under 300 words unless the file "
            f"is genuinely complex.\n\n"
            f"FILE: {path.name}\n\n{truncated_source}"
        )

        try:
            explanation = await ollama_service.chat(
                message=prompt, system_prompt=TEACHER_SYSTEM_PROMPT
            )
        except Exception as e:
            logger.error("Code explanation failed for %s: %s", path, e)
            explanation = (
                f"Could not generate an AI explanation ({e}). "
                f"Structure summary is still available below."
            )

        return {
            "file": str(path),
            "structure": structure,
            "explanation": explanation.strip(),
        }

    def _extract_structure(self, source: str) -> list[dict]:
        """Extract functions and classes with line ranges via AST."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        structure = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                structure.append({
                    "type": "async function" if isinstance(node, ast.AsyncFunctionDef) else "function",
                    "name": node.name,
                    "line_start": node.lineno,
                    "line_end": node.end_lineno,
                    "docstring": ast.get_docstring(node),
                })
            elif isinstance(node, ast.ClassDef):
                structure.append({
                    "type": "class",
                    "name": node.name,
                    "line_start": node.lineno,
                    "line_end": node.end_lineno,
                    "docstring": ast.get_docstring(node),
                })

        return sorted(structure, key=lambda s: s["line_start"])


# ── Singleton instance ────────────────────────────────────────────────────────
code_explainer = CodeExplainer()