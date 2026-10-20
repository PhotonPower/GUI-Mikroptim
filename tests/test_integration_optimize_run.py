"""G3-T2 gegen ein installiertes Mikroptim (``python -m pytest -m integration``)."""

import json
import os
import time
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import needs_uploader
from gui_mikroptim.backend import compute, jobs, mko, optimize_run
from gui_mikroptim.backend.optimize_options import OptimizeOptions

pytestmark = pytest.mark.integration

REPO = os.environ.get("MKO_GUI_MIKROPTIM_REPO")
EXAMPLES = "Beispielsysteme (Mikroptim)"
NAME = "einzellinse_bk7_biegung.json"


@pytest.fixture
def repo(monkeypatch) -> Path:
    if not REPO:
        pytest.skip("MKO_GUI_MIKROPTIM_REPO nicht gesetzt")
    monkeypatch.setenv("MKO_GUI_MIKROPTIM_REPO", REPO)
    return Path(REPO)


def _cli(path, options):
    code, out, err = mko.require().run_cli(
        ["optimize", str(path), "--json", "--quiet", *options.cli_args()]
    )
    assert code == 0, err
    return json.loads(out)


@pytest.mark.parametrize("options", [OptimizeOptions(), OptimizeOptions(runs=3, seed=5)])
def test_run_identical_to_cli(repo, options):
    """Ergebnis gleich `mikroptim optimize` mit denselben Optionen (Merit bitgleich)."""
    path = repo / "data" / "systems" / NAME
    out = optimize_run.run_optimize(compute.load_system(path), options)
    assert out.status == optimize_run.DONE
    cli = _cli(path, options)
    assert out.result.merit == cli["result"]["merit"]
    assert out.result.iterations == cli["result"]["iterations"]
    assert len(out.history) >= out.result.iterations


def test_cancel_keeps_system_unchanged(repo):
    path = repo / "data" / "systems" / NAME
    system = compute.load_system(path)
    before = [v["value"] for v in system.variables()]
    stop = {"n": 0}

    def should_stop():
        stop["n"] += 1
        return stop["n"] >= 2

    out = optimize_run.run_optimize(system, OptimizeOptions(), should_stop=should_stop)
    assert out.status == optimize_run.CANCELLED and len(out.history) == 2
    assert [v["value"] for v in system.variables()] == before
    # danach ist das System voll nutzbar: dieselbe Optimierung läuft bis zum Ende
    again = optimize_run.run_optimize(system, OptimizeOptions())
    assert again.result.merit == _cli(path, OptimizeOptions())["result"]["merit"]


def _page(app_file):
    at = AppTest.from_file(str(app_file), default_timeout=120).run()
    at.switch_page("pages/optimierung.py").run()
    source = at.selectbox(key="optimierung.quelle")
    source.select_index(source.options.index(EXAMPLES)).run()
    box = at.selectbox(key=f"optimierung.datei.{EXAMPLES}")
    box.select_index(box.options.index(NAME)).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


@needs_uploader
def test_page_run(app_file, workspace, repo):
    at = _page(app_file)
    at.button(key="optimierung.start").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Optimierung beendet" in s.value for s in at.success)
    cli = _cli(repo / "data" / "systems" / NAME, OptimizeOptions())
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Merit Ende"] == f"{cli['result']['merit']:.6g}"
    assert at.session_state["optimierung.lauf"]["result"].merit == cli["result"]["merit"]
    assert "optimierung.verlauf" in [c.key for c in at.get("plotly_chart")]
    variables = at.dataframe[-1].value
    assert list(variables["Variable"]) == ["c[1]", "c[2]", "w"]

    # andere Optionen: das alte Ergebnis wird nicht als aktuelles gezeigt
    at.number_input(key="optimierung.zyklen").set_value(5).run()
    assert any("anderen Optionen" in c.value for c in at.caption)


@needs_uploader
def test_page_interrupted_run_shows_cancel(app_file, workspace, repo):
    """Ein Klick auf „Abbrechen“ unterbricht den Lauf (Streamlit startet die Seite neu); der
    Neustart findet den Zustand „läuft“ mit gesetztem Abbruch und meldet „Abgebrochen“."""
    at = _page(app_file)
    at.button(key="optimierung.start").click().run()
    state = at.session_state["optimierung.lauf"]
    state.update(status="läuft", result=None, history=state["history"][:2])
    at.session_state["optimierung.stopp"] = True
    at.run()
    assert not at.exception
    assert any("Abgebrochen. 2 Zyklen gerechnet" in i.value for i in at.info)


@needs_uploader
def test_time_limit_offers_job(app_file, workspace, repo):
    at = _page(app_file)
    at.button(key="optimierung.start").click().run()
    state = at.session_state["optimierung.lauf"]
    state.update(status=optimize_run.TIME_LIMIT, result=None)  # wie nach Zeitgrenze
    at.run()
    assert any("Zeitgrenze erreicht" in w.value for w in at.warning)
    at.button(key="optimierung.job").click().run()
    assert not at.exception, [e.value for e in at.exception]
    created = jobs.list_jobs(workspace)
    assert len(created) == 1 and created[0].data["kind"] == "optimize"
    deadline = time.monotonic() + 120
    while not jobs.load(created[0].path).final and time.monotonic() < deadline:
        time.sleep(0.2)
    done = jobs.load(created[0].path)
    assert done.status == jobs.DONE, done.tail(jobs.STDERR_FILE)
    assert (done.path / optimize_run.RESULT_FILE).is_file()
