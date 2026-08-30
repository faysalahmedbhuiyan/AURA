# AURA — Master Documentation

**Project:** Personal AI Operating System for MD Faysal Ahmed Bhuiyan
**Last updated:** August 10, 2026
**Branch:** `checking`
**Purpose of this file:** Single source of truth for everything AURA can
do, how it's built, and its known limitations. Any AI or human reading
this file should be able to understand the full current state without
needing any other document. All other scattered docs in `docs/` can be
deleted once this file is committed.

---

## 1. What AURA Is

AURA is a **local-first personal AI OS assistant**. Its core intelligence
(LLM), memory, and generated content all live on the user's own machine —
nothing is sent to the cloud except where explicitly noted (video
generation, and optionally URL/YouTube fetching for learning).

```
Backend:  FastAPI (Python 3.11) + SQLite (WAL mode) + ChromaDB
Frontend: React 19 + Vite + Electron (packaged as a clickable desktop app)
LLM:      Ollama, custom "aura-brain" model (based on qwen2.5:3b-instruct)
Voice:    faster-whisper (STT) + Piper (TTS) — built, currently unused
Hardware target (dev machine): Intel i5 11th Gen, 8GB RAM, Intel Iris Xe
          (3.9GB shared VRAM, no dedicated GPU) — every design decision
          below accounts for this constraint.
Deployment: Ubuntu (for Tier 6B security monitoring), Windows (main dev/use)
```

---

## 2. Feature Inventory (What AURA Can Actually Do)

### 2.1 Chat & Memory (Tier 1-4, pre-existing)

- Text chat in Bangla and English via `aura-brain`
- Conversation history in sidebar; conversations can be deleted
- 4-tier memory: Personal, Knowledge Base, Decision, Learning Queue
  (nothing is permanently learned without explicit user confirmation)
- Document ingestion: PDF, DOCX, images (OCR), plain text — stage
  temporarily or save permanently to the File Vault
- Background save with live progress ("is it saved?" shows X/N sections)
- Voice (STT/TTS) code exists and works, but is currently turned off by
  user preference — Bangla + English only supported

### 2.2 Self-Improvement System (pre-existing)

- Self Review (Python code only — JS/JSX not yet supported)
- Self-Improvement Planner (plans changes before making them)
- Safe Self-Modification (git-backed backup before any self-edit,
  protected files like `main.py`/`.env` can never be touched)
- Rollback system (git-based)

### 2.3 Image Generation (Tier 5) — 100% Local

| Capability                | Model                             | Notes                                                                |
| ------------------------- | --------------------------------- | -------------------------------------------------------------------- |
| Text-to-image, fast       | SD-Turbo (ONNX, CPU)              | 1 step, ~1-2 min, `quality: "fast"`                                  |
| Text-to-image, realistic  | Realistic Vision V5.1 (ONNX, CPU) | ~22 steps, ~15-20 min, `quality: "realistic"`                        |
| Style transform (img2img) | Same models, img2img mode         | cartoon/sketch confirmed good; watercolor is weak (model limitation) |
| Face preservation         | OpenCV Haar cascade + blend       | Keeps the person recognizable during style transform                 |

- **Endpoints:** `POST /api/v1/image/generate`, `POST /api/v1/image/transform`, `GET /api/v1/image/file/{name}`, `GET /api/v1/image/status`, `POST /api/v1/image/unload`
- **Chat commands:** `"generate an image of ..."`, `"generate a realistic image of ..."`, long descriptive prompts starting with generate/create are also auto-detected. `"transform image: <style>"` (after attaching a photo).
- **Hardware notes:** DirectML (GPU) was tried and abandoned — Iris Xe's 3.9GB shared VRAM reliably OOMs mid-generation. CPU-only is the proven path. ~70% of logical CPU threads used, 30% left free. Ollama is force-unloaded before every generation.
- **Known limits:** multi-person scenes often fail (SD1.5-class model at 512x512 struggles with 2+ distinct subjects), readable text on signs rarely works, watercolor-style transforms are inconsistent.
- **Hard boundary (will not build):** face-swap/identity-transfer onto a different generated scene (deepfake-adjacent) was explicitly declined and never built.

### 2.4 Video Generation (Tier 5) — Cloud (Free Tier)

