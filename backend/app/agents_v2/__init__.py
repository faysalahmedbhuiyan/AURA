"""
AURA Backend — Multi-Agent Framework v2.

Package: app.agents_v2
Phase: Tier 4-A1

Agents collaborate through a central Coordinator.
Each agent is specialized and independent.
Agents communicate via structured messages.

Available agents:
    CodingAgent   — Write, fix, explain, test code
    ResearchAgent — Web research via SearXNG

Coordinator:
    Routes tasks to appropriate agent(s).
    Handles sequential execution (RAM constraint on 8GB).
    Returns consolidated result.
"""