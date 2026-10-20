"""Seite „Auswertung“: RMS-Wellenfront (G2-T1); OPD, Spots, PSF folgen (G2-T2 bis G2-T4)."""

from __future__ import annotations

import streamlit as st

from gui_mikroptim.views import common, file_picker, system_view, wavefront_view

cfg = common.settings_or_stop()
st.title("Auswertung")
status = common.require_mikroptim()

entry = file_picker.pick_document(
    cfg,
    ("mikroptim.system",),
    key="auswertung",
    empty_hint="Systemdatei auf der Seite „System“ wählen oder hochladen.",
    source_list=file_picker.system_sources(cfg),
    remember=True,
)
if entry is not None:
    system, error = system_view.load(entry)
    if error is not None:
        system_view.show_load_error(error)
        st.caption("Details und Reparatur auf der Seite „System“.")
    else:
        st.subheader(system.name or entry.path.stem)
        options = wavefront_view.options_form(status)
        wavefront_view.render(entry, system, options)

st.divider()
st.caption(
    "Als Nächstes (docs/plan/meilensteine.md): `G2-T2` OPD-Karten und Spots, `G2-T3` PSF, MTF "
    "und Strehl, `G2-T4` Vergleich zweier Systeme."
)
