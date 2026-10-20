"""G2-T4: Vergleichbarkeit, Differenz und Paraxialvergleich (ohne Mikroptim)."""

import math
from types import SimpleNamespace

import numpy as np
import pytest

from gui_mikroptim.backend import compare
from gui_mikroptim.views.wavefront_plots import rms_difference_heatmap


def _sys(fields=(0.0, 1.0), wls=(486.13, 587.56), ref=587.56):
    return SimpleNamespace(
        field_angles_deg=np.array(fields), wavelengths_nm=np.array(wls), reference_nm=ref
    )


def _res(rms, failed=None):
    rms = np.array(rms, dtype=float)
    return SimpleNamespace(
        rms_waves=rms, failed=np.zeros(rms.shape, dtype=int) if failed is None else np.array(failed)
    )


def test_comparability_same():
    assert compare.comparability(_sys(), _sys()).same_grid


@pytest.mark.parametrize(
    ("b", "word"),
    [
        (_sys(fields=(0.0, 2.0)), "Feldwinkel"),
        (_sys(fields=(0.0,)), "Feldwinkel"),
        (_sys(wls=(486.13, 656.27)), "Wellenlängen"),
        (_sys(ref=486.13), "Referenzwellenlänge"),
    ],
)
def test_comparability_reasons(b, word):
    check = compare.comparability(_sys(), b)
    assert not check.same_grid
    assert len(check.reasons) == 1 and check.reasons[0].startswith(word)


def test_comparability_several_reasons():
    check = compare.comparability(_sys(), _sys(fields=(1.0,), wls=(500.0,), ref=500.0))
    assert len(check.reasons) == 3


def test_rms_difference_and_rows():
    a = _res([[0.5, 0.25], [math.nan, 1.0]])
    b = _res([[0.4, 0.5], [0.2, 1.0]], failed=[[0, 0], [0, 2]])
    np.testing.assert_allclose(compare.rms_difference(a, b)[0], [-0.1, 0.25])
    rows = compare.rms_compare_rows(a, b, [0.0, 1.0], [486.13, 587.56])
    assert rows[1]["Δ B − A [W]"] == pytest.approx(0.25)
    assert rows[2]["RMS A [W]"] is None and rows[2]["Δ B − A [W]"] is None
    assert rows[3]["Δ B − A [W]"] == 0.0 and rows[3]["versagt B"] == 2


def test_rms_difference_shape_mismatch():
    with pytest.raises(ValueError, match="Formen"):
        compare.rms_difference(_res([[1.0]]), _res([[1.0, 2.0]]))


def test_paraxial_compare_rows():
    pa = {"focal_length": 100.0, "afocal": False, "exit_pupil": {"position": -9.5}, "abcd": [1, 0]}
    pb = {"focal_length": None, "afocal": True, "exit_pupil": {"position": -8.0}, "neu": 3}
    rows = {r["Schlüssel"]: r for r in compare.paraxial_compare_rows(pa, pb)}
    assert rows["focal_length"]["A"] == "100" and rows["focal_length"]["B"] == "–"
    assert rows["focal_length"]["Δ B − A"] == ""  # B nicht endlich bzw. None
    assert rows["exit_pupil.position"]["Δ B − A"] == "1.5"
    assert rows["afocal"]["Δ B − A"] == ""  # Wahrheitswerte werden nicht subtrahiert
    assert rows["abcd"]["A"] == "[1, 0]" and rows["abcd"]["B"] == "–"
    assert rows["neu"]["A"] == "–" and rows["neu"]["B"] == "3"
    assert rows["focal_length"]["Größe"] == "Brennweite f"
    assert compare.paraxial_compare_rows(None, None) == []


def test_difference_heatmap():
    fig = rms_difference_heatmap(
        np.array([[-0.2, 0.1], [math.nan, 0.05]]), ["F0", "F1"], ["a", "b"]
    )
    hm = fig.data[0]
    assert hm.zmin == -0.2 and hm.zmax == 0.2 and hm.zmid == 0.0
    assert hm.text[0][0] == "-0.2" and hm.text[0][1] == "+0.1" and hm.text[1][0] == "–"
    assert hm.z[1][0] is None
