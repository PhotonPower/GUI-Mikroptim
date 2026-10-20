"""G2-T3: Optionen, Fensterregel und Figuren der PSF (ohne Mikroptim)."""

from pathlib import Path

import numpy as np
import pytest

from gui_mikroptim.backend import compute
from gui_mikroptim.views import psf_plots as pp


def _result(**overrides):
    base = dict(
        field=1, wavelength=0, wavelength_nm=486.13, model="scalar",
        psf=np.zeros((8, 8)), dx=0.001, dy=0.001, fft_size=8,
        frequencies=np.linspace(0, 1, 5), mtf_sagittal=np.array([1, 0.8, 0.5, 0.2, 0.0]),
        mtf_tangential=np.array([1, 0.7, 0.4, 0.1, 0.0]), cutoff_x=700.0, cutoff_y=710.0,
        na_x=0.2, na_y=0.2, airy_radius=0.0015, strehl=0.5, strehl_fft=0.6, strehl_origin=0.6,
        peak=0.6, peak_position=(0.0, 0.0), energy=1.0, backend="cpu",
    )  # fmt: skip
    base.update(overrides)
    return compute.PsfResult(**base)


def _stats(cx=0.0, cy=0.0, rms=0.0):
    return {
        "centroid_x": np.array([[0.0], [cx]]),
        "centroid_y": np.array([[0.0], [cy]]),
        "rms_spot": np.array([[0.0], [rms]]),
    }


def test_psf_options():
    o = compute.PsfOptions()
    o.validate()
    assert o.cli_args() == ["--psf", "--padding", "4.0"]
    assert compute.PsfOptions(6.0, 0.15).cli_args() == ["--psf", "--padding", "6.0", "--na", "0.15"]
    with pytest.raises(ValueError, match="Padding"):
        compute.PsfOptions(padding=1.0).validate()
    with pytest.raises(ValueError, match="NA"):
        compute.PsfOptions(numerical_aperture=-0.1).validate()


def test_vector_options():
    v = compute.VectorOptions("circular", 0.002)
    v.validate()
    assert v.cli_args() == ["--vector", "--polarization", "circular", "--defocus", "0.002"]
    with pytest.raises(ValueError, match="Polarisation"):
        compute.VectorOptions("radial").validate()


def test_vector_grid_limit(tmp_path: Path):
    with pytest.raises(ValueError, match="als Job"):
        compute.vector_psf(
            tmp_path / "s.json",
            compute.EvalOptions(grid=compute.VECTOR_GRID_LIMIT + 8),
            compute.PsfOptions(),
            compute.VectorOptions(),
            0,
            0,
        )


def test_mtf_half_cutoff_and_na_limit():
    r = _result()
    assert r.mtf_half_cutoff == (0.5, 0.4)  # Stützstelle ν = 0,5
    assert not r.scalar_na_too_high
    assert _result(na_y=0.61).scalar_na_too_high
    assert not _result(na_y=0.9, model="vector").scalar_na_too_high


@pytest.mark.parametrize(
    ("stats", "expected"),
    [
        (_stats(0.0, 0.002, 0.0005), None),  # 0,0035 ≤ 0,004
        (_stats(0.0, 0.003, 0.0005), (0.0045, 0.004)),  # y reicht hinaus
        (_stats(-0.0035, 0.0, 0.0002), (0.0041, 0.004)),  # x, Betrag des Schwerpunkts
    ],
)
def test_window_warning_rule(stats, expected):
    # halbes Fenster 0,5 · 8 · 0,001 = 0,004 mm in beiden Richtungen
    got = compute.window_warning(_result(), stats)
    if expected is None:
        assert got is None
    else:
        assert got == pytest.approx(expected)


def test_window_warning_uses_smaller_half_window():
    got = compute.window_warning(_result(dy=0.0005), _stats(0.0, 0.0, 0.0014))
    assert got == pytest.approx((0.0042, 0.002))


def test_read_csv_matrix_flips_rows(tmp_path: Path):
    path = tmp_path / "m.csv"
    path.write_text("1,2\n3,\n", encoding="utf-8")  # erste Zeile = größtes y
    m = compute._read_csv_matrix(path)
    assert m[0, 0] == 3 and np.isnan(m[0, 1]) and m[1, 1] == 2


def test_psf_axes_centered():
    x, y = pp.psf_axes(8, 0.5, 0.25)
    assert x[4] == 0.0 and x[0] == -2.0 and x[-1] == 1.5
    assert y[4] == 0.0 and y[0] == -1.0


def test_crop():
    psf = np.arange(64.0).reshape(8, 8)
    x, y = pp.psf_axes(8, 1.0, 1.0)
    z, xc, yc = pp.crop(psf, x, y, 1.0)
    assert list(xc) == [-1.0, 0.0, 1.0] and list(yc) == [-1.0, 0.0, 1.0]
    assert z.shape == (3, 3)
    assert z[1, 1] == psf[4, 4]
    assert pp.crop(psf, x, y, None)[0] is psf


def test_psf_figure_log_floor_and_units():
    psf = np.zeros((4, 4))
    psf[2, 2] = 0.5
    fig = pp.psf_figure(psf, 0.001, 0.001, log=True)
    z = np.array(fig.data[0].z)
    assert z.min() == np.log10(pp.LOG_FLOOR)
    assert z[2, 2] == pytest.approx(np.log10(0.5))
    assert fig.data[0].x[2] == 0.0 and fig.data[0].x[0] == pytest.approx(-2.0)  # µm
    assert fig.layout.yaxis.scaleanchor == "x"


def test_mtf_figure():
    r = _result()
    fig = pp.mtf_figure(r.frequencies, r.mtf_sagittal, r.mtf_tangential, 700.0, 710.0)
    sag, tan = fig.data
    assert list(sag.x) == [0.0, 175.0, 350.0, 525.0, 700.0]  # f = ν · f_c,x
    assert tan.x[-1] == 710.0
    lines = [s for s in fig.layout.shapes if s.type == "line"]
    assert sorted(s.x0 for s in lines) == [355.0, 710.0]
