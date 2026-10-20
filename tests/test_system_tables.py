import math
from types import SimpleNamespace

import numpy as np
import pytest

from gui_mikroptim.backend import system_tables as t


def _system():
    return SimpleNamespace(
        num_surfaces=3,
        surface_types=["stop", "sphere", "plane"],
        curvatures=np.array([0.0, 0.05, 0.0]),
        thicknesses=np.array([5.0, 4.0, 20.0]),
        semi_diameters=np.array([2.0, 3.0, 3.0]),
        materials=["AIR", "buchdahl", "AIR"],
        wavelengths_nm=np.array([486.13, 587.56]),
        wavelength_weights=np.array([1.0, 2.0]),
        reference_nm=587.56,
        field_angles_deg=np.array([0.0, 2.5]),
        field_weights=np.array([1.0, 0.5]),
        indices=np.array([[1.0, 1.0], [1.52, 1.51], [1.0, 1.0]]),
    )


def _data():
    return {
        "surfaces": [
            {"type": "stop", "material": "AIR"},
            {
                "type": "sphere",
                "material": {"model": "buchdahl", "n0": 1.5, "nu": [-0.1, 0.02, 0.0]},
                "decenter": [0.0, 0.01],
                "tilt_deg": [0.0, 0.08],
                "comment": "Linse",
            },
            {"type": "plane", "material": "AIR"},
        ]
    }


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (math.inf, "∞"),
        (-math.inf, "−∞"),
        (math.nan, "NaN"),
        (None, "–"),
        (True, "ja"),
        (False, "nein"),
        (3, "3"),
        (101.04968094724019, "101.05"),
        ("x", "x"),
    ],
)
def test_fmt_number(value, text):
    assert t.fmt_number(value, 5) == text


def test_radius_text():
    assert t.radius_text(0.0) == "∞"
    assert t.radius_text(0.05) == "20"
    assert t.radius_text(-0.00967) == "-103.413"


@pytest.mark.parametrize(
    ("material", "text"),
    [
        ("N-BK7", "N-BK7"),
        ({"model": "constant", "n": 1.72}, "konstant n = 1.72"),
        (
            {"model": "buchdahl", "n0": 1.5, "nu": [-0.1, 0.02]},
            "Buchdahl n₀ = 1.5, ν = [-0.1, 0.02]",
        ),
        ({"model": "neu"}, "neu"),
        (None, "–"),
    ],
)
def test_material_text(material, text):
    assert t.material_text(material) == text


def test_surface_rows():
    rows = t.surface_rows(_system(), _data())
    assert [r["Typ"] for r in rows] == ["stop", "sphere", "plane"]
    lens = rows[1]
    assert lens["Radius [mm]"] == "20"
    assert lens["Material danach"].startswith("Buchdahl n₀ = 1.5")
    assert lens["n(486.13 nm)"] == 1.52
    assert lens["n(587.56 nm)"] == 1.51
    assert lens["Dezentrierung [mm]"] == "0, 0.01"
    assert lens["Verkippung [°]"] == "0, 0.08"
    assert lens["Kommentar"] == "Linse"
    assert rows[0]["Radius [mm]"] == "∞"
    assert rows[0]["Dezentrierung [mm]"] == ""


def test_surface_rows_without_dict_entries():
    rows = t.surface_rows(_system(), {})
    assert rows[1]["Material danach"] == "buchdahl"


def test_spectrum_and_field_rows():
    spec = t.spectrum_rows(_system())
    assert [r["Referenz"] for r in spec] == ["", "λ_ref"]
    assert spec[1]["Gewicht"] == 2.0
    fields = t.field_rows(_system())
    assert fields[1] == {"Nr.": 1, "Feldwinkel [°]": 2.5, "Gewicht": 0.5}


def test_paraxial_rows():
    rows = t.paraxial_rows(
        {
            "focal_length": math.inf,
            "afocal": True,
            "exit_pupil": {"position": -9.5, "at_infinity": False},
            "abcd": [1.0, 0.0, 0.0, 1.0],
            "neues_feld": 7,
        }
    )
    by_key = {r["Schlüssel"]: r for r in rows}
    assert by_key["focal_length"]["Wert"] == "∞"
    assert by_key["focal_length"]["Größe"] == "Brennweite f"
    assert by_key["focal_length"]["Einheit"] == "mm"
    assert by_key["afocal"]["Wert"] == "ja"
    assert by_key["exit_pupil.position"]["Größe"] == "Austrittspupille: Lage"
    assert by_key["abcd"]["Wert"] == "[1, 0, 0, 1]"
    assert by_key["neues_feld"]["Größe"] == "neues_feld"  # unbekannte Felder bleiben sichtbar


def test_variable_rows():
    rows = t.variable_rows(
        [{"name": "c[1]", "type": "curvature", "surface": 1, "lower": -0.05, "value": 0.01}]
    )
    assert rows[0]["Name"] == "c[1]"
    assert rows[0]["untere Schranke"] == -0.05
    assert rows[0]["obere Schranke"] is None
