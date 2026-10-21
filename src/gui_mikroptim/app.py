"""Einstieg der Streamlit-App: Seitenkonfiguration, Seitenleiste, Navigation.

Start: ``gui-mikroptim`` oder ``streamlit run src/gui_mikroptim/app.py --server.address 127.0.0.1``.
"""

from __future__ import annotations

import streamlit as st

from gui_mikroptim import __version__
from gui_mikroptim.views import common

st.set_page_config(page_title="GUI-Mikroptim", page_icon="🔬", layout="wide")

PAGES = [
    st.Page("pages/start.py", title="Start", icon=":material/home:", default=True),
    st.Page("pages/system.py", title="System", icon=":material/lens:"),
    st.Page("pages/auswertung.py", title="Auswertung", icon=":material/insights:"),
    st.Page("pages/optimierung.py", title="Optimierung", icon=":material/tune:"),
    st.Page("pages/synthese.py", title="Jobs und Synthese", icon=":material/account_tree:"),
    st.Page("pages/dateien.py", title="Dateien", icon=":material/download:"),
]

navigation = st.navigation(PAGES)
current_line = common.sidebar(__version__)
try:
    navigation.run()
finally:
    # auch nach st.stop() einer Seite: aktuelle Auswahl anzeigen
    common.sidebar_current(current_line)
