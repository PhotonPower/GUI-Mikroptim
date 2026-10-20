"""Lauf von ``mikroptim.optimize`` mit Rückruf, Abbruch und Zeitgrenze (G3-T2).

Ohne Streamlit. Der Rückruf von Mikroptim liefert nach jedem LM-Zyklus ein dict (``run``,
``iteration``, ``merit``, ``trial_merit``, ``accepted``, ``damping``, ``failed_rays``, ``x`` …);
eine Ausnahme darin bricht die Optimierung ab (Mikroptim M9-T1). Ausnahmen, die nicht von hier
stammen (z. B. die Unterbrechung eines Streamlit-Laufs), werden unverändert durchgereicht.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gui_mikroptim.backend import jobs, mko
from gui_mikroptim.backend.optimize_options import OptimizeOptions

DONE, CANCELLED, TIME_LIMIT = "fertig", "abgebrochen", "Zeitgrenze"
RESULT_FILE = "ergebnis.json"


class _Stop(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass
class RunOutcome:
    """Ergebnis eines Laufs; ``result`` nur, wenn Mikroptim den Lauf beendet hat."""

    status: str
    history: list[dict[str, Any]] = field(default_factory=list)
    result: Any = None
    seconds: float = 0.0

    @property
    def best_merit(self) -> float | None:
        values = [h["merit"] for h in self.history if h.get("merit") is not None]
        finite = [v for v in values if math.isfinite(v)]
        return min(finite) if finite else None


def history_entry(info: dict[str, Any]) -> dict[str, Any]:
    """Zeile des Verlaufs aus dem Rückruf (ohne das Array ``x``)."""
    return {
        "Lauf": int(info.get("run", 0)),
        "Zyklus": int(info.get("iteration", 0)),
        "merit": float(info["merit"]) if info.get("merit") is not None else None,
        "Versuchsmerit": info.get("trial_merit"),
        "angenommen": bool(info.get("accepted", False)),
        "Dämpfung": info.get("damping"),
        "versagt": info.get("failed_rays"),
    }


def run_optimize(
    system: Any,
    options: OptimizeOptions,
    on_cycle: Callable[[dict[str, Any], list[dict[str, Any]]], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    time_limit_s: float | None = None,
) -> RunOutcome:
    """``mikroptim.optimize`` mit Verlauf; Abbruch über ``should_stop`` oder die Zeitgrenze.

    ``on_cycle(entry, history)`` wird nach jedem Zyklus aufgerufen (z. B. zum Anzeigen); was
    es wirft, wird nicht abgefangen. Das übergebene System bleibt unverändert.
    """
    m = mko.require()
    kwargs = options.kwargs()
    history: list[dict[str, Any]] = []
    start = time.monotonic()

    def callback(info: dict[str, Any]) -> None:
        entry = history_entry(info)
        history.append(entry)
        if on_cycle is not None:
            on_cycle(entry, history)
        if should_stop is not None and should_stop():
            raise _Stop(CANCELLED)
        if time_limit_s is not None and time.monotonic() - start >= time_limit_s:
            raise _Stop(TIME_LIMIT)

    try:
        result = m.optimize(system, callback=callback, **kwargs)
    except _Stop as stop:
        return RunOutcome(stop.reason, history, None, time.monotonic() - start)
    return RunOutcome(DONE, history, result, time.monotonic() - start)


def submit_optimize_job(
    workspace: Path,
    system_path: Path,
    options: OptimizeOptions,
    max_jobs: int,
    allowed_roots: list[Path],
    cli: Path | None = None,
) -> jobs.Job:
    """Dieselbe Optimierung als Job (für Läufe über der Zeitgrenze, ADR-0003)."""
    from gui_mikroptim.backend.synth_job import copy_system_with_catalogs

    argv = jobs.mikroptim_argv(
        cli, ["optimize", "{eingabe:0}", *options.cli_args(), "--json", "-o", RESULT_FILE]
    )
    return jobs.submit(
        workspace,
        "optimize",
        argv,
        max_jobs,
        inputs=[system_path],
        allowed_roots=allowed_roots,
        options={"optimize": options.to_dict(), "system": system_path.name},
        mikroptim_version=mko.status().version,
        copy_system=copy_system_with_catalogs,
    )


RESULTS_SUBDIR = "ergebnisse"


def default_result_name(source: Path) -> str:
    return f"{source.stem}-optimiert.json"


def save_result(result: Any, workspace: Path, filename: str) -> Path:
    """Speichert ``OptimizeResult.system`` als neue Datei unter ``ergebnisse/`` (G3-T3).

    Der Name wird bereinigt und nie überschrieben (``name-2.json`` …); ``System.save`` schreibt
    die Glaskatalog-Pfade relativ zur neuen Datei. Die Eingabedatei bleibt unverändert.
    """
    from gui_mikroptim.backend import files

    name = files.safe_filename(filename)
    if not name.lower().endswith(".json"):
        name += ".json"
    directory = files.resolve_inside(workspace, RESULTS_SUBDIR)
    directory.mkdir(parents=True, exist_ok=True)
    target = files.unique_path(directory, name)
    # Platz sofort belegen, damit ein gleichzeitiger zweiter Aufruf nicht denselben Namen nimmt
    with target.open("x", encoding="utf-8"):
        pass
    try:
        result.system.save(str(target))
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return target
