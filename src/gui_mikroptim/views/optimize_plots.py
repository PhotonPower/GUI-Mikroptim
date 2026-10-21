"""Plotly-Figuren des Optimierungsverlaufs (G3-T2, G6-T3, Strafrunden). Reine Funktionen.

Beim weichen Strahlversagen startet Mikroptim einen Lauf, der mit versagten Strahlen endet, an
seinem Endpunkt mit zehnfachem Strafgewicht neu (äußeres Strafverfahren, Mikroptim docs/cli.md,
„Strahlversagen“); ``max_iterations`` gilt pro Runde, die Zyklen zählen über die Runden weiter.
Innerhalb einer Runde fällt die Merit nur (LM nimmt nur bessere Schritte an); steigt sie, hat
eine neue Runde begonnen. Die Merit enthält die Strafe versagter Strahlen: Nur Läufe, die ohne
versagte Strahlen enden, haben vergleichbare Endwerte (reine Wellenfront).
"""

from __future__ import annotations

import math
from typing import Any

import plotly.graph_objects as go

#: bis zu so vielen Läufen bekommt jeder eine eigene Farbe
MAX_COLORED_RUNS = 3
BEST_COLOR = "#d62828"
OTHER_COLOR = "rgba(120, 120, 120, 0.35)"
FAILED_COLOR = "rgba(231, 111, 81, 0.45)"
RESTART_COLOR = "#6a4c93"


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


def ends_with_failed_rays(rows: list[dict[str, Any]]) -> bool:
    return bool(rows) and bool(rows[-1].get("versagt"))


def restart_indices(
    rows: list[dict[str, Any]], cycles_per_round: int | None = None, rounds: int | None = None
) -> list[int]:
    """Zyklen eines Laufs (Indizes in ``rows``), mit denen eine neue Strafrunde beginnt.

    Der Rückruf von Mikroptim nennt die Runde nicht (Wunsch W10). Exakt, wenn nach dem Lauf die
    Zahl der Runden bekannt ist (``OptimizeResult.runs[…]["penalty_rounds"]``) und alle Runden voll
    waren (Runden × Zyklen pro Runde = Zyklen): dann beginnen sie bei den Vielfachen. Sonst über
    den Anstieg der Merit (innerhalb einer Runde fällt sie nur); das übersieht Neustarts, deren
    erster Schritt die Merit schon unter den Wert davor senkt.
    """
    if cycles_per_round and rounds and rounds > 1 and len(rows) == rounds * cycles_per_round:
        return [k * cycles_per_round for k in range(1, rounds)]
    starts = []
    for i in range(1, len(rows)):
        previous, now = _positive(rows[i - 1]["merit"]), _positive(rows[i]["merit"])
        if previous is not None and now is not None and now > previous:
            starts.append(i)
    return starts


def best_run(history: list[dict[str, Any]], preferred: int | None = None) -> int | None:
    """Bester Lauf: ``preferred`` (von Mikroptim, ``OptimizeResult.best_run``), sonst der mit
    kleinster Endmerit unter den Läufen ohne versagte Strahlen am Ende (falls es solche gibt)."""
    runs = runs_of(history)
    if preferred is not None and preferred in runs:
        return preferred
    finals = final_merits(history)
    clean = {
        r: m for r, m in finals.items() if m is not None and not ends_with_failed_rays(runs[r])
    }
    pool = clean or {r: m for r, m in finals.items() if m is not None}
    return min(pool, key=pool.get) if pool else None


def _y_range(history: list[dict[str, Any]]) -> list[float] | None:
    """Logarithmischer Bereich nach den Läufen ohne versagte Strahlen am Ende, wenn andere
    Läufe mit ihrer Strafe weit darüber liegen; sonst automatisch."""
    runs = runs_of(history)
    clean = [r for r, rows in runs.items() if not ends_with_failed_rays(rows)]
    if not clean or len(clean) == len(runs):
        return None
    values = [v for r in clean for h in runs[r] if (v := _positive(h["merit"])) is not None]
    if not values:
        return None
    return [math.log10(min(values)) - 0.5, math.log10(max(values)) + 0.5]


def _hover(run: int) -> str:
    return (
        "Zyklus %{x}<br>Merit %{y:.6g}<br>versagt %{customdata}<extra>Lauf " + str(run) + "</extra>"
    )


