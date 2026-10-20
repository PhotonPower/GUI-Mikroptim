"""Plotly-Figuren für EVAL: OPD-Karte und Spotdiagramm (G2-T2, ADR-0005). Reine Funktionen."""

from __future__ import annotations

import math

import numpy as np
import plotly.graph_objects as go

#: divergierende Skala für OPD (blau negativ, rot positiv), symmetrisch um 0
OPD_COLORSCALE = "RdBu_r"
#: ab dieser Punktzahl zeichnet das Spotdiagramm mit WebGL
SCATTERGL_FROM = 5000


def pupil_axis(grid: int) -> np.ndarray:
    """Mittelpunkte der Rasterzellen in normierten Pupillenkoordinaten: −1 + (2i + 1)/N."""
    return -1.0 + (2.0 * np.arange(grid) + 1.0) / grid


def symmetric_range(values: np.ndarray) -> float:
    """Halbbreite der Farbskala: größter Betrag der endlichen Werte (1, wenn es keine gibt)."""
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return 1.0
    peak = float(np.max(np.abs(finite)))
    return peak if peak > 0 else 1.0


def opd_figure(opd_waves: np.ndarray, title: str | None = None) -> go.Figure:
    """OPD-Karte [Wellen] auf dem N×N-Raster; Zeile j = y, Spalte i = x (wie ``opd_map``).

    NaN (außerhalb der Pupille, versagte Strahlen) bleibt leer. Die Farbskala ist divergierend
    und symmetrisch um 0 (AGENTS.md, Abschnitt 5).
    """
    opd = np.asarray(opd_waves, dtype=float)
    grid = opd.shape[0]
    axis = pupil_axis(grid)
    half = symmetric_range(opd)
    z = np.where(np.isfinite(opd), opd, np.nan)
    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=axis,
            y=axis,
            colorscale=OPD_COLORSCALE,
            zmin=-half,
            zmax=half,
            zmid=0.0,
            colorbar={"title": {"text": "Wellen"}},
            hovertemplate="x %{x:.3f}, y %{y:.3f}<br>OPD %{z:.5g} Wellen<extra></extra>",
            hoverongaps=False,
        )
    )
    fig.update_xaxes(title_text="x (normierte Pupille)", range=[-1.02, 1.02], constrain="domain")
    fig.update_yaxes(
        title_text="y (normierte Pupille)",
        range=[-1.02, 1.02],
        scaleanchor="x",
        scaleratio=1,
        constrain="domain",
    )
    fig.update_layout(
        title=title, height=460, margin={"l": 60, "r": 20, "t": 40 if title else 20, "b": 50}
    )
    return fig


def spot_figure(
    x_mm: np.ndarray,
    y_mm: np.ndarray,
    centroid_mm: tuple[float, float] | None = None,
    title: str | None = None,
) -> go.Figure:
    """Spotdiagramm in µm relativ zum idealen Bildpunkt; versagte Strahlen (NaN) fehlen."""
    x = np.asarray(x_mm, dtype=float) * 1e3
    y = np.asarray(y_mm, dtype=float) * 1e3
    ok = np.isfinite(x) & np.isfinite(y)
    scatter = go.Scattergl if int(ok.sum()) >= SCATTERGL_FROM else go.Scatter
    fig = go.Figure(
        scatter(
            x=x[ok],
            y=y[ok],
            mode="markers",
            marker={"size": 3, "color": "#2f6690", "opacity": 0.6},
            name="Durchstoßpunkte",
            hovertemplate="x %{x:.4g} µm, y %{y:.4g} µm<extra></extra>",
        )
    )
    if centroid_mm is not None and all(math.isfinite(v) for v in centroid_mm):
        fig.add_trace(
            go.Scatter(
                x=[centroid_mm[0] * 1e3],
                y=[centroid_mm[1] * 1e3],
                mode="markers",
                marker={"symbol": "x", "size": 12, "color": "#d62828"},
                name="Schwerpunkt",
                hovertemplate="Schwerpunkt x %{x:.4g} µm, y %{y:.4g} µm<extra></extra>",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=[0.0],
            y=[0.0],
            mode="markers",
            marker={"symbol": "cross-thin", "size": 14, "line": {"width": 2, "color": "#222"}},
            name="idealer Bildpunkt",
            hoverinfo="skip",
        )
    )
    fig.update_xaxes(title_text="x [µm]", zeroline=False)
    fig.update_yaxes(title_text="y [µm]", scaleanchor="x", scaleratio=1, zeroline=False)
    fig.update_layout(
        title=title,
        height=460,
        margin={"l": 60, "r": 20, "t": 40 if title else 20, "b": 50},
        legend={"orientation": "h", "y": -0.15},
    )
    return fig
