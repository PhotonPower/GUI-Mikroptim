"""G1-T3: Geometrie und Figur des Linsenschnitts, ohne Streamlit und ohne Mikroptim."""

import math

import numpy as np
import pytest

from gui_mikroptim.views import lens_plot as lp


def _stop(h=5.0, t=10.0):
    return {"type": "stop", "thickness": t, "material": "AIR", "semi_diameter": h}


def _plate_system(t_glass=4.0, h=8.0):
    return {
        "surfaces": [
            _stop(),
            {"type": "plane", "thickness": t_glass, "material": "N-BK7", "semi_diameter": h},
            {"type": "plane", "thickness": 20.0, "material": "AIR", "semi_diameter": h},
        ]
    }


def _biconvex(radius=50.0, h=10.0, t=5.0):
    return {
        "surfaces": [
            _stop(),
            {
                "type": "sphere",
                "curvature": 1 / radius,
                "thickness": t,
                "material": {"model": "constant", "n": 1.5},
                "semi_diameter": h,
            },
            {
                "type": "sphere",
                "curvature": -1 / radius,
                "thickness": 40.0,
                "material": "AIR",
                "semi_diameter": h,
            },
        ]
    }


@pytest.mark.parametrize("c", [0.0, 0.02, -0.02, 0.5, -0.81])
def test_sag_matches_closed_formula(c):
    y = np.linspace(-1.0, 1.0, 21) * (0.999 / abs(c) if c else 3.0)
    expected = np.zeros_like(y) if c == 0 else (1 / c) - np.sign(c) * np.sqrt(1 / c**2 - y**2)
    np.testing.assert_allclose(lp.sag(c, y), expected, rtol=0, atol=1e-12)


def test_plane_plate_is_rectangle():
    g = lp.outline(_plate_system(t_glass=4.0, h=8.0))
    assert [s.vertex_z for s in g.surfaces] == [0.0, 10.0, 14.0]
    assert g.elements == [(1, 2)]
    z, y = g.element_polygon(1, 2)
    assert set(np.round(z, 12)) == {10.0, 14.0}
    assert y.max() == pytest.approx(8.0)
    assert y.min() == pytest.approx(-8.0)
    # geschlossener Umriss
    assert (z[0], y[0]) == (z[-1], y[-1])
    assert g.image_z == pytest.approx(34.0)
    assert g.notes == []


def test_biconvex_vertices_and_edges():
    radius, h, t = 50.0, 10.0, 5.0
    g = lp.outline(_biconvex(radius, h, t))
    s1, s2 = g.surfaces[1], g.surfaces[2]
    edge_sag = radius - math.sqrt(radius**2 - h**2)  # geschlossene Formel, 1.0102 mm
    # Scheitel in der Mitte der Abtastung
    mid = len(s1.y) // 2
    assert s1.y[mid] == pytest.approx(0.0, abs=1e-12)
    assert s1.z[mid] == pytest.approx(10.0)
    assert s2.z[mid] == pytest.approx(10.0 + t)
    # Randpunkte: erste Fläche nach +z, zweite nach −z (bikonvex)
    assert s1.y[0] == pytest.approx(h)
    assert s1.z[0] == pytest.approx(10.0 + edge_sag, abs=1e-12)
    assert s1.z[-1] == pytest.approx(10.0 + edge_sag, abs=1e-12)
    assert s2.z[0] == pytest.approx(10.0 + t - edge_sag, abs=1e-12)
    # Randdicke t − 2·Pfeilhöhe
    assert s2.z[0] - s1.z[0] == pytest.approx(t - 2 * edge_sag, abs=1e-12)
    assert g.elements == [(1, 2)]


def test_half_diameter_larger_than_radius_is_clipped():
    data = _biconvex(radius=1.0, h=1.3, t=2.0)
    g = lp.outline(data)
    assert g.surfaces[1].clipped and g.surfaces[2].clipped
    assert np.max(np.abs(g.surfaces[1].y)) == pytest.approx(1.0)
    assert any("Fläche 1" in n and "Halbkugel" in n for n in g.notes)


