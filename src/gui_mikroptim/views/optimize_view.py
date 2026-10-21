"""Seite „Optimierung“: Variablen und Optionen (G3-T1); Lauf und Ergebnis folgen (G3-T2, T3)."""

from __future__ import annotations

from typing import Any

import streamlit as st

from gui_mikroptim.backend import compute, mko, system_tables
from gui_mikroptim.backend.files import FileEntry
from gui_mikroptim.backend.optimize_options import JACOBIANS, OptimizeOptions
from gui_mikroptim.views import common
from gui_mikroptim.views.wavefront_view import gpu_inputs

KEY = "optimierung"


def variables_section(system: Any) -> None:
    info = compute.details(system)
    st.markdown("**Variablen**")
    if info.variables_error:
        st.warning(
            f"Mikroptim kann die Variablen nicht auflösen: {info.variables_error}. "
            "`mikroptim optimize` wandelt Glasvariablen erst beim Start um; angezeigt wird der "
            "Abschnitt `variables` der Datei."
        )
        st.json(info.data.get("variables") or {})
    elif not info.variables:
        st.info("Das System hat keine Variablen; eine Optimierung ändert nichts.")
    else:
        st.dataframe(system_tables.variable_rows(info.variables), hide_index=True, width="stretch")
    constraints = info.data.get("constraints")
    if constraints:
        with st.expander("Nebenbedingungen"):
            st.json(constraints)


def options_form(status: mko.MikroptimStatus) -> OptimizeOptions:
    """Einstellungen mit den Standardwerten von Mikroptim; ungültige Kombinationen sind gesperrt."""
    d = OptimizeOptions()
    c1, c2, c3, c4 = st.columns(4)
    max_iterations = c1.number_input(
        "Zyklen pro Lauf", 0, 100000, d.max_iterations, key=f"{KEY}.zyklen",
        help="0: nur den Startpunkt auswerten",
    )  # fmt: skip
    rings = c2.number_input("Ringe", 1, 256, d.rings, key=f"{KEY}.ringe")
    spokes = c3.number_input("Speichen", 1, 256, d.spokes, key=f"{KEY}.speichen")
    jacobian = c4.radio("Jacobi-Matrix", list(JACOBIANS), horizontal=True, key=f"{KEY}.jacobi")

    c1, c2, c3 = st.columns(3)
    runs = c1.number_input("Läufe (Multistart)", 1, 1000, d.runs, key=f"{KEY}.laeufe")
    multistart = runs >= 2
    perturbation = c2.number_input(
        "relative Störung", 0.0, 10.0, d.perturbation, 0.01, key=f"{KEY}.stoerung",
        disabled=not multistart, help="nur mit mindestens 2 Läufen",
    )  # fmt: skip
    seed = c3.number_input(
        "Seed", 0, 2**31 - 1, d.seed, key=f"{KEY}.seed", disabled=not multistart,
        help="nur mit mindestens 2 Läufen; gleicher Seed ergibt dasselbe Ergebnis",
    )  # fmt: skip

    c1, c2, c3, c4 = st.columns(4)
    hard = c1.toggle("hartes Strahlversagen", value=False, key=f"{KEY}.hart")
    own_weight = c2.toggle(
        "eigenes Strafgewicht", value=False, key=f"{KEY}.eigenes_gewicht", disabled=hard,
        help="nur beim weichen Strahlversagen",
    )  # fmt: skip
    weight = c3.number_input(
        "w_fail [Wellen²]", 1e-9, 1e9, 1.0, format="%.4g", key=f"{KEY}.gewicht",
        disabled=hard or not own_weight,
    )  # fmt: skip
    gpu, device, _ = gpu_inputs(status, c4, c4, KEY, with_precision=False)
    return OptimizeOptions(
        max_iterations=int(max_iterations),
        rings=int(rings),
        spokes=int(spokes),
        runs=int(runs),
        perturbation=float(perturbation),
        seed=int(seed),
        fail_weight=float(weight) if own_weight and not hard else None,
        hard_failure=bool(hard),
        gpu=gpu,
        device=device,
        jacobian=str(jacobian),
    )


def command_caption(entry: FileEntry, options: OptimizeOptions) -> None:
    args = " ".join(options.cli_args())
    st.caption(
        f"Entspricht: `mikroptim optimize {entry.path.name} --json {args}`".replace("  ", " ")
    )


# --- Lauf (G3-T2) ------------------------------------------------------------------------------

RUN_STATE = f"{KEY}.lauf"
STOP_FLAG = f"{KEY}.stopp"
#: höchstens so oft pro Sekunde wird die Anzeige während des Laufs erneuert
REFRESH_INTERVAL_S = 0.25


def _run_key(entry: FileEntry, options: OptimizeOptions) -> str:
    return f"{entry.path}|{entry.mtime}|{entry.size}|{options!r}"


