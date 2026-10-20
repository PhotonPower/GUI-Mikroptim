"""Seite „Auswertung“: Wellenfront (G2-T1), OPD und Spots (G2-T2), PSF und MTF (G2-T3)."""

from __future__ import annotations

import streamlit as st

from gui_mikroptim.views import (
    common,
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
        tab_trace, tab_eval, tab_psf = st.tabs(
            ["Wellenfront (trace)", "OPD und Spots (eval)", "PSF und MTF"]
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

st.divider()
st.caption("Als Nächstes (docs/plan/meilensteine.md): `G2-T4` Vergleich zweier Systeme.")
