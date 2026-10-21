"""G6-T1/T2: Sitzungsordner und Seite „Dateien“ in der App (ohne Mikroptim)."""

import io
import zipfile
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import needs_uploader


@pytest.fixture
def sessions_root(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "sitzungen"
    monkeypatch.setenv("MKO_GUI_SESSIONS", str(root))
    monkeypatch.setenv("MKO_GUI_WORKSPACE", str(tmp_path / "gemeinsam"))
    monkeypatch.delenv("MKO_GUI_MIKROPTIM_REPO", raising=False)
    return root


def _start(app_file, sid=None) -> AppTest:
    at = AppTest.from_file(str(app_file), default_timeout=30)
    if sid is not None:
        at.query_params["sitzung"] = sid
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _sid(at) -> str:
    return at.session_state["sitzung.id"]


def test_session_folder_and_url(app_file, sessions_root, without_mikroptim):
    at = _start(app_file)
    sid = _sid(at)
    assert at.query_params["sitzung"] in (sid, [sid])  # AppTest: Text oder Liste
    assert (sessions_root / sid / "uploads").is_dir()
    table = next(d.value for d in at.dataframe if "Zweck" in d.value.columns)
    assert str(sessions_root / sid) in set(table["Pfad"])
    at.run()
    assert _sid(at) == sid  # Neulauf behält die Sitzung
    again = _start(app_file, sid)  # Lesezeichen: neue Browsersitzung, gleiche Adresse
    assert _sid(again) == sid
    fresh = _start(app_file, "../../ungueltig")
    assert _sid(fresh) != sid and _sid(fresh) != "../../ungueltig"


@needs_uploader
def test_sessions_are_isolated(app_file, sessions_root, test_data, without_mikroptim):
    a = _start(app_file)
    a.switch_page("pages/synthese.py").run()
    a.file_uploader[0].set_value(
        ("lauf.json", (test_data / "synth_beispiel.json").read_bytes(), "x")
    ).run()
    assert (sessions_root / _sid(a) / "uploads" / "lauf.json").is_file()
    b = _start(app_file)
    assert _sid(b) != _sid(a)
    b.switch_page("pages/synthese.py").run()
    assert any("Keine passenden Dateien" in i.value for i in b.info)  # B sieht A nicht
    assert not (sessions_root / _sid(b) / "uploads" / "lauf.json").exists()


def test_files_page_zip(app_file, sessions_root, without_mikroptim):
    at = _start(app_file)
    folder = sessions_root / _sid(at)
    (folder / "ergebnisse" / "linse-optimiert.json").write_text('{"x": 1}', encoding="utf-8")
    (folder / "jobs" / "20261021-1200-synth").mkdir()
    (folder / "jobs" / "20261021-1200-synth" / "protokoll.json").write_text("{}", encoding="utf-8")
    at.switch_page("pages/dateien.py").run()
    assert not at.exception, [e.value for e in at.exception]
    assert {m.label: m.value for m in at.metric}["Dateien"] == "2"
    at.button(key="dateien.erstellen").click().run()
    assert not at.exception, [e.value for e in at.exception]
    data = at.session_state["dateien.zip"][1]
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert sorted(archive.namelist()) == [
            "ergebnisse/linse-optimiert.json",
            "jobs/20261021-1200-synth/protokoll.json",
        ]
    assert any(d.proto.label.endswith("MB)") for d in at.get("download_button"))


def test_files_page_empty_and_without_sessions(app_file, workspace, without_mikroptim):
    at = AppTest.from_file(str(app_file), default_timeout=30).run()
    at.switch_page("pages/dateien.py").run()
    assert not at.exception
    assert any("noch keine Dateien" in i.value for i in at.info)
