"""G2-T2: Optionen, Kennzahlen und Figuren von EVAL (ohne Mikroptim)."""

import math

import numpy as np
import pytest

from gui_mikroptim.backend import compute, system_tables
from gui_mikroptim.views import eval_plots as ep


def test_eval_options():
    o = compute.EvalOptions()
    o.validate()
    assert o.cli_args() == ["--grid", "64", "--reference", "exit-pupil"]
    o = compute.EvalOptions(128, True, "vertex", True, 1)
    assert o.cli_args() == [
        "--grid", "128", "--reference", "vertex", "--half", "--gpu", "--device", "1",
    ]  # fmt: skip
    with pytest.raises(ValueError, match="Raster"):
        compute.EvalOptions(grid=0).validate()
    with pytest.raises(ValueError, match="Referenz"):
        compute.EvalOptions(reference="mitte").validate()


def test_mm_to_waves_like_cli():
    # dieselbe Formel wie mikroptim eval: mm / (λ · 1e-6)
    assert compute.mm_to_waves(0.0012473028031294777, 587.56) == 2.1228517991855775


def test_pupil_axis():
    np.testing.assert_allclose(ep.pupil_axis(4), [-0.75, -0.25, 0.25, 0.75])
    np.testing.assert_allclose(ep.pupil_axis(16)[:2], [-0.9375, -0.8125])


def test_opd_figure_nan_and_symmetric_scale():
    opd = np.full((4, 4), np.nan)
    opd[1:3, 1:3] = [[-0.2, 0.1], [0.05, 0.4]]
    fig = ep.opd_figure(opd)
    hm = fig.data[0]
    z = np.array(hm.z, dtype=float)
    assert np.isnan(z[0, 0]) and np.isnan(z[3, 3])  # außerhalb der Pupille leer
    assert z[2, 2] == 0.4
    assert hm.zmin == -0.4 and hm.zmax == 0.4 and hm.zmid == 0.0
    assert hm.hoverongaps is False
    assert fig.layout.yaxis.scaleanchor == "x"
    np.testing.assert_allclose(hm.x, ep.pupil_axis(4))


def test_opd_figure_all_nan_or_zero():
    assert ep.symmetric_range(np.full((2, 2), np.nan)) == 1.0
    assert ep.symmetric_range(np.zeros((2, 2))) == 1.0
    ep.opd_figure(np.full((3, 3), np.nan))  # darf nicht werfen


def test_spot_figure_units_and_failed_rays():
    x = np.array([1e-3, np.nan, -2e-3])
    y = np.array([0.0, 5e-3, 1e-3])
    fig = ep.spot_figure(x, y, centroid_mm=(1e-4, 2e-4))
    pts = fig.data[0]
    np.testing.assert_allclose(pts.x, [1.0, -2.0])  # µm, NaN entfernt
    np.testing.assert_allclose(pts.y, [0.0, 1.0])
    centroid = next(t for t in fig.data if t.name == "Schwerpunkt")
    assert centroid.x[0] == pytest.approx(0.1)
    assert fig.layout.xaxis.title.text == "x [µm]"
    assert fig.layout.yaxis.scaleanchor == "x"
    assert pts.type == "scatter"


def test_spot_figure_uses_webgl_for_many_points():
    n = ep.SCATTERGL_FROM
    fig = ep.spot_figure(np.zeros(n), np.zeros(n), centroid_mm=(math.nan, 0.0))
    assert fig.data[0].type == "scattergl"
    assert "Schwerpunkt" not in [t.name for t in fig.data]  # nicht endlich: weggelassen


def test_eval_rows():
    shape = (2, 1)
    stats = {
        k: np.zeros(shape)
        for k in [
            "rays",
            "failed",
            "image_height",
            "rms_spot",
            "centroid_x",
            "centroid_y",
            "chief_y",
            "focus_tangential",
            "focus_sagittal",
            "astigmatism",
            "defocus",
            "pv_opd",
            "rms_opd_tilt",
            "rms_opd_defocus",
        ]
    }
    stats["rms_opd"] = np.array([[0.0012473028031294777], [np.nan]])
    stats["distortion_chief"] = np.array([[np.nan], [-0.0055]])
    stats["distortion_centroid"] = np.array([[np.nan], [0.52]])
    stats["rays"] = np.array([[812.0], [812.0]])
    stats["failed"] = np.array([[0.0], [3.0]])
    rows = system_tables.eval_rows(stats, 587.56, [0.0, 1.0])
    assert rows[0]["RMS-OPD [W]"] == 2.1228517991855775
    assert rows[0]["Verzeichnung HS [%]"] is None  # auf der Achse nicht endlich, wie null
    assert rows[1]["RMS-OPD [W]"] is None
    assert rows[1]["versagt"] == 3 and isinstance(rows[1]["Strahlen"], int)
    assert rows[1]["Feldwinkel [°]"] == 1.0
