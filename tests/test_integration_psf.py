"""G2-T3 gegen ein installiertes Mikroptim (``python -m pytest -m integration``)."""

import csv
import json
import os
import re
from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from conftest import needs_uploader
from gui_mikroptim.backend import compute, mko

pytestmark = pytest.mark.integration

REPO = os.environ.get("MKO_GUI_MIKROPTIM_REPO")
WARNING = re.compile(
    r"PSF Feld (\d+), Wellenlänge (\d+): geometrischer Spot \(([^ ]+) mm\) größer als das halbe "
    r"Bildfenster \(([^ ]+) mm\)"
)


@pytest.fixture
def repo(monkeypatch) -> Path:
    if not REPO:
        pytest.skip("MKO_GUI_MIKROPTIM_REPO nicht gesetzt")
    monkeypatch.setenv("MKO_GUI_MIKROPTIM_REPO", REPO)
    return Path(REPO)


CASES = [
    ("einzellinse_bk7.json", compute.EvalOptions(grid=64), compute.PsfOptions()),
    ("testsystem_mehrlinser.json", compute.EvalOptions(grid=64), compute.PsfOptions(padding=6.0)),
    (
        "testsystem_mehrlinser_dezentriert.json",
        compute.EvalOptions(grid=32, reference="vertex"),
        compute.PsfOptions(numerical_aperture=0.15),
    ),
]


@pytest.mark.parametrize(("name", "eval_options", "psf_options"), CASES)
def test_scalar_psf_identical_to_cli(repo, name, eval_options, psf_options):
    """Strehl, MTF bei f_c/2 und alle PSF-Kennzahlen bitgleich zu `eval --psf --json`;
    Fensterwarnungen für dieselben Tupel und mit denselben Zahlen wie die CLI."""
    path = repo / "data" / "systems" / name
    ev = compute.evaluate(compute.load_system(path), eval_options)
    code, out, err = mko.require().run_cli(
        ["eval", str(path), "--json", *eval_options.cli_args(), *psf_options.cli_args()]
    )
    assert code == 0, err
    cli = json.loads(out)
    assert cli["psf"]["model"] == "scalar"
    ours_warnings = {}
    for tup in cli["tuples"]:
        r = compute.scalar_psf(ev, tup["field"], tup["wavelength"], psf_options)
        p = tup["psf"]
        assert r.fft_size == cli["psf"]["fft_size"]
        assert [r.na_x, r.na_y] == p["na"]
        assert [r.dx, r.dy] == p["pixel_mm"]
        assert r.airy_radius == p["airy_radius_mm"]
        assert (r.strehl, r.strehl_origin, r.strehl_fft) == (
            p["strehl"],
            p["strehl_origin"],
            p["strehl_fft"],
        )
        assert r.peak == p["peak"] and list(r.peak_position) == p["peak_mm"]
        assert r.energy == p["energy"]
        assert [r.cutoff_x, r.cutoff_y] == p["cutoff_lpmm"]
        assert list(r.mtf_half_cutoff) == p["mtf_half_cutoff"]
        w = compute.window_warning(r, ev.stats)
        if w is not None:
            ours_warnings[(tup["field"], tup["wavelength"])] = (f"{w[0]:.3e}", f"{w[1]:.3e}")
    theirs = {
        (int(m[1]), int(m[2])): (m[3], m[4])
        for m in (WARNING.match(w) for w in cli["warnings"])
        if m
    }
    assert ours_warnings == theirs


