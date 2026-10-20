"""G2-T2 gegen ein installiertes Mikroptim (``python -m pytest -m integration``)."""

import csv
import json
import math
import os
from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from conftest import needs_uploader
from gui_mikroptim.backend import compute, mko, system_tables

pytestmark = pytest.mark.integration

REPO = os.environ.get("MKO_GUI_MIKROPTIM_REPO")

#: Spalten der GUI-Tabelle → Felder von mikroptim eval --json (tuples)
COLUMNS = {
    "Bildhöhe [mm]": "image_height_mm",
    "Strahlen": "rays",
    "versagt": "failed_rays",
    "RMS-OPD [W]": "rms_opd_waves",
    "PV-OPD [W]": "pv_opd_waves",
    "RMS ohne Kippung [W]": "rms_opd_tilt_waves",
    "RMS ohne Defokus [W]": "rms_opd_defocus_waves",
    "RMS-Spot [mm]": "rms_spot_mm",
    "Verzeichnung HS [%]": "distortion_chief_percent",
    "Verzeichnung SP [%]": "distortion_centroid_percent",
    "z_t [mm]": "focus_tangential_mm",
    "z_s [mm]": "focus_sagittal_mm",
    "Astigmatismus [mm]": "astigmatism_mm",
    "Defokus [mm]": "defocus_mm",
}


@pytest.fixture
def repo(monkeypatch) -> Path:
    if not REPO:
        pytest.skip("MKO_GUI_MIKROPTIM_REPO nicht gesetzt")
    monkeypatch.setenv("MKO_GUI_MIKROPTIM_REPO", REPO)
    return Path(REPO)


@pytest.mark.parametrize(
    ("name", "options"),
    [
        ("einzellinse_bk7.json", compute.EvalOptions(grid=32)),
        ("testsystem_mehrlinser.json", compute.EvalOptions(grid=24, reference="vertex")),
        ("testsystem_mehrlinser_dezentriert.json", compute.EvalOptions(grid=16)),
        ("weiches_versagen_start.json", compute.EvalOptions(grid=16, half=True)),
    ],
)
def test_eval_rows_identical_to_cli(repo, name, options):
    """Jede Kennzahl der Tabelle gleich `mikroptim eval --json` (bitgleich, null = None)."""
    path = repo / "data" / "systems" / name
    system = compute.load_system(path)
    ev = compute.evaluate(system, options)
    rows = system_tables.eval_rows(ev.stats, ev.reference_nm, system.field_angles_deg)

    code, out, err = mko.require().run_cli(["eval", str(path), "--json", *options.cli_args()])
    assert code == 0, err
    cli = json.loads(out)
    assert (cli["grid"], cli["grid_points"], cli["half_pupil"]) == (
        ev.grid,
        ev.grid_points,
        ev.half_pupil,
    )
    assert cli["failed_rays"] == ev.failed_rays
    assert len(cli["tuples"]) == len(rows)
    for row, tup in zip(rows, cli["tuples"], strict=True):
        assert (row["Feld"], row["Wellenlänge"]) == (tup["field"], tup["wavelength"])
        for column, field in COLUMNS.items():
            assert row[column] == tup[field], (name, column, row[column], tup[field])
        assert [row["Schwerpunkt x [mm]"], row["Schwerpunkt y [mm]"]] == tup["centroid_mm"]
        assert row["Hauptstrahl y [mm]"] == tup["chief_ray_mm"][1]


@pytest.mark.parametrize("remove", compute.REMOVALS)
def test_opd_map_identical_to_cli_csv(repo, tmp_path, remove):
    """OPD-Karte in Wellen gleich der CSV von `mikroptim eval --map` (17 Stellen, verlustfrei).

    Die CSV beginnt mit dem größten y, die Karte von opd_map mit dem kleinsten.
    """
    path = repo / "data" / "systems" / "testsystem_mehrlinser.json"
    options = compute.EvalOptions(grid=16)
    ev = compute.evaluate(compute.load_system(path), options)
    ours = compute.mm_to_waves(ev.opd_map(1, 2, remove), ev.reference_nm)

    target = tmp_path / "karte.csv"
    code, _, err = mko.require().run_cli(
        ["eval", str(path), *options.cli_args(), "--map", "1,2", "--map-file", str(target),
         "--remove", remove]
    )  # fmt: skip
    assert code == 0, err
    with target.open(encoding="utf-8") as handle:
        rows = [[float(v) if v.strip() else math.nan for v in r] for r in csv.reader(handle)]
    theirs = np.array(rows[::-1])
    assert theirs.shape == ours.shape
    assert np.array_equal(np.isnan(theirs), np.isnan(ours))
    mask = ~np.isnan(ours)
    assert np.array_equal(theirs[mask], ours[mask])


def _page(app_file):
    at = AppTest.from_file(str(app_file), default_timeout=60).run()
    at.switch_page("pages/auswertung.py").run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _select(at, file_label):
    source = at.selectbox(key="auswertung.quelle")
    source.select_index(source.options.index("Beispielsysteme (Mikroptim)")).run()
    box = next(s for s in at.selectbox if s.label.startswith("Datei"))
    box.select_index(box.options.index(file_label)).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


@needs_uploader
def test_page_shows_eval(app_file, workspace, repo):
    at = _select(_page(app_file), "testsystem_mehrlinser.json")
    keys = [c.key for c in at.get("plotly_chart")]
    assert "auswertung.eval.opd" in keys and "auswertung.eval.spots" in keys
    assert any(
        "mikroptim eval testsystem_mehrlinser.json --json --grid 64" in c.value for c in at.caption
    )

    # set_value mit dem echten Wert: AppTest.select_index wendet format_func auf den bereits
    # formatierten Text an und passt deshalb nicht zu Auswahlen mit eigener Formatierung
    at.selectbox(key="auswertung.eval.feld").set_value(2).run()
    at.selectbox(key="auswertung.eval.wl").set_value(3).run()
    at.selectbox(key="auswertung.eval.abzug").set_value("defocus").run()
    at.number_input(key="auswertung.eval.raster").set_value(16).run()
    at.toggle(key="auswertung.eval.halb").set_value(True).run()
    at.selectbox(key="auswertung.eval.referenz").set_value("vertex").run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("--map 2,3" in c.value and "--remove defocus" in c.value for c in at.caption)
    assert any("--grid 16 --reference vertex --half" in c.value for c in at.caption)
    assert any("Nur die gerechnete Hälfte" in c.value for c in at.caption)


@needs_uploader
def test_eval_failed_rays(app_file, workspace, repo):
    at = _select(_page(app_file), "weiches_versagen_start.json")
    assert any("Strahlen versagt" in w.value for w in at.warning)
