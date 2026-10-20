"""G1-T2 gegen ein installiertes Mikroptim (``python -m pytest -m integration``)."""

import hashlib
import json
import math
import os
import shutil
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import needs_uploader
from gui_mikroptim.backend import compute, mko, system_tables

pytestmark = pytest.mark.integration

REPO = os.environ.get("MKO_GUI_MIKROPTIM_REPO")
EXAMPLES = sorted((Path(REPO) / "data" / "systems").glob("*.json")) if REPO else []


@pytest.fixture
def repo(monkeypatch) -> Path:
    if not REPO:
        pytest.skip("MKO_GUI_MIKROPTIM_REPO nicht gesetzt")
    monkeypatch.setenv("MKO_GUI_MIKROPTIM_REPO", REPO)
    return Path(REPO)


def _finite_or_none(value):
    """Wie die CLI-JSON-Ausgabe: nicht endliche Zahlen als null."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _finite_or_none(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_finite_or_none(v) for v in value]
    return value


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_example_details_match_cli(repo, path):
    """Alle Beispielsysteme laden; Paraxialdaten gleich `mikroptim trace --json`."""
    m = mko.require()
    system = compute.load_system(path)
    info = compute.details(system)
    assert system_tables.surface_rows(system, info.data)
    code, out, err = m.run_cli(["trace", str(path), "--json", "--rings", "2", "--spokes", "2"])
    assert code == 0, err
    cli = json.loads(out)["paraxial"]
    assert _finite_or_none(info.paraxial) == cli


def _page(app_file):
    at = AppTest.from_file(str(app_file), default_timeout=60).run()
    at.switch_page("pages/system.py").run()
    return at


def _select(at, source_label, file_label):
    source = at.selectbox(key="system.quelle")
    source.select_index(source.options.index(source_label)).run()
    box = next(s for s in at.selectbox if s.label.startswith("Datei"))
    box.select_index(box.options.index(file_label)).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


@needs_uploader
def test_page_shows_paraxial_data(app_file, workspace, repo):
    at = _select(_page(app_file), "Beispielsysteme (Mikroptim)", "einzellinse_bk7.json")
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Brennweite f [mm]"] == "101.0497"
    assert metrics["Flächen"] == "3"
    paraxial = next(
        df.value for df in at.dataframe if "Schlüssel" in getattr(df.value, "columns", [])
    )
    values = dict(zip(paraxial["Schlüssel"], paraxial["Wert"], strict=True))
    assert values["focal_length"].startswith("101.04968")
    assert values["back_focal_distance"].startswith("99.05208")


@needs_uploader
def test_format_error_shows_json_path(app_file, workspace, repo):
    data = json.loads((repo / "data" / "systems" / "einzellinse_bk7.json").read_text("utf-8"))
    data["surfaces"][1]["curvature"] = "keine Zahl"
    (workspace / "uploads").mkdir(parents=True)
    (workspace / "uploads" / "kaputt.json").write_text(json.dumps(data), encoding="utf-8")
    at = _select(_page(app_file), "Uploads", "kaputt.json")
    assert any("JSON-Pfad `surfaces[1].curvature`" in e.value for e in at.error)


@needs_uploader
def test_catalog_repair(app_file, workspace, repo):
    upload = workspace / "uploads" / "einzellinse_bk7.json"
    upload.parent.mkdir(parents=True)
    shutil.copy(repo / "data" / "systems" / "einzellinse_bk7.json", upload)
    before = hashlib.sha256(upload.read_bytes()).hexdigest()

    at = _select(_page(app_file), "Uploads", "einzellinse_bk7.json")
    assert any("glass_catalogs[0]" in e.value for e in at.error)
    at.button(key="system.kataloge").click().run()
    assert not at.exception, [e.value for e in at.exception]

    assert any("Neu gespeichert als einzellinse_bk7-kataloge.json" in s.value for s in at.success)
    box = next(s for s in at.selectbox if s.label.startswith("Datei"))
    assert box.value.label == "einzellinse_bk7-kataloge.json"
    assert {m.label: m.value for m in at.metric}["Brennweite f [mm]"] == "101.0497"
    assert hashlib.sha256(upload.read_bytes()).hexdigest() == before  # Eingabe unverändert
    repaired = json.loads((workspace / "uploads" / "einzellinse_bk7-kataloge.json").read_text())
    original = json.loads(upload.read_text())
    assert {k: v for k, v in repaired.items() if k != "glass_catalogs"} == {
        k: v for k, v in original.items() if k != "glass_catalogs"
    }


@needs_uploader
def test_catalog_hint_without_repo(app_file, workspace, repo, monkeypatch):
    upload = workspace / "uploads" / "einzellinse_bk7.json"
    upload.parent.mkdir(parents=True)
    shutil.copy(repo / "data" / "systems" / "einzellinse_bk7.json", upload)
    monkeypatch.delenv("MKO_GUI_MIKROPTIM_REPO")
    at = _select(_page(app_file), "Uploads", "einzellinse_bk7.json")
    assert any("MKO_GUI_MIKROPTIM_REPO" in c.value for c in at.caption)
    assert not [b for b in at.button if b.key == "system.kataloge"]


@needs_uploader
def test_every_example_renders(app_file, workspace, repo):
    """Jede Beispieldatei läuft durch die Seite ohne Ausnahme und ohne Ladefehler."""
    at = _page(app_file)
    source = at.selectbox(key="system.quelle")
    source.select_index(source.options.index("Beispielsysteme (Mikroptim)")).run()
    box = next(s for s in at.selectbox if s.label.startswith("Datei"))
    for i, label in enumerate(box.options):
        box = next(s for s in at.selectbox if s.label.startswith("Datei"))
        box.select_index(i).run()
        assert not at.exception, (label, [e.value for e in at.exception])
        assert not at.error, (label, [e.value for e in at.error])
        assert at.metric, label


@needs_uploader
def test_afocal_system(app_file, workspace, repo):
    at = _select(_page(app_file), "Beispielsysteme (Mikroptim)", "planplatte_bk7.json")
    assert {m.label: m.value for m in at.metric}["Brennweite f [mm]"] == "afokal"
