"""App-Tests mit Streamlit AppTest: jede Seite läuft ohne Ausnahme, mit und ohne Mikroptim."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import needs_uploader

PAGES = ["pages/system.py", "pages/synthese.py"]


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


def _workspace_with(workspace: Path, test_data: Path, name: str, content: bytes | None = None):
    (workspace / "uploads").mkdir(parents=True, exist_ok=True)
    data = content if content is not None else (test_data / "synth_beispiel.json").read_bytes()
    (workspace / "uploads" / name).write_bytes(data)


def test_protocol_browser_shows_protocol(
    app_file: Path, workspace: Path, test_data: Path, without_mikroptim
):
    _workspace_with(workspace, test_data, "lauf.json")
    at = _run(app_file, "pages/synthese.py")
    assert any("Ziel erreicht" in s.value for s in at.success)
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Elemente"] == "1 → 2"
    assert len(at.dataframe) == 2  # Schritte und Kandidaten
    assert "Kandidat" in [s.label for s in at.selectbox]


@needs_uploader
def test_protocol_browser_filter(
    app_file: Path, workspace: Path, test_data: Path, without_mikroptim
):
    _workspace_with(workspace, test_data, "lauf.json")
    at = _run(app_file, "pages/synthese.py")
    at.selectbox(key="synthese.angenommen").select("nein").run()
    assert not at.exception
    assert any("1 von 3 Schritten" in c.value for c in at.caption)


def test_protocol_browser_broken_file(
    app_file: Path, workspace: Path, test_data: Path, without_mikroptim
):
    _workspace_with(workspace, test_data, "kaputt.json", b'{"format": "mikroptim.synth/1", ')
    at = _run(app_file, "pages/synthese.py")
    assert any("nicht lesbar" in e.value for e in at.error)


def test_protocol_browser_empty(app_file: Path, workspace: Path, without_mikroptim):
    at = _run(app_file, "pages/synthese.py")
    assert any("Keine passenden Dateien" in i.value for i in at.info)


@needs_uploader
def test_protocol_upload(app_file: Path, workspace: Path, test_data: Path, without_mikroptim):
    at = _run(app_file, "pages/synthese.py")
    data = (test_data / "synth_beispiel.json").read_bytes()
    at.file_uploader[0].set_value(("lauf.json", data, "application/json")).run()
    assert not at.exception
    assert (workspace / "uploads" / "lauf.json").is_file()
    assert any("Ziel erreicht" in s.value for s in at.success)
    # ein System passt hier nicht
    at.file_uploader[0].set_value(
        ("s.json", b'{"format": "mikroptim.system/1"}', "application/json")
    ).run()
    assert any("Upload abgelehnt" in e.value for e in at.error)
    assert not (workspace / "uploads" / "s.json").exists()


def test_evaluation_page_without_mikroptim(app_file: Path, workspace: Path, without_mikroptim):
    at = _run(app_file, "pages/auswertung.py")
    assert at.title[0].value == "Auswertung"
    assert any("Mikroptim ist nicht nutzbar" in w.value for w in at.warning)


def test_jobs_tab(app_file: Path, workspace: Path, without_mikroptim):
    import sys
    import time

    from gui_mikroptim.backend import jobs

    done = jobs.submit(workspace, "test", [sys.executable, "-c", "print('fertig')"], 1)
    deadline = time.monotonic() + 30
    while not jobs.load(done.path).final and time.monotonic() < deadline:
        time.sleep(0.1)
    long = jobs.submit(workspace, "test", [sys.executable, "-c", "import time; time.sleep(60)"], 2)
    try:
        at = _run(app_file, "pages/synthese.py")
        assert any(m.label == "laufend" and m.value == "1 / 1" for m in at.metric)
        table = at.dataframe[-1].value
        assert set(table["Job"]) == {done.id, long.id}
        box = at.selectbox(key="jobs.auswahl")
        assert box.value == long.id  # neuester zuerst
        assert any(long.id in c.value or "time.sleep(60)" in c.value for c in at.code)
        at.button(key=f"jobs.abbrechen.{long.id}").click().run()
        assert not at.exception, [e.value for e in at.exception]
        deadline = time.monotonic() + 20
        while not jobs.load(long.path).final and time.monotonic() < deadline:
            time.sleep(0.1)
        assert jobs.load(long.path).status == jobs.CANCELLED
        box = at.selectbox(key="jobs.auswahl")
        box.set_value(done.id).run()
        assert not [b for b in at.button if b.key == f"jobs.abbrechen.{done.id}"]
        assert any("fertig" in c.value for c in at.code)
    finally:
        jobs.cancel(workspace, long.id)


def test_optimization_page_without_mikroptim(app_file: Path, workspace: Path, without_mikroptim):
    at = _run(app_file, "pages/optimierung.py")
    assert at.title[0].value == "Optimierung"
    assert any("Mikroptim ist nicht nutzbar" in w.value for w in at.warning)
