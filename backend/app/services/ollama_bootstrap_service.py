"""
AURA Backend — Ollama Bootstrap Service.

Module: app.services.ollama_bootstrap_service
Purpose: On startup, make sure Ollama itself is installed, running, has the
         base LLM pulled, and has the custom `aura-brain` model built —
         WITHOUT requiring the person who installs AURA on a fresh PC to
         know what Ollama is or run any command themselves.

Why this exists:
    AURA's chat feature is 100% dependent on Ollama (see ollama_service.py),
    but nothing previously installed Ollama on a new machine. Someone
    installing the packaged AURA.exe on a PC that had never had Ollama
    would get an app that opens fine but where chat silently fails —
    "AURA doesn't work" from the user's point of view, even though the
    backend itself was healthy. This closes that gap the same way
    model_bootstrap_service.py already does for the image/voice models:
    checked automatically, once, in the background, on first run.

Scope:
    Windows is the primary supported auto-install path (this project ships
    as a Windows desktop app — see build_portable_python.ps1 / NSIS
    target). Linux is also automated (Ollama's official install.sh is
    scriptable). macOS's installer is a drag-to-Applications .app bundle
    with no official silent/CLI install path, so on macOS this service
    only detects/starts an existing install and otherwise leaves a clear
    message rather than guessing at an unsupported silent-install method.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx
import psutil

from app.config import get_settings

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]  # .../backend
MODELS_DIR = BACKEND_DIR.parent / "models"           # matches package.json's ../models
AURA_BRAIN_MODELFILE = MODELS_DIR / "aura-brain.modelfile"
AURA_BRAIN_MODEL_NAME = "aura-brain"

OLLAMA_WIN_INSTALLER_URL = "https://ollama.com/download/OllamaSetup.exe"
OLLAMA_UNIX_INSTALL_SCRIPT_URL = "https://ollama.com/install.sh"

# Pulling AND running a 7B-class model needs real headroom — this project's
# own model_bootstrap_service.py already found as little as ~669MB free on
# a constrained machine. Rather than plow ahead, download a multi-GB model,
# and thrash the whole OS into a multi-minute freeze (which is what an
# under-provisioned machine will do), skip the pull with a clear status the
# UI can show, exactly like the SD-Turbo RAM guard already does.
#
# This is now PER-MODEL rather than one flat number — a flat 2000MB was
# too conservative for the lightest tier (1.5b realistically needs a lot
# less headroom than 7b) and was blocking pulls that would actually have
# been fine on genuinely low-RAM machines.
def _min_ram_mb_for_pull(model_name: str) -> int:
    if model_name.endswith(":1.5b") or model_name.endswith(":0.5b"):
        return 800
    if model_name.endswith(":3b"):
        return 1200
    return 2000  # 7b and anything larger/unrecognized — stay conservative

# The chat model to pull when settings.ollama_model is configured as
# "aura-brain" (a name Ollama itself can never natively provide — it only
# exists if built here from a base model). Previously this was a single
# hardcoded "qwen2.5:7b" — a 7B model realistically needs ~8GB+ RAM just
# to run at all. A PC with less than that would either fail to run it or
# grind to a crawl. Picked by TOTAL system RAM (not just what's free right
# now) so the choice is stable across restarts, unlike current free RAM.
def _pick_fallback_model() -> str:
    total_gb = psutil.virtual_memory().total / (1024 ** 3)
    if total_gb >= 16:
        return "qwen2.5:7b"
    if total_gb >= 6:
        return "qwen2.5:3b"
    return "qwen2.5:1.5b"  # runs on almost anything, including old/weak PCs


FALLBACK_BASE_MODEL = _pick_fallback_model()

# nomic-embed-text powers every embedding call (MemoryService / knowledge
# search / RAG) via Ollama's /api/embeddings — this was never pulled by
# this bootstrap at all before, causing a permanent 404 on every single
# embedding request regardless of whether chat itself worked.
EMBEDDING_MODEL = "nomic-embed-text"
MIN_RAM_MB_FOR_EMBED_PULL = 400  # nomic-embed-text is tiny (~270MB) — this was
                                   # also too conservative before

# Windows-only flag so spawned helper processes don't flash a console window.
_CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# ── Status reported to the UI via /api/v1/ollama-bootstrap-status ───────────
# States: pending -> checking -> installing -> starting -> pulling_model ->
#         building_brain -> ready   (or -> error / unsupported_platform)
ollama_bootstrap_state: dict = {"status": "pending", "detail": "", "error": None}


def _set_state(status: str, detail: str = "", error: str | None = None) -> None:
    ollama_bootstrap_state["status"] = status
    ollama_bootstrap_state["detail"] = detail
    ollama_bootstrap_state["error"] = error
    logger.info("[ollama-bootstrap] %s — %s", status, detail)


# ── Detection ─────────────────────────────────────────────────────────────
async def _is_ollama_running(base_url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{base_url}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


def _find_ollama_exe() -> Path | None:
    """Look for an installed ollama executable without relying on PATH
    having been refreshed in this process (Windows only updates PATH for
    NEW processes/shells after install, not ones already running)."""
    which = shutil.which("ollama")
    if which:
        return Path(which)

    if sys.platform == "win32":
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            Path(local_appdata) / "Programs" / "Ollama" / "ollama.exe",
            Path(os.environ.get("PROGRAMFILES", "")) / "Ollama" / "ollama.exe",
        ]
        return next((p for p in candidates if p.exists()), None)

    if sys.platform == "darwin":
        p = Path("/usr/local/bin/ollama")
        return p if p.exists() else None

    p = Path("/usr/local/bin/ollama")
    if p.exists():
        return p
    p = Path("/usr/bin/ollama")
    return p if p.exists() else None


# ── Install ───────────────────────────────────────────────────────────────
async def _download_file(url: str, dest: Path, label: str = "") -> bool:
    try:
        timeout = httpx.Timeout(connect=30.0, read=120.0, write=120.0, pool=120.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                total = int(response.headers.get("content-length", 0))
                downloaded = 0
                last_logged_pct = -1
                with open(dest, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                        f.write(chunk)
                        downloaded += len(chunk)
                        # Log every 10% — this was the missing piece: before
                        # this, the log showed the download's initial "200 OK"
                        # and then nothing until it finished or a 120s stall
                        # timeout fired, making a genuinely-still-downloading
                        # installer indistinguishable from a stuck one.
                        if total > 0:
                            pct = int(downloaded / total * 100)
                            if pct != last_logged_pct and pct % 10 == 0:
                                last_logged_pct = pct
                                _set_state(
                                    "installing",
                                    f"{label} ডাউনলোড হচ্ছে... {pct}% "
                                    f"({downloaded // (1024*1024)}MB / {total // (1024*1024)}MB)",
                                )
                        elif downloaded % (10 * 1024 * 1024) < (1024 * 1024):
                            # No content-length header — report raw MB instead.
                            _set_state(
                                "installing",
                                f"{label} ডাউনলোড হচ্ছে... {downloaded // (1024*1024)}MB",
                            )
        return True
    except Exception as e:
        logger.error("[ollama-bootstrap] Download failed (%s): %s", url, e)
        return False


async def _install_windows() -> bool:
    tmp_dir = Path(tempfile.gettempdir())
    installer = tmp_dir / "AURA-OllamaSetup.exe"

    _set_state("installing", "OllamaSetup.exe ডাউনলোড হচ্ছে...")
    if not await _download_file(OLLAMA_WIN_INSTALLER_URL, installer, label="OllamaSetup.exe"):
        return False

    _set_state("installing", "Ollama silent install চলছে (কয়েক মিনিট লাগতে পারে)...")
    try:
        # Ollama's Windows installer is Inno Setup-based — these are the
        # standard Inno Setup unattended flags (no UI, no reboot prompt,
        # no admin rights required — Ollama installs per-user by default).
        proc = await asyncio.create_subprocess_exec(
            str(installer), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
            creationflags=_CREATE_NO_WINDOW,
        )
        await asyncio.wait_for(proc.wait(), timeout=900)
    except asyncio.TimeoutError:
        logger.error("[ollama-bootstrap] Windows installer timed out after 15 minutes.")
        return False
    except Exception as e:
        logger.error("[ollama-bootstrap] Windows installer failed to launch: %s", e)
        return False
    finally:
        installer.unlink(missing_ok=True)

    return _find_ollama_exe() is not None


async def _install_unix() -> bool:
    tmp_dir = Path(tempfile.gettempdir())
    script = tmp_dir / "aura-ollama-install.sh"

    _set_state("installing", "install.sh ডাউনলোড হচ্ছে...")
    if not await _download_file(OLLAMA_UNIX_INSTALL_SCRIPT_URL, script, label="install.sh"):
        return False
    script.chmod(0o755)

    _set_state("installing", "Ollama install script চলছে...")
    try:
        proc = await asyncio.create_subprocess_exec("sh", str(script))
        await asyncio.wait_for(proc.wait(), timeout=900)
        return proc.returncode == 0
    except Exception as e:
        logger.error("[ollama-bootstrap] Unix install script failed: %s", e)
        return False
    finally:
        script.unlink(missing_ok=True)


async def _ensure_installed() -> bool:
    if _find_ollama_exe() is not None:
        return True

    if sys.platform == "win32":
        return await _install_windows()
    if sys.platform == "darwin":
        # No official silent/CLI install path for macOS's .app bundle —
        # auto-installing here would mean silently downloading and
        # mounting a DMG with no user-visible confirmation, which is
        # worse than a clear one-time manual step.
        _set_state(
            "unsupported_platform",
            "macOS-এ Ollama auto-install সাপোর্ট করে না এখনো। "
            "একবার https://ollama.com থেকে ম্যানুয়ালি ইনস্টল করুন।",
        )
        return False
    # Linux and other POSIX platforms.
    return await _install_unix()


# ── Start / warm up ───────────────────────────────────────────────────────
async def _ensure_running(base_url: str) -> bool:
    if await _is_ollama_running(base_url):
        return True

    exe = _find_ollama_exe()
    if exe is None:
        return False

    _set_state("starting", "Ollama service চালু করা হচ্ছে...")
    try:
        subprocess.Popen(
            [str(exe), "serve"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=_CREATE_NO_WINDOW,
            start_new_session=(sys.platform != "win32"),
        )
    except Exception as e:
        logger.error("[ollama-bootstrap] Failed to spawn 'ollama serve': %s", e)
        return False

    for _ in range(60):  # up to ~60s for the service to come up
        if await _is_ollama_running(base_url):
            return True
        await asyncio.sleep(1)
    return False


# ── Models ────────────────────────────────────────────────────────────────
async def _list_model_names(base_url: str) -> set[str]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{base_url}/api/tags")
            r.raise_for_status()
            data = r.json()
            return {m.get("name", "").split(":")[0] for m in data.get("models", [])}
    except Exception:
        return set()


async def _pull_model(base_url: str, model: str) -> bool:
    """Streams progress from /api/pull so a large (multi-GB) base-model
    pull is visible in the log and never silently 'hangs'."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(connect=30.0, read=None, write=120.0, pool=120.0)) as client:
            async with client.stream(
                "POST", f"{base_url}/api/pull", json={"name": model, "stream": True}
            ) as response:
                response.raise_for_status()
                last_pct = -1
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    total, completed = data.get("total"), data.get("completed")
                    if total and completed:
                        pct = int(completed / total * 100)
                        if pct != last_pct and pct % 10 == 0:
                            last_pct = pct
                            _set_state("pulling_model", f"'{model}' ডাউনলোড হচ্ছে... {pct}%")
                    if data.get("status") == "success":
                        return True
        return True
    except Exception as e:
        logger.error("[ollama-bootstrap] Pulling '%s' failed: %s", model, e)
        return False


