"""Plotly-Figuren für PSF und MTF (G2-T3, ADR-0005). Reine Funktionen."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from gui_mikroptim.views.display_limits import reduce_grid

#: kleinster Wert der logarithmischen Darstellung (Strehl-Einheiten)
LOG_FLOOR = 1e-8


def psf_axes(size: int, dx: float, dy: float) -> tuple[np.ndarray, np.ndarray]:
    """Achsen in mm relativ zum idealen Bildpunkt: x = (i − M/2)·dx, y = (j − M/2)·dy."""
    index = np.arange(size) - size // 2
    return index * dx, index * dy


def crop(
    psf: np.ndarray, x: np.ndarray, y: np.ndarray, half_width: float | None
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Ausschnitt |x|, |y| ≤ ``half_width`` (mm); ``None`` oder 0: ganzes Fenster."""
    if not half_width:
        return psf, x, y
    keep_x = np.abs(x) <= half_width
    keep_y = np.abs(y) <= half_width
    return psf[np.ix_(keep_y, keep_x)], x[keep_x], y[keep_y]


def psf_figure(
    psf: np.ndarray,
    dx: float,
    dy: float,
    half_width_mm: float | None = None,
    log: bool = False,
    title: str | None = None,
) -> go.Figure:
    """PSF in Strehl-Einheiten über der Bildebene in µm; linear oder log₁₀ (Untergrenze 1e-8)."""
    psf = np.asarray(psf, dtype=float)
    x, y = psf_axes(psf.shape[0], dx, dy)
    z, x, y = crop(psf, x, y, half_width_mm)
    # Maximum je Block: die Spitze der PSF bleibt sichtbar
    z, x, y, k = reduce_grid(z, x, y, "max")
    if k > 1:
        title = f"{title or 'PSF'} (Anzeige: Maximum über {k} × {k} Pixel)"
    if log:
        z = np.log10(np.maximum(z, LOG_FLOOR))
        colorbar = {"title": {"text": "log₁₀"}}
        hover = "x %{x:.4g} µm, y %{y:.4g} µm<br>log₁₀ I %{z:.3f}<extra></extra>"
    else:
        colorbar = {"title": {"text": "Strehl"}}
        hover = "x %{x:.4g} µm, y %{y:.4g} µm<br>I %{z:.4g}<extra></extra>"
    fig = go.Figure(
        go.Heatmap(
            z=z, x=x * 1e3, y=y * 1e3, colorscale="Inferno", colorbar=colorbar,
            hovertemplate=hover,
        )
    )  # fmt: skip
    fig.update_xaxes(title_text="x [µm]", constrain="domain")
    fig.update_yaxes(title_text="y [µm]", scaleanchor="x", scaleratio=1, constrain="domain")
    fig.update_layout(
        title=title, height=460, margin={"l": 60, "r": 20, "t": 40 if title else 20, "b": 50}
    )
    return fig


def mtf_figure(
    frequencies: np.ndarray,
    mtf_sagittal: np.ndarray,
    mtf_tangential: np.ndarray,
    cutoff_x: float,
    cutoff_y: float,
    title: str | None = None,
) -> go.Figure:
    """MTF-Schnitte über der Ortsfrequenz in Linienpaaren/mm (f = ν · f_c, wie die CLI).

    Die Grenzfrequenz f_c = 2 NA/λ und f_c/2 sind als senkrechte Linien eingezeichnet (Werte aus
    Mikroptim); eine beugungsbegrenzte Referenzkurve rechnet die GUI nicht (ADR-0002).
    """
    nu = np.asarray(frequencies, dtype=float)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=nu * cutoff_x, y=mtf_sagittal, mode="lines", name="sagittal"))
    fig.add_trace(
        go.Scatter(
            x=nu * cutoff_y, y=mtf_tangential, mode="lines", name="tangential",
            line={"dash": "dash"},
        )
    )  # fmt: skip
    cutoff = max(cutoff_x, cutoff_y)
    fig.add_vline(x=cutoff, line={"color": "#888", "width": 1}, annotation_text="f_c")
    fig.add_vline(
        x=0.5 * cutoff, line={"color": "#bbb", "width": 1, "dash": "dot"}, annotation_text="f_c/2"
    )
    fig.update_xaxes(title_text="Ortsfrequenz [lp/mm]", range=[0, cutoff * 1.02])
    fig.update_yaxes(title_text="MTF", range=[0, 1.02])
    fig.update_layout(
        title=title,
        height=400,
        margin={"l": 60, "r": 20, "t": 40 if title else 20, "b": 50},
        legend={"orientation": "h", "y": -0.2},
    )
    return fig
