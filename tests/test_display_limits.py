"""G5-T2: Begrenzung der Anzeige (ohne Mikroptim)."""

import math

import numpy as np
import pytest

from gui_mikroptim.views import display_limits as dl
from gui_mikroptim.views.eval_plots import opd_figure, spot_figure
from gui_mikroptim.views.psf_plots import psf_figure


def test_small_grid_unchanged():
    z = np.arange(16.0).reshape(4, 4)
    out, _x, _y, k = dl.reduce_grid(z, np.arange(4.0), np.arange(4.0), "mean")
    assert k == 1 and out is not None and np.array_equal(out, z)


def test_mean_ignores_nan_and_keeps_empty_blocks():
    z = np.array([[1.0, 3.0, np.nan, np.nan], [5.0, np.nan, np.nan, np.nan]])
    out, x, y, k = dl.reduce_grid(z, np.arange(4.0), np.arange(2.0), "mean", max_side=2)
    assert k == 2 and out.shape == (1, 2)
    assert out[0, 0] == 3.0  # Mittel aus 1, 3, 5
    assert math.isnan(out[0, 1])  # ganz außerhalb der Pupille
    np.testing.assert_allclose(x, [0.5, 2.5])
    np.testing.assert_allclose(y, [0.5])


def test_max_and_padding():
    z = np.zeros((5, 5))
    z[4, 4] = 7.0
    out, x, _y, k = dl.reduce_grid(z, np.arange(5.0), np.arange(5.0), "max", max_side=2)
    assert k == 3 and out.shape == (2, 2)
    assert out[1, 1] == 7.0  # Rand mit NaN aufgefüllt, Spitze erhalten
    np.testing.assert_allclose(x, [1.0, 4.0])
    with pytest.raises(ValueError):
        dl.reduce_grid(z, np.arange(5.0), np.arange(5.0), "median", max_side=2)


def test_thin_points():
    x, y, k = dl.thin_points(np.arange(10), np.arange(10) * 2, max_points=3)
    assert list(y) == [0, 8, 16]
    assert k == 4 and list(x) == [0, 4, 8]
    x, _y, k = dl.thin_points(np.arange(3), np.arange(3), max_points=3)
    assert k == 1 and len(x) == 3


def test_figures_are_bounded():
    big = np.random.default_rng(0).normal(size=(1024, 1024))
    big[:10, :10] = np.nan
    fig = opd_figure(big)
    assert np.asarray(fig.data[0].z).shape == (512, 512)
    assert "Mittel über 2 × 2" in fig.layout.title.text
    assert fig.data[0].zmax == pytest.approx(np.nanmax(np.abs(big)))  # Skala aus vollen Daten

    psf = np.zeros((2048, 2048))
    psf[1024, 1024] = 0.9
    fig = psf_figure(psf, 1e-4, 1e-4)
    z = np.asarray(fig.data[0].z, dtype=float)
    assert z.shape == (512, 512) and z.max() == 0.9  # Spitze bleibt sichtbar

    n = 200_000
    fig = spot_figure(np.zeros(n), np.zeros(n))
    assert len(fig.data[0].x) == dl.MAX_POINTS
    assert "jeder 4. von 200000 Punkten" in fig.layout.title.text
