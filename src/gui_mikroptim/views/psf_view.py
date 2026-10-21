"""PSF, MTF und Strehl auf der Seite „Auswertung“ (G2-T3)."""

from __future__ import annotations

from typing import Any

import streamlit as st

from gui_mikroptim.backend import compute, mko
from gui_mikroptim.backend.files import FileEntry
from gui_mikroptim.views import common, eval_view
from gui_mikroptim.views.psf_plots import mtf_figure, psf_figure
from gui_mikroptim.views.wavefront_plots import field_labels, wavelength_labels

KEY = "auswertung.psf"
POLARIZATION_LABELS = {
    "x": "linear x",
    "y": "linear y",
    "circular": "zirkular",
    "unpolarized": "unpolarisiert",
}


@st.cache_data(show_spinner="PSF wird gerechnet …", max_entries=64)
def _scalar(
    path: str,
    mtime: float,
    size: int,
    eval_options: compute.EvalOptions,
    psf_options: compute.PsfOptions,
    field_index: int,
    wavelength: int,
) -> compute.PsfResult:
    ev = eval_view.cached_evaluation(path, mtime, size, eval_options)
    return compute.scalar_psf(ev, field_index, wavelength, psf_options)


@st.cache_data(show_spinner="Vektorielle PSF wird gerechnet …", max_entries=16)
def _vector(
    path: str,
    mtime: float,
    size: int,
    eval_options: compute.EvalOptions,
    psf_options: compute.PsfOptions,
    vector_options: compute.VectorOptions,
    field_index: int,
    wavelength: int,
) -> compute.PsfResult:
    del mtime, size  # nur Schlüssel
    from pathlib import Path

    return compute.vector_psf(
        Path(path), eval_options, psf_options, vector_options, field_index, wavelength
    )


def options_form(
    status: mko.MikroptimStatus, eval_options: compute.EvalOptions
) -> tuple[compute.PsfOptions, compute.VectorOptions | None]:
    c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
    padding = c1.number_input("Zero-Padding Q", 2.0, 16.0, 4.0, step=1.0, key=f"{KEY}.padding")
    na = c2.number_input(
        "NA vorgeben",
        0.0,
        1.5,
        0.0,
        step=0.05,
        format="%.3f",
        key=f"{KEY}.na",
        help="0: NA aus den Feldstrahlen (Standard von Mikroptim)",
    )
    model = c3.radio("Modell", ["skalar", "vektoriell"], horizontal=True, key=f"{KEY}.modell")
    psf_options = compute.PsfOptions(
        float(padding), float(na), eval_options.gpu, eval_options.device
    )
    if model == "skalar":
        return psf_options, None
    pol_col, defocus_col = c4.columns(2)
    polarization = pol_col.selectbox(
        "Polarisation",
        list(compute.POLARIZATIONS),
        format_func=POLARIZATION_LABELS.get,
        key=f"{KEY}.polarisation",
    )
    defocus = defocus_col.number_input(
        "Defokus [mm]",
        value=0.0,
        step=0.001,
        format="%.4f",
        key=f"{KEY}.defokus",
        help="Auswerteebene relativ zur Bildebene, > 0 in Tracerichtung",
    )
    return psf_options, compute.VectorOptions(str(polarization), float(defocus))


def _metrics(result: compute.PsfResult, stats: dict[str, Any]) -> None:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Strehl", f"{result.strehl:.4g}", help="nach Abzug der Kippung")
    c2.metric("Strehl im Bildpunkt", f"{result.strehl_origin:.4g}")
    c3.metric("Maximum", f"{result.peak:.4g}")
    c4.metric("Airy-Radius [µm]", f"{result.airy_radius * 1e3:.4g}")
    mtf_s, mtf_t = result.mtf_half_cutoff
    c5.metric("MTF bei f_c/2 (s / t)", f"{mtf_s:.3f} / {mtf_t:.3f}")
    peak_x, peak_y = result.peak_position
    st.caption(
        f"λ = {result.wavelength_nm:g} nm · NA {result.na_x:.5g} (x) / {result.na_y:.5g} (y) · "
        f"FFT {result.fft_size} × {result.fft_size}, Pixel {result.dx * 1e3:.4g} µm · "
        f"Maximum bei ({peak_x * 1e3:.4g}, {peak_y * 1e3:.4g}) µm · transmittiert "
        f"{result.energy:.6g} · f_c = {max(result.cutoff_x, result.cutoff_y):.5g} lp/mm"
    )
    if result.scalar_na_too_high:
        st.warning(
            f"NA {max(result.na_x, result.na_y):.3g} > {compute.SCALAR_NA_LIMIT}: Die skalare "
            "Näherung ist hier ungenau; das Modell „vektoriell“ verwenden (Mikroptim M8-T2/M8-T5)."
        )
    window = compute.window_warning(result, stats)
    if window is not None:
        reach, half = window
        st.warning(
            f"Geometrischer Spot ({reach:.3e} mm) größer als das halbe Bildfenster "
            f"({half:.3e} mm): PSF zurückgefaltet. Raster im Reiter „OPD und Spots“ vergrößern."
        )


