"""Auswahl einer Datei aus festen Quellen (Arbeitsbereich, Mikroptim-Checkout).

Erste Fassung für den Protokollbrowser (G4-T2). Upload und die seitenübergreifende
Auswahl ``aktuell.datei`` kommen mit G1-T1.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from gui_mikroptim.backend import protocols
from gui_mikroptim.backend.files import FileEntry
from gui_mikroptim.config import Settings


@dataclass(frozen=True)
class Source:
    """Eine Wurzel, unter der gesucht wird."""

    label: str
    root: Path


def sources(cfg: Settings) -> list[Source]:
    """Quellen in fester Reihenfolge; fehlende Verzeichnisse werden ausgelassen."""
    result = [Source("Arbeitsbereich", cfg.workspace)]
    if cfg.mikroptim_repo is not None:
        for sub, label in (
            ("docs/ergebnisse", "Mikroptim: docs/ergebnisse"),
            ("data", "Mikroptim: data"),
        ):
            path = cfg.mikroptim_repo / sub
            if path.is_dir():
                result.append(Source(label, path))
    return [s for s in result if s.root.is_dir()]


@st.cache_data(show_spinner="Dateien werden gesucht …", ttl=30)
def _documents(root: str, names: tuple[str, ...]) -> list[FileEntry]:
    return protocols.list_documents(Path(root), names)


def pick_document(
    cfg: Settings, names: tuple[str, ...], key: str, empty_hint: str
) -> FileEntry | None:
    """Quelle und Datei wählen; zeigt nur Dateien der Formate ``names``."""
    available = sources(cfg)
    if not available:
        st.info(empty_hint)
        return None
    col_source, col_file = st.columns([1, 3])
    source = col_source.selectbox(
        "Quelle", available, format_func=lambda s: s.label, key=f"{key}.quelle"
    )
    entries = _documents(str(source.root), names)
    if not entries:
        col_file.info(f"Keine passenden Dateien unter {source.root}.")
        st.caption(empty_hint)
        return None
    entry = col_file.selectbox(
        f"Datei ({len(entries)})", entries, format_func=lambda e: e.label, key=f"{key}.datei"
    )
    if col_source.button("Liste neu laden", key=f"{key}.neu"):
        _documents.clear()
        st.rerun()
    return entry
