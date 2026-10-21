"""Sitzungsordner (G6-T1): jede Sitzung arbeitet in ``<MKO_GUI_SESSIONS>/<kennung>/``.

Darin liegen ``uploads/``, ``ergebnisse/``, ``jobs/`` und ``kataloge/`` – alles, was die GUI
für diese Sitzung schreibt. Die Kennung ist zufällig und nicht erratbar (``secrets``); sie steht
in der Adresse (``?sitzung=…``), damit Neuladen den Ordner behält. Alte Ordner ohne laufenden
Job werden nach ``session_days`` gelöscht. Ohne Streamlit.
"""

from __future__ import annotations

import contextlib
import re
import secrets
import shutil
import time
from pathlib import Path

from gui_mikroptim.config import WORKSPACE_SUBDIRS

ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
SEEN_MARKER = ".zuletzt"
CLEANUP_MARKER = ".aufgeraeumt"
#: höchstens so oft wird aufgeräumt bzw. der Zugriff vermerkt
CLEANUP_INTERVAL_S = 3600.0
TOUCH_INTERVAL_S = 60.0


class SessionError(ValueError):
    """Ungültige Sitzungskennung."""


def new_id() -> str:
    return secrets.token_urlsafe(16)


def valid_id(value: str | None) -> bool:
    return bool(value) and bool(ID_PATTERN.match(str(value)))


def session_dir(root: Path, session_id: str) -> Path:
    """Ordner der Sitzung (angelegt, mit Unterordnern); Zugriff wird vermerkt."""
    if not valid_id(session_id):
        raise SessionError(f"ungültige Sitzungskennung: {session_id!r}")
    folder = root.resolve() / session_id
    for name in WORKSPACE_SUBDIRS:
        (folder / name).mkdir(parents=True, exist_ok=True)
    marker = folder / SEEN_MARKER
    if not marker.exists() or time.time() - marker.stat().st_mtime > TOUCH_INTERVAL_S:
        marker.touch()
    return folder


def last_seen(folder: Path) -> float:
    marker = folder / SEEN_MARKER
    return marker.stat().st_mtime if marker.exists() else folder.stat().st_mtime


def _has_active_job(folder: Path) -> bool:
    from gui_mikroptim.backend import jobs

    jobs_dir = folder / "jobs"
    if not jobs_dir.is_dir():
        return False
    for job_dir in jobs_dir.iterdir():
        if (job_dir / jobs.JOB_FILE).is_file():
            with contextlib.suppress(jobs.JobError):
                if not jobs.load(job_dir).final:
                    return True
    return False


def cleanup(
    root: Path, max_age_days: float, keep: str | None = None, force: bool = False
) -> list[str]:
    """Löscht Sitzungsordner, die länger als ``max_age_days`` nicht benutzt wurden.

    Ordner mit wartenden oder laufenden Jobs und die Sitzung ``keep`` bleiben. Ohne ``force``
    höchstens einmal pro :data:`CLEANUP_INTERVAL_S`. Gibt die gelöschten Kennungen zurück.
    """
    root = root.resolve()
    if not root.is_dir():
        return []
    marker = root / CLEANUP_MARKER
    if not force and marker.exists() and time.time() - marker.stat().st_mtime < CLEANUP_INTERVAL_S:
        return []
    marker.touch()
    cutoff = time.time() - max_age_days * 86400.0
    removed = []
    for folder in root.iterdir():
        if not folder.is_dir() or not valid_id(folder.name) or folder.name == keep:
            continue
        if last_seen(folder) >= cutoff or _has_active_job(folder):
            continue
        shutil.rmtree(folder, ignore_errors=True)
        removed.append(folder.name)
    return removed


def all_sessions(root: Path) -> list[Path]:
    """Alle Sitzungsordner (für die gemeinsame Warteschlange der Jobs)."""
    root = root.resolve()
    if not root.is_dir():
        return []
    return sorted(f for f in root.iterdir() if f.is_dir() and valid_id(f.name))
