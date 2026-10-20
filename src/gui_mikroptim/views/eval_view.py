"""EVAL auf der Seite „Auswertung“: Kennzahlen, OPD-Karte, Spotdiagramm (G2-T2)."""

from __future__ import annotations

from typing import Any

import numpy as np
import streamlit as st

from gui_mikroptim.backend import compute, mko, system_tables
from gui_mikroptim.backend.files import FileEntry
from gui_mikroptim.views import system_view
from gui_mikroptim.views.eval_plots import opd_figure, spot_figure
from gui_mikroptim.views.wavefront_plots import field_labels, wavelength_labels
from gui_mikroptim.views.wavefront_view import gpu_inputs

KEY = "auswertung.eval"
REMOVAL_LABELS = {
    "piston": "Kolben",
    "tilt": "Kolben und Kippung",
    "defocus": "Kolben, Kippung, Defokus",
}
REFERENCE_LABELS = {"exit-pupil": "Austrittspupille", "vertex": "Scheitel der letzten Fläche"}
#: ab diesem Raster weist die Seite auf längere Rechenzeiten hin
LARGE_GRID = 512


@st.cache_resource(show_spinner="EVAL wird gerechnet …", max_entries=8)
def cached_evaluation(path: str, mtime: float, size: int, options: compute.EvalOptions) -> Any:
    """``Evaluation`` pro Datei, Stand und Optionen (nanobind-Objekt, daher Ressourcen-Cache)."""
    return compute.evaluate(system_view.cached_system(path, mtime, size), options)


def options_form(status: mko.MikroptimStatus) -> compute.EvalOptions:
    c1, c2, c3, c4, c5 = st.columns([1, 1, 2, 1, 2])
    grid = c1.number_input("Raster N", 8, 2048, 64, step=8, key=f"{KEY}.raster")
    half = c2.toggle("halbe Pupille", value=False, key=f"{KEY}.halb", help="Symmetrie x → −x")
    reference = c3.selectbox(
        "Referenzsphäre",
        list(compute.REFERENCES),
        format_func=REFERENCE_LABELS.get,
        key=f"{KEY}.referenz",
    )
    gpu, device, _ = gpu_inputs(status, c4, c5, KEY, with_precision=False)
    if grid >= LARGE_GRID:
        st.caption(f"Raster {grid} × {grid}: {grid * grid:,} Strahlen pro Feld und Wellenlänge.")
    return compute.EvalOptions(int(grid), bool(half), str(reference), gpu, device)


def render(entry: FileEntry, system: Any, options: compute.EvalOptions) -> None:
    try:
        ev = cached_evaluation(str(entry.path), entry.mtime, entry.size, options)
    except Exception as exc:  # ValueError, GpuUnavailableError, CudaError
        error = compute.load_error(exc)
        st.error(f"{error.kind}: {error.message}")
        return

    ref_nm = float(ev.reference_nm)
    exit_pupil = ev.exit_pupil_position
    ref_text = REFERENCE_LABELS[options.reference]
    if options.reference == "exit-pupil" and exit_pupil is not None:
        ref_text += f" (z = {exit_pupil:.6g} mm ab letzter Fläche)"
    st.markdown(
        f"**EVAL** · Raster {ev.grid} × {ev.grid}, {ev.grid_points} Punkte in der Pupille"
        f"{' (halbe Pupille)' if ev.half_pupil else ''} · Referenzsphäre {ref_text} · "
        f"{str(ev.backend).upper()} · OPD in Wellen bei λ_ref = {ref_nm:g} nm"
    )
    if ev.failed_rays:
        st.warning(f"{ev.failed_rays} Strahlen versagt.")

    rows = system_tables.eval_rows(ev.stats, ref_nm, system.field_angles_deg)
    st.dataframe(rows, hide_index=True, width="stretch")
    st.caption(
        "HS: Hauptstrahl, SP: Schwerpunkt; Schwerpunkt und Brennlinien z_t, z_s relativ zum "
        "idealen Bildpunkt bzw. zur Bildebene. Strehl folgt mit G2-T3 (FFT)."
    )

    fields, wavelengths = ev.stats["rms_opd"].shape
    c1, c2, c3 = st.columns(3)
    f = c1.selectbox(
        "Feld",
        list(range(fields)),
        format_func=dict(enumerate(field_labels(fields, system.field_angles_deg))).get,
        key=f"{KEY}.feld",
    )
    wl_labels = wavelength_labels(system.wavelengths_nm, system.reference_nm)
    j = c2.selectbox(
        "Wellenlänge", list(range(wavelengths)), format_func=wl_labels.__getitem__, key=f"{KEY}.wl"
    )
    remove = c3.selectbox(
        "Abziehen", list(compute.REMOVALS), format_func=REMOVAL_LABELS.get, key=f"{KEY}.abzug"
    )

    left, right = st.columns(2)
    with left:
        opd_waves = compute.mm_to_waves(ev.opd_map(int(f), int(j), remove), ref_nm)
        st.plotly_chart(
            opd_figure(opd_waves, f"OPD nach Abzug: {REMOVAL_LABELS[remove]}"),
            width="stretch",
            key=f"{KEY}.opd",
        )
    with right:
        spots = ev.spots(int(f), int(j))
        stats = ev.stats
        centroid = (float(stats["centroid_x"][f, j]), float(stats["centroid_y"][f, j]))
        st.plotly_chart(
            spot_figure(spots["x"], spots["y"], centroid, "Spotdiagramm"),
            width="stretch",
            key=f"{KEY}.spots",
        )
        valid = int(np.isfinite(np.asarray(spots["x"], dtype=float)).sum())
        note = " Nur die gerechnete Hälfte x ≥ 0." if ev.half_pupil else ""
        st.caption(f"{valid} von {len(spots['x'])} Durchstoßpunkten.{note}")

    args = " ".join(options.cli_args())
    st.caption(
        f"Nachrechnen: `mikroptim eval {entry.path.name} --json {args}`; OPD-Karte als CSV: "
        f"`--map {f},{j} --map-file karte.csv --remove {remove}`"
    )
