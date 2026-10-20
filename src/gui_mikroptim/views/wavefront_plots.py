"""Plotly-Figuren zur RMS-Wellenfront (G2-T1, ADR-0005). Reine Funktionen."""

from __future__ import annotations

import math
from typing import Any

import plotly.graph_objects as go


def field_labels(fields: int, field_angles_deg: Any = None) -> list[str]:
    angles = [] if field_angles_deg is None else list(field_angles_deg)
    return [f"F{f} ({float(angles[f]):g}°)" if f < len(angles) else f"F{f}" for f in range(fields)]


def wavelength_labels(wavelengths_nm: Any, reference_nm: float) -> list[str]:
    return [
        f"{float(wl):g} nm" + (" (λ_ref)" if float(wl) == float(reference_nm) else "")
        for wl in wavelengths_nm
    ]


def rms_heatmap(result: Any, field_angles_deg: Any = None) -> go.Figure:
    """Heatmap Feld × Wellenlänge der RMS-Wellenfront in Wellen bei λ_ref.

    Zellen ohne gültigen Strahl bleiben leer („–“); Zellen mit versagten Strahlen tragen ⚠ und
    die Zahl der versagten Strahlen.
    """
    fields, wavelengths = result.rms_waves.shape
    z: list[list[float | None]] = []
    text: list[list[str]] = []
    for f in range(fields):
        z_row: list[float | None] = []
        t_row: list[str] = []
        for j in range(wavelengths):
            value = float(result.rms_waves[f, j])
            finite = math.isfinite(value)
            z_row.append(value if finite else None)
            cell = f"{value:.4g}" if finite else "–"
            failed = int(result.failed[f, j])
            if failed:
                cell += f"<br>⚠ {failed} versagt"
            t_row.append(cell)
        z.append(z_row)
        text.append(t_row)

    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=wavelength_labels(result.wavelengths_nm, result.reference_nm),
            y=field_labels(fields, field_angles_deg),
            text=text,
            texttemplate="%{text}",
            colorscale="Viridis",
            colorbar={"title": {"text": "Wellen"}},
            hovertemplate="%{y}, %{x}<br>RMS %{z:.6g} Wellen<extra></extra>",
            xgap=2,
            ygap=2,
        )
    )
    fig.update_yaxes(autorange="reversed", title_text="Feld")
    fig.update_xaxes(title_text="Wellenlänge", side="top")
    fig.update_layout(
        height=max(220, 70 * fields + 120), margin={"l": 80, "r": 20, "t": 60, "b": 20}
    )
    return fig
