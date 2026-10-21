"""G3-T2: Lauf mit Rückruf, Abbruch und Zeitgrenze (mit einem Ersatz für mikroptim.optimize)."""

import types

import pytest

from gui_mikroptim.backend import mko, optimize_run
from gui_mikroptim.backend.optimize_options import OptimizeOptions
from gui_mikroptim.views.optimize_plots import merit_history_figure


def _fake(monkeypatch, cycles=5, runs=1):
    calls = {}

    def optimize(system, callback=None, **kwargs):
        calls["kwargs"] = kwargs
        n = 0
        for run in range(runs):
            for i in range(1, cycles + 1):
                n += 1
                merit = 1.0 / (n + 1)
                info = {"run": run, "iteration": i, "merit": merit, "accepted": i != 2}
                info.update(trial_merit=2.0 if i == 2 else merit, damping=0.1, failed_rays=0)
                callback({**info, "x": [n]})
        return types.SimpleNamespace(status="max_iterations", merit=0.01)

    monkeypatch.setattr(
        mko, "require", lambda name="mikroptim": types.SimpleNamespace(optimize=optimize)
    )
    return calls


def test_run_to_end(monkeypatch):
    calls = _fake(monkeypatch, cycles=4, runs=2)
    seen = []
    out = optimize_run.run_optimize(
        object(), OptimizeOptions(runs=2, seed=3), on_cycle=lambda e, h: seen.append(len(h))
    )
    assert out.status == optimize_run.DONE and out.result.merit == 0.01
    assert len(out.history) == 8 and seen == list(range(1, 9))
    assert out.history[0] == {"Lauf": 0, "Zyklus": 1, "merit": 0.5, "Versuchsmerit": 0.5,
                              "angenommen": True, "Dämpfung": 0.1, "versagt": 0}  # fmt: skip
    assert calls["kwargs"]["runs"] == 2 and calls["kwargs"]["seed"] == 3
    assert out.best_merit == pytest.approx(1 / 9)


def test_cancel(monkeypatch):
    _fake(monkeypatch, cycles=10)
    flag = {"stop": False}

    def on_cycle(entry, history):
        if len(history) == 3:
            flag["stop"] = True

    out = optimize_run.run_optimize(object(), OptimizeOptions(), on_cycle, lambda: flag["stop"])
    assert out.status == optimize_run.CANCELLED and len(out.history) == 3 and out.result is None


def test_time_limit(monkeypatch):
    _fake(monkeypatch, cycles=10)
    out = optimize_run.run_optimize(object(), OptimizeOptions(), time_limit_s=0.0)
    assert out.status == optimize_run.TIME_LIMIT and len(out.history) == 1


def test_foreign_exceptions_pass_through(monkeypatch):
    """Unterbrechungen von Streamlit (BaseException) dürfen nicht abgefangen werden."""
    _fake(monkeypatch)

    class Interrupt(BaseException):
        pass

    def on_cycle(entry, history):
        raise Interrupt

    with pytest.raises(Interrupt):
        optimize_run.run_optimize(object(), OptimizeOptions(), on_cycle)


def _history(runs: int, cycles: int = 3):
    rows = []
    for run in range(runs):
        for i in range(1, cycles + 1):
            merit = (run + 1) * 0.1 / i
            rows.append({"Lauf": run, "Zyklus": i, "merit": merit, "Versuchsmerit": merit * 2,
                         "angenommen": i != 2})  # fmt: skip
    return rows


def test_merit_history_few_runs_colored():
    fig = merit_history_figure(_history(2))
    assert [t.name for t in fig.data] == ["Lauf 0", "Lauf 1", "abgelehnter Versuch"]
    assert list(fig.data[1].x) == [1, 2, 3]  # Läufe übereinander ab Zyklus 1
    assert len(fig.data[2].x) == 2  # abgelehnte Versuche beider Läufe
    assert fig.layout.yaxis.type == "log"


def test_merit_history_many_runs_stays_readable():
    fig = merit_history_figure(_history(40))
    names = [t.name for t in fig.data]
    assert names == ["übrige Läufe (39)", "bester Lauf 0", "abgelehnter Versuch (bester Lauf)"]
    grey = fig.data[0]
    assert grey.x.count(None) == 39  # eine Kurve, Läufe durch Lücken getrennt
    assert len(fig.data[2].x) == 1  # Kreuze nur für den besten Lauf


