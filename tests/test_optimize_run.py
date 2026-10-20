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


def test_merit_history_figure():
    hist = [
        {"Lauf": 0, "Zyklus": 1, "merit": 0.5, "Versuchsmerit": 0.5, "angenommen": True},
        {"Lauf": 0, "Zyklus": 2, "merit": 0.5, "Versuchsmerit": 0.9, "angenommen": False},
        {"Lauf": 1, "Zyklus": 1, "merit": 0.2, "Versuchsmerit": 0.2, "angenommen": True},
    ]
    fig = merit_history_figure(hist)
    names = [t.name for t in fig.data]
    assert names == ["Lauf 0", "Lauf 1", "abgelehnter Versuch"]
    assert list(fig.data[1].x) == [3] and list(fig.data[2].y) == [0.9]
    assert fig.layout.yaxis.type == "log"
