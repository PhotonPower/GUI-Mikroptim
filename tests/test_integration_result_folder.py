"""G4-T4: Ergebnisordner von Mikroptim M6-T6 vollständig navigierbar (Integration)."""

import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import needs_uploader

pytestmark = pytest.mark.integration

REPO = os.environ.get("MKO_GUI_MIKROPTIM_REPO")
FOLDER = "Mikroptim: m6-t6"


@pytest.fixture
def repo(monkeypatch) -> Path:
    if not REPO:
        pytest.skip("MKO_GUI_MIKROPTIM_REPO nicht gesetzt")
    if not (Path(REPO) / "docs" / "ergebnisse" / "m6-t6").is_dir():
        pytest.skip("docs/ergebnisse/m6-t6 fehlt (Mikroptim vor M6-T6)")
    monkeypatch.setenv("MKO_GUI_MIKROPTIM_REPO", REPO)
    return Path(REPO)


def _tab(app_file) -> AppTest:
    at = AppTest.from_file(str(app_file), default_timeout=180).run()
    at.switch_page("pages/synthese.py").run()
    at.selectbox(key="ordner.auswahl").set_value(FOLDER).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


@needs_uploader
def test_m6t6_fully_navigable(app_file, workspace, repo):
    at = _tab(app_file)
    metrics = {m.label: m.value for m in at.metric}
    assert (metrics["System"], metrics["Protokoll"], metrics["Auswertung"]) == ("11", "44", "16")
    assert any("m6-t6-zielspezifikation.md" in e.label for e in at.expander)
    stages = next(
        d.value for d in at.dataframe if "Stufe" in d.value.columns and "Texte" in d.value.columns
    )
    assert {"p1", "p7", "z2", "a1"} <= set(stages["Stufe"])
    for key in ("ordner.system", "ordner.protokoll", "ordner.weitere"):
        options = at.selectbox(key=key).options
        for option in options:
            at.selectbox(key=key).set_value(option).run()
            assert not at.exception, (key, option, [e.value for e in at.exception])
            # rot ist nur der Status „Startsystem abgelehnt“ eines Protokolls (Inhalt, kein Fehler)
            errors = [e.value for e in at.error if "Startsystem abgelehnt" not in e.value]
            assert not errors, (key, option, errors)


@needs_uploader
def test_jumps_to_system_and_compare(app_file, workspace, repo):
    at = _tab(app_file)
    at.selectbox(key="ordner.system").set_value("p7.json").run()
    at.button(key="ordner.auswerten").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["aktuell.datei"].endswith("p7.json")
    assert at.title[0].value == "Auswertung"

    at = _tab(app_file)
    at.selectbox(key="ordner.system").set_value("z2_s0.json").run()
    at.button(key="ordner.vergleichen").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.title[0].value == "Auswertung"
    box = at.selectbox(key="auswertung.vergleich.quelle")
    assert box.value.label == "Mikroptim: docs/ergebnisse"
