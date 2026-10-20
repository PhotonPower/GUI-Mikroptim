"""Linsenschnitt in der y-z-Ebene als Plotly-Figur (G1-T3, ADR-0005).

Reine Darstellung aus Krümmung, Dicke, Halbdurchmesser, Material, Dezentrierung und Verkippung
einer Systembeschreibung (``mikroptim.system_to_dict`` oder die Datei selbst); keine Optik
(ADR-0002). Konventionen wie in Mikroptim (docs/numerik.md §2, docs/dateiformat.md, ADR-0011):

- z entlang der Achse in Tracerichtung, Scheitel der Fläche 0 bei z = 0; ``thickness`` ist der
  Abstand zum nächsten Scheitel, bei der letzten Fläche zur Bildebene.
- Krümmung c > 0: Krümmungsmittelpunkt auf der +z-Seite; Pfeilhöhe z(y) = c y² / (1 + √(1 − c² y²)).
- Dezentrierung [Δx, Δy] und Verkippung [α, β] betreffen nur die Fläche („dezentrieren und
  zurück“), Drehpunkt ist ihr Scheitel, R = R_y(β)·R_x(α). Gezeichnet wird das lokale
  Meridianprofil (x_lokal = 0) nach der Transformation, projiziert auf die y-z-Ebene; Δx ist im
  Schnitt nicht sichtbar.
- Geisterplatten liegen im Luftspalt nach ``after_surface`` im Abstand ``distance``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import plotly.graph_objects as go

SAMPLES = 41
GLASS_FILL = "rgba(120, 170, 220, 0.35)"
GLASS_LINE = "#2f6690"
STOP_COLOR = "#222222"
GHOST_COLOR = "#9d4edd"
IMAGE_COLOR = "#d62828"


def sag(curvature: float, y: np.ndarray) -> np.ndarray:
    """Pfeilhöhe der Kugelfläche; ``y`` muss |c·y| ≤ 1 erfüllen."""
    y = np.asarray(y, dtype=float)
    cy2 = curvature * y * y
    return cy2 / (1.0 + np.sqrt(np.maximum(0.0, 1.0 - curvature * cy2)))


def _is_glass(material: Any) -> bool:
    if isinstance(material, str):
        return material.strip().upper() != "AIR"
    return isinstance(material, dict)


@dataclass(frozen=True)
class SurfaceOutline:
    """Profil einer Fläche in globalen Koordinaten (y nach oben, z entlang der Achse)."""

    index: int
    type: str
    vertex_z: float
    y: np.ndarray
    z: np.ndarray
    semi_diameter: float
    clipped: bool  # Halbdurchmesser größer als |R|: Profil bis zur Halbkugel gekürzt
    transformed: bool


@dataclass(frozen=True)
class LensOutline:
    """Geometrie für den Linsenschnitt."""

    surfaces: list[SurfaceOutline]
    #: Glaskörper als (Fläche davor, Fläche danach), Medium dazwischen ist kein Luft
    elements: list[tuple[int, int]]
    ghost_plates: list[dict[str, float]]
    image_z: float
    notes: list[str] = field(default_factory=list)

    def element_polygon(self, first: int, second: int) -> tuple[np.ndarray, np.ndarray]:
        """Umriss eines Glaskörpers: Profil ``first`` abwärts, Profil ``second`` aufwärts."""
        a, b = self.surfaces[first], self.surfaces[second]
        z = np.concatenate([a.z[::-1], b.z, a.z[-1:]])
        y = np.concatenate([a.y[::-1], b.y, a.y[-1:]])
        return z, y


def _transform(
    y: np.ndarray, z_local: np.ndarray, decenter: list[float], tilt_deg: list[float]
) -> tuple[np.ndarray, np.ndarray]:
    """Lokales Profil (0, y, z) → global relativ zum nominellen Scheitel: R·p + Δ."""
    alpha, beta = (math.radians(t) for t in tilt_deg)
    # R_x(α): y' = y cos α − z sin α, z' = y sin α + z cos α
    y1 = y * math.cos(alpha) - z_local * math.sin(alpha)
    z1 = y * math.sin(alpha) + z_local * math.cos(alpha)
    # R_y(β) mit x = 0: x' = z sin β, z' = z cos β; y bleibt
    z2 = z1 * math.cos(beta)
    return y1 + decenter[1], z2


def outline(data: dict[str, Any], samples: int = SAMPLES) -> LensOutline:
    """Geometrie aus einer Systembeschreibung (``system_to_dict`` oder Datei)."""
    raw_surfaces = [s for s in data.get("surfaces") or [] if isinstance(s, dict)]
    notes: list[str] = []
    surfaces: list[SurfaceOutline] = []
    vertex_z = 0.0
    for i, s in enumerate(raw_surfaces):
        kind = str(s.get("type", "plane"))
        c = float(s.get("curvature", 0.0)) if kind == "sphere" else 0.0
        h = float(s.get("semi_diameter", 0.0))
        clipped = False
        h_draw = h
        if c != 0.0 and abs(c) * h > 1.0:
            h_draw = 1.0 / abs(c)
            clipped = True
            notes.append(
                f"Fläche {i}: Halbdurchmesser {h:g} mm größer als |R| = {1 / abs(c):g} mm, "
                "Profil bis zur Halbkugel gezeichnet."
            )
        y = np.linspace(h_draw, -h_draw, samples)
        z_local = sag(c, y)
        decenter = list(s.get("decenter") or [0.0, 0.0])
        tilt = list(s.get("tilt_deg") or [0.0, 0.0])
        transformed = any(v != 0 for v in decenter + tilt)
        if transformed:
            y, z_local = _transform(y, z_local, decenter, tilt)
        surfaces.append(
            SurfaceOutline(i, kind, vertex_z, y, vertex_z + z_local, h, clipped, transformed)
        )
        vertex_z += float(s.get("thickness", 0.0))

    elements = [
        (i, i + 1) for i, s in enumerate(raw_surfaces[:-1]) if _is_glass(s.get("material", "AIR"))
    ]
    if raw_surfaces and _is_glass(raw_surfaces[-1].get("material", "AIR")):
        notes.append("Das Medium nach der letzten Fläche ist kein Luft (Immersion?).")

    plates = []
    vertices = [s.vertex_z for s in surfaces]
    for g, plate in enumerate(data.get("ghost_plates") or []):
        after = int(plate.get("after_surface", -1))
        if 0 <= after < len(vertices):
            plates.append(
                {
                    "index": g,
                    "z": vertices[after] + float(plate.get("distance", 0.0)),
                    "radius": float(plate.get("norm_radius", 0.0)),
                    "after_surface": after,
                }
            )
    return LensOutline(surfaces, elements, plates, vertex_z, notes)


def last_vertex_z(geometry: LensOutline) -> float:
    return geometry.surfaces[-1].vertex_z if geometry.surfaces else 0.0


def image_space_is_long(geometry: LensOutline, factor: float = 1.0) -> bool:
    """Bildraum länger als ``factor`` × Baulänge (Fläche 0 bis letzte Fläche)?"""
    length = max(last_vertex_z(geometry), 1e-9)
    return geometry.image_z - last_vertex_z(geometry) > factor * length


def lens_figure(
    geometry: LensOutline, title: str | None = None, full_image_space: bool = True
) -> go.Figure:
    """Linsenschnitt: Glaskörper gefüllt, Flächen als Linien, Blende, Geisterplatten, Bild.

    Mit ``full_image_space=False`` endet die z-Achse kurz hinter der letzten Fläche; die Lage
    der Bildebene steht dann als Hinweis am rechten Rand.
    """
    fig = go.Figure()
    max_h = max([s.semi_diameter for s in geometry.surfaces] + [1.0])

    for first, second in geometry.elements:
        z, y = geometry.element_polygon(first, second)
        fig.add_trace(
            go.Scatter(
                x=z,
                y=y,
                fill="toself",
                fillcolor=GLASS_FILL,
                line={"color": GLASS_LINE, "width": 0.5},
                mode="lines",
                hoverinfo="skip",
                showlegend=False,
                name=f"Glas {first}–{second}",
            )
        )

    for s in geometry.surfaces:
        if s.type == "stop":
            stop_text = f"Fläche {s.index}: Blende, Pupillenradius {s.semi_diameter:g} mm"
            ys = [s.semi_diameter, s.semi_diameter * 1.25 + 0.05 * max_h]
            for sign in (1, -1):
                fig.add_trace(
                    go.Scatter(
                        x=[s.vertex_z, s.vertex_z],
                        y=[sign * ys[0], sign * ys[1]],
                        mode="lines",
                        line={"color": STOP_COLOR, "width": 4},
                        showlegend=False,
                        name="Blende",
                        hovertext=stop_text,
                        hoverinfo="text",
                    )
                )
            continue
        fig.add_trace(
            go.Scatter(
                x=s.z,
                y=s.y,
                mode="lines",
                line={
                    "color": GLASS_LINE,
                    "width": 1.5,
                    "dash": "dot" if s.clipped else "solid",
                },
                showlegend=False,
                name=f"Fläche {s.index}",
                hovertext=f"Fläche {s.index} ({s.type}), Scheitel z = {s.vertex_z:g} mm"
                + (", dezentriert/verkippt" if s.transformed else ""),
                hoverinfo="text",
            )
        )

    for plate in geometry.ghost_plates:
        r = plate["radius"] or max_h
        fig.add_trace(
            go.Scatter(
                x=[plate["z"], plate["z"]],
                y=[-r, r],
                mode="lines",
                line={"color": GHOST_COLOR, "width": 1, "dash": "dash"},
                showlegend=False,
                name=f"Geisterplatte {plate['index']}",
                hovertext=f"Geisterplatte {plate['index']} nach Fläche {plate['after_surface']}, "
                f"z = {plate['z']:g} mm",
                hoverinfo="text",
            )
        )

    last_h = geometry.surfaces[-1].semi_diameter if geometry.surfaces else max_h
    image_h = max(last_h, 0.1 * max_h)
    fig.add_trace(
        go.Scatter(
            x=[geometry.image_z, geometry.image_z],
            y=[-image_h, image_h],
            mode="lines",
            line={"color": IMAGE_COLOR, "width": 2},
            showlegend=False,
            name="Bildebene",
            hovertext=f"Bildebene, z = {geometry.image_z:g} mm",
            hoverinfo="text",
        )
    )
    z_min = min([0.0] + [float(s.z.min()) for s in geometry.surfaces])
    fig.add_shape(
        type="line",
        x0=z_min,
        x1=geometry.image_z,
        y0=0,
        y1=0,
        line={"color": "#888888", "width": 1, "dash": "dashdot"},
        layer="below",
    )
    for s in geometry.surfaces:
        fig.add_annotation(
            x=s.vertex_z,
            y=max(s.semi_diameter, 0.0) * (1.25 if s.type == "stop" else 1.0) + 0.08 * max_h,
            text=str(s.index),
            showarrow=False,
            font={"size": 10, "color": "#555555"},
        )

    if not full_image_space:
        z_end = last_vertex_z(geometry)
        z_max_surface = max([z_end] + [float(s.z.max()) for s in geometry.surfaces])
        margin = 0.15 * max(z_max_surface - z_min, 2 * max_h)
        right = z_max_surface + margin
        fig.update_xaxes(range=[z_min - margin, right])
        fig.add_annotation(
            x=right,
            y=0,
            xanchor="right",
            yanchor="bottom",
            text=f"Bildebene bei z = {geometry.image_z:g} mm →",
            showarrow=False,
            font={"size": 11, "color": IMAGE_COLOR},
        )
    fig.update_xaxes(title_text="z [mm]", zeroline=False)
    fig.update_yaxes(title_text="y [mm]", scaleanchor="x", scaleratio=1, zeroline=False)
    fig.update_layout(
        title=title,
        height=420,
        margin={"l": 50, "r": 20, "t": 40 if title else 20, "b": 40},
        hovermode="closest",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
