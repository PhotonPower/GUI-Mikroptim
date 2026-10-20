"""Plotly-Figur des Optimierungsverlaufs (G3-T2, ADR-0005). Reine Funktion."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go


def merit_history_figure(history: list[dict[str, Any]]) -> go.Figure:
    """Merit über den Zyklen, logarithmisch, eine Kurve pro Lauf des Multistarts.

    Die x-Achse zählt die Zyklen fortlaufend über alle Läufe; abgelehnte Versuchsschritte
    (``angenommen`` falsch) sind als Kreuze mit ihrer Versuchsmerit eingetragen.
    """
    fig = go.Figure()
    runs = sorted({h["Lauf"] for h in history})
    position = {id(h): i + 1 for i, h in enumerate(history)}
    for run in runs:
        rows = [h for h in history if h["Lauf"] == run]
        fig.add_trace(
            go.Scatter(
                x=[position[id(h)] for h in rows],
                y=[h["merit"] if h["merit"] and h["merit"] > 0 else None for h in rows],
                mode="lines+markers",
                marker={"size": 4},
                name=f"Lauf {run}",
                hovertemplate="Zyklus %{x}<br>Merit %{y:.6g}<extra>Lauf " + str(run) + "</extra>",
            )
        )
    rejected = [h for h in history if not h["angenommen"] and (h.get("Versuchsmerit") or 0) > 0]
    if rejected:
        fig.add_trace(
            go.Scatter(
                x=[position[id(h)] for h in rejected],
                y=[h["Versuchsmerit"] for h in rejected],
                mode="markers",
                marker={"symbol": "x", "size": 6, "color": "#e76f51"},
                name="abgelehnter Versuch",
            )
        )
    fig.update_yaxes(type="log", title_text="Merit")
    fig.update_xaxes(title_text="Zyklus (fortlaufend)")
    fig.update_layout(
        height=340, margin={"l": 60, "r": 20, "t": 20, "b": 40}, legend={"orientation": "h"}
    )
    return fig