def merit_history_figure(
    history: list[dict[str, Any]],
    best: int | None = None,
    runs_info: list[dict] | None = None,
    cycles_per_round: int | None = None,
) -> go.Figure:
    """Merit über den Zyklen jedes Laufs (logarithmisch, über alle Strafrunden), Läufe
    übereinander. Dreiecke markieren Neustarts mit zehnfachem Strafgewicht (siehe
    :func:`restart_indices`; ``runs_info`` und ``cycles_per_round`` machen sie exakt)."""
    rounds = {int(r["run"]): r.get("penalty_rounds") for r in runs_info or []}
    runs = runs_of(history)
    best = best_run(history, best)
    fig = go.Figure()
    many = len(runs) > MAX_COLORED_RUNS
    if many:
        for failed, color, label in (
            (False, OTHER_COLOR, "übrige Läufe"),
            (True, FAILED_COLOR, "Läufe mit versagten Strahlen am Ende"),
        ):
            members = [
                r for r, rows in runs.items() if r != best and ends_with_failed_rays(rows) == failed
            ]
            if not members:
                continue
            xs: list[Any] = []
            ys: list[Any] = []
            for run in members:
                xs += [h["Zyklus"] for h in runs[run]] + [None]
                ys += [_positive(h["merit"]) for h in runs[run]] + [None]
            fig.add_trace(
                go.Scatter(
                    x=xs, y=ys, mode="lines", hoverinfo="skip", name=f"{label} ({len(members)})",
                    line={"color": color, "width": 1, "dash": "dot" if failed else "solid"},
                )
            )  # fmt: skip
    shown = [best] if many else list(runs)
    for run in shown:
        if run is None:
            continue
        rows = runs[run]
        is_best = run == best
        fig.add_trace(
            go.Scatter(
                x=[h["Zyklus"] for h in rows],
                y=[_positive(h["merit"]) for h in rows],
                customdata=[h.get("versagt") for h in rows],
                mode="lines+markers",
                marker={"size": 4},
                line={"width": 3 if many else 2, **({"color": BEST_COLOR} if many else {})},
                name=f"bester Lauf {run}" if is_best and many else f"Lauf {run}",
                hovertemplate=_hover(run),
            )
        )
    restarts = [
        runs[r][i]
        for r in shown
        if r is not None
        for i in restart_indices(runs[r], cycles_per_round, rounds.get(r))
    ]
    if restarts:
        fig.add_trace(
            go.Scatter(
                x=[h["Zyklus"] for h in restarts],
                y=[_positive(h["merit"]) for h in restarts],
                mode="markers",
                marker={"symbol": "triangle-up", "size": 10, "color": RESTART_COLOR},
                name="Neustart: Strafgewicht × 10",
                hovertemplate="Zyklus %{x}: neue Strafrunde (Strahlen versagt)<extra></extra>",
            )
        )
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
    y_range = _y_range(history)
    fig.update_yaxes(type="log", title_text="Merit", range=y_range)
    fig.update_xaxes(title_text="Zyklus im Lauf (über alle Strafrunden)")
    fig.update_layout(
        height=360, margin={"l": 60, "r": 20, "t": 20, "b": 40},
        legend={"orientation": "h", "y": -0.25},
    )  # fmt: skip
    return fig


def run_summary_figure(
    history: list[dict[str, Any]], best: int | None = None, runs_info: list[dict] | None = None
) -> go.Figure:
    """Endmerit pro Lauf (logarithmisch). Hohl: Lauf endet mit versagten Strahlen (Merit enthält
    Strafe, nicht vergleichbar). ``runs_info`` (``OptimizeResult.runs``) liefert die genauen
    Endwerte und Strafrunden, sonst der Verlauf."""
    runs = runs_of(history)
    best = best_run(history, best)
    info = {int(r["run"]): r for r in runs_info or []}
    rows = []
    for run in sorted(set(runs) | set(info)):
        if run in info:
            merit, failed = (
                _positive(info[run].get("merit")),
                int(info[run].get("failed_rays") or 0),
            )
            rounds = info[run].get("penalty_rounds")
        else:
            merit, failed, rounds = (
                _positive(runs[run][-1]["merit"]),
                int(runs[run][-1].get("versagt") or 0),
                None,
            )
        rows.append((run, merit, failed, rounds))
    fig = go.Figure()
    groups = (
        (False, "ohne versagte Strahlen", "circle"),
        (True, "mit versagten Strahlen (Merit mit Strafe)", "circle-open"),
    )
    for failed, label, symbol in groups:
        sel = [r for r in rows if (r[2] > 0) == failed]
        if not sel:
            continue
        fig.add_trace(
            go.Scatter(
                x=[r[0] for r in sel], y=[r[1] for r in sel], mode="markers", name=label,
                marker={"size": 8, "symbol": symbol, "color": "#e76f51" if failed else "#2f6690"},
                customdata=[[r[2], r[3] if r[3] is not None else "–"] for r in sel],
                hovertemplate="Lauf %{x}<br>Endmerit %{y:.6g}<br>versagt %{customdata[0]}"
                "<br>Strafrunden %{customdata[1]}<extra></extra>",
            )
        )  # fmt: skip
    if best is not None:
        merit = next((r[1] for r in rows if r[0] == best), None)
        fig.add_trace(
            go.Scatter(
                x=[best], y=[merit], mode="markers", name=f"bester Lauf {best}",
                marker={"size": 15, "symbol": "star", "color": BEST_COLOR},
            )
        )  # fmt: skip
    fig.update_yaxes(type="log", title_text="Endmerit")
    fig.update_xaxes(title_text="Lauf", dtick=max(1, len(rows) // 10))
    fig.update_layout(
        height=360, margin={"l": 60, "r": 20, "t": 20, "b": 40},
        legend={"orientation": "h", "y": -0.25},
    )  # fmt: skip
    return fig
