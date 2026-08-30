# Tier 3 — Learning Engine (L1: Document Ingestion + File Vault) — Final Report

**Status:** ✅ Complete and verified working end-to-end
**Date:** 2026-07-25
**Verified by:** Live testing across multiple conversations (NID card OCR,
multi-page DOCX MOU), confirmed correct cross-conversation recall and
accurate document-grounded Q&A.

---

## Scope Evolution

Original Tier 3 plan (L1-L4) was narrowed after auditing Tier 2 directly
via GitHub clone: L2 (multi-source merging), L3 (confirmation queue),
and L4 (knowledge graph) were already implemented inside Tier 2's
`evolution_engine.py` / `is_confirmed` flag / `relationship_builder.py`.

Tier 3's real, new scope became:

1. **L1: Document ingestion** (PDF/DOCX/image → Tier 2 pipeline)
2. **File Vault** (added mid-development, per explicit user request) —
   permanent original-file storage, named recall from ANY conversation,
   and page-image viewing — because Tier 2 alone only stores
   LLM-summarized knowledge, which lost exact details (NID numbers,
   specific names) and couldn't answer "show me page 4."

---

## Final Architecture

User attaches file (📎) → text extracted (OCR/PDF/DOCX) → STAGED
(nothing permanent yet, conversation-scoped)
↓
"save it as <name>" →

1. File Vault: original file + full text + page images → permanent disk + DB
2. Tier 2: text chunked → classified/deduped/related (existing pipeline, reused)
   ↓
   From ANY future conversation, mentioning the saved name →
   auto-detected → re-staged from Vault → questions answered from
   REAL full text (not the Tier 2 summary) → isolated, persona-free
   LLM prompt for accuracy

---

## New Files Created

backend/app/ingestion/init.py
backend/app/ingestion/document_parser.py # PDF (PyMuPDF/fitz), DOCX (python-docx), image OCR (pytesseract)
backend/app/ingestion/chunker.py # overlapping chunker, 4000 chars/200 overlap
backend/app/ingestion/staging_store.py # per-conversation staged file (in-memory + temp disk)
backend/app/ingestion/job_store.py # background-save progress tracker
backend/app/ingestion/ingestion_service.py # sync + background text->Tier2 pipeline
backend/app/api/v1/routes/ingestion.py # /stage, /upload, /confirm-source, /status
backend/app/models/vault_item.py # FileVaultItem model (permanent record)
backend/app/repositories/vault_repository.py # Vault DB ops + name-matching
backend/app/vault/init.py
backend/app/vault/vault_service.py # saves to Vault + triggers Tier 2 in parallel
backend/app/api/v1/routes/vault.py # /vault, /vault/{id}, /vault/{id}/page/{n}
**Modified files:**
backend/app/api/v1/routes/chat.py # staged-file-aware intent dispatch, name-based

# auto-recall, page-image requests, isolated

# file-Q&A prompt (see Bug 5 below)

backend/app/main.py # ingestion + vault routers registered
backend/app/intelligence/evolution_engine.py # removed wasted per-chunk embedding call
frontend/src/services/api.js
frontend/src/components/Chat/ChatWindow.jsx
frontend/src/components/Chat/ChatInput.jsx
frontend/src/components/Chat/MessageBubble.jsx # renders [[IMAGE:url]] markers as real images

---

## Dependencies Added

pip install pypdf python-docx pytesseract pillow pymupdf
Plus external: **Tesseract OCR** binary (confirmed working: v5.5.0.20241111, Windows).

---

## New API Endpoints

| Method | Endpoint                                     | Purpose                                                               |
| ------ | -------------------------------------------- | --------------------------------------------------------------------- |
| POST   | `/api/v1/chat/new`                           | Create empty conversation (needed to stage a file before any message) |
| POST   | `/api/v1/ingestion/stage`                    | Attach file to a conversation, extract text, stage (no save)          |
| DELETE | `/api/v1/ingestion/stage/{conversation_id}`  | Detach staged file without saving                                     |
| GET    | `/api/v1/ingestion/status/{conversation_id}` | Poll background-save progress                                         |
| POST   | `/api/v1/ingestion/upload`                   | Silent bulk PDF/DOCX upload straight to Tier 2 queue                  |
| POST   | `/api/v1/ingestion/confirm-source`           | Bulk-confirm pending items from one file                              |
| GET    | `/api/v1/vault`                              | List all permanently saved vault items                                |
| GET    | `/api/v1/vault/{item_id}`                    | Get vault item details + text preview                                 |
| GET    | `/api/v1/vault/{item_id}/page/{n}`           | Serve a rendered page image (PNG)                                     |

