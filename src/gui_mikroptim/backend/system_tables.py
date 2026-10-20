"""Tabellenzeilen für die Seite „System“ aus Mikroptim-Objekten (G1-T2).

Reine Funktionen ohne Streamlit. Eingaben sind ein ``mikroptim.System`` (oder ein Objekt mit
denselben Eigenschaften) und ``mikroptim.system_to_dict(system)``. Gerechnet wird nichts außer
Darstellung: der Radius 1/c zur Anzeige und das Umbenennen von Feldern (ADR-0002).
"""

from __future__ import annotations

import math
from typing import Any

#: Bezeichnung und Einheit der Felder von ``Paraxial.to_dict()`` (Mikroptim, docs/cli.md,
#: Feld ``paraxial`` von ``mikroptim.trace/1``). Unbekannte Felder erscheinen mit ihrem Schlüssel.
PARAXIAL_LABELS: dict[str, tuple[str, str]] = {
    "wavelength_nm": ("Wellenlänge", "nm"),
    "afocal": ("afokal", ""),
    "power": ("Brechkraft φ", "1/mm"),
    "focal_length": ("Brennweite f", "mm"),
    "back_focal_distance": ("bildseitige Schnittweite", "mm"),
    "front_focal_distance": ("objektseitige Schnittweite", "mm"),
    "front_principal_plane": ("Hauptebene H (objektseitig)", "mm"),
    "rear_principal_plane": ("Hauptebene H′ (bildseitig)", "mm"),
    "image_defocus": ("Defokus der Bildebene", "mm"),
    "petzval_sum": ("Petzvalsumme", "1/mm"),
    "petzval_curvature": ("Petzvalkrümmung κ_P", "1/mm"),
    "petzval_radius": ("Petzvalradius", "mm"),
    "exit_pupil.at_infinity": ("Austrittspupille im Unendlichen", ""),
    "exit_pupil.position": ("Austrittspupille: Lage", "mm"),
    "exit_pupil.magnification": ("Austrittspupille: Abbildungsmaßstab", ""),
    "exit_pupil.semi_diameter": ("Austrittspupille: Halbdurchmesser", "mm"),
    "abcd": ("ABCD-Matrix", ""),
}


def fmt_number(value: Any, digits: int = 6) -> str:
    """Zahl für Anzeigen.

    ``∞``/``−∞``/``NaN`` statt ``inf``/``nan``, Wahrheitswerte als ja/nein, sonst ``digits``
    gültige Stellen.
    """
    if isinstance(value, bool) or value is None:
        return {True: "ja", False: "nein", None: "–"}[value]
    if isinstance(value, (int, float)):
        x = float(value)
        if math.isnan(x):
            return "NaN"
        if math.isinf(x):
            return "∞" if x > 0 else "−∞"
        if isinstance(value, int):
            return str(value)
        return f"{x:.{digits}g}"
    return str(value)


def radius_text(curvature: float) -> str:
    """Radius zur Anzeige: ``∞`` bei Krümmung 0, sonst 1/c."""
    return "∞" if curvature == 0 else fmt_number(1.0 / curvature)


def material_text(material: Any) -> str:
    """Material aus der Systembeschreibung (Name oder Modell mit Parametern)."""
    if isinstance(material, str):
        return material
    if isinstance(material, dict):
        model = material.get("model", "?")
        if model == "constant":
            return f"konstant n = {fmt_number(material.get('n'))}"
        if model == "buchdahl":
            nu = ", ".join(fmt_number(v, 5) for v in material.get("nu") or [])
            return f"Buchdahl n₀ = {fmt_number(material.get('n0'))}, ν = [{nu}]"
        return str(model)
    return "–"


