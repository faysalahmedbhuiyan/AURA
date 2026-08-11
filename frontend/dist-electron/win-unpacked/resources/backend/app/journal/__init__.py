"""
AURA Backend — Development Journal Package.

Package: app.journal
Purpose: Automated engineering log and decision tracker (Phase 12).
         Records session summaries, Architecture Decision Records (ADR),
         and change history. Read/write for entries themselves, but
         entries are never edited or deleted once created — the journal
         is an append-only history.

Modules:
    summary_generator — Builds a readable summary from a set of entries
"""