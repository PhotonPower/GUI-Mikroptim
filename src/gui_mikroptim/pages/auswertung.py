"""Seite „Auswertung“: Wellenfront, OPD und Spots, PSF und MTF, Vergleich (G2-T1 bis G2-T4)."""

from __future__ import annotations

import streamlit as st

from gui_mikroptim.views import (
    common,
    compare_view,
    eval_view,
    file_picker,
    psf_view,
    system_view,
    wavefront_view,
)

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
        tab_trace, tab_eval, tab_psf, tab_compare = st.tabs(
            ["Wellenfront (trace)", "OPD und Spots (eval)", "PSF und MTF", "Vergleich"]
        )
        with tab_trace:
            options = wavefront_view.options_form(status)
            wavefront_view.render(entry, system, options)
        with tab_eval:
            eval_options = eval_view.options_form(status)
            eval_view.render(entry, system, eval_options)
        with tab_psf:
            st.caption(
                "Raster, Referenzsphäre und GPU wie im Reiter „OPD und Spots“ "
                f"(Raster {eval_options.grid})."
            )
            psf_options, vector_options = psf_view.options_form(status, eval_options)
            psf_view.render(entry, system, eval_options, psf_options, vector_options)
        with tab_compare:
            compare_view.render(cfg, entry, system, options)
