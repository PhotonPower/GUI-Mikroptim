"""G3-T1 gegen ein installiertes Mikroptim (``python -m pytest -m integration``)."""

import json
import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import needs_uploader
from gui_mikroptim.backend import compute, mko
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


@pytest.mark.parametrize(
    "options",
    [
        OptimizeOptions(max_iterations=5),
        OptimizeOptions(max_iterations=5, rings=4, spokes=6, runs=3, perturbation=0.1, seed=3),
        OptimizeOptions(max_iterations=5, jacobian="adjoint", fail_weight=2.0),
    ],
)
def test_cli_args_and_kwargs_agree(repo, options):
    """CLI-Argumente und Python-Argumente ergeben in Mikroptim dasselbe Ergebnis (bitgleich)."""
    path = repo / "data" / "systems" / NAME
    m = mko.require()
    result = m.optimize(compute.load_system(path), **options.kwargs())
    code, out, err = m.run_cli(["optimize", str(path), "--json", "--quiet", *options.cli_args()])
    assert code == 0, err
    cli = json.loads(out)
    assert cli["result"]["merit"] == result.merit
    assert cli["result"]["start_merit"] == result.start_merit
    assert (cli["result"]["status"], cli["result"]["iterations"]) == (
        result.status,
        result.iterations,
    )


def _page(app_file):
    at = AppTest.from_file(str(app_file), default_timeout=60).run()
    at.switch_page("pages/optimierung.py").run()
    source = at.selectbox(key="optimierung.quelle")
    source.select_index(source.options.index(EXAMPLES)).run()
    box = at.selectbox(key=f"optimierung.datei.{EXAMPLES}")
    box.select_index(box.options.index(NAME)).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _command(at) -> str:
    return next(c.value for c in at.caption if c.value.startswith("Entspricht:"))


@needs_uploader
def test_form_produces_expected_arguments(app_file, workspace, repo):
    at = _page(app_file)
    table = at.dataframe[0].value
    assert list(table["Name"]) == ["c[1]", "c[2]", "w"]
    assert _command(at) == f"Entspricht: `mikroptim optimize {NAME} --json `"
    assert at.number_input(key="optimierung.seed").disabled  # nur mit Multistart
    assert at.number_input(key="optimierung.gewicht").disabled
    assert not [t for t in at.toggle if t.key == "optimierung.gpu"]  # CPU-Build: keine GPU

    at.number_input(key="optimierung.zyklen").set_value(20).run()
    at.number_input(key="optimierung.laeufe").set_value(4).run()
    assert not at.number_input(key="optimierung.seed").disabled
    at.number_input(key="optimierung.seed").set_value(7).run()
    at.radio(key="optimierung.jacobi").set_value("adjoint").run()
    at.toggle(key="optimierung.eigenes_gewicht").set_value(True).run()
    at.number_input(key="optimierung.gewicht").set_value(2.5).run()
    expected = OptimizeOptions(
        max_iterations=20, runs=4, seed=7, jacobian="adjoint", fail_weight=2.5
    ).cli_args()
    assert _command(at) == f"Entspricht: `mikroptim optimize {NAME} --json {' '.join(expected)}`"

    at.toggle(key="optimierung.hart").set_value(True).run()  # sperrt das Strafgewicht
    assert at.toggle(key="optimierung.eigenes_gewicht").disabled
    assert "--hard-failure" in _command(at) and "--fail-weight" not in _command(at)


@needs_uploader
def test_gpu_only_with_device(app_file, workspace, repo, monkeypatch):
    real = mko.status()
    fake = mko.MikroptimStatus(True, real.version, True, [{"index": 0, "name": "Test-GPU"}])
    monkeypatch.setattr(mko, "status", lambda module_name="mikroptim": fake)
    at = _page(app_file)
    at.toggle(key="optimierung.gpu").set_value(True).run()
    assert _command(at).endswith("--json --gpu`")


@needs_uploader
def test_glass_variables_fall_back_to_file(app_file, workspace, repo):
    at = AppTest.from_file(str(app_file), default_timeout=60).run()
    at.switch_page("pages/optimierung.py").run()
    source = at.selectbox(key="optimierung.quelle")
    source.select_index(source.options.index(EXAMPLES)).run()
    box = at.selectbox(key=f"optimierung.datei.{EXAMPLES}")
    box.select_index(box.options.index("achromat_glasvariablen.json")).run()
    assert not at.exception
    assert any("Variablen nicht auflösen" in w.value for w in at.warning)
