"""G2-T1: Optionen, Tabellenzeilen und Heatmap der RMS-Wellenfront (ohne Mikroptim)."""

import math
from types import SimpleNamespace

import numpy as np
import pytest

from gui_mikroptim.backend import compute, system_tables
from gui_mikroptim.views import wavefront_plots as wp


def _result():
    return SimpleNamespace(
        rms_waves=np.array([[0.5, 0.25], [math.nan, 1.5]]),
        rms_mm=np.array([[2e-4, 1e-4], [math.nan, 6e-4]]),
        piston_mm=np.array([[1.0, 1.1], [1.2, 1.3]]),
        rays=np.array([[6, 6], [48, 48]]),
        failed=np.array([[0, 0], [48, 3]]),
        image_points=np.array([[0, 0, 10], [0, 0.5, 10]], dtype=float),
        pupil_modes=["axis", "half"],
        wavelengths_nm=np.array([486.13, 587.56]),
        reference_nm=587.56,
    )


def test_options_defaults_and_cli_args():
    o = compute.TraceOptions()
    o.validate()
    assert (o.rings, o.spokes, o.gpu, o.precision) == (10, 8, False, "fp64")
    assert o.cli_args() == ["--rings", "10", "--spokes", "8"]
    g = compute.TraceOptions(4, 6, True, 1, "df64")
    assert g.cli_args() == [
        "--rings", "4", "--spokes", "6", "--gpu", "--device", "1", "--precision", "df64",
    ]  # fmt: skip
    assert "GPU 1, df64" in g.label()


@pytest.mark.parametrize(
    ("options", "message"),
    [
        (compute.TraceOptions(rings=0), "Ringe"),
        (compute.TraceOptions(spokes=300), "Speichen"),
        (compute.TraceOptions(precision="fp32"), "unbekannt"),
        (compute.TraceOptions(precision="df64"), "nur mit GPU"),
    ],
)
def test_options_validation(options, message):
    with pytest.raises(ValueError, match=message):
        options.validate()


def test_wavefront_rows_order_and_nonfinite():
    rows = system_tables.wavefront_rows(_result(), [0.0, 2.0])
    assert [(r["Feld"], r["λ [nm]"]) for r in rows] == [
        (0, 486.13),
        (0, 587.56),
        (1, 486.13),
        (1, 587.56),
    ]
    assert rows[2]["RMS [Wellen]"] is None  # kein gültiger Strahl, wie null in der CLI
    assert rows[2]["RMS [mm]"] is None
    assert rows[3]["versagt"] == 3
    assert rows[3]["Feldwinkel [°]"] == 2.0
    assert rows[3]["Pupille"] == "half"
    assert rows[3]["Bildpunkt y [mm]"] == 0.5


def test_heatmap_cells_and_labels():
    fig = wp.rms_heatmap(_result(), [0.0, 2.0])
    hm = fig.data[0]
    assert list(hm.y) == ["F0 (0°)", "F1 (2°)"]
    assert list(hm.x) == ["486.13 nm", "587.56 nm (λ_ref)"]
    assert list(hm.z[0]) == [0.5, 0.25]
    assert hm.z[1][0] is None
    assert hm.text[1][0] == "–<br>⚠ 48 versagt"
    assert hm.text[1][1] == "1.5<br>⚠ 3 versagt"
    assert fig.layout.yaxis.autorange == "reversed"


def test_field_labels_without_angles():
    assert wp.field_labels(2) == ["F0", "F1"]