def _request_stop() -> None:
    st.session_state[STOP_FLAG] = True


def _show_progress(placeholders, history) -> None:
    from gui_mikroptim.views.optimize_plots import merit_history_figure

    metrics, chart = placeholders
    last = history[-1]
    best = min((h["merit"] for h in history if h["merit"] is not None), default=None)
    with metrics.container():
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Lauf", last["Lauf"])
        c2.metric("Zyklus", last["Zyklus"])
        c3.metric("Merit", f"{last['merit']:.6g}" if last["merit"] is not None else "–")
        c4.metric("beste Merit", f"{best:.6g}" if best is not None else "–")
    common.chart(merit_history_figure(history), key=f"{KEY}.live.{len(history)}", container=chart)


def run_section(cfg, entry: FileEntry, system: Any, options: OptimizeOptions) -> None:
    """Starten, Live-Verlauf, Abbruch, Zeitgrenze; das Ergebnis bleibt in der Sitzung."""
    import time

    from gui_mikroptim.backend import optimize_run
    from gui_mikroptim.views.optimize_plots import merit_history_figure

    key = _run_key(entry, options)
    state = st.session_state.get(RUN_STATE)
    if state is not None and state.get("status") == "läuft":
        # Der vorige Lauf wurde unterbrochen: durch „Abbrechen“ oder eine andere Eingabe
        stopped = st.session_state.pop(STOP_FLAG, False)
        state["status"] = optimize_run.CANCELLED
        state["note"] = (
            "Abgebrochen." if stopped else "Durch eine Eingabe auf der Seite unterbrochen."
        )
    st.session_state.pop(STOP_FLAG, None)

    c1, c2 = st.columns([1, 3])
    limit = c1.number_input(
        "Zeitgrenze [s]", 1, 86400, 60, key=f"{KEY}.zeitgrenze",
        help="Danach bricht die Seite ab und bietet an, die Optimierung als Job zu rechnen.",
    )  # fmt: skip
    start = c2.button("Optimierung starten", type="primary", key=f"{KEY}.start")

    if start:
        state = {"key": key, "status": "läuft", "history": [], "result": None, "seconds": 0.0}
        st.session_state[RUN_STATE] = state
        st.button("Abbrechen", key=f"{KEY}.abbrechen", on_click=_request_stop)
        placeholders = (st.empty(), st.empty())
        last_draw = [0.0]

        def on_cycle(entry_row, history):
            state["history"] = history  # bleibt bei einer Unterbrechung erhalten
            now = time.monotonic()
            if now - last_draw[0] >= REFRESH_INTERVAL_S:
                last_draw[0] = now
                _show_progress(placeholders, history)

        try:
            outcome = optimize_run.run_optimize(
                system,
                options,
                on_cycle=on_cycle,
                should_stop=lambda: bool(st.session_state.get(STOP_FLAG)),
                time_limit_s=float(limit),
            )
        except Exception as exc:  # Fehler von Mikroptim (GPU, Optionen); Unterbrechungen nicht
            error = compute.load_error(exc)
            state.update(status="fehler", note=f"{error.kind}: {error.message}")
        else:
            state.update(
                status=outcome.status,
                history=outcome.history,
                result=outcome.result,
                seconds=outcome.seconds,
                note=None,
            )
        for placeholder in placeholders:
            placeholder.empty()

    saved = st.session_state.pop(f"{KEY}.gespeichert", None)
    if saved:
        st.success(saved)  # vor der Prüfung: nach der Übernahme gehört das Ergebnis zur alten Datei
    state = st.session_state.get(RUN_STATE)
    if state is None:
        return
    if state["key"] != key:
        st.caption("Das letzte Ergebnis gehört zu einer anderen Datei oder anderen Optionen.")
        return
    _show_outcome(cfg, entry, options, state, merit_history_figure)


