"""Glaskataloge hochladen, ansehen und löschen (ADR-0006)."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from gui_mikroptim.backend import catalogs, compute
from gui_mikroptim.config import Settings
from gui_mikroptim.views import common

KEY = "kataloge"


def _mikroptim_catalogs(cfg: Settings) -> list[Path]:
    if cfg.mikroptim_repo is None:
        return []
    return sorted((cfg.mikroptim_repo / "data" / "glass").glob("*.json"))


def _upload(cfg: Settings) -> None:
    counter = st.session_state.get(f"{KEY}.upload_nr", 0)
    uploaded = st.file_uploader(
        "Glaskatalog hochladen (mikroptim.glass/1)",
        type=["json"],
        key=f"{KEY}.upload.{counter}",
        help=(
            "Wird unter kataloge/ im Arbeitsbereich gespeichert. Systemdateien finden ihn über "
            "den Dateinamen, z. B. data/glass/private/schott.json → kataloge/schott.json."
        ),
    )
    if uploaded is None:
        return
    try:
        info = catalogs.save_catalog(cfg.workspace, uploaded.name, uploaded.getvalue())
    except catalogs.CatalogError as exc:
        st.error(f"Katalog abgelehnt: {exc}")
        return
    status = common.mikroptim_status()
    if status.available:
        try:
            compute.validate_catalog_with_mikroptim(info.path)
        except Exception as exc:  # von Mikroptim abgelehnt: Datei wieder entfernen
            info.path.unlink(missing_ok=True)
            error = compute.load_error(exc)
            st.error(f"Mikroptim lehnt den Katalog ab: {error.kind}: {error.message}")
            return
    st.session_state[f"{KEY}.upload_nr"] = counter + 1
    clashes = sorted(set(info.names) & set(catalogs.glass_names_in(_mikroptim_catalogs(cfg))))
    note = f"{info.path.name} gespeichert ({len(info.names)} Gläser)."
    if clashes:
        note += (
            f" Achtung: {', '.join(clashes)} steht auch in den Katalogen von Mikroptim; ein "
            "System, das beide nennt, lädt Mikroptim nicht (Gläser dürfen nicht doppelt "
            "vorkommen)."
        )
    st.session_state[f"{KEY}.meldung"] = note
    st.rerun()


def section(cfg: Settings) -> None:
    """Aufklappbarer Bereich auf der Seite „System“."""
    infos = catalogs.list_catalogs(cfg.workspace)
    message = st.session_state.pop(f"{KEY}.meldung", None)
    with st.expander(f"Glaskataloge ({len(infos)} hochgeladen)", expanded=bool(message)):
        if message:
            st.success(message)
        st.caption(
            "Eigene Glaskataloge, z. B. Herstellerdaten, die nicht ins Mikroptim-Repository "
            "dürfen. Format mikroptim.glass/1 (Mikroptim docs/dateiformat.md, „Glasdaten“). "
            "Systemdateien finden sie über den Dateinamen; fehlt ein Katalog beim Laden, "
            "ordnet „Glaskataloge zuordnen und neu speichern“ ihn zu."
        )
        if infos:
            st.dataframe(
                [
                    {"Datei": i.path.name, "Gläser": len(i.names), "Namen": ", ".join(i.names)}
                    for i in infos
                ],
                hide_index=True,
                width="stretch",
            )
        _upload(cfg)
        if infos:
            c1, c2, c3 = st.columns([2, 2, 1])
            name = c1.selectbox(
                "Katalog löschen", [i.path.name for i in infos], key=f"{KEY}.loeschen"
            )
            sure = c2.checkbox("wirklich löschen", key=f"{KEY}.sicher")
            if c3.button("Löschen", key=f"{KEY}.loeschen_knopf", disabled=not sure):
                catalogs.delete_catalog(cfg.workspace, name)
                st.session_state[f"{KEY}.meldung"] = f"{name} gelöscht."
                st.session_state.pop(f"{KEY}.sicher", None)
                st.rerun()
