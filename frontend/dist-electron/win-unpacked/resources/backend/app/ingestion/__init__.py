"""
AURA Backend — Document Ingestion Package (Tier 3, L1).

Purpose: Extracts text from PDF/DOCX files and feeds it into the
         EXISTING Tier 2 Intelligence pipeline (classify -> dedupe ->
         create/evolve -> relate). Does NOT duplicate that pipeline —
         L2 (merging), L3 (confirmation queue), and L4 (knowledge
         graph) are already implemented by intelligence_service and
         are reused as-is here.

Safety: auto_confirm defaults to False — a large document produces
many chunks the user hasn't reviewed individually, so they go to the
pending queue (visible via GET /intelligence/pending) rather than
becoming permanent immediately, unlike the single-message "save it"
chat command where the user's own words ARE the confirmation.

Modules:
    document_parser  — PDF (pypdf) and DOCX (python-docx) text extraction
    chunker            — Splits long text into overlapping chunks
    ingestion_service     — Orchestrates parse -> chunk -> Tier 2 pipeline
"""