async def _ensure_aura_brain(base_url: str, pulled_base_model: str) -> bool:
    """Builds the custom aura-brain model from the bundled Modelfile if one
    shipped with this build. If NOT — this is the critical fallback that
    was missing before: creates aura-brain as a plain alias of whatever
    base model was actually pulled, via a throwaway one-line Modelfile
    (`FROM <base>`), so a chat request for "aura-brain" can never 404 just
    because the personality Modelfile wasn't bundled into this particular
    installer. Only relevant at all if settings.ollama_model is literally
    "aura-brain" — see run_ollama_bootstrap_in_background()."""
    existing = await _list_model_names(base_url)
    if AURA_BRAIN_MODEL_NAME in existing:
        return True

    exe = _find_ollama_exe()
    if exe is None:
        return False

    if AURA_BRAIN_MODELFILE.exists():
        _set_state("building_brain", "aura-brain মডেল তৈরি হচ্ছে...")
        modelfile_path = AURA_BRAIN_MODELFILE
        cwd = str(AURA_BRAIN_MODELFILE.parent)
    else:
        logger.info(
            "[ollama-bootstrap] No aura-brain.modelfile bundled at %s — "
            "creating aura-brain as a plain alias of '%s' instead, so it "
            "still resolves to a real model rather than 404-ing forever.",
            AURA_BRAIN_MODELFILE, pulled_base_model,
        )
        _set_state("building_brain", f"aura-brain ('{pulled_base_model}' থেকে) তৈরি হচ্ছে...")
        tmp_dir = Path(tempfile.gettempdir())
        modelfile_path = tmp_dir / "aura-brain-fallback.modelfile"
        modelfile_path.write_text(f"FROM {pulled_base_model}\n", encoding="utf-8")
        cwd = str(tmp_dir)

    try:
        proc = await asyncio.create_subprocess_exec(
            str(exe), "create", AURA_BRAIN_MODEL_NAME, "-f", str(modelfile_path),
            cwd=cwd,
            creationflags=_CREATE_NO_WINDOW,
        )
        await asyncio.wait_for(proc.wait(), timeout=600)
        return proc.returncode == 0
    except Exception as e:
        logger.error("[ollama-bootstrap] 'ollama create aura-brain' failed: %s", e)
        return False


