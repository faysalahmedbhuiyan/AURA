"""
AURA Backend — Rollback System Package.

Package: app.rollback
Purpose: Implements Phase 11 — Git-based Rollback System.

         Allows safe restoration of any previous project version.
         Every rollback creates a backup of the current state first,
         so rollback itself is also reversible.

         Constitution Rule 11: Every important change must be reversible.

Modules:
    git_service      — Git operations: log, diff, status, checkout
    snapshot_service — Named snapshot creation and management
    rollback_service — Full rollback pipeline orchestrator
"""