def test_decenter_shifts_profile_in_y():
    data = _biconvex()
    data["surfaces"][1]["decenter"] = [0.3, 0.5]  # Δx nicht sichtbar, Δy verschiebt
    ref = lp.outline(_biconvex()).surfaces[1]
    moved = lp.outline(data).surfaces[1]
    assert moved.transformed and not ref.transformed
    np.testing.assert_allclose(moved.y, ref.y + 0.5, atol=1e-12)
    np.testing.assert_allclose(moved.z, ref.z, atol=1e-12)


def test_tilt_rotates_about_vertex():
    alpha = 2.0
    data = _biconvex()
    data["surfaces"][1]["tilt_deg"] = [alpha, 0.0]
    ref = lp.outline(_biconvex()).surfaces[1]
    tilted = lp.outline(data).surfaces[1]
    a = math.radians(alpha)
    zl = ref.z - ref.vertex_z
    np.testing.assert_allclose(tilted.y, ref.y * math.cos(a) - zl * math.sin(a), atol=1e-12)
    np.testing.assert_allclose(
        tilted.z - tilted.vertex_z, ref.y * math.sin(a) + zl * math.cos(a), atol=1e-12
    )
    mid = len(ref.y) // 2  # Drehpunkt ist der Scheitel
    assert (tilted.y[mid], tilted.z[mid]) == pytest.approx((0.0, ref.vertex_z))


def test_ghost_plates_positions():
    data = _plate_system()
    data["ghost_plates"] = [
        {"after_surface": 0, "distance": 1.0, "norm_radius": 4.0},
        {"after_surface": 2, "distance": 3.5, "norm_radius": 2.0},
        {"after_surface": 9, "distance": 1.0, "norm_radius": 2.0},  # ungültig: ignoriert
    ]
    g = lp.outline(data)
    assert [(p["index"], p["z"], p["radius"]) for p in g.ghost_plates] == [
        (0, 1.0, 4.0),
        (1, 17.5, 2.0),
    ]


def test_cemented_doublet_and_immersion_note():
    data = _biconvex()
    data["surfaces"][2]["material"] = "N-SF6"  # Kittglied: Glas auch nach Fläche 2
    data["surfaces"].append(
        {"type": "plane", "thickness": 1.0, "material": "OEL", "semi_diameter": 10.0}
    )
    g = lp.outline(data)
    assert g.elements == [(1, 2), (2, 3)]
    assert any("Immersion" in n for n in g.notes)


def test_figure_axes_and_traces():
    g = lp.outline(_biconvex())
    fig = lp.lens_figure(g)
    assert fig.layout.yaxis.scaleanchor == "x"
    assert fig.layout.yaxis.scaleratio == 1
    assert fig.layout.xaxis.title.text == "z [mm]"
    assert fig.layout.yaxis.title.text == "y [mm]"
    names = [t.name for t in fig.data]
    assert names.count("Blende") == 2
    assert "Glas 1–2" in names and "Fläche 1" in names and "Bildebene" in names
    glass = next(t for t in fig.data if t.name == "Glas 1–2")
    assert glass.fill == "toself"


def test_cropped_image_space():
    g = lp.outline(_biconvex())  # Bildraum 40 mm, Baulänge 15 mm
    assert lp.image_space_is_long(g)
    fig = lp.lens_figure(g, full_image_space=False)
    assert fig.layout.xaxis.range[1] < g.image_z
    note = next(a for a in fig.layout.annotations if "Bildebene bei z = 55 mm" in a.text)
    assert (note.xref, note.x, note.xanchor) == ("paper", 1.0, "right")  # am Diagrammrand
    assert lp.lens_figure(g).layout.xaxis.range is None


def test_empty_and_incomplete_data():
    g = lp.outline({})
    assert g.surfaces == [] and g.image_z == 0.0
    lp.lens_figure(g)  # darf nicht werfen
    g = lp.outline({"surfaces": [{"type": "plane"}]})  # fehlende Felder: Standard 0
    assert g.surfaces[0].semi_diameter == 0.0
