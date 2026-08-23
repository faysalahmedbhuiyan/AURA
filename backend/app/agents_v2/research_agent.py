"""
AURA Backend — Research Agent.

Module: app.agents_v2.research_agent
Purpose: Specialized agent for web research tasks.

Capabilities:
    - web_search    : Quick web search
    - deep_research : Multi-source research with synthesis
    - fact_check    : Verify a claim against web sources
    - news_search   : Latest news on a topic
"""

import logging
import time

from app.agents_v2.base_agent_v2 import AgentResult, BaseAgentV2

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgentV2):
    """
    Specialized agent for web research.

    Uses SearXNG for search and Ollama for synthesis.
    Never stores results automatically — returns candidate.
    """

    @property
    def name(self) -> str:
        return "ResearchAgent"

    @property
    def description(self) -> str:
        return "Researches topics on the web using SearXNG."

    @property
    def capabilities(self) -> list[str]:
        return [
            "web_search", "deep_research",
            "fact_check", "news_search", "research",
        ]

    async def execute(self, task: str, context: dict) -> AgentResult:
        """
        Execute a research task.

        Args:
            task: Research topic or question.
            context: {
                "task_type": web_search|deep_research|news_search|fact_check,
                "language": en|bn,
                "max_results": int,
            }

        Returns:
            AgentResult: Research results (NOT auto-saved).
        """
        start = time.time()
        self.log(f"Researching: {task[:80]}")

        task_type = context.get("task_type", "web_search")
        language = context.get("language", "en")

        try:
            from app.research_engine.searcher import web_searcher

            if not await web_searcher.is_available():
                return AgentResult(
                    agent_name=self.name,
                    task=task,
                    success=False,
                    output="",
                    error="SearXNG not available. Ensure Docker is running.",
                )

            if task_type == "news_search":
                results = await self._run_sync(
                    lambda: web_searcher.search_news(task, max_results=5, language=language)
                )
            else:
                results = await self._run_sync(
                    lambda: web_searcher.search(task, max_results=6, language=language)
                )

            if not results:
                return AgentResult(
                    agent_name=self.name,
                    task=task,
                    success=False,
                    output="",
                    error="No search results found.",
                )

            formatted = self._format_results(results, task_type)
            duration = int((time.time() - start) * 1000)
            self.log(f"Found {len(results)} results in {duration}ms")

            return AgentResult(
                agent_name=self.name,
                task=task,
                success=True,
                output=formatted,
                metadata={
                    "result_count": len(results),
                    "task_type": task_type,
                    "sources": [r.url for r in results[:5]],
                },
                duration_ms=duration,
            )

        except Exception as e:
            logger.exception("ResearchAgent error: %s", e)
            return AgentResult(
                agent_name=self.name,
                task=task,
                success=False,
                output="",
                error=str(e),
            )

    async def _run_sync(self, fn):
        """Run synchronous search in executor."""
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(None, fn)

    def _format_results(self, results, task_type: str) -> str:
        """Format search results as markdown."""
        header = "📰 Latest News:" if task_type == "news_search" else "🔍 Search Results:"
        lines = [header, ""]
        for i, r in enumerate(results[:5], 1):
            snippet = (r.snippet or "")[:200]
            lines.append(f"**{i}. [{r.title}]({r.url})**")
            if snippet:
                lines.append(snippet)
            lines.append("")
        return "\n".join(lines).strip()


research_agent = ResearchAgent()