---

## Bugs Found & Fixed During This Phase (chronological)

1. **`pypdf` not installed** — missed install step, simple fix.
2. **`SAVE_PATTERNS` anchored with `^`** — "save it" only matched at
   message START, so "...she will be my wife. save it" (trigger at the
   END) was never detected. Fixed: removed anchor, added inline-content
   extraction so text written alongside the trigger gets saved directly.
3. **50-page PDF timeout** — each chunk needs 2-3 sequential Ollama
   calls; 15 chunks × several seconds each exceeded any HTTP timeout.
   Fixed: hybrid sync (≤3 chunks)/background (asyncio.create_task with
   its own DB session, since the request's session closes on response)
   path, chunk size increased 1500→4000 chars to reduce call count,
   plus a wasted duplicate-check embedding call removed from
   `evolution_engine.find_duplicate()` for a direct speed win.
4. **Staging cleared immediately after "save it"** — any follow-up
   question about a just-saved file got zero context, causing total
   hallucination (the LLM fell back to reciting its own system prompt).
   Fixed: `mark_saved()` instead of `clear()` — staging persists until
   explicit "forget it" or a new file is attached.
5. **AURA persona bleeding into document answers** (found via the MOU
   chairman-name test) — the general chat system prompt strongly
   associates "chairman"-adjacent identity questions with
   "MD Faysal Ahmed Bhuiyan" (the hardcoded owner-name rule), pulling
   answers toward that name even when a document named someone else.
   Fixed: file Q&A now uses a fully isolated `FILE_QA_SYSTEM_PROMPT` —
   no AURA persona, no chat history, no RAG context, just the document
   text and the question, explicitly instructed to never substitute a
   recognized name for what the document actually says.
6. **`SEARCH_PATTERNS_WITH_STAGED_FILE` referenced but never defined**
   — an incomplete patch application caused `NameError` on EVERY chat
   message (not just search-like ones), since intent detection runs
   before the dispatch branch. Fixed by adding the missing constant.
7. **"what is my X" routed to web search instead of file context** —
   broad `SEARCH_PATTERNS` (`what is`, `who is`) fired even with a file
   staged. Fixed: narrower `SEARCH_PATTERNS_WITH_STAGED_FILE` used
   whenever a file is staged, only explicit web-intent verbs
   (search/google/news/research) still force a real search.

---

## Known Limitations (honest)

- **Name matching is exact-substring, not fuzzy.** Saved as "FAYSAL
  NID", asking about "Faysal Passport" will NOT auto-match. User must
  reference the saved name reasonably closely.
- **No page images for DOCX** (no fixed pagination in that format) —
  page-image viewing only works for PDF/image vault items.
- **"Summarize the whole document" is capped at ~8000 characters** of
  context — very large documents only get their first portion
  considered. True map-reduce summarization not built.
- **Small model (qwen2.5:3b) accuracy on documents with multiple
  similar names/entities is not 100% guaranteed** even after the
  isolated-prompt fix — Bug 5's fix significantly improved but did not
  mathematically eliminate this class of error.
- **Ollama serializes requests** — a background Vault save in progress
  will make concurrent normal chat feel slower until it finishes.
- **NID/personal document images are now stored, unencrypted, under
  `D:/AURA/vault/`.** User was warned to keep `vault/` and `database/`
  in `.gitignore` before any `git push` — should be re-verified before
  each push involving sensitive test data.

---

## What a future session should NOT do

- Do NOT rebuild classification, deduplication, or the knowledge graph
  — Tier 2's `intelligence_service` already owns that, and Vault calls
  into it rather than duplicating it.
- Do NOT change `ingestion_service.MAX_CHUNKS_PER_FILE` (30) or
  `chunker.CHUNK_SIZE` (4000) without re-testing large-file timing —
  these were tuned against real timeout failures.
