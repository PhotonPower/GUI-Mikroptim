"""Plotly-Figuren für Protokolle ``mikroptim.synth/1`` (ADR-0005).

Reine Funktionen: Eingabe sind die Schrittzeilen aus ``backend.protocols``, Ausgabe eine
``go.Figure``. Nicht endliche Werte stehen im Protokoll als ``null`` und erscheinen als Lücke.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots

ACCEPTED_COLOR = "#2a9d8f"
REJECTED_COLOR = "#e76f51"
INSERT_COLOR = "#6a4c93"


def _positive_or_none(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and value > 0 else None


def _hover(row: dict[str, Any]) -> str:
    parts = [
        f"Schritt {row.get('schritt')} ({row.get('art')})",
        f"Kandidat {row.get('kandidat')}" if row.get("kandidat") is not None else None,
        f"Aktion: {row.get('aktion')}",
        f"LM: {row.get('lm_status')}, {row.get('lm_iterationen')} Zyklen",
        f"Operation: {row.get('operation')}" if row.get("operation") else None,
    ]
    return "<br>".join(p for p in parts if p)


def synth_progress_figure(steps: list[dict[str, Any]]) -> go.Figure:
    """Verlauf über die Schritte: Homotopie-Punkt, RMS-Wellenfront, Zahl der Elemente.

    Oben NA und Feldanteil, Mitte RMS in Wellen (logarithmisch; angenommene Schritte als
    Linie, abgelehnte als rote Kreuze), unten die Glaselemente. Einfügungen sind in allen
    Zeilen als senkrechte Linien markiert.
    """
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.35, 0.4, 0.25],
        subplot_titles=("Homotopie-Punkt", "RMS-Wellenfront [Wellen]", "Glaselemente"),
    )
    accepted = [r for r in steps if r.get("angenommen")]
    rejected = [r for r in steps if r.get("angenommen") is False]

    def xs(rows: list[dict[str, Any]]) -> list[Any]:
        return [r.get("schritt") for r in rows]

    fig.add_trace(
        go.Scatter(
            x=xs(accepted),
            y=[r.get("na") for r in accepted],
            mode="lines+markers",
            name="NA",
            line={"shape": "hv"},
            hovertext=[_hover(r) for r in accepted],
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=xs(accepted),
            y=[r.get("feld") for r in accepted],
            mode="lines",
            name="Feldanteil",
            line={"shape": "hv", "dash": "dot"},
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=xs(accepted),
            y=[_positive_or_none(r.get("rms_wellen")) for r in accepted],
            mode="lines+markers",
            name="RMS angenommen",
            marker={"color": ACCEPTED_COLOR},
            line={"color": ACCEPTED_COLOR},
            hovertext=[_hover(r) for r in accepted],
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=xs(rejected),
            y=[_positive_or_none(r.get("rms_wellen")) for r in rejected],
            mode="markers",
            name="RMS abgelehnt",
            marker={"color": REJECTED_COLOR, "symbol": "x", "size": 8},
            hovertext=[_hover(r) for r in rejected],
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=xs(steps),
            y=[r.get("elemente") for r in steps],
            mode="lines",
            name="Elemente",
            line={"shape": "hv", "color": INSERT_COLOR},
        ),
        row=3,
        col=1,
    )
    for row in steps:
        if row.get("aktion") == "insert" and row.get("schritt") is not None:
            fig.add_vline(
                x=row["schritt"], line={"color": INSERT_COLOR, "width": 1, "dash": "dash"}
            )

    fig.update_yaxes(title_text="NA / Feld", row=1, col=1)
    fig.update_yaxes(type="log", title_text="Wellen", row=2, col=1)
    fig.update_yaxes(title_text="Anzahl", rangemode="tozero", dtick=1, row=3, col=1)
    fig.update_xaxes(title_text="Schritt", row=3, col=1)
    fig.update_layout(
        height=620,
        margin={"l": 60, "r": 20, "t": 40, "b": 40},
        legend={"orientation": "h", "y": -0.12},
        hovermode="closest",
    )
    return fig
