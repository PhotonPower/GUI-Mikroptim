"""Plotly-Figuren des Optimierungsverlaufs (G3-T2, überarbeitet in G6-T3). Reine Funktionen.

Beim Multistart mit vielen Läufen wird ein Diagramm mit einer farbigen Kurve pro Lauf
unübersichtlich. Deshalb: alle Läufe beginnen bei Zyklus 0 (übereinander, Konvergenz
vergleichbar); ab :data:`MAX_COLORED_RUNS` + 1 Läufen sind alle grau in einer Kurve und nur der
beste Lauf farbig. Dazu die Endmerit pro Lauf als eigenes Diagramm.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

#: bis zu so vielen Läufen bekommt jeder eine eigene Farbe
MAX_COLORED_RUNS = 3
BEST_COLOR = "#d62828"
OTHER_COLOR = "rgba(120, 120, 120, 0.35)"


def _positive(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and value > 0 else None


def runs_of(history: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    runs: dict[int, list[dict[str, Any]]] = {}
    for row in history:
        runs.setdefault(int(row["Lauf"]), []).append(row)
    return runs


def final_merits(history: list[dict[str, Any]]) -> dict[int, float | None]:
    """Letzte Merit jedes Laufs (bei einem laufenden Lauf die bisher letzte)."""
    return {run: _positive(rows[-1]["merit"]) for run, rows in runs_of(history).items()}


def best_run(history: list[dict[str, Any]]) -> int | None:
    finals = {r: m for r, m in final_merits(history).items() if m is not None}
    return min(finals, key=finals.get) if finals else None


def merit_history_figure(history: list[dict[str, Any]]) -> go.Figure:
    """Merit über den Zyklen jedes Laufs (logarithmisch), Läufe übereinander ab Zyklus 0."""
    runs = runs_of(history)
    best = best_run(history)
    fig = go.Figure()
    many = len(runs) > MAX_COLORED_RUNS
    if many:
        xs: list[Any] = []
        ys: list[Any] = []
        for run, rows in runs.items():
            if run == best:
                continue
            xs += [h["Zyklus"] for h in rows] + [None]
            ys += [_positive(h["merit"]) for h in rows] + [None]
        fig.add_trace(
            go.Scatter(
                x=xs, y=ys, mode="lines", line={"color": OTHER_COLOR, "width": 1},
                name=f"übrige {len(runs) - (best is not None)} Läufe", hoverinfo="skip",
            )
        )  # fmt: skip
    for run, rows in runs.items():
        if many and run != best:
            continue
        is_best = run == best
        fig.add_trace(
            go.Scatter(
                x=[h["Zyklus"] for h in rows],
                y=[_positive(h["merit"]) for h in rows],
                mode="lines+markers",
                marker={"size": 4},
                line={"width": 3 if is_best and many else 2,
                      **({"color": BEST_COLOR} if is_best and many else {})},
                name=f"bester Lauf {run}" if is_best and many else f"Lauf {run}",
                hovertemplate="Zyklus %{x}<br>Merit %{y:.6g}<extra>Lauf " + str(run) + "</extra>",
            )
        )  # fmt: skip
    shown = [best] if many else list(runs)
    rejected = [
        h for run in shown if run is not None for h in runs[run]
        if not h["angenommen"] and (h.get("Versuchsmerit") or 0) > 0
    ]  # fmt: skip
    if rejected:
        fig.add_trace(
            go.Scatter(
                x=[h["Zyklus"] for h in rejected],
                y=[h["Versuchsmerit"] for h in rejected],
                mode="markers",
                marker={"symbol": "x", "size": 6, "color": "#e76f51"},
                name="abgelehnter Versuch" + (" (bester Lauf)" if many else ""),
            )
        )
    fig.update_yaxes(type="log", title_text="Merit")
    fig.update_xaxes(title_text="Zyklus im Lauf")
    fig.update_layout(
        height=340, margin={"l": 60, "r": 20, "t": 20, "b": 40}, legend={"orientation": "h"}
    )
    return fig


def run_summary_figure(history: list[dict[str, Any]]) -> go.Figure:
    """Endmerit pro Lauf (logarithmisch); der beste Lauf ist markiert."""
    finals = final_merits(history)
    best = best_run(history)
    runs = sorted(finals)
    fig = go.Figure(
        go.Scatter(
            x=runs, y=[finals[r] for r in runs], mode="markers",
            marker={"size": 7, "color": "#2f6690"}, name="Endmerit",
            hovertemplate="Lauf %{x}<br>Endmerit %{y:.6g}<extra></extra>",
        )
    )  # fmt: skip
    if best is not None:
        fig.add_trace(
            go.Scatter(
                x=[best], y=[finals[best]], mode="markers",
                marker={"size": 14, "symbol": "star", "color": BEST_COLOR},
                name=f"bester Lauf {best}",
            )
        )  # fmt: skip
    fig.update_yaxes(type="log", title_text="Endmerit")
    fig.update_xaxes(title_text="Lauf", dtick=max(1, len(runs) // 10))
    fig.update_layout(
        height=340, margin={"l": 60, "r": 20, "t": 20, "b": 40}, legend={"orientation": "h"}
    )
    return fig
