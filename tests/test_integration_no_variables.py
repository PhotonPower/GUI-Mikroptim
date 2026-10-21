"""Systeme ohne Variablen auf der Seite „Optimierung“ (Befund vom Server, 2026-10-21)."""

import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import needs_uploader
from gui_mikroptim.backend import compute

pytestmark = pytest.mark.integration

REPO = os.environ.get("MKO_GUI_MIKROPTIM_REPO")
EXAMPLES = "Beispielsysteme (Mikroptim)"


@pytest.fixture
def repo(monkeypatch) -> Path:
    if not REPO:
        pytest.skip("MKO_GUI_MIKROPTIM_REPO nicht gesetzt")
    monkeypatch.setenv("MKO_GUI_MIKROPTIM_REPO", REPO)
    return Path(REPO)


def _without_variables(repo: Path) -> list[str]:
    names = []
    for path in sorted((repo / "data" / "systems").glob("*.json")):
        try:
            if not compute.load_system(path).variables():
                names.append(path.name)
        except Exception:  # Glasvariablen auf Katalog-Gläsern: hat Variablen
            continue
    return names


def _page(app_file, name):
    at = AppTest.from_file(str(app_file), default_timeout=120).run()
    at.switch_page("pages/optimierung.py").run()
    source = at.selectbox(key="optimierung.quelle")
    source.select_index(source.options.index(EXAMPLES)).run()
    box = at.selectbox(key=f"optimierung.datei.{EXAMPLES}")
    box.select_index(box.options.index(name)).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


@needs_uploader
def test_systems_without_variables_offer_no_start(app_file, workspace, repo):
    names = _without_variables(repo)
    assert "testsystem_mehrlinser.json" in names and "einzellinse_bk7.json" in names
    for name in names:
        at = _page(app_file, name)
        assert any("keinen Abschnitt `variables`" in i.value for i in at.info), name
        assert not [b for b in at.button if b.key == "optimierung.start"], name
        assert not at.error, (name, [e.value for e in at.error])


@needs_uploader
def test_system_with_variables_still_offers_start(app_file, workspace, repo):
    at = _page(app_file, "einzellinse_bk7_variablen.json")
    assert [b for b in at.button if b.key == "optimierung.start"]
