"""G2-T1 gegen ein installiertes Mikroptim (``python -m pytest -m integration``)."""

import json
import math
import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import needs_uploader
from gui_mikroptim.backend import compute, mko, system_tables

pytestmark = pytest.mark.integration

REPO = os.environ.get("MKO_GUI_MIKROPTIM_REPO")


@pytest.fixture
def repo(monkeypatch) -> Path:
    if not REPO:
        pytest.skip("MKO_GUI_MIKROPTIM_REPO nicht gesetzt")
    monkeypatch.setenv("MKO_GUI_MIKROPTIM_REPO", REPO)
    return Path(REPO)


def _num(value):
    return None if isinstance(value, float) and not math.isfinite(value) else value


@pytest.mark.parametrize(
    ("name", "options"),
    [
        ("einzellinse_bk7.json", compute.TraceOptions()),
        ("testsystem_mehrlinser.json", compute.TraceOptions(rings=6, spokes=12)),
        ("testsystem_mehrlinser_dezentriert.json", compute.TraceOptions(rings=4, spokes=8)),
        ("weiches_versagen_start.json", compute.TraceOptions()),  # mit versagten Strahlen
    ],
)
def test_wavefront_identical_to_cli(repo, name, options):
    """Jede Zahl der Tabelle gleich `mikroptim trace --json` mit denselben Optionen (bitgleich)."""
    path = repo / "data" / "systems" / name
    system = compute.load_system(path)
    result = compute.trace_wavefront(system, options)
    rows = system_tables.wavefront_rows(result, system.field_angles_deg)

    code, out, err = mko.require().run_cli(["trace", str(path), "--json", *options.cli_args()])
    assert code == 0, err
    cli = json.loads(out)
    assert cli["quadrature"] == {"rings": options.rings, "spokes": options.spokes}
    assert cli["rays"] == result.total_rays
    assert cli["failed_rays"] == result.total_failed
    assert cli["target_focal_length"] == result.target_focal_length
    assert len(cli["wavefront"]) == len(rows)
    for row, tup in zip(rows, cli["wavefront"], strict=True):
        assert (row["Feld"], row["λ [nm]"]) == (tup["field"], tup["wavelength_nm"])
        assert row["RMS [Wellen]"] == tup["rms_waves"]
        assert row["RMS [mm]"] == tup["rms_mm"]
        assert row["Kolben [mm]"] == _num(tup["piston_mm"])
        assert row["Strahlen"] == tup["rays"]
        assert row["versagt"] == tup["failed_rays"]
        assert row["Pupille"] == tup["pupil_mode"]
        assert row["Bildpunkt y [mm]"] == tup["image_point"][1]


def _page(app_file):
    at = AppTest.from_file(str(app_file), default_timeout=60).run()
    at.switch_page("pages/auswertung.py").run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _select(at, file_label, source_label="Beispielsysteme (Mikroptim)"):
    source = at.selectbox(key="auswertung.quelle")
    source.select_index(source.options.index(source_label)).run()
    box = next(s for s in at.selectbox if s.label.startswith("Datei"))
    box.select_index(box.options.index(file_label)).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


@needs_uploader
def test_page_shows_wavefront(app_file, workspace, repo):
    at = _select(_page(app_file), "einzellinse_bk7.json")
    assert "auswertung.rms" in [c.key for c in at.get("plotly_chart")]
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["versagt"] == "0"
    assert int(metrics["Strahlen"]) > 0
    assert any(
        "mikroptim trace einzellinse_bk7.json --json --rings 10" in c.value for c in at.caption
    )
    assert not [t for t in at.toggle if t.key == "auswertung.gpu"]  # CPU-Build: kein Schalter

    at.number_input(key="auswertung.ringe").set_value(4).run()
    assert any("--rings 4" in c.value for c in at.caption)


@needs_uploader
def test_failed_rays_are_reported(app_file, workspace, repo):
    at = _select(_page(app_file), "weiches_versagen_start.json")
    assert {m.label: m.value for m in at.metric}["versagt"] != "0"
    assert any("versagt" in w.value for w in at.warning)


@needs_uploader
def test_afocal_system_reports_error(app_file, workspace, repo):
    at = _select(_page(app_file), "planplatte_bk7.json")
    assert any("ValueError" in e.value and "Sollbrennweite" in e.value for e in at.error)


@needs_uploader
def test_gpu_switch_and_unavailable_error(app_file, workspace, repo, monkeypatch):
    """Mit (vorgetäuschtem) CUDA-Gerät erscheint der Schalter; der CPU-Build meldet dann
    GpuUnavailableError, ohne dass die App abstürzt."""
    real = mko.status()
    if real.has_cuda:
        pytest.skip("echter CUDA-Build: GpuUnavailableError nicht erzwingbar")
    fake = mko.MikroptimStatus(
        True, real.version, True, [{"index": 0, "name": "Test-GPU", "total_bytes": 1}]
    )
    monkeypatch.setattr(mko, "status", lambda module_name="mikroptim": fake)
    at = _select(_page(app_file), "einzellinse_bk7.json")
    gpu = at.toggle(key="auswertung.gpu")
    gpu.set_value(True).run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.radio(key="auswertung.genauigkeit").options == ["fp64", "df64"]
    assert any("GpuUnavailableError" in e.value for e in at.error)
