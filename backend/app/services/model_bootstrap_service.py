"""
AURA Backend — Model Bootstrap Service.

Module: app.services.model_bootstrap_service
Purpose: On startup, checks every local AI model AURA needs against the
         CURRENT settings paths (app.config) — the same paths every
         other service actually reads at runtime — and downloads
         whichever required model is missing. Before attempting any
         download it checks free disk space AND free RAM against a
         minimum for that specific model, so a low-resource PC gets a
         clear, honest reason instead of a silent/half-finished
         download or a confusing crash later.

Why this exists:
    Previously each download script (download_model.py etc.) saved to
    its own hardcoded path, DIFFERENT from the path the app checked at
    startup and DIFFERENT again from the path image_service.py used at
    generation time. Reinstalling never fixed anything because the
    downloaded file could never land where the app was looking. Every
    path now flows from get_settings(), so there is exactly one source
    of truth for "where does this model live".
"""

import logging
import shutil
import subprocess
import sys
import time
import asyncio
from dataclasses import dataclass
from pathlib import Path

import psutil

from app.config import get_settings

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]  # .../backend
SCRIPTS_DIR = BACKEND_DIR / "scripts"

# ── Startup bootstrap state ──────────────────────────────────────────────────
# check_and_prepare_models() is launched as a BACKGROUND task from main.py's
# lifespan (not awaited) so a multi-GB first-run download can never block
# the server from answering /api/v1/health — Electron's 120s health-check
# timeout was firing simply because startup couldn't complete until an
# hour-long download subprocess returned. This dict is what the
# /api/v1/model-bootstrap-status route reports so the UI can show real
# progress instead of the app looking "stuck".
bootstrap_state: dict = {"status": "pending", "report": None, "error": None}


async def run_bootstrap_in_background() -> None:
    """Wrapper around check_and_prepare_models() that records state for the
    /model-bootstrap-status endpoint. Never raises."""
    bootstrap_state["status"] = "running"
    try:
        report = await check_and_prepare_models()
        bootstrap_state["report"] = report
        bootstrap_state["status"] = "done"
    except Exception as e:  # belt-and-suspenders — check_and_prepare_models()
        # already catches its own errors per-model, but this guarantees the
        # background task can never die silently.
        bootstrap_state["status"] = "error"
        bootstrap_state["error"] = str(e)
        logger.error("[model-check] Background bootstrap crashed: %s", e)


@dataclass
class RequiredModel:
    key: str                       # stable id used by ensure_model_async(), e.g. "sd_fast"
    name: str                      # human-readable label for logs
    path: Path                     # resolved absolute path the app expects
    is_dir: bool                   # True = folder (ONNX export), False = single file
    download_script: str | None    # filename in scripts/, or None if not auto-fetchable
    min_disk_gb: float             # free disk space needed to attempt download
    min_ram_mb: int                # crash-prevention floor to ATTEMPT download/export —
                                    # NOT "enough to guarantee success". Checked AFTER
                                    # unloading the Ollama LLM (see _unload_ollama_for_download),
                                    # which is usually the actual RAM hog on an 8GB machine.
                                    # Getting the model onto disk matters more than a
                                    # perfectly safe margin — see ensure_model_async.
    required: bool                 # False = optional add-on, warn only, never blocks startup


def _resolve(rel_or_abs: str) -> Path:
    """Settings paths are relative to backend/ (matches config.py convention)."""
    p = Path(rel_or_abs)
    return p if p.is_absolute() else (BACKEND_DIR / p).resolve()


def _required_models() -> list[RequiredModel]:
    settings = get_settings()
    return [
        RequiredModel(
            key="sd_fast",
            name="SD-Turbo (fast image generation)",
            path=_resolve(settings.image_model_path),
            is_dir=True,
            download_script="download_model.py",
            min_disk_gb=5.0,
            min_ram_mb=1500,   # was 3000 — crash-floor only, checked after Ollama unload
            required=True,
        ),
        RequiredModel(
            key="piper_base",
            name="Piper voice (AURA's own voice)",
            path=_resolve(settings.piper_model_path),
            is_dir=False,
            download_script=None,  # ships in the repo's models/ folder
            min_disk_gb=0.2,
            min_ram_mb=200,
            required=True,
        ),
        RequiredModel(
            key="sd_realistic",
            name="Realistic Vision (high-quality image generation)",
            path=_resolve(settings.image_realistic_model_path),
            is_dir=True,
            download_script="download_realistic_model.py",
            min_disk_gb=8.0,
            min_ram_mb=2000,   # was 4000 — crash-floor only, checked after Ollama unload
            required=False,  # heavy optional add-on — don't force it on an 8GB machine
        ),
        RequiredModel(
            key="piper_female",
            name="Piper female voice (video dialogue)",
            path=_resolve(settings.piper_model_path_female),
            is_dir=False,
            download_script="download_female_voice.py",
            min_disk_gb=0.2,
            min_ram_mb=200,
            required=False,
        ),
    ]


