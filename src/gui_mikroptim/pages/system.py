"""Seite „System“: Datei wählen oder hochladen (G1-T1), Tabellen und Paraxialdaten (G1-T2)."""

from __future__ import annotations

import streamlit as st

from gui_mikroptim.views import catalog_view, common, file_picker, system_view

cfg = common.settings_or_stop()
st.title("System")

entry = file_picker.pick_document(
    cfg,
    ("mikroptim.system",),
    key=system_view.PICKER_KEY,
    empty_hint=(
        "Systemdateien (mikroptim.system/1) hochladen oder MKO_GUI_MIKROPTIM_REPO setzen, "
        "um die Beispielsysteme von Mikroptim zu sehen."
    ),
    source_list=file_picker.system_sources(cfg),
    allow_upload=True,
    remember=True,
)
catalog_view.section(cfg)

if entry is not None:
    status = common.mikroptim_status()
    if not status.available:
        doc = system_view.file_header(entry)
        if doc is not None:
            system_view.lens_section(doc)
        st.warning(
            "Für Flächentabelle, Brechzahlen und Paraxialdaten wird Mikroptim benötigt "
            "(Details auf der Startseite). Der Linsenschnitt oben ist ungeprüft aus der Datei "
            "gezeichnet."
        )
    else:
        system = system_view.load_or_report(cfg, entry)
        if system is not None:
            system_view.details(system)
