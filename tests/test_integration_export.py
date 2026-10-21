"""G5-T3 gegen ein installiertes Mikroptim (``python -m pytest -m integration``)."""

import csv
import io
import json
import os
import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import needs_uploader
from gui_mikroptim.backend import compute, export, mko, system_tables

pytestmark = pytest.mark.integration

REPO = os.environ.get("MKO_GUI_MIKROPTIM_REPO")


@pytest.fixture
def repo(monkeypatch) -> Path:
    if not REPO:
        pytest.skip("MKO_GUI_MIKROPTIM_REPO nicht gesetzt")
    monkeypatch.setenv("MKO_GUI_MIKROPTIM_REPO", REPO)
    return Path(REPO)


def test_wavefront_csv_reads_back_identical_to_cli(repo):
    path = repo / "data" / "systems" / "testsystem_mehrlinser.json"
    system = compute.load_system(path)
    result = compute.trace_wavefront(system, compute.TraceOptions())
    text = export.rows_to_csv(system_tables.wavefront_rows(result, system.field_angles_deg))
    back = list(csv.DictReader(io.StringIO(text)))
    code, out, err = mko.require().run_cli(["trace", str(path), "--json"])
    assert code == 0, err
    cli = json.loads(out)["wavefront"]
    assert [float(r["RMS [Wellen]"]) for r in back] == [t["rms_waves"] for t in cli]


@pytest.mark.parametrize(
    "name",
    ["einzellinse_bk7.json", "testsystem_mehrlinser_dezentriert.json", "planplatte_bk7.json"],
)
def test_system_report(repo, name):
    system = compute.load_system(repo / "data" / "systems" / name)
    info = compute.details(system)
    try:
        wavefront = compute.trace_wavefront(system, compute.TraceOptions())
    except ValueError:  # afokal
        wavefront = None
    text = export.system_report(system, info.data, info.paraxial, info.variables, wavefront, name)
    surfaces = text.split("## Flächen\n", 1)[1].split("## Spektrum", 1)[0]
    body = [line for line in surfaces.splitlines() if re.match(r"^\| \d", line)]
    assert len(body) == system.num_surfaces
    assert ("## RMS-Wellenfront" in text) == (wavefront is not None)
    if name == "einzellinse_bk7.json":
        assert "| Brennweite f | 101.0496809 | mm |" in text


@needs_uploader
def test_pages_offer_exports(app_file, workspace, repo):
    at = AppTest.from_file(str(app_file), default_timeout=120).run()
    at.switch_page("pages/system.py").run()
    source = at.selectbox(key="system.quelle")
    source.select_index(source.options.index("Beispielsysteme (Mikroptim)")).run()
    box = at.selectbox(key="system.datei.Beispielsysteme (Mikroptim)")
    box.select_index(box.options.index("einzellinse_bk7.json")).run()
    assert not at.exception, [e.value for e in at.exception]
    downloads = at.get("download_button")
    labels = [d.proto.label for d in downloads]
    assert "Bericht (Markdown)" in labels and labels.count("CSV") == 2
    chart = at.get("plotly_chart")[0]
    config = json.loads(chart.proto.config)
    assert config["toImageButtonOptions"]["format"] == "svg"
    assert config["toImageButtonOptions"]["filename"] == "system_schnitt"
