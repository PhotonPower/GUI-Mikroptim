"""Vergleich zweier Systeme auf der Seite „Auswertung“ (G2-T4)."""

from __future__ import annotations

from typing import Any

import numpy as np
import streamlit as st

from gui_mikroptim.backend import compare, compute, mko
from gui_mikroptim.backend.files import FileEntry
from gui_mikroptim.config import Settings
from gui_mikroptim.views import common, file_picker, lens_plot, system_view
from gui_mikroptim.views.wavefront_plots import (
    field_labels,
    rms_difference_heatmap,
    rms_heatmap,
    wavelength_labels,
)
from gui_mikroptim.views.wavefront_view import cached_trace

KEY = "auswertung.vergleich"


def _max(values: Any) -> float | None:
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    return float(v.max()) if v.size else None


def _fmt(value: float | None, sign: bool = False) -> str:
    if value is None:
        return "–"
    return f"{value:+.4g}" if sign else f"{value:.4g}"


def _trace(entry: FileEntry, options: compute.TraceOptions):
    try:
        return cached_trace(str(entry.path), entry.mtime, entry.size, options), None
    except Exception as exc:  # afokal, GPU …
        return None, compute.load_error(exc)


def render(
    cfg: Settings,
    entry_a: FileEntry,
    system_a: Any,
    options: compute.TraceOptions,
) -> None:
    st.caption(
        f"A ist das aktuelle System ({entry_a.path.name}). B hier wählen; gerechnet wird mit den "
        f"Einstellungen des Reiters „Wellenfront“ ({options.label()})."
    )
    entry_b = file_picker.pick_document(
        cfg,
        ("mikroptim.system",),
        key=KEY,
        empty_hint="Zweites System hochladen oder auf der Seite „System“ wählen.",
        source_list=file_picker.system_sources(cfg),
    )
    if entry_b is None:
        return
    if entry_b.path == entry_a.path:
        st.info("A und B sind dieselbe Datei; für einen Vergleich ein anderes System wählen.")
        return
    system_b, error = system_view.load(entry_b)
    if error is not None:
        system_view.show_load_error(error)
        return

    result_a, error_a = _trace(entry_a, options)
    result_b, error_b = _trace(entry_b, options)
    for name, err in (("A", error_a), ("B", error_b)):
        if err is not None:
            st.error(f"Wellenfront von {name}: {err.kind}: {err.message}")
    if result_a is None or result_b is None:
        return

    st.markdown(
        f"**A:** {system_a.name or entry_a.path.stem} · **B:** {system_b.name or entry_b.path.stem}"
    )
    max_a, max_b = _max(result_a.rms_waves), _max(result_b.rms_waves)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("RMS max A [Wellen]", _fmt(max_a))
    c2.metric(
        "RMS max B [Wellen]",
        _fmt(max_b),
        delta=_fmt(max_b - max_a, sign=True) if None not in (max_a, max_b) else None,
        delta_color="inverse",
    )
    c3.metric("versagt A / B", f"{result_a.total_failed} / {result_b.total_failed}")
    c4.metric("Flächen A / B", f"{system_a.num_surfaces} / {system_b.num_surfaces}")

    check = compare.comparability(system_a, system_b)
    if check.same_grid:
        diff = compare.rms_difference(result_a, result_b)
        labels_f = field_labels(diff.shape[0], system_a.field_angles_deg)
        labels_w = wavelength_labels(system_a.wavelengths_nm, system_a.reference_nm)
        st.markdown("**RMS-Wellenfront B − A** (rot: B schlechter, blau: B besser)")
        common.chart(rms_difference_heatmap(diff, labels_f, labels_w), key=f"{KEY}.delta")
        with st.expander("Tabelle", expanded=False):
            rows = compare.rms_compare_rows(
                result_a, result_b, system_a.field_angles_deg, system_a.wavelengths_nm
            )
            st.dataframe(rows, hide_index=True, width="stretch")
            common.download_csv(
                rows, f"vergleich_{entry_a.path.stem}_{entry_b.path.stem}", f"{KEY}.csv"
            )
    else:
        st.warning(
            "Felder, Wellenlängen oder Referenzwellenlänge verschieden; deshalb nebeneinander "
            "statt als Differenz:\n\n" + "\n".join(f"- {r}" for r in check.reasons)
        )
        left, right = st.columns(2)
        with left:
            st.markdown("**A**")
            common.chart(rms_heatmap(result_a, system_a.field_angles_deg), key=f"{KEY}.a")
        with right:
            st.markdown("**B**")
            common.chart(rms_heatmap(result_b, system_b.field_angles_deg), key=f"{KEY}.b")

    st.markdown("**Paraxialdaten**")
    st.dataframe(
        compare.paraxial_compare_rows(
            compute.details(system_a).paraxial, compute.details(system_b).paraxial
        ),
        hide_index=True,
        width="stretch",
    )

    with st.expander("Linsenschnitte", expanded=False):
        left, right = st.columns(2)
        for col, name, sys_ in ((left, "A", system_a), (right, "B", system_b)):
            with col:
                geometry = lens_plot.outline(mko.require().system_to_dict(sys_))
                common.chart(
                    lens_plot.lens_figure(
                        geometry, name, full_image_space=not lens_plot.image_space_is_long(geometry)
                    ),
                    key=f"{KEY}.schnitt.{name}",
                )