def _show_outcome(cfg, entry, options, state, merit_history_figure) -> None:
    from gui_mikroptim.backend import jobs, optimize_run

    status = state["status"]
    history = state["history"]
    result = state["result"]
    if status == optimize_run.DONE and result is not None:
        st.success(
            f"Optimierung beendet: Status `{result.status}`, {result.iterations} Zyklen, "
            f"{state['seconds']:.1f} s."
        )
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Merit Start", f"{result.start_merit:.6g}")
        c2.metric("Merit Ende", f"{result.merit:.6g}")
        c3.metric("Läufe", len(result.runs) if hasattr(result.runs, "__len__") else result.runs)
        c4.metric("bester Lauf", result.best_run)
        names = list(result.variable_names)
        st.dataframe(
            [
                {"Variable": n, "Start": float(a), "Ende": float(b), "Änderung": float(b - a)}
                for n, a, b in zip(names, result.x0, result.x, strict=True)
            ],
            hide_index=True,
            width="stretch",
        )
        for warning in result.warnings:
            st.warning(warning)
        _before_after(entry, options, result)
        _save(cfg, entry, result)
    elif status == optimize_run.TIME_LIMIT:
        st.warning(
            f"Zeitgrenze erreicht nach {len(history)} Zyklen; das System ist unverändert. "
            "Längere Läufe als Job rechnen:"
        )
        if st.button("Als Job rechnen", key=f"{KEY}.job"):
            try:
                job = optimize_run.submit_optimize_job(
                    cfg.workspace, entry.path, options, cfg.max_jobs, cfg.read_roots, cfg.cli
                )
            except (ValueError, jobs.JobError) as exc:
                st.error(f"Job nicht angelegt: {exc}")
            else:
                st.session_state["jobs.auswahl_neu"] = job.id
                st.success(f"Job {job.id} angelegt; Verlauf auf der Seite „Jobs und Synthese“.")
    elif status == optimize_run.CANCELLED:
        st.info(
            f"{state.get('note') or 'Abgebrochen.'} {len(history)} Zyklen gerechnet; das "
            "System ist unverändert."
        )
    elif status == "fehler":
        st.error(state.get("note") or "Fehler")
    if history:
        common.download_csv(history, f"{entry.path.stem}_verlauf", f"{KEY}.csv.verlauf")
        common.chart(merit_history_figure(history), key=f"{KEY}.verlauf")


# --- Ergebnis: Vorher/Nachher und Speichern (G3-T3) --------------------------------------------


def _before_after(entry: FileEntry, options: OptimizeOptions, result: Any) -> None:
    """RMS-Wellenfront vorher (Datei) und nachher (``result.system``) mit derselben Quadratur."""
    from gui_mikroptim.backend import compare
    from gui_mikroptim.views.system_view import cached_system
    from gui_mikroptim.views.wavefront_plots import (
        field_labels,
        rms_difference_heatmap,
        wavelength_labels,
    )

    trace = compute.TraceOptions(options.rings, options.spokes, options.gpu, options.device)
    try:
        before_system = cached_system(str(entry.path), entry.mtime, entry.size)
        before = compute.trace_wavefront(before_system, trace)
        after = compute.trace_wavefront(result.system, trace)
    except Exception as exc:  # z. B. afokal
        error = compute.load_error(exc)
        st.warning(f"Wellenfront vorher/nachher nicht verfügbar: {error.kind}: {error.message}")
        return
    st.markdown(
        f"**RMS-Wellenfront vorher → nachher** (Wellen bei λ_ref, {trace.rings} × {trace.spokes})"
    )
    finite = lambda a: a[a == a]  # noqa: E731 - NaN entfernen
    c1, c2 = st.columns(2)
    b, a = finite(before.rms_waves), finite(after.rms_waves)
    c1.metric("RMS max vorher", f"{b.max():.4g}" if b.size else "–")
    c2.metric(
        "RMS max nachher",
        f"{a.max():.4g}" if a.size else "–",
        delta=f"{a.max() - b.max():+.4g}" if a.size and b.size else None,
        delta_color="inverse",
    )
    diff = compare.rms_difference(before, after)
    common.chart(
        rms_difference_heatmap(
            diff,
            field_labels(diff.shape[0], before_system.field_angles_deg),
            wavelength_labels(before_system.wavelengths_nm, before_system.reference_nm),
        ),
        key=f"{KEY}.vorher_nachher",
    )
    with st.expander("Tabelle vorher/nachher"):
        st.dataframe(
            compare.rms_compare_rows(
                before, after, before_system.field_angles_deg, before_system.wavelengths_nm
            ),
            hide_index=True,
            width="stretch",
        )


def _save(cfg, entry: FileEntry, result: Any) -> None:
    from gui_mikroptim.backend import optimize_run
    from gui_mikroptim.views import current, file_picker

    st.markdown("**Ergebnis speichern**")
    c1, c2, c3 = st.columns([3, 2, 1])
    name = c1.text_input(
        "Dateiname unter ergebnisse/",
        value=optimize_run.default_result_name(entry.path),
        key=f"{KEY}.dateiname",
    )
    adopt = c2.checkbox("als aktuelles System übernehmen", value=True, key=f"{KEY}.uebernehmen")
    if c3.button("Speichern", key=f"{KEY}.speichern"):
        try:
            target = optimize_run.save_result(result, cfg.workspace, name)
        except Exception as exc:
            error = compute.load_error(exc)
            st.error(f"Nicht gespeichert: {error.kind}: {error.message}")
            return
        text = f"Gespeichert als ergebnisse/{target.name}; die Eingabe bleibt unverändert."
        if adopt:
            current.set_path(target)
            file_picker.select_on_next_run(KEY, target, remember=True)
            text += " Jetzt aktuelles System."
        st.session_state[f"{KEY}.gespeichert"] = text
        st.rerun()