# ── Entry point (called as a background task from main.py's lifespan) ──────
async def _try_pull_models(base_url: str, configured_model: str, base_model: str) -> tuple[bool, str]:
    """One attempt at getting the base model + embedding model in place.
    Returns (ok, reason) — reason is only meaningful when ok=False, and
    distinguishes 'ram' (worth retrying — RAM may free up) from a hard
    failure (network/pull error, not worth retrying automatically)."""
    existing = await _list_model_names(base_url)
    if base_model.split(":")[0] not in existing:
        free_mb = psutil.virtual_memory().available / (1024 * 1024)
        min_needed = _min_ram_mb_for_pull(base_model)
        if free_mb < min_needed:
            _set_state(
                "skipped_ram",
                f"'{base_model}' pull-এর জন্য অপেক্ষা করা হচ্ছে — দরকার "
                f"~{min_needed}MB free RAM, আছে মাত্র "
                f"{free_mb:.0f}MB। RAM ফাঁকা হলে automatically আবার চেষ্টা হবে "
                f"(app restart করা লাগবে না)। দ্রুত ঠিক করতে চাইলে CMD থেকে সরাসরি "
                f"চালান: ollama pull {base_model}",
            )
            return False, "ram"
        _set_state("pulling_model", f"'{base_model}' ডাউনলোড হচ্ছে...")
        if not await _pull_model(base_url, base_model):
            _set_state("error", f"'{base_model}' pull করা যায়নি।", error="pull_failed")
            return False, "hard"

    existing = await _list_model_names(base_url)
    if EMBEDDING_MODEL.split(":")[0] not in existing:
        free_mb = psutil.virtual_memory().available / (1024 * 1024)
        if free_mb >= MIN_RAM_MB_FOR_EMBED_PULL:
            _set_state("pulling_model", f"'{EMBEDDING_MODEL}' ডাউনলোড হচ্ছে...")
            if not await _pull_model(base_url, EMBEDDING_MODEL):
                logger.error(
                    "[ollama-bootstrap] Pulling embedding model '%s' failed — "
                    "memory/knowledge search will error until this is retried.",
                    EMBEDDING_MODEL,
                )
        else:
            # Not RAM-blocking the whole bootstrap for this one — chat can
            # work without embeddings. Just log and move on; it'll be
            # retried on the next full bootstrap retry cycle too.
            logger.error(
                "[ollama-bootstrap] SKIPPED embedding model '%s' — needs "
                "~%dMB free RAM, only %.0fMB available.",
                EMBEDDING_MODEL, MIN_RAM_MB_FOR_EMBED_PULL, free_mb,
            )

    if configured_model == AURA_BRAIN_MODEL_NAME:
        if not await _ensure_aura_brain(base_url, pulled_base_model=base_model):
            _set_state("error", "aura-brain মডেল তৈরি করা যায়নি।", error="brain_build_failed")
            return False, "hard"

    return True, ""


