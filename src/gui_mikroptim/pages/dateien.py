"""Seite „Dateien“: alles, was diese Sitzung gespeichert hat, herunterladen (G6-T2)."""

import streamlit as st

from gui_mikroptim.views import common, files_view

cfg = common.settings_or_stop()
st.title("Dateien")
files_view.render(cfg)
