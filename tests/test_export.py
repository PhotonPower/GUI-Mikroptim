"""G5-T3: Exporte erzeugen und wieder lesen (ohne Mikroptim)."""

import csv
import io
import math
from types import SimpleNamespace

import numpy as np

from gui_mikroptim.backend import export


def test_rows_to_csv_roundtrip_full_precision():
    rows = [
        {"Feld": 0, "RMS [Wellen]": 0.1 + 0.2, "Status": "ok"},
        {"Feld": 1, "RMS [Wellen]": None, "extra": math.nan, "Status": "a,b"},
        {"Feld": 2, "RMS [Wellen]": math.inf, "Status": 'mit "Anführung"'},
    ]
    text = export.rows_to_csv(rows)
    back = list(csv.DictReader(io.StringIO(text)))
    assert list(back[0]) == ["Feld", "RMS [Wellen]", "Status", "extra"]
    assert float(back[0]["RMS [Wellen]"]) == 0.1 + 0.2  # bitgleich über repr
    assert back[1]["RMS [Wellen]"] == "" and back[1]["extra"] == "nan"
    assert back[1]["Status"] == "a,b" and back[2]["Status"] == 'mit "Anführung"'
    assert back[2]["RMS [Wellen]"] == "inf"


def test_markdown_table_escapes():
    text = export.markdown_table([{"a": "x|y", "b": 1.23456789012, "c": None}])
    lines = text.splitlines()
    assert lines[0] == "| a | b | c |" and lines[1] == "|---|---|---|"
    assert lines[2] == "| x\\|y | 1.2345679 | – |"
    assert export.markdown_table([]) == "_keine Einträge_\n"


def test_safe_stem_and_plotly_config():
    assert export.safe_stem("auswertung.eval.opd") == "auswertung_eval_opd"
    assert export.safe_stem("../ä b") == "b"
    assert export.safe_stem("...") == "export"
    cfg = export.plotly_config("auswertung.psf.E_x")
    assert cfg["displaylogo"] is False
    assert cfg["toImageButtonOptions"] == {
        "format": "svg",
        "filename": "auswertung_psf_E_x",
        "scale": 2,
    }


def _system():
    return SimpleNamespace(
        name="Testlinse", description="frei erfunden", reference_nm=587.56,
        source_type="collimated", warnings=["Achtung"], num_surfaces=2,
        surface_types=["stop", "plane"], curvatures=np.array([0.0, 0.0]),
        thicknesses=np.array([5.0, 10.0]), semi_diameters=np.array([2.0, 3.0]),
        materials=["AIR", "AIR"], wavelengths_nm=np.array([587.56]),
        wavelength_weights=np.array([1.0]), field_angles_deg=np.array([0.0]),
        field_weights=np.array([1.0]), indices=np.array([[1.0], [1.0]]),
    )  # fmt: skip


def test_system_report_sections():
    wf = SimpleNamespace(
        rings=10, spokes=8, backend="cpu", precision="fp64",
        rms_waves=np.array([[0.25]]), rms_mm=np.array([[1e-4]]), piston_mm=np.array([[0.0]]),
        rays=np.array([[80]]), failed=np.array([[0]]), image_points=np.array([[0, 0, 1.0]]),
        pupil_modes=["axis"], wavelengths_nm=np.array([587.56]), reference_nm=587.56,
    )  # fmt: skip
    text = export.system_report(
        _system(), {"surfaces": [{}, {}]}, {"focal_length": 100.0, "afocal": False},
        [{"name": "d[1]", "type": "thickness", "value": 10.0}], wf, "linse.json", "0.1.0",
    )  # fmt: skip
    assert text.startswith("# Testlinse\n")
    for heading in ("## Flächen", "## Spektrum", "## Felder", "## Paraxialdaten",
                    "## Variablen", "## RMS-Wellenfront"):  # fmt: skip
        assert heading in text
    assert "| Brennweite f | 100 | mm |" in text
    assert "> **Warnung:** Achtung" in text
    assert "Datei: `linse.json` · Mikroptim 0.1.0" in text
    assert "| 0 | 0 | 587.56 | 80 | 0 | 0.25 |" in text


def test_system_report_without_paraxial_and_wavefront():
    text = export.system_report(_system(), {}, None)
    assert "_nicht verfügbar_" in text and "## RMS-Wellenfront" not in text