def _vector_details(result: compute.PsfResult) -> None:
    vec = result.vector or {}
    fwhm = vec.get("fwhm_mm") or [None, None]
    fractions = vec.get("energy_fraction") or [None, None, None]
    parts = []
    if fwhm[0] is not None:
        parts.append(f"FWHM {fwhm[0] * 1e3:.4g} × {fwhm[1] * 1e3:.4g} µm")
    if fractions[0] is not None:
        parts.append(
            "Energieanteile E_x/E_y/E_z " + " / ".join(f"{100 * float(v):.3g} %" for v in fractions)
        )
    if vec.get("evanescent_points"):
        parts.append(f"{vec['evanescent_points']} evaneszente Pupillenpunkte")
    if parts:
        st.caption(" · ".join(parts))


def render(
    entry: FileEntry,
    system: Any,
    eval_options: compute.EvalOptions,
    psf_options: compute.PsfOptions,
    vector_options: compute.VectorOptions | None,
) -> None:
    try:
        ev = eval_view.cached_evaluation(str(entry.path), entry.mtime, entry.size, eval_options)
    except Exception as exc:
        error = compute.load_error(exc)
        st.error(f"{error.kind}: {error.message}")
        return

    fields, wavelengths = ev.stats["rms_opd"].shape
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
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
    log = c3.toggle("logarithmisch", value=False, key=f"{KEY}.log")
    airy = c4.number_input(
        "Ausschnitt [Airy-Radien]",
        0.0,
        500.0,
        10.0,
        step=1.0,
        key=f"{KEY}.ausschnitt",
        help="halbe Breite des gezeigten Ausschnitts; 0: ganzes Bildfenster",
    )

    try:
        if vector_options is None:
            result = _scalar(
                str(entry.path), entry.mtime, entry.size, eval_options, psf_options, int(f), int(j)
            )
        else:
            result = _vector(
                str(entry.path),
                entry.mtime,
                entry.size,
                eval_options,
                psf_options,
                vector_options,
                int(f),
                int(j),
            )
    except Exception as exc:  # ValueError, RuntimeError (CLI), GpuUnavailableError, CudaError
        error = compute.load_error(exc)
        st.error(f"{error.kind}: {error.message}")
        return

    model = "vektoriell" if result.model == "vector" else "skalar"
    st.markdown(f"**PSF {model}** · Feld {f}, {wl_labels[int(j)]} · {result.backend.upper()}")
    _metrics(result, ev.stats)
    if result.model == "vector":
        _vector_details(result)

    half_width = float(airy) * result.airy_radius if airy else None
    left, right = st.columns(2)
    with left:
        common.chart(
            psf_figure(result.psf, result.dx, result.dy, half_width, bool(log), "PSF"),
            key=f"{KEY}.psf",
        )
    with right:
        common.chart(
            mtf_figure(
                result.frequencies,
                result.mtf_sagittal,
                result.mtf_tangential,
                result.cutoff_x,
                result.cutoff_y,
                "MTF",
            ),
            key=f"{KEY}.mtf",
        )
    if result.components is not None:
        with st.expander("Feldkomponenten |E_x|², |E_y|², |E_z|² (logarithmisch)"):
            cols = st.columns(3)
            for col, name, comp in zip(cols, ("E_x", "E_y", "E_z"), result.components, strict=True):
                with col:
                    common.chart(
                        psf_figure(comp, result.dx, result.dy, half_width, True, f"|{name}|²"),
                        key=f"{KEY}.{name}",
                    )

    args = [
        *eval_options.cli_args(),
        *psf_options.cli_args(),
        *(vector_options.cli_args() if vector_options else []),
    ]
    st.caption(
        f"Nachrechnen: `mikroptim eval {entry.path.name} --json {' '.join(args)} "
        f"--psf-tuple {f},{j} --psf-file psf.csv --mtf-file mtf.csv`"
    )
