"""Seite „Jobs und Synthese“: Protokolle von synth (G4-T2), Jobs folgen (G4-T1, G4-T3)."""

import streamlit as st

from gui_mikroptim.views import common, file_picker, synth_view

cfg = common.settings_or_stop()
st.title("Jobs und Synthese")

tab_protocols, tab_jobs = st.tabs(["Protokolle", "Jobs"])

with tab_protocols:
    entry = file_picker.pick_document(
        cfg,
        ("mikroptim.synth",),
        key="synthese.protokoll",
        empty_hint=(
            "Protokolle entstehen mit `mikroptim synth … --log datei.json`. Sie werden im "
            "Arbeitsbereich und, mit MKO_GUI_MIKROPTIM_REPO, unter docs/ergebnisse und data "
            "von Mikroptim gesucht."
        ),
    )
    if entry is not None:
        synth_view.render(entry.path, key="synthese")

with tab_jobs:
    st.info("Hier laufen Synthese und andere lange Rechnungen als eigene Prozesse (ADR-0003).")
    st.markdown(
        "**Geplante Aufgaben** (docs/plan/meilensteine.md):\n"
        "- `G4-T1` Jobverwaltung: starten, Status, Ausgabe, abbrechen\n"
        "- `G4-T3` Synthese-Job mit Formular für mikroptim synth\n"
        "- `G4-T4` Ergebnisordner von Läufen durchsehen"
    )
