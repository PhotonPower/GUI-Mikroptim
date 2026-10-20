"""Reiter „Ergebnisordner“: einen Lauf als Ganzes durchsehen (G4-T4)."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from gui_mikroptim.backend import result_folder as rf
from gui_mikroptim.config import Settings
from gui_mikroptim.views import current, file_picker, synth_view

KEY = "ordner"
TEXT_LIMIT = 200_000


@st.cache_data(show_spinner="Ordner wird gelesen …", ttl=30)
def _scan(folder: str) -> rf.Inventory:
    return rf.scan(Path(folder))


@st.cache_data(show_spinner=False, ttl=30)
def _rows(kind: str, paths: tuple[str, ...], folder: str) -> list[dict]:
    inventory = _scan(folder)
    chosen = [f for f in inventory.files if str(f.path) in paths]
    make = {rf.SYSTEM: rf.system_row, rf.SYNTH: rf.synth_row, rf.EVAL: rf.eval_row}[kind]
    return [make(f) for f in chosen]


def folder_choices(cfg: Settings) -> list[tuple[str, Path]]:
    """(Beschriftung, Ordner): Mikroptim ``docs/ergebnisse``, Jobordner, ``ergebnisse/``."""
    choices: list[tuple[str, Path]] = []
    if cfg.mikroptim_repo is not None:
        base = cfg.mikroptim_repo / "docs" / "ergebnisse"
        for folder in rf.candidate_folders(base):
            choices.append((f"Mikroptim: {folder.relative_to(base).as_posix()}", folder))
    jobs_dir = cfg.workspace / "jobs"
    if jobs_dir.is_dir():
        for folder in sorted(jobs_dir.iterdir(), reverse=True):
            if folder.is_dir() and not folder.name.startswith("."):
                choices.append((f"Job: {folder.name}", folder))
    results = cfg.workspace / "ergebnisse"
    if results.is_dir() and any(results.glob("*.json")):
        choices.append(("Arbeitsbereich: ergebnisse", results))
    return choices


def _go(page: str) -> None:
    st.switch_page(page)


def _systems(inventory: rf.Inventory, folder: str) -> None:
    systems = inventory.of(rf.SYSTEM)
    if not systems:
        return
    st.markdown(f"**Systeme** ({len(systems)})")
    st.dataframe(
        _rows(rf.SYSTEM, tuple(str(f.path) for f in systems), folder),
        hide_index=True,
        width="stretch",
    )
    labels = [f.relative for f in systems]
    chosen = st.selectbox("System", labels, key=f"{KEY}.system")
    path = systems[labels.index(chosen)].path
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("Als aktuelles System", key=f"{KEY}.aktuell"):
        current.set_path(path)
        st.toast(f"Aktuelles System: {chosen}")
    if c2.button("Auf „System“ ansehen", key=f"{KEY}.ansehen"):
        current.set_path(path)
        _go("pages/system.py")
    if c3.button("Auswerten", key=f"{KEY}.auswerten"):
        current.set_path(path)
        _go("pages/auswertung.py")
    if c4.button(
        "Mit aktuellem System vergleichen",
        key=f"{KEY}.vergleichen",
        help="Öffnet „Auswertung“ mit diesem System als B im Reiter „Vergleich“; A bleibt das "
        "aktuelle System.",
    ):
        file_picker.select_on_next_run("auswertung.vergleich", path, remember=False)
        _go("pages/auswertung.py")


def _protocols(inventory: rf.Inventory, folder: str) -> None:
    protocols = inventory.of(rf.SYNTH)
    if not protocols:
        return
    st.markdown(f"**Synthese-Protokolle** ({len(protocols)})")
    st.dataframe(
        _rows(rf.SYNTH, tuple(str(f.path) for f in protocols), folder),
        hide_index=True,
        width="stretch",
    )
    labels = [f.relative for f in protocols]
    chosen = st.selectbox("Protokoll", labels, key=f"{KEY}.protokoll")
    with st.expander(f"Protokoll {chosen}", expanded=False):
        synth_view.render(protocols[labels.index(chosen)].path, key=f"{KEY}.synth")


def _evaluations(inventory: rf.Inventory, folder: str) -> None:
    evaluations = inventory.of(rf.EVAL)
    if not evaluations:
        return
    st.markdown(f"**Auswertungen** ({len(evaluations)}, `mikroptim eval --json`)")
    st.dataframe(
        _rows(rf.EVAL, tuple(str(f.path) for f in evaluations), folder),
        hide_index=True,
        width="stretch",
    )


def _other(inventory: rf.Inventory) -> None:
    rest = [f for f in inventory.files if f.kind in (rf.TEXT, rf.JSON, rf.DOT, rf.OTHER_DOC)]
    if not rest:
        return
    st.markdown(f"**Weitere Dateien** ({len(rest)}: Textausgaben, Laufdateien, Stammbäume)")
    labels = [f"{f.relative} ({f.kind})" for f in rest]
    chosen = st.selectbox("Datei", labels, key=f"{KEY}.weitere")
    f = rest[labels.index(chosen)]
    text = f.path.read_text(encoding="utf-8", errors="replace")[:TEXT_LIMIT]
    if f.kind in (rf.JSON, rf.OTHER_DOC):
        try:
            st.json(json.loads(text), expanded=1)
        except json.JSONDecodeError:
            st.code(text, language="json")
    elif f.kind == rf.DOT:
        st.graphviz_chart(text, width="stretch")
    else:
        st.code(text, language="text")
    if f.size > TEXT_LIMIT:
        st.caption(f"Gekürzt auf {TEXT_LIMIT // 1000} kB von {f.size // 1000} kB.")


def render(cfg: Settings) -> None:
    choices = folder_choices(cfg)
    if not choices:
        st.info(
            "Keine Ergebnisordner gefunden. Gesucht wird unter docs/ergebnisse im Mikroptim-"
            "Checkout (MKO_GUI_MIKROPTIM_REPO), in den Jobordnern und unter ergebnisse/."
        )
        return
    labels = [label for label, _ in choices]
    c1, c2 = st.columns([3, 1])
    label = c1.selectbox("Ordner", labels, key=f"{KEY}.auswahl")
    if c2.button("Neu einlesen", key=f"{KEY}.neu"):
        _scan.clear()
        _rows.clear()
    folder = dict(choices)[label]
    inventory = _scan(str(folder))

    counts = inventory.counts()
    cols = st.columns(5)
    for col, kind in zip(cols, (rf.SYSTEM, rf.SYNTH, rf.EVAL, rf.TEXT, rf.JSON), strict=True):
        col.metric(kind if kind != rf.JSON else "JSON ohne Format", counts.get(kind, 0))
    st.caption(f"`{inventory.folder}`")

    report = rf.find_report(inventory.folder)
    if report is not None:
        with st.expander(f"Bericht: {report.name}", expanded=False):
            st.markdown(report.read_text(encoding="utf-8", errors="replace")[:TEXT_LIMIT])

    st.markdown("**Stufen** (Kürzel am Anfang der Dateinamen)")
    st.dataframe(rf.stage_rows(inventory), hide_index=True, width="stretch")
    _systems(inventory, str(folder))
    _protocols(inventory, str(folder))
    _evaluations(inventory, str(folder))
    _other(inventory)
