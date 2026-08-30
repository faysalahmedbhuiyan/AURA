"""
AURA Backend — Natural Language Intelligence Engine Package.

Package: app.nlp
Purpose: Phase 20 — makes AURA understand Bangla, Banglish, English,
         Hindi, and mixed-language input the way a human would.
         Also handles intent detection, conversation compression, and
         context window optimization so long chats stay within the
         model's 8192-token context on an 8GB machine.

Design principle: Language detection is rule-based (fast, no LLM call).
Translation only invokes the LLM when Banglish is actually detected —
avoids adding latency/RAM cost to every single message.

Modules:
    language_detector  — Detects bn/banglish/en/hi/mixed via heuristics
    translator          — Banglish -> Bangla via LLM (only when needed)
    intent_detector       — Classifies message intent (chat/research/
                             file/code/task/question)
    context_compressor      — Summarizes old history to fit context window
    nlp_service               — Orchestrates the full pipeline, called by chat.py
"""