def test_run_summary():
    from gui_mikroptim.views.optimize_plots import best_run, final_merits, run_summary_figure

    hist = _history(5)
    assert final_merits(hist)[4] == pytest.approx(0.5 / 3)
    assert best_run(hist) == 0
    fig = run_summary_figure(hist)
    assert list(fig.data[0].x) == [0, 1, 2, 3, 4]
    assert fig.data[1].name == "bester Lauf 0" and fig.data[1].x == (0,)
    assert best_run([]) is None


def _penalty_history():
    """Lauf 0: zwei Strafrunden, endet ohne versagte Strahlen; Lauf 1: endet mit versagten."""
    rows = []
    for i, (merit, failed) in enumerate([(1e4, 5), (5e3, 5), (5e4, 2), (2e2, 0), (1.0, 0)], 1):
        rows.append({"Lauf": 0, "Zyklus": i, "merit": merit, "Versuchsmerit": merit,
                     "angenommen": True, "versagt": failed})  # fmt: skip
    for i, (merit, failed) in enumerate([(1e4, 9), (1e5, 9), (1e9, 9), (1e12, 9)], 1):
        rows.append({"Lauf": 1, "Zyklus": i, "merit": merit, "Versuchsmerit": merit,
                     "angenommen": True, "versagt": failed})  # fmt: skip
    for run in (2, 3, 4):
        for i in range(1, 4):
            rows.append({"Lauf": run, "Zyklus": i, "merit": 10.0 / i, "Versuchsmerit": 10.0 / i,
                         "angenommen": True, "versagt": 0})  # fmt: skip
    return rows


def test_restarts_and_failed_runs():
    from gui_mikroptim.views import optimize_plots as op

    hist = _penalty_history()
    runs = op.runs_of(hist)
    assert op.restart_indices(runs[0]) == [2]  # Merit steigt: neue Strafrunde
    assert op.restart_indices(runs[1]) == [1, 2, 3]
    assert not op.ends_with_failed_rays(runs[0]) and op.ends_with_failed_rays(runs[1])
    # bester Lauf nur unter Läufen ohne versagte Strahlen, Mikroptims Wahl hat Vorrang
    assert op.best_run(hist) == 0
    assert op.best_run(hist, preferred=3) == 3
    fig = op.merit_history_figure(hist)
    names = [t.name for t in fig.data]
    assert names[:3] == [
        "übrige Läufe (3)",
        "Läufe mit versagten Strahlen am Ende (1)",
        "bester Lauf 0",
    ]
    assert "Neustart: Strafgewicht × 10" in names
    restart = next(t for t in fig.data if t.name.startswith("Neustart"))
    assert list(restart.x) == [3]  # nur für den besten Lauf
    # y-Bereich nach den gültigen Läufen: 1e12 des versagten Laufs liegt außerhalb
    low, high = fig.layout.yaxis.range
    assert low < 0 < high < 12


def test_run_summary_marks_failed_runs():
    from gui_mikroptim.views import optimize_plots as op

    hist = _penalty_history()
    info = [{"run": 0, "merit": 1.0, "failed_rays": 0, "penalty_rounds": 2},
            {"run": 1, "merit": 1e12, "failed_rays": 9, "penalty_rounds": 9}]  # fmt: skip
    fig = op.run_summary_figure(hist, best=0, runs_info=info)
    names = [t.name for t in fig.data]
    assert names == [
        "ohne versagte Strahlen",
        "mit versagten Strahlen (Merit mit Strafe)",
        "bester Lauf 0",
    ]
    hollow = fig.data[1]
    assert list(hollow.x) == [1] and hollow.marker.symbol == "circle-open"
    assert list(hollow.customdata[0]) == [9, 9]


def test_restarts_exact_with_round_count():
    from gui_mikroptim.views import optimize_plots as op

    # drei volle Runden à 3 Zyklen; der Neustart bei Zyklus 7 senkt die Merit sofort
    merits = [9.0, 8.0, 7.0, 70.0, 60.0, 50.0, 40.0, 30.0, 20.0]
    rows = [{"Lauf": 0, "Zyklus": i + 1, "merit": m, "angenommen": True, "versagt": 0}
            for i, m in enumerate(merits)]  # fmt: skip
    assert op.restart_indices(rows) == [3]  # nur der Anstieg ist sichtbar
    assert op.restart_indices(rows, cycles_per_round=3, rounds=3) == [3, 6]  # exakt
    assert op.restart_indices(rows, cycles_per_round=4, rounds=3) == [3]  # nicht voll: Anstieg
