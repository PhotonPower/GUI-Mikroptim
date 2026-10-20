"""Seitenübergreifend gewählte Systemdatei (``st.session_state["aktuell.datei"]``).

Gespeichert wird ein absoluter Pfad als Text, nicht der Zustand eines Widgets: Streamlit
löscht Widget-Zustände von Seiten, die gerade nicht angezeigt werden.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from gui_mikroptim.backend.files import PathError, resolve_inside
from gui_mikroptim.config import Settings

KEY = "aktuell.datei"


def _inside_any(path: Path, roots: list[Path]) -> bool:
    for root in roots:
        try:
            resolve_inside(root, path.resolve().relative_to(root.resolve()))
            return True
        except (ValueError, PathError):
            continue
    return False


def get_path(cfg: Settings) -> Path | None:
    """Die aktuelle Datei, falls sie noch existiert und unter einer erlaubten Wurzel liegt."""
    value = st.session_state.get(KEY)
    if not value:
        return None
    path = Path(value)
    if not path.is_file() or not _inside_any(path, cfg.read_roots):
        st.session_state.pop(KEY, None)
        return None
    return path


def set_path(path: Path) -> None:
    st.session_state[KEY] = str(path.resolve())


def clear_path() -> None:
    st.session_state.pop(KEY, None)
