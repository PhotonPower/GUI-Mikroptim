"""G1-T1: Dateiauswahl, Upload und seitenübergreifende Auswahl auf der Seite „System“."""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import needs_uploader


def _system(name: str, surfaces: int = 2) -> str:
    # frei erfundene Minimaldatei; für G1-T1 zählt nur das Format
    return json.dumps(
        {
            "format": "mikroptim.system/1",
            "name": name,
            "spectrum": {"wavelengths_nm": [546.07], "weights": [1.0], "reference_nm": 546.07},
            "source": {"type": "collimated", "field_angles_deg": [0.0], "field_weights": [1.0]},
            "surfaces": [{"type": "plane"}] * surfaces,
            "glass_catalogs": [],
        }
    )


@pytest.fixture
def fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = tmp_path / "Mikroptim"
    systems = repo / "data" / "systems"
    systems.mkdir(parents=True)
    (systems / "alpha.json").write_text(_system("Alpha", 2), encoding="utf-8")
    (systems / "beta.json").write_text(_system("Beta", 5), encoding="utf-8")
    (systems / "glas.json").write_text('{"format": "mikroptim.glass/1"}', encoding="utf-8")
    monkeypatch.setenv("MKO_GUI_MIKROPTIM_REPO", str(repo))
    return repo


def _system_page(app_file: Path) -> AppTest:
    at = AppTest.from_file(str(app_file), default_timeout=30).run()
    at.switch_page("pages/system.py").run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _file_box(at: AppTest):
    return next(s for s in at.selectbox if s.label.startswith("Datei"))


def test_examples_listed_only_systems(app_file, workspace, fake_repo, without_mikroptim):
    at = _system_page(app_file)
    box = _file_box(at)
    assert box.label == "Datei (2)"  # glas.json wird nicht angeboten
    assert box.options == ["alpha.json", "beta.json"]
    assert at.subheader[0].value == "Alpha"


@needs_uploader
def test_selection_survives_page_switch(app_file, workspace, fake_repo, without_mikroptim):
    at = _system_page(app_file)
    _file_box(at).select_index(1).run()
    assert at.subheader[0].value == "Beta"
    assert at.session_state["aktuell.datei"] == str(fake_repo / "data" / "systems" / "beta.json")

    at.switch_page("pages/start.py").run()
    at.switch_page("pages/system.py").run()
    assert not at.exception
    assert _file_box(at).value.label == "beta.json"
    assert at.subheader[0].value == "Beta"


def test_sidebar_shows_current_system(app_file, workspace, fake_repo, without_mikroptim):
    # AppTest führt nach switch_page nur das Seitenskript aus, ohne Einstieg und Seitenleiste;
    # deshalb hier ein normaler Lauf des Einstiegs mit gesetzter Auswahl.
    at = AppTest.from_file(str(app_file), default_timeout=30)
    at.session_state["aktuell.datei"] = str(fake_repo / "data" / "systems" / "beta.json")
    at.run()
    assert not at.exception
    assert any("Aktuelles System: beta.json" in c.value for c in at.sidebar.caption)


def test_sidebar_drops_path_outside_roots(
    app_file, workspace, fake_repo, tmp_path, without_mikroptim
):
    outside = tmp_path / "anderswo.json"
    outside.write_text(_system("Fremd"), encoding="utf-8")
    at = AppTest.from_file(str(app_file), default_timeout=30)
    at.session_state["aktuell.datei"] = str(outside)
    at.run()
    assert any("Aktuelles System: –" in c.value for c in at.sidebar.caption)
    assert "aktuell.datei" not in at.session_state


@needs_uploader
def test_upload_appears_and_is_selected(app_file, workspace, fake_repo, without_mikroptim):
    at = _system_page(app_file)
    at.file_uploader[0].set_value(("neu.json", _system("Neu").encode(), "application/json"))
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Gespeichert als neu.json" in s.value for s in at.success)
    assert (workspace / "uploads" / "neu.json").is_file()
    assert at.selectbox(key="system.quelle").value.label == "Uploads"
    assert _file_box(at).value.label == "neu.json"
    assert at.subheader[0].value == "Neu"


@needs_uploader
def test_same_name_twice_gives_suffix(app_file, workspace, fake_repo, without_mikroptim):
    at = _system_page(app_file)
    for name in ("Eins", "Zwei"):
        at.file_uploader[0].set_value(("s.json", _system(name).encode(), "application/json"))
        at.run()
        assert not at.exception
    assert sorted(p.name for p in (workspace / "uploads").iterdir()) == ["s-2.json", "s.json"]
    assert _file_box(at).value.label == "s-2.json"
    assert at.subheader[0].value == "Zwei"


@needs_uploader
@pytest.mark.parametrize(
    "data",
    [b'{"format": "mikroptim.glass/1"}', b"kein json", b'{"format": "fremd/1"}'],
)
def test_wrong_upload_rejected(app_file, workspace, fake_repo, without_mikroptim, data):
    at = _system_page(app_file)
    at.file_uploader[0].set_value(("x.json", data, "application/json"))
    at.run()
    assert not at.exception
    assert any("Upload abgelehnt" in e.value for e in at.error)
    assert not any((workspace / "uploads").iterdir())


def test_without_repo_only_workspace_sources(app_file, workspace, without_mikroptim, monkeypatch):
    monkeypatch.delenv("MKO_GUI_MIKROPTIM_REPO", raising=False)
    at = _system_page(app_file)
    assert at.selectbox(key="system.quelle").options == ["Uploads", "Ergebnisse"]


def test_lens_section_without_mikroptim(app_file, workspace, fake_repo, without_mikroptim):
    at = _system_page(app_file)
    charts = at.get("plotly_chart")
    assert len(charts) == 1
    assert any("ungeprüft aus der Datei" in w.value for w in at.warning)
