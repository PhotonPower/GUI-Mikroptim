"""App-Tests mit Streamlit AppTest: jede Seite läuft ohne Ausnahme, mit und ohne Mikroptim."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

PAGES = ["pages/system.py", "pages/auswertung.py", "pages/optimierung.py", "pages/synthese.py"]


def _run(app_file: Path, page: str | None = None) -> AppTest:
    at = AppTest.from_file(str(app_file), default_timeout=30)
    at.run()
    if page is not None:
        at.switch_page(page)
        at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_start_page_without_mikroptim(app_file: Path, workspace: Path, without_mikroptim):
    at = _run(app_file)
    assert at.title[0].value == "GUI-Mikroptim"
    assert any("nicht nutzbar" in e.value for e in at.error)
    assert (workspace / "uploads").is_dir()


@pytest.mark.parametrize("page", PAGES)
def test_planned_pages_without_mikroptim(app_file: Path, workspace: Path, without_mikroptim, page):
    at = _run(app_file, page)
    assert len(at.title) == 1
    assert at.info  # Platzhalter mit Hinweis


def test_invalid_config_shows_error(app_file: Path, tmp_path: Path, monkeypatch, without_mikroptim):
    file = tmp_path / "datei"
    file.write_text("x")
    monkeypatch.setenv("MKO_GUI_WORKSPACE", str(file))
    at = AppTest.from_file(str(app_file), default_timeout=30).run()
    assert any("Konfiguration ungültig" in e.value for e in at.error)
