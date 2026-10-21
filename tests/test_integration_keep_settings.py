"""G5-T4: Einstellungen bleiben über Seitenwechsel erhalten (Integration)."""

import os

import pytest
from streamlit.testing.v1 import AppTest

from conftest import needs_uploader

pytestmark = pytest.mark.integration

REPO = os.environ.get("MKO_GUI_MIKROPTIM_REPO")
EXAMPLES = "Beispielsysteme (Mikroptim)"


@pytest.fixture
def at(app_file, workspace, monkeypatch) -> AppTest:
    if not REPO:
        pytest.skip("MKO_GUI_MIKROPTIM_REPO nicht gesetzt")
    monkeypatch.setenv("MKO_GUI_MIKROPTIM_REPO", REPO)
    app = AppTest.from_file(str(app_file), default_timeout=120).run()
    app.switch_page("pages/system.py").run()
    source = app.selectbox(key="system.quelle")
    source.select_index(source.options.index(EXAMPLES)).run()
    box = app.selectbox(key=f"system.datei.{EXAMPLES}")
    box.select_index(box.options.index("testsystem_mehrlinser.json")).run()
    return app


def _away_and_back(app: AppTest, page: str) -> None:
    app.switch_page("pages/system.py").run()
    app.switch_page("pages/start.py").run()
    app.switch_page(page).run()
    assert not app.exception, [e.value for e in app.exception]


@needs_uploader
def test_evaluation_settings_kept(at):
    at.switch_page("pages/auswertung.py").run()
    at.number_input(key="auswertung.ringe").set_value(6).run()
    at.number_input(key="auswertung.eval.raster").set_value(256).run()
    at.toggle(key="auswertung.eval.halb").set_value(True).run()
    at.selectbox(key="auswertung.eval.referenz").set_value("vertex").run()
    at.selectbox(key="auswertung.eval.feld").set_value(2).run()
    at.selectbox(key="auswertung.eval.abzug").set_value("defocus").run()
    _away_and_back(at, "pages/auswertung.py")
    assert at.number_input(key="auswertung.ringe").value == 6
    assert at.number_input(key="auswertung.eval.raster").value == 256
    assert at.toggle(key="auswertung.eval.halb").value is True
    assert at.selectbox(key="auswertung.eval.referenz").value == "vertex"
    assert at.selectbox(key="auswertung.eval.feld").value == 2
    assert at.selectbox(key="auswertung.eval.abzug").value == "defocus"
    assert not at.warning or all("default value" not in w.value for w in at.warning)


@needs_uploader
def test_psf_settings_kept(at):
    at.switch_page("pages/auswertung.py").run()
    at.number_input(key="auswertung.psf.padding").set_value(6.0).run()
    at.number_input(key="auswertung.psf.ausschnitt").set_value(25.0).run()
    at.toggle(key="auswertung.psf.log").set_value(True).run()
    at.radio(key="auswertung.psf.modell").set_value("vektoriell").run()
    at.selectbox(key="auswertung.psf.polarisation").set_value("circular").run()
    _away_and_back(at, "pages/auswertung.py")
    assert at.number_input(key="auswertung.psf.padding").value == 6.0
    assert at.number_input(key="auswertung.psf.ausschnitt").value == 25.0
    assert at.toggle(key="auswertung.psf.log").value is True
    assert at.radio(key="auswertung.psf.modell").value == "vektoriell"
    assert at.selectbox(key="auswertung.psf.polarisation").value == "circular"


@needs_uploader
def test_optimization_settings_kept(at):
    at.switch_page("pages/optimierung.py").run()
    at.number_input(key="optimierung.zyklen").set_value(20).run()
    at.number_input(key="optimierung.laeufe").set_value(3).run()
    at.number_input(key="optimierung.seed").set_value(7).run()
    at.radio(key="optimierung.jacobi").set_value("adjoint").run()
    at.number_input(key="optimierung.zeitgrenze").set_value(120).run()
    _away_and_back(at, "pages/optimierung.py")
    assert at.number_input(key="optimierung.zyklen").value == 20
    assert at.number_input(key="optimierung.laeufe").value == 3
    assert at.number_input(key="optimierung.seed").value == 7
    assert at.radio(key="optimierung.jacobi").value == "adjoint"
    assert at.number_input(key="optimierung.zeitgrenze").value == 120
    caption = next(c.value for c in at.caption if c.value.startswith("Entspricht:"))
    assert "--max-iterations 20 --runs 3 --seed 7 --jacobian adjoint" in caption


@needs_uploader
def test_kept_field_out_of_range_falls_back(at):
    """Ein gemerktes Feld, das ein anderes System nicht hat, fällt auf das erste zurück."""
    at.switch_page("pages/auswertung.py").run()
    at.selectbox(key="auswertung.eval.feld").set_value(2).run()
    at.switch_page("pages/system.py").run()
    source = at.selectbox(key="system.quelle")
    source.select_index(source.options.index(EXAMPLES)).run()
    box = at.selectbox(key=f"system.datei.{EXAMPLES}")
    box.select_index(box.options.index("einzellinse_bk7_biegung.json")).run()  # nur Feld 0
    at.switch_page("pages/auswertung.py").run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.selectbox(key="auswertung.eval.feld").value == 0
