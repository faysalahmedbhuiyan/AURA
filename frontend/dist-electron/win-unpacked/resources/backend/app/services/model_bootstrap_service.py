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
from dataclasses import dataclass
from pathlib import Path

import psutil

from app.config import get_settings

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]  # .../backend
SCRIPTS_DIR = BACKEND_DIR / "scripts"


@dataclass
class RequiredModel:
    name: str                      # human-readable label for logs
    path: Path                     # resolved absolute path the app expects
    is_dir: bool                   # True = folder (ONNX export), False = single file
    download_script: str | None    # filename in scripts/, or None if not auto-fetchable
    min_disk_gb: float             # free disk space needed to attempt download
    min_ram_mb: int                # free RAM needed to attempt download/export
    required: bool                 # False = optional add-on, warn only, never blocks startup


def _resolve(rel_or_abs: str) -> Path:
    """Settings paths are relative to backend/ (matches config.py convention)."""
    p = Path(rel_or_abs)
    return p if p.is_absolute() else (BACKEND_DIR / p).resolve()


def _required_models() -> list[RequiredModel]:
    settings = get_settings()
    return [
        RequiredModel(
            name="SD-Turbo (fast image generation)",
            path=_resolve(settings.image_model_path),
            is_dir=True,
            download_script="download_model.py",
            min_disk_gb=5.0,
            min_ram_mb=3000,
            required=True,
        ),
        RequiredModel(
            name="Piper voice (AURA's own voice)",
            path=_resolve(settings.piper_model_path),
            is_dir=False,
            download_script=None,  # ships in the repo's models/ folder
            min_disk_gb=0.2,
            min_ram_mb=200,
            required=True,
        ),
        RequiredModel(
            name="Realistic Vision (high-quality image generation)",
            path=_resolve(settings.image_realistic_model_path),
            is_dir=True,
            download_script="download_realistic_model.py",
            min_disk_gb=8.0,
            min_ram_mb=4000,
            required=False,  # heavy optional add-on — don't force it on an 8GB machine
        ),
        RequiredModel(
            name="Piper female voice (video dialogue)",
            path=_resolve(settings.piper_model_path_female),
            is_dir=False,
            download_script="download_female_voice.py",
            min_disk_gb=0.2,
            min_ram_mb=200,
            required=False,
        ),
    ]


def _free_disk_gb(path: Path) -> float:
    check_dir = path.parent if not path.is_dir() else path
    while not check_dir.exists():
        check_dir = check_dir.parent
    _, _, free = shutil.disk_usage(check_dir)
    return free / (1024 ** 3)


def _free_ram_mb() -> float:
    return psutil.virtual_memory().available / (1024 * 1024)


def check_and_prepare_models() -> dict:
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
            report["skipped_ram"].append(m.name)
            logger.error(
                "[model-check] SKIPPED '%s' — needs ~%dMB free RAM to download/export, "
                "only %.0fMB available right now. Close other apps and restart "
                "AURA to retry.",
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