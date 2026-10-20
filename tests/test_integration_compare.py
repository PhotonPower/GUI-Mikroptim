"""G2-T4 gegen ein installiertes Mikroptim (``python -m pytest -m integration``)."""

import json
import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import needs_uploader
from gui_mikroptim.backend import compare, compute, mko

pytestmark = pytest.mark.integration

REPO = os.environ.get("MKO_GUI_MIKROPTIM_REPO")
EXAMPLES = "Beispielsysteme (Mikroptim)"


@pytest.fixture
def repo(monkeypatch) -> Path:
    if not REPO:
        pytest.skip("MKO_GUI_MIKROPTIM_REPO nicht gesetzt")
    monkeypatch.setenv("MKO_GUI_MIKROPTIM_REPO", REPO)
    return Path(REPO)


def test_difference_equals_cli_values(repo):
    """Δ = B − A aus den Werten von `mikroptim trace --json` beider Systeme."""
    names = ("testsystem_mehrlinser.json", "testsystem_mehrlinser_dezentriert.json")
    options = compute.TraceOptions(rings=6, spokes=8)
    systems = [compute.load_system(repo / "data" / "systems" / n) for n in names]
    assert compare.comparability(*systems).same_grid
    results = [compute.trace_wavefront(s, options) for s in systems]
    rows = compare.rms_compare_rows(
        *results, systems[0].field_angles_deg, systems[0].wavelengths_nm
    )
    cli = []
    for n in names:
        code, out, err = mko.require().run_cli(
            ["trace", str(repo / "data" / "systems" / n), "--json", *options.cli_args()]
        )
        assert code == 0, err
        cli.append(json.loads(out)["wavefront"])
    for row, ta, tb in zip(rows, *cli, strict=True):
        assert row["RMS A [W]"] == ta["rms_waves"] and row["RMS B [W]"] == tb["rms_waves"]
        assert row["Δ B − A [W]"] == tb["rms_waves"] - ta["rms_waves"]
    assert any(r["Δ B − A [W]"] != 0 for r in rows)  # Dezentrierung wirkt


def _page(app_file, name_a):
    at = AppTest.from_file(str(app_file), default_timeout=60).run()
    at.switch_page("pages/auswertung.py").run()
    source = at.selectbox(key="auswertung.quelle")
    source.select_index(source.options.index(EXAMPLES)).run()
    box = at.selectbox(key=f"auswertung.datei.{EXAMPLES}")
    box.select_index(box.options.index(name_a)).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _select_b(at, name_b):
    source = at.selectbox(key="auswertung.vergleich.quelle")
    source.select_index(source.options.index(EXAMPLES)).run()
    box = at.selectbox(key=f"auswertung.vergleich.datei.{EXAMPLES}")
    box.select_index(box.options.index(name_b)).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _chart_keys(at):
    return [c.key for c in at.get("plotly_chart")]


@needs_uploader
def test_page_difference_for_comparable_systems(app_file, workspace, repo):
    at = _select_b(
        _page(app_file, "testsystem_mehrlinser.json"), "testsystem_mehrlinser_dezentriert.json"
    )
    keys = _chart_keys(at)
    assert "auswertung.vergleich.delta" in keys
    assert "auswertung.vergleich.a" not in keys
    assert {"auswertung.vergleich.schnitt.A", "auswertung.vergleich.schnitt.B"} <= set(keys)
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Flächen A / B"] == "8 / 8"
    # A bleibt das aktuelle System, B ändert es nicht
    assert at.session_state["aktuell.datei"].endswith("testsystem_mehrlinser.json")


@needs_uploader
def test_page_side_by_side_for_different_grids(app_file, workspace, repo):
    at = _select_b(_page(app_file, "einzellinse_bk7.json"), "testsystem_mehrlinser.json")
    keys = _chart_keys(at)
    assert "auswertung.vergleich.a" in keys and "auswertung.vergleich.b" in keys
    assert "auswertung.vergleich.delta" not in keys
    warning = next(w.value for w in at.warning if "nebeneinander" in w.value)
    assert "Feldwinkel verschieden" in warning and "Wellenlängen verschieden" in warning
    assert "Referenzwellenlänge verschieden" in warning


@needs_uploader
def test_page_same_file_and_afocal(app_file, workspace, repo):
    at = _select_b(_page(app_file, "einzellinse_bk7.json"), "einzellinse_bk7.json")
    assert any("dieselbe Datei" in i.value for i in at.info)
    at = _select_b(_page(app_file, "einzellinse_bk7.json"), "planplatte_bk7.json")
    assert any("Wellenfront von B" in e.value and "ValueError" in e.value for e in at.error)
