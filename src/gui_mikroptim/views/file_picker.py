"""Auswahl einer Datei aus festen Quellen, mit Upload (G4-T2, G1-T1).

Zwei Verwendungen:

- **Systeme** (Seite „System“): Quellen aus :func:`system_sources`, Upload nach ``uploads/``,
  Auswahl wird seitenübergreifend als aktuelle Datei gemerkt (``views.current``).
- **Protokolle** (Seite „Jobs und Synthese“): Quellen aus :func:`protocol_sources`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from gui_mikroptim.backend import protocols, uploads
from gui_mikroptim.backend.files import FileEntry
from gui_mikroptim.config import Settings
from gui_mikroptim.views import current


@dataclass(frozen=True)
class Source:
    """Eine Wurzel, unter der gesucht wird."""

    label: str
    root: Path


def system_sources(cfg: Settings) -> list[Source]:
    """Quellen für Systemdateien: Beispiele aus Mikroptim, Uploads, Ergebnisse, Jobordner."""
    result = []
    if cfg.example_systems_dir is not None:
        result.append(Source("Beispielsysteme (Mikroptim)", cfg.example_systems_dir))
    result.append(Source("Uploads", cfg.workspace / uploads.UPLOAD_SUBDIR))
    result.append(Source("Ergebnisse", cfg.workspace / "ergebnisse"))
    result.append(Source("Jobergebnisse", cfg.workspace / "jobs"))
    if cfg.mikroptim_repo is not None and (cfg.mikroptim_repo / "docs" / "ergebnisse").is_dir():
        result.append(
            Source("Mikroptim: docs/ergebnisse", cfg.mikroptim_repo / "docs" / "ergebnisse")
        )
    return result


def protocol_sources(cfg: Settings) -> list[Source]:
    """Quellen für Protokolle: Arbeitsbereich, Mikroptim ``docs/ergebnisse`` und ``data``."""
    result = [Source("Arbeitsbereich", cfg.workspace)]
    if cfg.mikroptim_repo is not None:
        for sub, label in (
            ("docs/ergebnisse", "Mikroptim: docs/ergebnisse"),
            ("data", "Mikroptim: data"),
        ):
            path = cfg.mikroptim_repo / sub
            if path.is_dir():
                result.append(Source(label, path))
    return result


# Rückwärtsverträglicher Name aus G4-T2
sources = protocol_sources


@st.cache_data(show_spinner="Dateien werden gesucht …", ttl=30)
def _documents(root: str, names: tuple[str, ...]) -> list[FileEntry]:
    return protocols.list_documents(Path(root), names)


def _source_index(available: list[Source], path: Path | None) -> int:
    if path is not None:
        for i, src in enumerate(available):
            try:
                path.resolve().relative_to(src.root.resolve())
                return i
            except ValueError:
                continue
    return 0


def _entry_index(entries: list[FileEntry], path: Path | None) -> int:
    if path is not None:
        resolved = path.resolve()
        for i, entry in enumerate(entries):
            if entry.path == resolved:
                return i
    return 0


def select_on_next_run(key: str, path: Path, remember: bool, message: str | None = None) -> None:
    """Wählt ``path`` beim nächsten Lauf aus (nach Upload oder neu gespeicherter Datei).

    Liest die Dateilisten neu und setzt die Zustände der Auswahl-Widgets zurück, damit die
    Vorauswahl greift. Der Aufrufer startet danach ``st.rerun()``.
    """
    _documents.clear()
    st.session_state.pop(f"{key}.quelle", None)
    for widget_key in [k for k in st.session_state if str(k).startswith(f"{key}.datei.")]:
        st.session_state.pop(widget_key, None)
    st.session_state[f"{key}.gewaehlt"] = str(path)
    if remember:
        current.set_path(path)
    if message:
        st.session_state[f"{key}.meldung"] = message


def _upload_box(cfg: Settings, names: tuple[str, ...], key: str, remember: bool) -> None:
    counter_key = f"{key}.upload_nr"
    counter = st.session_state.get(counter_key, 0)
    uploaded = st.file_uploader(
        "Datei hochladen",
        type=["json"],
        key=f"{key}.upload.{counter}",
        help=f"Wird unter {cfg.workspace / uploads.UPLOAD_SUBDIR} gespeichert, nie überschrieben.",
    )
    if uploaded is None:
        return
    try:
        result = uploads.save_upload(cfg.workspace, uploaded.name, uploaded.getvalue(), names)
    except uploads.UploadError as exc:
        st.error(f"Upload abgelehnt: {exc}")
        return
    st.session_state.pop(f"{key}.upload.{counter}", None)
    st.session_state[counter_key] = counter + 1
    select_on_next_run(
        key, result.path, remember, f"Gespeichert als {result.path.name} ({result.format})."
    )
    st.rerun()


def pick_document(
    cfg: Settings,
    names: tuple[str, ...],
    key: str,
    empty_hint: str,
    source_list: list[Source] | None = None,
    allow_upload: bool = False,
    remember: bool = False,
) -> FileEntry | None:
    """Quelle und Datei wählen; zeigt nur Dateien der Formate ``names``.

    Args:
        source_list: Quellen; Standard :func:`protocol_sources`.
        allow_upload: Upload nach ``uploads/`` anbieten (nur Formate ``names``).
        remember: Auswahl als aktuelle Datei merken und beim nächsten Besuch vorwählen.
    """
    available = [s for s in (source_list or protocol_sources(cfg)) if s.root.is_dir()]
    message = st.session_state.pop(f"{key}.meldung", None)
    if message:
        st.success(message)

    preferred_text = st.session_state.pop(f"{key}.gewaehlt", None)
    preferred = Path(preferred_text) if preferred_text else None
    if preferred is None and remember:
        preferred = current.get_path(cfg)

    col_source, col_file = st.columns([1, 3])
    entry = None
    if available:
        source = col_source.selectbox(
            "Quelle",
            available,
            index=_source_index(available, preferred),
            format_func=lambda s: s.label,
            key=f"{key}.quelle",
        )
        entries = _documents(str(source.root), names)
        if entries:
            entry = col_file.selectbox(
                f"Datei ({len(entries)})",
                entries,
                index=_entry_index(entries, preferred),
                format_func=lambda e: e.label,
                key=f"{key}.datei.{source.label}",
            )
        else:
            col_file.info(f"Keine passenden Dateien unter {source.root}.")
        if col_source.button("Liste neu laden", key=f"{key}.neu"):
            _documents.clear()
            st.rerun()
    else:
        st.info(empty_hint)

    if allow_upload:
        with st.expander("Datei hochladen", expanded=entry is None):
            _upload_box(cfg, names, key, remember)

    if entry is None:
        if available:
            st.caption(empty_hint)
        return None
    if remember:
        # Nur bei einer Änderung dieser Auswahl übernehmen: Sonst würde ein Wähler bei jedem
        # Lauf ein anderswo gesetztes aktuelles System (z. B. „Ergebnis übernehmen“) überschreiben.
        last_key = f"{key}.zuletzt"
        chosen = str(entry.path)
        if st.session_state.get(last_key) != chosen:
            st.session_state[last_key] = chosen
            current.set_path(entry.path)
    return entry