# Retry cadence for the RAM-gated step — a momentary low-RAM reading (e.g.
# antivirus scanning right after boot, or Windows itself still settling)
# used to mean bootstrap gave up FOREVER until the whole app was restarted.
# Now it just waits and checks again — the person never has to notice or
# do anything for a transient condition like that to resolve itself.
_RAM_RETRY_INTERVAL_SECONDS = 60
_RAM_RETRY_MAX_ATTEMPTS = 30  # 30 minutes of retrying before giving up


# ── Entry point (called as a background task from main.py's lifespan) ──────
async def run_ollama_bootstrap_in_background() -> None:
    settings = get_settings()
    base_url = settings.ollama_base_url

    try:
        _set_state("checking", "Ollama আছে কিনা চেক করা হচ্ছে...")
        if not await _ensure_running(base_url):
            if not await _ensure_installed():
                if ollama_bootstrap_state["status"] != "unsupported_platform":
                    _set_state("error", "Ollama install করা যায়নি।", error="install_failed")
                return
            if not await _ensure_running(base_url):
                _set_state("error", "Ollama install হলো কিন্তু চালু করা যায়নি।", error="start_failed")
                return

        # ── Determine what to actually pull ────────────────────────────────
        # CRITICAL FIX: the previous version skipped pulling ANY base model
        # whenever settings.ollama_model was exactly "aura-brain" — on the
        # (wrong) assumption that the bundled Modelfile would always handle
        # it. If that Modelfile wasn't bundled into a given installer build,
        # NOTHING ever got pulled at all: Ollama installed and ran, but had
        # zero models, so every /api/chat call 404'd forever. Now there's
        # always a concrete base model to pull, regardless of what
        # ollama_model is configured as.
        configured_model = settings.ollama_model
        base_model = (
            configured_model if configured_model and configured_model != AURA_BRAIN_MODEL_NAME
            else FALLBACK_BASE_MODEL
        )

        # ── Retry loop for the RAM-gated pull ───────────────────────────────
        # This is the actual fix for what just happened on the DELL laptop:
        # 539MB free at the exact moment AURA started is a snapshot, not a
        # permanent fact about that machine — Windows was still settling
        # right after boot. Before, "skipped_ram" was final until the whole
        # app was restarted by hand. Now it keeps re-checking in the
        # background every minute for up to 30 minutes.
        for attempt in range(1, _RAM_RETRY_MAX_ATTEMPTS + 1):
            ok, reason = await _try_pull_models(base_url, configured_model, base_model)
            if ok:
                break
            if reason == "hard":
                return  # a real pull/build error already logged — retrying won't help
            if attempt == _RAM_RETRY_MAX_ATTEMPTS:
                _set_state(
                    "error",
                    f"{_RAM_RETRY_MAX_ATTEMPTS} মিনিট চেষ্টা করেও যথেষ্ট RAM পাওয়া যায়নি। "
                    f"এই PC-তে RAM স্থায়ীভাবেই কম মনে হচ্ছে। CMD থেকে সরাসরি চালান: "
                    f"ollama pull {base_model}  (এটা AURA-র RAM-check এড়িয়ে সরাসরি download করবে)",
                    error="ram_timeout",
                )
                return
            await asyncio.sleep(_RAM_RETRY_INTERVAL_SECONDS)
        else:
            return

        _set_state("ready", "Ollama ও aura-brain প্রস্তুত।")
    except Exception as e:
        logger.error("[ollama-bootstrap] Unexpected failure: %s", e)
        _set_state("error", "অপ্রত্যাশিত সমস্যা।", error=str(e))