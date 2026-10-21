"""RMS-Wellenfront auf der Seite „Auswertung“ (G2-T1)."""

from __future__ import annotations

from typing import Any

import streamlit as st

from gui_mikroptim.backend import compute, mko, system_tables
from gui_mikroptim.backend.files import FileEntry
from gui_mikroptim.views import common, system_view
from gui_mikroptim.views.wavefront_plots import rms_heatmap


@st.cache_data(show_spinner="Wellenfront wird gerechnet …", max_entries=64)
def cached_trace(
    path: str, mtime: float, size: int, options: compute.TraceOptions
) -> compute.WavefrontResult:
    """Ergebnis pro Datei, Stand und Optionen (architektur.md, „Zustand und Cache“)."""
    system = system_view.cached_system(path, mtime, size)
    return compute.trace_wavefront(system, options)


def gpu_inputs(
    status: mko.MikroptimStatus, col_toggle, col_extra, key: str, with_precision: bool
) -> tuple[bool, int, str]:
    """GPU-Schalter, Gerät und Genauigkeit – nur mit CUDA-Build und nutzbarem Gerät."""
    gpu, device, precision = False, 0, "fp64"
    if not (status.has_cuda and status.devices):
        return gpu, device, precision
    gpu = col_toggle.toggle("GPU", value=False, key=f"{key}.gpu")
    if gpu:
        if len(status.devices) > 1:
            device = col_extra.selectbox(
                "Gerät",
                [int(d.get("index", i)) for i, d in enumerate(status.devices)],
                format_func=lambda i: f"{i}: {status.devices[i].get('name', '')}",
                key=f"{key}.geraet",
            )
        if with_precision:
            precision = col_extra.radio(
                "Genauigkeit",
                list(compute.PRECISIONS),
                horizontal=True,
                key=f"{key}.genauigkeit",
                help="df64: doppelte Gleitkommazahl aus zwei FP32-Werten (Mikroptim ADR-0003)",
            )
    return gpu, int(device), precision


def options_form(status: mko.MikroptimStatus, key: str = "auswertung") -> compute.TraceOptions:
    """Einstellungen; GPU-Schalter nur mit CUDA-Build und nutzbarem Gerät."""
    c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
    rings = c1.number_input("Ringe", 1, 256, 10, key=f"{key}.ringe")
    spokes = c2.number_input("Speichen", 1, 256, 8, key=f"{key}.speichen")
    gpu, device, precision = gpu_inputs(status, c3, c4, key, with_precision=True)
    return compute.TraceOptions(int(rings), int(spokes), gpu, device, precision)


def render(entry: FileEntry, system: Any, options: compute.TraceOptions) -> None:
    """Rechnen (gecacht) und darstellen; Fehler von Mikroptim als Meldung."""
    try:
        result = cached_trace(str(entry.path), entry.mtime, entry.size, options)
    except Exception as exc:  # ValueError (afokal, Optionen), GpuUnavailableError, CudaError
        error = compute.load_error(exc)
        st.error(f"{error.kind}: {error.message}")
        return

    backend = result.backend.upper()
    if result.device_name:
        backend += f" ({result.device_name})"
    focal = system_tables.fmt_number(result.target_focal_length, 7)
    st.markdown(
        f"**RMS-Wellenfront** in Wellen bei λ_ref = {result.reference_nm:g} nm · "
        f"{result.rings} Ringe × {result.spokes} Speichen · {backend}, {result.precision} · "
        f"Sollbrennweite {focal} mm"
    )
    finite = result.rms_waves[result.rms_waves == result.rms_waves]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("RMS max [Wellen]", f"{finite.max():.4g}" if finite.size else "–")
    c2.metric("RMS min [Wellen]", f"{finite.min():.4g}" if finite.size else "–")
    c3.metric("Strahlen", result.total_rays)
    c4.metric("versagt", result.total_failed)
    if result.total_failed:
        st.warning(
            f"{result.total_failed} von {result.total_rays} Strahlen versagt "
            "(Fehlschnitt, Totalreflexion oder Blende); betroffene Zellen sind mit ⚠ markiert."
        )

    common.chart(rms_heatmap(result, system.field_angles_deg), key="auswertung.rms")
    with st.expander("Tabelle", expanded=False):
        rows = system_tables.wavefront_rows(result, system.field_angles_deg)
        st.dataframe(rows, hide_index=True, width="stretch")
        common.download_csv(rows, f"{entry.path.stem}_wellenfront", "auswertung.csv.rms")
    st.caption(
        "Nachrechnen: `mikroptim trace "
        + entry.path.name
        + " --json "
        + " ".join(options.cli_args())
        + "`"
    )