- `POST /api/v1/video/generate` (text-to-video), `POST /api/v1/video/animate` (image-to-video), `POST /api/v1/video/add-dialogue` (gendered TTS dialogue muxed onto video via ffmpeg)
- Uses Hugging Face Inference Providers (`Wan-AI/Wan2.2-TI2V-5B` via fal-ai), requires a free `HF_TOKEN` in `.env` with Inference Providers permission enabled
- **Real limits:** free tier is credit-limited (~10 clips/month), native output isn't guaranteed 1080p, output is silent by default (dialogue is a separate add-on step), clips are short (a few seconds) — not controllable to arbitrary lengths like 30s
- Gendered dialogue uses two local Piper voices (male: `en_US-lessac-medium`, female: `en_US-amy-medium`) — **English only, no Bangla voice available**

### 2.5 Sub-Agent Factory (new)

AURA can create specialized "sub-agent" personas on request. Not real
fine-tuning (infeasible on this hardware) — each sub-agent is a
custom system prompt (AURA writes it itself) plus a private knowledge
scratchpad the user can teach it, both stored in SQLite (`sub_agents`,
`sub_agent_knowledge` tables).

- `create sub agent: <task description>`
- `teach sub agent <name>: <content>`
- `ask sub agent <name>: <question>`
- `list sub agents`

### 2.6 Coding Assistance (upgraded)

