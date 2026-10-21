"""Seite „Dateien“: Dateien der Sitzung ansehen und herunterladen (G6-T2)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import streamlit as st

from gui_mikroptim.backend import export
from gui_mikroptim.config import Settings

KEY = "dateien"
FOLDERS = {
    "uploads": "Uploads",
    "ergebnisse": "Ergebnisse",
    "jobs": "Jobs",
    "kataloge": "Glaskataloge",
}


def session_files(workspace: Path) -> list[dict]:
    """Alle Dateien der Sitzung (ohne versteckte), sortiert nach Ordner und Pfad."""
    root = workspace.resolve()
    rows = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part.startswith(".") for part in rel.parts) or not path.is_file():
            continue
        stat = path.stat()
        rows.append(
            {
                "Ordner": FOLDERS.get(rel.parts[0], rel.parts[0]) if len(rel.parts) > 1 else "–",
                "Datei": rel.as_posix(),
                "Größe [kB]": round(stat.st_size / 1024, 1),
                "geändert": dt.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "_bytes": stat.st_size,
            }
        )
    return rows


def zip_button(base: Path, relative: list[str], name: str, key: str, label: str) -> None:
    """Zweistufig: „ZIP erstellen“, dann „herunterladen“ (das ZIP entsteht nur auf Wunsch)."""
    store = f"{key}.zip"
    if st.button(label, key=f"{key}.erstellen", disabled=not relative):
        st.session_state[store] = (tuple(relative), export.zip_files(base, relative))
    prepared = st.session_state.get(store)
    if prepared and list(prepared[0]) == list(relative):
        st.download_button(
            f"{name}.zip herunterladen ({len(prepared[1]) / 1e6:.1f} MB)",
            prepared[1],
            file_name=f"{name}.zip",
            mime="application/zip",
            key=f"{key}.herunterladen",
            type="primary",
        )


def render(cfg: Settings) -> None:
    rows = session_files(cfg.workspace)
    if cfg.sessions_root is not None:
        st.caption(
            f"Sitzungsordner `{cfg.workspace}`. Ordner ohne Zugriff werden nach "
            f"{cfg.session_days:g} Tagen gelöscht – wichtige Ergebnisse hier herunterladen."
        )
    if not rows:
        st.info("Diese Sitzung hat noch keine Dateien (Uploads, Ergebnisse, Jobs, Glaskataloge).")
        return
    total = sum(r["_bytes"] for r in rows)
    c1, c2 = st.columns(2)
    c1.metric("Dateien", len(rows))
    c2.metric("Größe", f"{total / 1e6:.2f} MB")
    st.dataframe([{k: v for k, v in r.items() if k != "_bytes"} for r in rows],
                 hide_index=True, width="stretch")  # fmt: skip

    st.markdown("**Auswahl herunterladen**")
    folders = sorted({r["Ordner"] for r in rows})
    chosen_folders = st.multiselect("Ordner", folders, default=folders, key=f"{KEY}.ordner")
    candidates = [r["Datei"] for r in rows if r["Ordner"] in chosen_folders]
    chosen = st.multiselect(
        "Dateien (leer: alle der gewählten Ordner)", candidates, key=f"{KEY}.auswahl"
    )
    selection = chosen or candidates
    size = sum(r["_bytes"] for r in rows if r["Datei"] in selection)
    st.caption(f"{len(selection)} Dateien, {size / 1e6:.2f} MB")
    if size > export.LARGE_ZIP_BYTES:
        st.warning("Großes Archiv: das Erstellen kann dauern.")
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M")
    zip_button(cfg.workspace, selection, f"gui-mikroptim-{stamp}", KEY, "ZIP erstellen")

    st.markdown("**Einzelne Datei**")
    single = st.selectbox("Datei", [r["Datei"] for r in rows], key=f"{KEY}.einzeln")
    path = (cfg.workspace / single).resolve()
    if cfg.workspace.resolve() in path.parents and path.is_file():
        st.download_button(
            f"{Path(single).name} herunterladen",
            path.read_bytes(),
            file_name=Path(single).name,
            key=f"{KEY}.einzeln.knopf",
        )