def surface_rows(system: Any, data: dict[str, Any]) -> list[dict[str, Any]]:
    """Eine Zeile pro Dateifläche.

    Brechzahlen stehen pro Wellenlänge, so wie Mikroptim sie liefert (``System.indices``,
    Medium nach der Fläche); es wird nicht interpoliert.
    """
    surfaces = data.get("surfaces") or []
    wavelengths = list(system.wavelengths_nm)
    indices = system.indices
    rows = []
    for i in range(system.num_surfaces):
        raw = surfaces[i] if i < len(surfaces) and isinstance(surfaces[i], dict) else {}
        curvature = float(system.curvatures[i])
        row: dict[str, Any] = {
            "Nr.": i,
            "Typ": system.surface_types[i],
            "Krümmung [1/mm]": curvature,
            "Radius [mm]": radius_text(curvature),
            "Dicke [mm]": float(system.thicknesses[i]),
            "Material danach": material_text(raw.get("material", system.materials[i])),
            "Halbdurchmesser [mm]": float(system.semi_diameters[i]),
        }
        for j, wl in enumerate(wavelengths):
            row[f"n({fmt_number(wl)} nm)"] = float(indices[i][j])
        decenter = raw.get("decenter")
        tilt = raw.get("tilt_deg")
        row["Dezentrierung [mm]"] = ", ".join(fmt_number(v) for v in decenter) if decenter else ""
        row["Verkippung [°]"] = ", ".join(fmt_number(v) for v in tilt) if tilt else ""
        row["Kommentar"] = raw.get("comment", "")
        rows.append(row)
    return rows


def _as_list(value: Any) -> list[Any]:
    """NumPy-Array, Liste oder ``None`` als Liste (``x or []`` ist bei Arrays mehrdeutig)."""
    return [] if value is None else list(value)


def spectrum_rows(system: Any) -> list[dict[str, Any]]:
    weights = _as_list(getattr(system, "wavelength_weights", None))
    rows = []
    for j, wl in enumerate(system.wavelengths_nm):
        rows.append(
            {
                "Nr.": j,
                "Wellenlänge [nm]": float(wl),
                "Gewicht": float(weights[j]) if j < len(weights) else None,
                "Referenz": "λ_ref" if float(wl) == float(system.reference_nm) else "",
            }
        )
    return rows


def field_rows(system: Any) -> list[dict[str, Any]]:
    weights = _as_list(getattr(system, "field_weights", None))
    return [
        {
            "Nr.": f,
            "Feldwinkel [°]": float(angle),
            "Gewicht": float(weights[f]) if f < len(weights) else None,
        }
        for f, angle in enumerate(system.field_angles_deg)
    ]


def _flatten(prefix: str, value: Any, out: list[tuple[str, Any]]) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            _flatten(f"{prefix}.{k}" if prefix else k, v, out)
    else:
        out.append((prefix, value))


def paraxial_rows(paraxial: dict[str, Any]) -> list[dict[str, str]]:
    """Paraxialdaten als Zeilen (Größe, Wert, Einheit, Schlüssel), Werte als Text.

    Werte werden als Text gezeigt, damit ``∞`` (z. B. Brennweite der Planplatte) lesbar bleibt;
    die Zahlen selbst stehen unverändert im aufklappbaren JSON.
    """
    flat: list[tuple[str, Any]] = []
    _flatten("", paraxial, flat)
    rows = []
    for key, value in flat:
        label, unit = PARAXIAL_LABELS.get(key, (key, ""))
        if isinstance(value, list):
            text = "[" + ", ".join(fmt_number(v, 10) for v in value) + "]"
        else:
            text = fmt_number(value, 10)
        rows.append({"Größe": label, "Wert": text, "Einheit": unit, "Schlüssel": key})
    return rows


