"""Seite „Jobs und Synthese“: Protokolle, Jobs, neue Synthese, Ergebnisordner (G4)."""

import streamlit as st

from gui_mikroptim.views import (
    common,
    file_picker,
    folder_view,
    jobs_view,
    synth_form_view,
    synth_view,
)

cfg = common.settings_or_stop()
st.title("Jobs und Synthese")

tab_protocols, tab_jobs, tab_new, tab_folder = st.tabs(
    ["Protokolle", "Jobs", "Neue Synthese", "Ergebnisordner"]
)

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

with tab_new:
    synth_form_view.render(cfg)

with tab_folder:
    folder_view.render(cfg)
