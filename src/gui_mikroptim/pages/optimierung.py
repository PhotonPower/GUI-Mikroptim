"""Seite „Optimierung“: Variablen und Optionen (G3-T1); Lauf und Ergebnis folgen (G3-T2, G3-T3)."""

from __future__ import annotations

import streamlit as st

from gui_mikroptim.views import common, file_picker, optimize_view, system_view

cfg = common.settings_or_stop()
st.title("Optimierung")
status = common.require_mikroptim()

entry = file_picker.pick_document(
    cfg,
    ("mikroptim.system",),
    key="optimierung",
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
        optimize_view.variables_section(system)
        st.markdown("**Optionen**")
        options = optimize_view.options_form(status)
        optimize_view.command_caption(entry, options)
        st.info(
            "Lauf mit Live-Verlauf und Speichern des Ergebnisses folgen mit G3-T2 und G3-T3 "
            "(docs/plan/meilensteine.md)."
        )
