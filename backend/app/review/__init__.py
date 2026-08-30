"""
AURA Backend — Self Review Engine Package.

Package: app.review
Purpose: Analyzes AURA's own codebase for quality issues and technical
         debt. This package is READ-ONLY — it never modifies code.
         Per Constitution: analysis and suggestions only, all changes
         require explicit user approval through later phases (9-10).

Modules:
    code_analyzer      — AST-based per-file issue detection
    debt_detector       — Aggregates issues into a debt score
    suggestion_engine    — Converts issues into human-readable suggestions
    review_service       — Orchestrates the full review pipeline
"""