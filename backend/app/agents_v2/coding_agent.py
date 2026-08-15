"""
AURA Backend — Coding Agent.

Module: app.agents_v2.coding_agent
Purpose: Specialized agent for code-related tasks.

Capabilities:
    - write_code    : Generate code from description
    - fix_code      : Debug and fix broken code
    - explain_code  : Explain what code does
    - review_code   : Code quality review
    - generate_tests: Generate test cases
"""

import logging
import time

from app.agents_v2.base_agent_v2 import AgentResult, BaseAgentV2

logger = logging.getLogger(__name__)

CODING_SYSTEM_PROMPT = (
    "You are an expert software engineer. "
    "Write clean, production-ready code with proper error handling. "
    "Always add comments for complex logic. "
    "If fixing code, explain what was wrong and what you changed. "
    "If explaining code, be clear and concise. "
    "Format code with proper indentation."
)


class CodingAgent(BaseAgentV2):
    """
    Specialized agent for code-related tasks.

    Handles: write, fix, explain, review, test generation.
    Uses Ollama LLM for all code tasks.
    """

    @property
    def name(self) -> str:
        return "CodingAgent"

    @property
    def description(self) -> str:
        return "Writes, fixes, explains, and reviews code."

    @property
    def capabilities(self) -> list[str]:
        return [
            "write_code", "fix_code", "explain_code",
            "review_code", "generate_tests", "code",
        ]

    async def execute(self, task: str, context: dict) -> AgentResult:
        """
        Execute a coding task.

        Args:
            task: Description of coding task.
            context: {
                "task_type": write|fix|explain|review|test,
                "code": existing code (for fix/explain/review),
                "language": programming language,
                "error": error message (for fix tasks),
            }

        Returns:
            AgentResult: Generated/fixed/explained code.
        """
        start = time.time()
        self.log(f"Task: {task[:80]}")

        task_type = context.get("task_type", "write")
        code = context.get("code", "")
        language = context.get("language", "python")
        error_msg = context.get("error", "")

        try:
            if task_type == "write":
                response = await self._write_multistep(task, language)
            else:
                prompt = self._build_prompt(task, task_type, code, language, error_msg)
                from app.services.brain_orchestrator import BrainRole, run_with_role
                response = await run_with_role(
                    BrainRole.CODING, prompt, system_prompt=CODING_SYSTEM_PROMPT,
                )

            duration = int((time.time() - start) * 1000)
            self.log(f"Completed in {duration}ms")

            return AgentResult(
                agent_name=self.name,
                task=task,
                success=True,
                output=response.strip(),
                metadata={
                    "task_type": task_type,
                    "language": language,
                },
                duration_ms=duration,
            )

        except Exception as e:
            logger.error("CodingAgent error: %s", e)
            return AgentResult(
                agent_name=self.name,
                task=task,
                success=False,
                output="",
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )

    async def _write_multistep(self, task: str, language: str) -> str:
        """
        Plan -> Code -> Self-review -> Final. A single LLM call from a
        small (3B) model tends to produce shallow, buggy code for
        anything beyond a few lines. Breaking it into stages — plan the
        structure first, write against that plan, then have the model
        critique and fix its own output — measurably improves quality
        for multi-part tasks (websites, multi-function scripts) at the
        cost of a few extra seconds per stage.
        """
        from app.services.brain_orchestrator import BrainRole, run_with_role

        # Stage 1: Plan — keep this short, it's scaffolding not prose.
        plan_prompt = (
            f"Task: Write {language} code for: {task}\n\n"
            f"Before writing any code, list a short plan: what files/"
            f"functions/sections are needed and in what order. "
            f"3-6 bullet points max. No code yet."
        )
        plan = await run_with_role(
            BrainRole.CODING, plan_prompt, system_prompt=CODING_SYSTEM_PROMPT,
        )

        # Stage 2: Code — write against the plan.
        code_prompt = (
            f"Task: Write {language} code for: {task}\n\n"
            f"Follow this plan:\n{plan.strip()}\n\n"
            f"Now write the complete code. Requirements:\n"
            f"- Clean, readable code\n"
            f"- Proper error handling\n"
            f"- Comments for complex parts\n"
            f"- Production-ready quality, no placeholders"
        )
        draft_code = await run_with_role(
            BrainRole.CODING, code_prompt, system_prompt=CODING_SYSTEM_PROMPT,
        )

        # Stage 3: Self-review — catch obvious bugs before returning.
        review_prompt = (
            f"Review this {language} code you just wrote for the task "
            f'"{task}":\n\n{draft_code.strip()}\n\n'
            f"Check for: syntax errors, unclosed brackets, missing "
            f"imports, logic bugs, missing error handling. "
            f"If you find issues, output the CORRECTED full code. "
            f"If it's already correct, output it unchanged. "
            f"Output ONLY the final code (with brief comments), no meta-commentary."
        )
        final_code = await run_with_role(
            BrainRole.CODING, review_prompt, system_prompt=CODING_SYSTEM_PROMPT,
        )

        return final_code

    def _build_prompt(
        self,
        task: str,
        task_type: str,
        code: str,
        language: str,
        error: str,
    ) -> str:
        """Build task-specific prompt."""
        if task_type == "fix" and code:
            prompt = f"Fix this {language} code:\n\n```{language}\n{code}\n```\n"
            if error:
                prompt += f"\nError message:\n{error}\n"
            prompt += "\nProvide the fixed code and explain what was wrong."

        elif task_type == "explain" and code:
            prompt = (
                f"Explain this {language} code clearly:\n\n"
                f"```{language}\n{code}\n```\n"
                f"\nBreak down what each part does."
            )

        elif task_type == "review" and code:
            prompt = (
                f"Review this {language} code for quality, bugs, and improvements:\n\n"
                f"```{language}\n{code}\n```\n"
                f"\nProvide specific suggestions."
            )

        elif task_type == "test" and code:
            prompt = (
                f"Generate comprehensive test cases for this {language} code:\n\n"
                f"```{language}\n{code}\n```\n"
                f"\nInclude edge cases and error cases."
            )

        else:
            prompt = (
                f"Write {language} code for: {task}\n\n"
                f"Requirements:\n"
                f"- Clean, readable code\n"
                f"- Proper error handling\n"
                f"- Comments for complex parts\n"
                f"- Production-ready quality"
            )

        return prompt


coding_agent = CodingAgent()