def _model_by_key(key: str) -> RequiredModel | None:
    for m in _required_models():
        if m.key == key:
            return m
    return None


def _free_disk_gb(path: Path) -> float:
    check_dir = path.parent if not path.is_dir() else path
    while not check_dir.exists():
        check_dir = check_dir.parent
    _, _, free = shutil.disk_usage(check_dir)
    return free / (1024 ** 3)


def _free_ram_mb() -> float:
    return psutil.virtual_memory().available / (1024 * 1024)


async def _unload_ollama_for_download() -> None:
    """Free RAM before a download/export by unloading the LLM from Ollama.
    On an 8GB machine the LLM (not the download itself) is usually the
    real reason 'free RAM' looks low — this reclaims that RAM instead of
    just refusing to download. Safe no-op if Ollama isn't running; the
    LLM reloads automatically on the next chat message."""
    try:
        import httpx

        settings = get_settings()
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={"model": settings.ollama_model, "keep_alive": 0},
            )
        logger.info("[model-check] Unloaded Ollama LLM to free RAM before download.")
        await asyncio.sleep(1.5)  # give the OS a moment to actually reclaim the pages
    except Exception as e:
        logger.info("[model-check] Ollama unload skipped (not running?): %s", e)


async def check_and_prepare_models() -> dict:
    """
    Check every required local model and download what's missing and
    affordable. Never raises — a missing/optional model degrades one
    feature, it should never crash the whole app on startup.

    Returns a report dict grouping model names by outcome:
        ok, downloaded, skipped_ram, skipped_disk, download_failed,
        missing_no_script
    """
    report: dict[str, list[str]] = {
        "ok": [], "downloaded": [], "skipped_ram": [], "skipped_disk": [],
        "download_failed": [], "missing_no_script": [],
    }

    for m in _required_models():
        exists = m.path.is_dir() if m.is_dir else m.path.is_file()
        if exists:
            report["ok"].append(m.name)
            logger.info("[model-check] OK: %s -> %s", m.name, m.path)
            continue

        if not m.required:
            logger.info(
                "[model-check] Optional model not installed: %s (expected at %s). "
                "Run 'python scripts/%s' manually if you want it.",
                m.name, m.path, m.download_script,
            )
            continue

        if m.download_script is None:
            report["missing_no_script"].append(m.name)
            logger.error(
                "[model-check] REQUIRED model missing and has no auto-downloader: "
                "%s (expected at %s). This should have shipped with the repo — "
                "re-clone or restore it manually.",
                m.name, m.path,
            )
            continue

        free_gb = _free_disk_gb(m.path)
        if free_gb < m.min_disk_gb:
            report["skipped_disk"].append(m.name)
            logger.error(
                "[model-check] SKIPPED '%s' — needs %.1fGB free disk space, only "
                "%.1fGB available. Free up space and restart AURA to retry "
                "(nothing else was affected).",
                m.name, m.min_disk_gb, free_gb,
            )
            continue

        free_ram = _free_ram_mb()
        if free_ram < m.min_ram_mb:
            await _unload_ollama_for_download()
            free_ram = _free_ram_mb()
        if free_ram < m.min_ram_mb:
            report["skipped_ram"].append(m.name)
            logger.error(
                "[model-check] SKIPPED '%s' — needs ~%dMB free RAM to download/export, "
                "only %.0fMB available right now (even after freeing the LLM). Close "
                "other apps and restart AURA to retry.",
                m.name, m.min_ram_mb, free_ram,
            )
            continue

        script_path = SCRIPTS_DIR / m.download_script
        if not script_path.exists():
            report["missing_no_script"].append(m.name)
            logger.error("[model-check] Downloader script not found: %s", script_path)
            continue

        logger.info(
            "[model-check] Downloading '%s' — this can take a while, do not close AURA...",
            m.name,
        )
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True, text=True, timeout=3600,
            )
        except subprocess.TimeoutExpired:
            report["download_failed"].append(m.name)
            logger.error("[model-check] Download of '%s' timed out after 1 hour.", m.name)
            continue
        except Exception as e:
            report["download_failed"].append(m.name)
            logger.error("[model-check] Download of '%s' crashed: %s", m.name, e)
            continue

        if result.returncode == 0 and (m.path.is_dir() if m.is_dir else m.path.is_file()):
            report["downloaded"].append(m.name)
            logger.info("[model-check] Downloaded successfully: %s -> %s", m.name, m.path)
        else:
            report["download_failed"].append(m.name)
            logger.error(
                "[model-check] Download FAILED for '%s' (exit code %s).\n"
                "--- stdout (tail) ---\n%s\n--- stderr (tail) ---\n%s",
                m.name, result.returncode, result.stdout[-1500:], result.stderr[-1500:],
            )

    if report["skipped_disk"] or report["skipped_ram"] or report["download_failed"] or report["missing_no_script"]:
        logger.warning(
            "[model-check] Startup finished with issues — see errors above. "
            "AURA will still run; only the affected features (e.g. image "
            "generation) will report a clear error until fixed."
        )
    else:
        logger.info("[model-check] All required local models are present and ready.")

    return report