def test_psf_and_mtf_arrays_identical_to_cli_files(repo, tmp_path):
    path = repo / "data" / "systems" / "testsystem_mehrlinser.json"
    eval_options, psf_options = compute.EvalOptions(grid=32), compute.PsfOptions()
    ev = compute.evaluate(compute.load_system(path), eval_options)
    r = compute.scalar_psf(ev, 1, 2, psf_options)
    code, _, err = mko.require().run_cli(
        ["eval", str(path), *eval_options.cli_args(), *psf_options.cli_args(),
         "--psf-tuple", "1,2", "--psf-file", str(tmp_path / "psf.csv"),
         "--mtf-file", str(tmp_path / "mtf.csv")]
    )  # fmt: skip
    assert code == 0, err
    assert np.array_equal(compute._read_csv_matrix(tmp_path / "psf.csv"), r.psf)
    with (tmp_path / "mtf.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [float(x["nu"]) for x in rows] == list(r.frequencies)
    assert [float(x["mtf_sagittal"]) for x in rows] == list(r.mtf_sagittal)
    assert [float(x["mtf_tangential"]) for x in rows] == list(r.mtf_tangential)
    assert [float(x["f_sagittal_lpmm"]) for x in rows] == list(r.frequencies * r.cutoff_x)


def test_vector_psf(repo):
    path = repo / "data" / "systems" / "testsystem_mehrlinser.json"
    eval_options = compute.EvalOptions(grid=32)
    psf_options = compute.PsfOptions()
    vec = compute.VectorOptions("circular", 0.0)
    r = compute.vector_psf(path, eval_options, psf_options, vec, 1, 1)
    code, out, err = mko.require().run_cli(
        ["eval", str(path), "--json", *eval_options.cli_args(), *psf_options.cli_args(),
         *vec.cli_args()]
    )  # fmt: skip
    assert code == 0, err
    cli = json.loads(out)
    assert cli["psf"]["model"] == "vector" and cli["psf"]["polarization"] == "circular"
    p = next(t["psf"] for t in cli["tuples"] if (t["field"], t["wavelength"]) == (1, 1))
    assert (r.strehl, r.strehl_fft, r.peak) == (p["strehl"], p["strehl_fft"], p["peak"])
    assert r.vector == p["vector"]
    assert list(r.mtf_half_cutoff) == p["mtf_half_cutoff"]
    assert r.psf.shape == (r.fft_size, r.fft_size)
    assert all(c.shape == r.psf.shape for c in r.components)
    assert r.model == "vector" and not r.scalar_na_too_high


def _page(app_file, name="testsystem_mehrlinser.json"):
    at = AppTest.from_file(str(app_file), default_timeout=60).run()
    at.switch_page("pages/auswertung.py").run()
    source = at.selectbox(key="auswertung.quelle")
    source.select_index(source.options.index("Beispielsysteme (Mikroptim)")).run()
    box = next(s for s in at.selectbox if s.label.startswith("Datei"))
    box.select_index(box.options.index(name)).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


@needs_uploader
def test_page_scalar_vector_and_warnings(app_file, workspace, repo):
    at = _page(app_file)
    keys = [c.key for c in at.get("plotly_chart")]
    assert "auswertung.psf.psf" in keys and "auswertung.psf.mtf" in keys
    assert "Strehl" in [m.label for m in at.metric]

    at.selectbox(key="auswertung.psf.feld").set_value(2).run()
    at.selectbox(key="auswertung.psf.wl").set_value(0).run()
    assert any(
        "Geometrischer Spot (6.280e-02 mm)" in w.value and "(3.985e-02 mm)" in w.value
        for w in at.warning
    )  # dieselben Zahlen wie die Warnung von mikroptim eval

    at.toggle(key="auswertung.psf.log").set_value(True).run()
    at.radio(key="auswertung.psf.modell").set_value("vektoriell").run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]
    keys = [c.key for c in at.get("plotly_chart")]
    assert {"auswertung.psf.E_x", "auswertung.psf.E_y", "auswertung.psf.E_z"} <= set(keys)
    assert any("FWHM" in c.value for c in at.caption)
    assert any("--vector --polarization x" in c.value for c in at.caption)


@needs_uploader
def test_page_scalar_na_hint(app_file, workspace, repo):
    at = _page(app_file, "einzellinse_bk7.json")
    at.number_input(key="auswertung.psf.na").set_value(0.8).run()
    assert not at.exception
    assert any("skalare Näherung ist hier ungenau" in w.value for w in at.warning)
