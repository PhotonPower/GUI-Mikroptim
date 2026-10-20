"""Seite „Jobs und Synthese“: Protokolle von synth (G4-T2), Jobs (G4-T1)."""

import streamlit as st

from gui_mikroptim.views import common, file_picker, jobs_view, synth_view

cfg = common.settings_or_stop()
st.title("Jobs und Synthese")

tab_protocols, tab_jobs = st.tabs(["Protokolle", "Jobs"])

with tab_protocols:
    entry = file_picker.pick_document(
        cfg,
        ("mikroptim.synth",),
        key="synthese.protokoll",
        allow_upload=True,
        empty_hint=(
            "Protokolle entstehen mit `mikroptim synth … --log datei.json`. Sie werden im "
            "Arbeitsbereich und, mit MKO_GUI_MIKROPTIM_REPO, unter docs/ergebnisse und data "
            "von Mikroptim gesucht."
        ),
    )
    if entry is not None:
        synth_view.render(entry.path, key="synthese")

with tab_jobs:
    jobs_view.render(cfg)
    st.caption(
        "Als Nächstes (docs/plan/meilensteine.md): `G4-T3` Synthese-Job mit Formular, "
        "`G4-T4` Ergebnisordner von Läufen."
    )