# ── On-demand background download (used mid-request, e.g. by image_service) ──
#
# check_and_prepare_models() above only runs once, at startup. If it skipped
# a model (RAM/disk busy at that exact moment) or a model becomes needed
# later, a feature would previously just fail with "run the script
# yourself". ensure_model_async() instead kicks off the SAME download in
# the background right when it's actually needed, and returns immediately
# with a status the caller can turn into an honest, friendly message —
# never blocks the request for the 5-20 minutes a download can take.

_download_status: dict[str, dict] = {}
_download_locks: dict[str, asyncio.Lock] = {}


def _get_lock(key: str) -> asyncio.Lock:
    if key not in _download_locks:
        _download_locks[key] = asyncio.Lock()
    return _download_locks[key]


async def _run_download_bg(key: str, m: RequiredModel) -> None:
    script_path = SCRIPTS_DIR / m.download_script
    logger.info("[model-check] Background download started for '%s' -> %s", m.name, m.path)
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(script_path),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            cwd=str(BACKEND_DIR),
        )
        stdout, stderr = await proc.communicate()
    except Exception as e:
        _download_status[key] = {"state": "failed", "error": str(e), "finished_at": time.time()}
        logger.error("[model-check] Background download crashed for '%s': %s", m.name, e)
        return

    exists = m.path.is_dir() if m.is_dir else m.path.is_file()
    if proc.returncode == 0 and exists:
        _download_status[key] = {"state": "ready", "finished_at": time.time()}
        logger.info("[model-check] Background download finished: %s -> %s", m.name, m.path)
    else:
        err_tail = (stderr or b"").decode(errors="ignore")[-1500:]
        _download_status[key] = {"state": "failed", "error": err_tail, "finished_at": time.time()}
        logger.error(
            "[model-check] Background download FAILED for '%s' (exit %s):\n%s",
            m.name, proc.returncode, err_tail,
        )


async def ensure_model_async(key: str) -> dict:
    """
    Call this right before a feature needs a model (e.g. image_service
    before generating). Non-blocking:
      - model already present            -> {"state": "ready", "path": ...}
      - download already running         -> {"state": "downloading", "elapsed_min": ...}
      - not enough free disk to start    -> {"state": "insufficient_disk", "need_gb", "free_gb", "name"}
      - not enough free RAM to start     -> {"state": "insufficient_ram", "need_mb", "free_mb", "name"}
      - no downloader available          -> {"state": "no_script", "name"}
      - previous attempt failed          -> retried fresh on next call (see below)
      - otherwise: starts the download in the background and returns
        {"state": "downloading", "elapsed_min": 0, "just_started": True}
    """
    m = _model_by_key(key)
    if m is None:
        return {"state": "unknown_model", "name": key}

    exists = m.path.is_dir() if m.is_dir else m.path.is_file()
    if exists:
        _download_status.pop(key, None)
        return {"state": "ready", "path": str(m.path)}

    current = _download_status.get(key)
    if current and current["state"] == "downloading":
        elapsed_min = (time.time() - current["started_at"]) / 60
        return {"state": "downloading", "elapsed_min": elapsed_min, "name": m.name}

    if m.download_script is None:
        return {"state": "no_script", "name": m.name}

    lock = _get_lock(key)
    async with lock:
        # Re-check inside the lock — another concurrent request may have
        # already started (or just finished) the download.
        current = _download_status.get(key)
        if current and current["state"] == "downloading":
            elapsed_min = (time.time() - current["started_at"]) / 60
            return {"state": "downloading", "elapsed_min": elapsed_min, "name": m.name}

        exists = m.path.is_dir() if m.is_dir else m.path.is_file()
        if exists:
            return {"state": "ready", "path": str(m.path)}

        free_gb = _free_disk_gb(m.path)
        if free_gb < m.min_disk_gb:
            return {
                "state": "insufficient_disk", "name": m.name,
                "need_gb": m.min_disk_gb, "free_gb": round(free_gb, 1),
            }

        # RAM is checked LAST and only as a crash-prevention floor — getting
        # the model onto disk matters more than a comfortable margin. Free
        # up real RAM first (the Ollama LLM, not the download, is usually
        # the actual hog) before deciding there truly isn't enough.
        free_ram = _free_ram_mb()
        if free_ram < m.min_ram_mb:
            await _unload_ollama_for_download()
            free_ram = _free_ram_mb()

        if free_ram < m.min_ram_mb:
            return {
                "state": "insufficient_ram", "name": m.name,
                "need_mb": m.min_ram_mb, "free_mb": round(free_ram),
            }

        script_path = SCRIPTS_DIR / m.download_script
        if not script_path.exists():
            return {"state": "no_script", "name": m.name}

        _download_status[key] = {"state": "downloading", "started_at": time.time()}
        asyncio.create_task(_run_download_bg(key, m))
        return {"state": "downloading", "elapsed_min": 0, "just_started": True, "name": m.name}