"""
AURA Backend — Self-Improvement Service.

Module: app.self_improve.self_improve_service
Purpose: Orchestrates the full self-improvement pipeline.

Pipeline:
    1. Analyze codebase (AST)
    2. Find top issues
    3. Generate patches (LLM)
    4. Present to user for review
    5. User confirms → apply via Phase 10 modification engine
    6. Run tests
    7. Commit if tests pass

NEVER auto-applies. User must confirm every patch.
"""

import logging
from pathlib import Path

from app.self_improve.code_analyzer import AnalysisResult, code_analyzer
from app.self_improve.patch_generator import patch_generator

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path("D:/AURA/backend")


class SelfImprovementService:
    """
    Self-improvement orchestrator.

    Methods:
        analyze: Analyze codebase and find issues.
        generate_improvements: Generate patch suggestions.
        apply_patch: Apply a confirmed patch via modification engine.
        get_health_report: Full health report.
    """

    async def analyze(self, max_files: int = 30) -> AnalysisResult:
        """
        Analyze AURA's codebase.

        Args:
            max_files: Max files to analyze.

        Returns:
            AnalysisResult: Issues found and health score.
        """
        logger.info("Starting self-analysis (max_files=%d)", max_files)
        return code_analyzer.analyze_project(
            root=BACKEND_ROOT,
            max_files=max_files,
            include_frontend=True, 
        )

    async def generate_improvements(
        self,
        max_patches: int = 3,
    ) -> dict:
        """
        Analyze + generate improvement patches.

        Args:
            max_patches: Max patches to generate (RAM limit).

        Returns:
            dict: Analysis + patches for user review.
        """
        analysis = await self.analyze()

        if not analysis.issues:
            return {
                "health_score": analysis.health_score,
                "message": "No issues found! Codebase looks healthy.",
                "patches": [],
                "analysis": analysis.to_dict(),
            }

        # Generate patches for top issues
        patches = await patch_generator.generate_patches(
            analysis.issues,
            max_patches=max_patches,
        )

        return {
            "health_score": analysis.health_score,
            "total_issues": analysis.total_issues,
            "patches_generated": len(patches),
            "patches": [p.to_dict() for p in patches],
            "analysis": analysis.to_dict(),
            "warning": (
                "These are SUGGESTIONS only. "
                "Review each patch carefully before applying. "
                "Use POST /api/v1/self-improve/apply to apply a patch."
            ),
        }

    async def apply_patch(
        self,
        file_path: str,
        old_text: str,
        new_text: str,
        confirmed: bool = False,
        description: str = "Self-improvement patch",
    ) -> dict:
        """
        Apply a confirmed patch via Phase 10 modification engine.

        Args:
            file_path: Relative path from backend root.
            old_text: Original text to replace.
            new_text: Improved text.
            confirmed: MUST be True.
            description: Change description.

        Returns:
            dict: Application result.
        """
        if not confirmed:
            return {
                "success": False,
                "error": "confirmed=True required to apply patches.",
            }

        try:
            from app.modification.modification_service import modification_service

            full_path = str(BACKEND_ROOT / file_path)
            result = modification_service.apply(
                description=description,
                changes=[{
                    "file_path": full_path,
                    "operation": "replace_text",
                    "params": {
                        "old_text": old_text,
                        "new_text": new_text,
                    },
                }],
                confirmed=True,
            )
            return result

        except Exception as e:
            logger.error("Patch application failed: %s", e)
            return {"success": False, "error": str(e)}

    async def get_health_report(self) -> dict:
        """Get a quick health overview without generating patches."""
        analysis = await self.analyze(max_files=20)
        return {
            "health_score": analysis.health_score,
            "health_label": (
                "Excellent" if analysis.health_score > 0.9
                else "Good" if analysis.health_score > 0.7
                else "Needs Attention" if analysis.health_score > 0.5
                else "Poor"
            ),
            "files_analyzed": analysis.files_analyzed,
            "total_issues": analysis.total_issues,
            "by_severity": analysis.by_severity,
            "by_type": analysis.by_type,
        }


self_improve_service = SelfImprovementService()