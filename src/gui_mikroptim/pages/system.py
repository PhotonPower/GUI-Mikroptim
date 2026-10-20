"""Seite „System“: Systemdatei wählen oder hochladen (G1-T1); Tabellen folgen (G1-T2, G1-T3)."""

from __future__ import annotations

import datetime as dt

import streamlit as st

from gui_mikroptim.backend import protocols
from gui_mikroptim.views import common, file_picker

cfg = common.settings_or_stop()
st.title("System")

entry = file_picker.pick_document(
    cfg,
    ("mikroptim.system",),
    key="system",
    empty_hint=(
        "Systemdateien (mikroptim.system/1) hochladen oder MKO_GUI_MIKROPTIM_REPO setzen, "
        "um die Beispielsysteme von Mikroptim zu sehen."
    ),
    source_list=file_picker.system_sources(cfg),
    allow_upload=True,
    remember=True,
)

if entry is not None:
    try:
        fmt, doc = protocols.load_document(entry.path)
    except protocols.ProtocolError as exc:
        st.error(str(exc))
        st.stop()

    st.subheader(doc.get("name") or entry.path.stem)
    if doc.get("description"):
        st.write(doc["description"])
    spectrum = doc.get("spectrum") or {}
    source = doc.get("source") or {}
    c1, c2, c3 = st.columns(3)
    c1.metric("Flächen", len(doc.get("surfaces") or []))
    c2.metric("Wellenlängen", len(spectrum.get("wavelengths_nm") or []))
    c3.metric("Felder", len(source.get("field_angles_deg") or []))
    modified = dt.datetime.fromtimestamp(entry.mtime).strftime("%Y-%m-%d %H:%M")
    st.caption(
        f"{entry.path} · {fmt} · {entry.size / 1024:.1f} KiB · geändert {modified} · "
        f"Glaskataloge: {', '.join(doc.get('glass_catalogs') or []) or '–'}"
    )

st.divider()
st.markdown(
    "**Als Nächstes** (docs/plan/meilensteine.md):\n"
    "- `G1-T2` Flächentabelle, Spektrum, Felder, Variablen, Nebenbedingungen, Paraxialdaten "
    "(gerechnet von Mikroptim)\n"
    "- `G1-T3` Linsenschnitt in der y-z-Ebene"
)