- `aura-brain.modelfile` has strict coding rules baked into its system prompt (complete code, error handling, comments, type hints/PEP8, etc.)
- `CodingAgent` now runs a 3-stage pipeline for "write" tasks: **Plan → Code → Self-review**, instead of one raw LLM call — meaningfully better output quality for anything beyond a few lines. Fix/explain/review/test tasks remain single-call (they don't need the extra stages).
- A dedicated "coder" sub-agent can be created via the Sub-Agent Factory above and taught project-specific conventions over time.

### 2.7 Tier 6A — Deep Learning Engine

- **A1 Deep Reader:** `learn from url: <url>` (via `trafilatura`), `learn from youtube: <url>` (via `youtube-transcript-api`) — both feed into the existing Tier 2 knowledge pipeline (classify → dedupe → relate), same as document uploads. PDF/DOCX already worked before this.
- **A2 Critical Thinking:** `think critically about: <topic>` — structured claim/assumptions/evidence-for/evidence-against/conclusion, grounded in the knowledge base where relevant (LLM is explicitly told to ignore irrelevant retrieved sources).
- **A3 Problem Solving:** `solve: <problem>` — decomposes into sub-problems, then options with trade-offs + a concrete recommendation.
- **A4 Knowledge Synthesis:** `synthesize: <topic>` — pulls everything taught about a topic and weaves it into one coherent explanation, noting contradictions between sources.
- **Honesty built into the design:** none of this is human-level reasoning — it's structured prompting over a 3B model, deliberately imposing steps a small model can follow reliably.

### 2.8 Tier 6B — Network Security Monitor (Ubuntu only)

- `app/security/`: `connection_monitor.py` (psutil-based connection tracking), `threat_detector.py` (port-scan / connection-flood / SSH brute-force pattern detection, conservative thresholds), `alert_service.py` (desktop notification + cooldown-gated response), `firewall_controller.py` (ufw block, nmcli wifi-off, shutdown — the only module allowed to touch the system)
- Auto-starts on backend boot **only on Linux** (`platform.system() == "Linux"` check in `main.py`'s lifespan) — does nothing on Windows, no wasted resources
- `security status` chat command; `/api/v1/security/*` HTTP endpoints
- Deployed via systemd (`aura-backend.service`) so it starts automatically on login — see `UBUNTU_SETUP_GUIDE.md`
- **Explicit boundary:** this is defensive only (protects AURA's own machine from intrusion). Anti-forensic/traceability-evasion tooling was requested and explicitly declined.

### 2.9 Tier 6C — Company Website Monitoring

**Not started.** Deferred until the user has their own server (current hosting won't grant AURA the access needed to monitor it). Planned scope when revisited: uptime/HTTP health checks, SSL expiry checks, and (if self-hosted with log access) traffic/error-rate anomaly detection.

### 2.10 Desktop App Packaging

- Electron + `electron-builder`, configured to auto-start the Python backend as a child process when the packaged app launches (`electron/main.js`) — so the end product is a single clickable app, no manual `uvicorn`/terminal steps needed for the end user.
- Backend (including its `venv`) is bundled via `extraResources` in `package.json`.

---

## 3. Full Dependency/Version Notes (why these exact versions matter)

The image-generation dependency stack went through significant version
hell before landing on a working, **modern and mutually-compatible**
combination. Do not casually upgrade individual packages without
checking this list first.

```
torch                  — latest (modern, not old-pinned)
transformers            — latest
diffusers               — latest (0.39+)
optimum + optimum-onnx  — latest (the modern SPLIT package — not the
                            old monolithic optimum<2.0)
huggingface_hub         — >=0.34.4,<1.0 (needs 0.34.4+ for video's
                            image_to_video method; needs <1.0 for
                            transformers compatibility)
onnxruntime (plain, NOT -directml) — CPU-only inference is the proven
                            working path on this hardware
numpy                   — 2.x is fine with modern torch (old numpy<2
                            pin is no longer needed)
opencv-python-headless  — 4.10.0.84 pinned (5.0.0 has a broken
                            CascadeClassifier — do not use 5.x)
```

Run `pip freeze > requirements.txt` after confirming everything works,
and commit it — this exact combination is fragile to arrive at again
from scratch.

---

## 4. Known Bugs Fixed Today (for future reference, avoid regressions)

- Circular import from a corrupted `knowledge_item.py` (route code had
  overwritten the actual SQLAlchemy model file) — restored via
  `git show <old-commit>` and `git checkout`.
- `asyncio.create_task()` results not stored anywhere → garbage
  collected mid-execution, silently killing background saves. Fixed by
  keeping a strong reference in a module-level set with a done-callback.
- SQLite "database is locked" under concurrent background writes —
  fixed via `PRAGMA journal_mode=WAL` + `busy_timeout=30000` on the
  engine's connect event.
- Two disconnected `if/elif` intent-dispatch chains in `chat.py` — an
  intent handled correctly in the first chain (e.g. `ingestion_status`)
  could get silently overwritten by the second chain's fallback
  (document Q&A) if that intent wasn't also listed there. Any new
  intent must be added to the chain it's actually reachable from, or
  given a `pass` no-op in the other chain.
- img2img completely ignoring the input image — root cause was
  `optimum-onnx`'s `ORTStableDiffusionImg2ImgPipeline` needing `image=`
  passed as a **list**, not a bare PIL Image.
- Repeated `from backend.app...` import typos (should always be
  `from app...` — the project root for imports is `backend/`, not
  `backend/backend/`).

---

## 5. Explicit Boundaries (things Claude declined to build, on purpose)

These came up during development and were refused for safety reasons —
documented here so no future session re-litigates them from scratch:

1. **Giving AURA autonomous dark-web/Kali-Linux operational capability**
   (framed as "security research") — declined as equivalent to building
   hacking tooling regardless of stated intent.
2. **Face-swap/identity-transfer into a separately generated scene**
   (e.g. "put my face on a different character in this video") —
   declined as deepfake-adjacent, no way to verify consent of any
   depicted person.
3. **Anti-tracing/anti-forensic tooling** for network activity (as an
   extra layer "in case Tor is bypassed") — declined; legitimate privacy
   is Tor's job, evading identification is a different thing entirely.
4. img2img was found to be capable of producing sexualized/nude content
   from a real, identifiable person's photo under certain style prompts.
   Once discovered, real-photo img2img transformation was fully retired
   from active development — text-to-image (no real person's photo as
   input) remains in use.

---

## 6. What's NOT Built Yet (honest backlog)

- Tier 6C (company website monitoring) — waiting on own server
- Coding Mentor Mode, Project Understanding Engine, Goal Manager —
  documented in old planning docs, no code written
- Self Review for JS/JSX/CSS (Python only currently)
- Automated test running after self-modification
- Web browsing agent
- Bangla voice (Piper has no Bangla model currently)
- True LoRA/fine-tuning for personalized image style/subject (would
  need free cloud training, e.g. Google Colab — plan exists, not
  executed)

---

## 7. Where Things Live (quick file map)

```
backend/app/services/image_service.py       — image generation + transform
backend/app/services/video_service.py       — video generation (HF)
backend/app/services/video_audio_service.py — gendered dialogue muxing
backend/app/services/reasoning_service.py   — Tier 6A think/solve/synthesize
backend/app/services/deep_reader_service.py — Tier 6A URL/YouTube reading
backend/app/agents_v2/sub_agent_factory.py  — sub-agent create/teach/ask
backend/app/agents_v2/coding_agent.py       — multi-step code generation
backend/app/security/                       — Tier 6B (Ubuntu only)
backend/app/api/v1/routes/chat.py           — all chat intent routing (fragile, be careful)
backend/scripts/download_model.py           — SD-Turbo ONNX export
backend/scripts/download_realistic_model.py — Realistic Vision ONNX export
backend/scripts/download_female_voice.py    — second Piper voice
frontend/electron/main.js                   — desktop app + backend auto-start
UBUNTU_SETUP_GUIDE.md                       — Tier 6B deployment steps
```
