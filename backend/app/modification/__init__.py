"""
AURA Backend — Safe Self Modification Package.

Package: app.modification
Purpose: Applies approved changes to files with mandatory backup,
         explicit confirmation, and result reporting. This is the
         ONLY package in AURA allowed to write to arbitrary project
         files on the user's behalf — every other package (planning,
         review) is read-only by design.

Core Rule (non-negotiable):
    AURA never modifies a file without:
    1. An explicit confirmed=True from the user for THIS SPECIFIC change
    2. A backup created immediately before the write
    3. A full report of what changed afterward

Modules:
    backup_manager    — Creates and restores timestamped file backups
    change_applier     — Writes new content to a file (confirmed only)
    result_reporter      — Builds the final human-readable report
    modification_service — Orchestrates apply → verify → report
"""