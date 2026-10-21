"""Startseite: Status von Mikroptim, GPUs und Arbeitsbereich."""

from __future__ import annotations

import streamlit as st

from gui_mikroptim.backend import files
from gui_mikroptim.views import common

st.title("GUI-Mikroptim")
st.write(
    "Test- und Auswertecockpit für Mikroptim. Alle Zahlen kommen aus Mikroptim; "
    "die Oberfläche rechnet keine Optik."
)

cfg = common.settings_or_stop()
status = common.mikroptim_status()

st.subheader("Mikroptim")
if status.available:
    st.success(f"Mikroptim {status.version} geladen.")
    if status.has_cuda:
        if status.devices:
            rows = [
                {
                    "Index": d.get("index"),
                    "Name": d.get("name"),
                    "Speicher gesamt (GB)": round(d["total_bytes"] / 1e9, 1)
                    if "total_bytes" in d
                    else None,
                    "frei (GB)": round(d["free_bytes"] / 1e9, 1) if "free_bytes" in d else None,
                }
                for d in status.devices
            ]
            st.dataframe(rows, hide_index=True)
        else:
            st.info("CUDA-Build, aber kein nutzbares Gerät (ab sm_60) gefunden.")
    else:
        st.info("CPU-Build von Mikroptim: GPU-Schalter sind ausgeblendet.")
    if status.error:
        st.warning(status.error)
else:
    st.error("Mikroptim ist nicht nutzbar.")
    st.code(status.error or "unbekannter Fehler", language="text")
    st.markdown(
        "Mikroptim-Wheel im Mikroptim-Checkout bauen und in dieselbe Umgebung installieren:\n\n"
        "```bash\n"
        "cd ../Mikroptim && python -m pip wheel . -w dist --no-deps\n"
        "python -m pip install --no-index --find-links dist mikroptim\n"
        "```\n"
        "Mit CUDA: docs/betrieb.md, Abschnitt „Mikroptim mit CUDA“."
    )

if st.button("Neu prüfen", help="Mikroptim und GPUs erneut abfragen"):
    common.mikroptim_status.clear()
    st.rerun()

st.subheader("Verzeichnisse")
examples = cfg.example_systems_dir
st.dataframe(
    [
        {
            "Zweck": "Sitzungsordner (schreiben)"
            if cfg.sessions_root
            else "Arbeitsbereich (schreiben)",
            "Pfad": str(cfg.workspace),
        },
        {
            "Zweck": "Mikroptim-Checkout",
            "Pfad": str(cfg.mikroptim_repo) if cfg.mikroptim_repo else "– (MKO_GUI_MIKROPTIM_REPO)",
        },
        {"Zweck": "Beispielsysteme", "Pfad": str(examples) if examples else "–"},
        {
            "Zweck": "CLI für Jobs",
            "Pfad": str(cfg.cli) if cfg.cli else "python -m mikroptim (MKO_GUI_CLI nicht gesetzt)",
        },
    ],
    hide_index=True,
)
if cfg.sessions_root is not None:
    st.info(
        "Diese Sitzung hat einen eigenen Ordner für Uploads, Ergebnisse, Jobs und Glaskataloge. "
        "Die Adresse im Browser (mit `?sitzung=…`) führt zu ihm zurück – als Lesezeichen "
        f"speichern. Ordner ohne Zugriff und ohne laufenden Job werden nach {cfg.session_days:g} "
        "Tagen gelöscht; wichtige Ergebnisse auf der Seite „Dateien“ herunterladen."
    )
if cfg.mikroptim_repo and not examples:
    st.warning(f"Unter {cfg.mikroptim_repo} gibt es kein Verzeichnis data/systems.")

n_examples = len(files.list_files(examples)) if examples else 0
n_uploads = len(files.list_files(cfg.workspace / "uploads"))
n_results = len(files.list_files(cfg.workspace / "ergebnisse"))
c1, c2, c3 = st.columns(3)
c1.metric("Beispielsysteme", n_examples)
c2.metric("Uploads", n_uploads)
c3.metric("Ergebnisse", n_results)
