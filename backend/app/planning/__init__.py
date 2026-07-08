"""
AURA Backend — Self Improvement Planner Package.

Package: app.planning
Purpose: Turns a free-text improvement request into a structured plan:
         which files are affected, how risky the change is, and what
         the tradeoffs are. NEVER modifies any file — planning only.
         Applying a plan is Phase 10's responsibility and does not
         exist yet; every plan requires explicit user approval before
         any future application step can run.

Modules:
    request_parser  — Extracts intent/keywords/mentioned files from text
    impact_mapper    — Finds candidate affected files across the project
    risk_estimator   — Assigns a risk level and explanation
    plan_service     — Orchestrates the full planning pipeline
"""