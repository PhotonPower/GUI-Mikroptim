"""ADR-0006: Glaskatalog hochladen und System mit eigenen Gläsern laden (Integration).

Das Szenario vom Server: Nutzer ohne Shell-Zugang laden einen eigenen Katalog und eine
Systemdatei hoch, die Kataloge aus dem Mikroptim-Checkout (basis.json) und aus
data/glass/private/ nennt. Die Gläser sind frei erfunden (aus Mikroptims synthetisch.json).
"""

import json
import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import needs_uploader

pytestmark = pytest.mark.integration

REPO = os.environ.get("MKO_GUI_MIKROPTIM_REPO")


@pytest.fixture
def repo(monkeypatch) -> Path:
    if not REPO:
        pytest.skip("MKO_GUI_MIKROPTIM_REPO nicht gesetzt")
    monkeypatch.setenv("MKO_GUI_MIKROPTIM_REPO", REPO)
    return Path(REPO)


def _catalog(repo: Path, names=("SYN-36",)) -> bytes:
    data = json.loads((repo / "data" / "glass" / "synthetisch.json").read_text("utf-8"))
    glasses = [g for g in data["glasses"] if g["name"] in names]
    return json.dumps({"format": "mikroptim.glass/1", "glasses": glasses}).encode()


def _system(repo: Path) -> bytes:
    data = json.loads((repo / "data" / "systems" / "einzellinse_bk7.json").read_text("utf-8"))
    data["name"] = "Einzellinse aus eigenem Glas"
    data["glass_catalogs"] = ["data/glass/basis.json", "data/glass/private/meine_glaeser.json"]
    data["surfaces"][1]["material"] = "SYN-36"
    return json.dumps(data).encode()


def _page(app_file) -> AppTest:
    at = AppTest.from_file(str(app_file), default_timeout=120).run()
    at.switch_page("pages/system.py").run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _uploader(at, key_prefix):
    return next(u for u in at.file_uploader if u.key.startswith(key_prefix))


@needs_uploader
def test_upload_catalog_and_system(app_file, workspace, repo):
    at = _page(app_file)
    _uploader(at, "kataloge.upload").set_value(
        ("meine_glaeser.json", _catalog(repo), "application/json")
    ).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("meine_glaeser.json gespeichert (1 Gläser)" in s.value for s in at.success)
    assert (workspace / "kataloge" / "meine_glaeser.json").is_file()

    _uploader(at, "system.upload").set_value(
        ("eigen.json", _system(repo), "application/json")
    ).run()
    assert any("glass_catalogs" in e.value for e in at.error)  # Mikroptim findet sie nicht
    table = next(d.value for d in at.dataframe if "Eintrag" in d.value.columns)
    assert list(table["gefunden"]) == ["Mikroptim", "Arbeitsbereich"]

    at.button(key="system.kataloge").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Neu gespeichert als eigen-kataloge.json" in s.value for s in at.success)
    assert at.subheader[0].value == "Einzellinse aus eigenem Glas"
    assert {m.label for m in at.metric} >= {"Brennweite f [mm]"}
    assert not at.error


@needs_uploader
def test_missing_catalog_is_named(app_file, workspace, repo):
    at = _page(app_file)
    _uploader(at, "system.upload").set_value(
        ("eigen.json", _system(repo), "application/json")
    ).run()
    assert any("`meine_glaeser.json`" in w.value and "hochladen" in w.value for w in at.warning)
    assert not [b for b in at.button if b.key == "system.kataloge"]


@needs_uploader
def test_catalog_rejected_and_clash_warning(app_file, workspace, repo):
    at = _page(app_file)
    _uploader(at, "kataloge.upload").set_value(
        ("system.json", (repo / "data" / "systems" / "einzellinse_bk7.json").read_bytes(), "x")
    ).run()
    assert any("Katalog abgelehnt" in e.value and "kein Glaskatalog" in e.value for e in at.error)
    assert not (workspace / "kataloge" / "system.json").exists()

    basis = json.loads((repo / "data" / "glass" / "basis.json").read_text("utf-8"))
    bk7 = next(g for g in basis["glasses"] if g["name"] == "N-BK7")
    clash = json.dumps({"format": "mikroptim.glass/1", "glasses": [bk7]}).encode()
    _uploader(at, "kataloge.upload").set_value(("doppelt.json", clash, "application/json")).run()
    assert any("N-BK7 steht auch in den Katalogen von Mikroptim" in s.value for s in at.success)


@needs_uploader
def test_delete_catalog(app_file, workspace, repo):
    at = _page(app_file)
    _uploader(at, "kataloge.upload").set_value(("weg.json", _catalog(repo), "x")).run()
    assert at.button(key="kataloge.loeschen_knopf").disabled  # erst bestätigen
    at.checkbox(key="kataloge.sicher").check().run()
    at.button(key="kataloge.loeschen_knopf").click().run()
    assert not (workspace / "kataloge" / "weg.json").exists()
    assert any("weg.json gelöscht" in s.value for s in at.success)
