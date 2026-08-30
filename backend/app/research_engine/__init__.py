"""
AURA Backend — Autonomous Research Engine Package.

Package: app.research_engine
Purpose: Phase 24 — Research the internet intelligently.

         Workflow (strictly enforced):
         1. Search   — Multi-source DuckDuckGo search
         2. Collect  — Fetch and extract content from URLs
         3. Deduplicate — Remove duplicate/redundant results
         4. Rank     — Score sources by credibility
         5. Confidence — Calculate overall confidence score
         6. Synthesize — LLM-powered multi-source summary
         7. Ask User  — Present candidate, never auto-save
         8. Store     — Only after explicit confirmation

         CRITICAL RULES:
         - NEVER store automatically
         - ALWAYS provide source URLs
         - ALWAYS show confidence score
         - ALWAYS ask user before saving
         - Every source is tracked and shown to user
"""