def variable_rows(variables: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Variablen aus ``System.variables()`` mit deutschen Spaltennamen."""
    return [
        {
            "Name": v.get("name"),
            "Typ": v.get("type"),
            "Fläche": v.get("surface"),
            "Platte": v.get("plate"),
            "Ordnung": v.get("order"),
            "Wert": v.get("value"),
            "untere Schranke": v.get("lower"),
            "obere Schranke": v.get("upper"),
            "typische Größe": v.get("typical"),
        }
        for v in variables
    ]


def wavefront_rows(result: Any, field_angles_deg: Any = None) -> list[dict[str, Any]]:
    """Eine Zeile pro (Feld, Wellenlänge), Reihenfolge wie ``wavefront`` von ``trace --json``.

    Nicht endliche RMS-Werte (kein gültiger Strahl) erscheinen als ``None`` wie in der CLI.
    """
    angles = _as_list(field_angles_deg)
    rows = []
    fields, wavelengths = result.rms_waves.shape
    for f in range(fields):
        for j in range(wavelengths):
            rms = float(result.rms_waves[f, j])
            rows.append(
                {
                    "Feld": f,
                    "Feldwinkel [°]": float(angles[f]) if f < len(angles) else None,
                    "λ [nm]": float(result.wavelengths_nm[j]),
                    "Pupille": result.pupil_modes[f] if f < len(result.pupil_modes) else "",
                    "Strahlen": int(result.rays[f, j]),
                    "versagt": int(result.failed[f, j]),
                    "RMS [Wellen]": rms if math.isfinite(rms) else None,
                    "RMS [mm]": float(result.rms_mm[f, j])
                    if math.isfinite(float(result.rms_mm[f, j]))
                    else None,
                    "Kolben [mm]": float(result.piston_mm[f, j]),
                    "Bildpunkt y [mm]": float(result.image_points[f, 1]),
                }
            )
    return rows


def _finite(value: Any) -> float | None:
    x = float(value)
    return x if math.isfinite(x) else None


def eval_rows(stats: dict[str, Any], reference_nm: float, field_angles_deg: Any = None) -> list:
    """Kennzahlen von ``Evaluation.stats`` pro (Feld, Wellenlänge) wie ``tuples`` von
    ``mikroptim eval --json``: OPD in Wellen bei λ_ref, Längen in mm, Verzeichnung in %.

    Nicht endliche Werte (z. B. Verzeichnung auf der Achse) erscheinen als ``None`` wie in der
    CLI. Strehl nach Maréchal ist nicht enthalten (dafür G2-T3, Strehl über die FFT).
    """
    angles = _as_list(field_angles_deg)

    def to_waves(key: str, f: int, j: int) -> float | None:
        # genau wie mikroptim eval: mm / (λ_ref · 1e-6), bitgleich (compute.mm_to_waves)
        return _finite(stats[key][f, j] / (reference_nm * 1e-6))

    fields, wavelengths = stats["rms_opd"].shape
    rows = []
    for f in range(fields):
        for j in range(wavelengths):
            rows.append(
                {
                    "Feld": f,
                    "Feldwinkel [°]": float(angles[f]) if f < len(angles) else None,
                    "Wellenlänge": j,
                    "Bildhöhe [mm]": _finite(stats["image_height"][f, j]),
                    "Strahlen": int(stats["rays"][f, j]),
                    "versagt": int(stats["failed"][f, j]),
                    "RMS-OPD [W]": to_waves("rms_opd", f, j),
                    "PV-OPD [W]": to_waves("pv_opd", f, j),
                    "RMS ohne Kippung [W]": to_waves("rms_opd_tilt", f, j),
                    "RMS ohne Defokus [W]": to_waves("rms_opd_defocus", f, j),
                    "RMS-Spot [mm]": _finite(stats["rms_spot"][f, j]),
                    "Schwerpunkt x [mm]": _finite(stats["centroid_x"][f, j]),
                    "Schwerpunkt y [mm]": _finite(stats["centroid_y"][f, j]),
                    "Hauptstrahl y [mm]": _finite(stats["chief_y"][f, j]),
                    "Verzeichnung HS [%]": _finite(stats["distortion_chief"][f, j]),
                    "Verzeichnung SP [%]": _finite(stats["distortion_centroid"][f, j]),
                    "z_t [mm]": _finite(stats["focus_tangential"][f, j]),
                    "z_s [mm]": _finite(stats["focus_sagittal"][f, j]),
                    "Astigmatismus [mm]": _finite(stats["astigmatism"][f, j]),
                    "Defokus [mm]": _finite(stats["defocus"][f, j]),
                }
            )
    return rows
