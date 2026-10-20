"""G3-T3 gegen ein installiertes Mikroptim (``python -m pytest -m integration``)."""

import hashlib
import json
import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import needs_uploader
from gui_mikroptim.backend import compute, mko, optimize_run
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


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_saved_result_reproduces_final_merit(repo, workspace):
    source = repo / "data" / "systems" / NAME
    before = _sha(source)
    out = optimize_run.run_optimize(compute.load_system(source), OptimizeOptions())
    saved = optimize_run.save_result(out.result, workspace, "../../biegung optimiert")
    assert saved.parent == (workspace / "ergebnisse").resolve()
    assert saved.name == "biegung_optimiert.json"
    # lädt mit mikroptim trace (Glaskataloge relativ zur neuen Datei)
    code, _, err = mko.require().run_cli(["trace", str(saved), "--json"])
    assert code == 0, err
    # Endmerit reproduziert: Auswertung des gespeicherten Systems ohne Zyklen
    code, text, err = mko.require().run_cli(
        ["optimize", str(saved), "--json", "--quiet", "--max-iterations", "0"]
    )
    assert code == 0, err
    assert json.loads(text)["result"]["start_merit"] == out.result.merit
    assert _sha(source) == before  # Eingabe unverändert
    again = optimize_run.save_result(out.result, workspace, "biegung optimiert.json")
    assert again.name == "biegung_optimiert-2.json"  # nie überschrieben


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
def test_page_before_after_and_save(app_file, workspace, repo):
    source = repo / "data" / "systems" / NAME
    before = _sha(source)
    at = _page(app_file)
    at.button(key="optimierung.start").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert "optimierung.vorher_nachher" in [c.key for c in at.get("plotly_chart")]
    metrics = {m.label: m for m in at.metric}
    assert float(metrics["RMS max nachher"].value) < float(metrics["RMS max vorher"].value)
    assert (
        at.text_input(key="optimierung.dateiname").value == "einzellinse_bk7_biegung-optimiert.json"
    )

    at.button(key="optimierung.speichern").click().run()
    assert not at.exception, [e.value for e in at.exception]
    saved = workspace / "ergebnisse" / "einzellinse_bk7_biegung-optimiert.json"
    assert saved.is_file()
    assert any("Gespeichert als ergebnisse/" in s.value for s in at.success)
    assert at.session_state["aktuell.datei"] == str(saved.resolve())
    assert at.selectbox(key="optimierung.quelle").value.label == "Ergebnisse"
    assert _sha(source) == before

    # das gespeicherte System ist sofort wieder optimierbar; die Endmerit bleibt erhalten
    at.number_input(key="optimierung.zyklen").set_value(0).run()
    at.button(key="optimierung.start").click().run()
    first = json.loads(mko.require().run_cli(["optimize", str(source), "--json", "--quiet"])[1])[
        "result"
    ]["merit"]
    assert at.session_state["optimierung.lauf"]["result"].start_merit == first


@needs_uploader
def test_save_without_adopting(app_file, workspace, repo):
    at = _page(app_file)
    at.button(key="optimierung.start").click().run()
    at.checkbox(key="optimierung.uebernehmen").uncheck().run()
    at.text_input(key="optimierung.dateiname").set_value("anders.json").run()
    at.button(key="optimierung.speichern").click().run()
    assert (workspace / "ergebnisse" / "anders.json").is_file()
    assert at.session_state["aktuell.datei"].endswith(NAME)
    assert any("anders.json" in s.value for s in at.success)
