"""Vergleich zweier Systeme (G2-T4): Prüfung der Vergleichbarkeit und Tabellenzeilen.

Reine Funktionen ohne Streamlit. Verglichen werden Ergebnisse von Mikroptim; die einzige
Rechnung ist die Differenz B − A zur Anzeige.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from gui_mikroptim.backend.system_tables import PARAXIAL_LABELS, fmt_number


@dataclass(frozen=True)
class Comparability:
    """Ob RMS-Werte zweier Systeme Zelle für Zelle vergleichbar sind, und wenn nicht, warum."""

    reasons: list[str] = field(default_factory=list)

    @property
    def same_grid(self) -> bool:
        return not self.reasons


def _same(a: Any, b: Any) -> bool:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return a.shape == b.shape and bool(np.array_equal(a, b))


def comparability(a: Any, b: Any) -> Comparability:
    """Gleiche Feldwinkel, Wellenlängen und Referenzwellenlänge?

    ``a`` und ``b`` sind ``mikroptim.System`` (oder Objekte mit ``field_angles_deg``,
    ``wavelengths_nm``, ``reference_nm``). RMS-Werte stehen in Wellen bei λ_ref des jeweiligen
    Systems; nur bei gleichem λ_ref ist eine Differenz in Wellen sinnvoll.
    """

    def values(v: Any) -> str:
        return ", ".join(f"{float(x):g}" for x in v)

    reasons = []
    if not _same(a.field_angles_deg, b.field_angles_deg):
        reasons.append(
            f"Feldwinkel verschieden: A [{values(a.field_angles_deg)}] °, "
            f"B [{values(b.field_angles_deg)}] °"
        )
    if not _same(a.wavelengths_nm, b.wavelengths_nm):
        reasons.append(
            f"Wellenlängen verschieden: A [{values(a.wavelengths_nm)}] nm, "
            f"B [{values(b.wavelengths_nm)}] nm"
        )
    if float(a.reference_nm) != float(b.reference_nm):
        reasons.append(
            f"Referenzwellenlänge verschieden: A {float(a.reference_nm):g} nm, "
            f"B {float(b.reference_nm):g} nm (RMS in Wellen nicht direkt vergleichbar)"
        )
    return Comparability(reasons)


def rms_difference(a: Any, b: Any) -> np.ndarray:
    """B − A der RMS-Wellenfront [Wellen]; nur bei gleicher Form, NaN bleibt NaN."""
    ra = np.asarray(a.rms_waves, dtype=float)
    rb = np.asarray(b.rms_waves, dtype=float)
    if ra.shape != rb.shape:
        raise ValueError(f"Formen verschieden: {ra.shape} gegen {rb.shape}")
    return rb - ra


def rms_compare_rows(a: Any, b: Any, field_angles_deg: Any, wavelengths_nm: Any) -> list[dict]:
    """Zeilen (Feld, Wellenlänge) mit RMS A, RMS B und Δ = B − A sowie versagten Strahlen."""
    diff = rms_difference(a, b)
    rows = []
    fields, wavelengths = diff.shape
    for f in range(fields):
        for j in range(wavelengths):
            va, vb, d = float(a.rms_waves[f, j]), float(b.rms_waves[f, j]), float(diff[f, j])
            rows.append(
                {
                    "Feld": f,
                    "Feldwinkel [°]": float(field_angles_deg[f]),
                    "λ [nm]": float(wavelengths_nm[j]),
                    "RMS A [W]": va if math.isfinite(va) else None,
                    "RMS B [W]": vb if math.isfinite(vb) else None,
                    "Δ B − A [W]": d if math.isfinite(d) else None,
                    "versagt A": int(a.failed[f, j]),
                    "versagt B": int(b.failed[f, j]),
                }
            )
    return rows


def _flatten(prefix: str, value: Any, out: dict[str, Any]) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            _flatten(f"{prefix}.{k}" if prefix else k, v, out)
    else:
        out[prefix] = value


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def paraxial_compare_rows(pa: dict[str, Any] | None, pb: dict[str, Any] | None) -> list[dict]:
    """Paraxialdaten nebeneinander: Größe, A, B, Δ (B − A, nur bei zwei endlichen Zahlen)."""
    fa: dict[str, Any] = {}
    fb: dict[str, Any] = {}
    _flatten("", pa or {}, fa)
    _flatten("", pb or {}, fb)
    keys = list(fa) + [k for k in fb if k not in fa]
    rows = []
    for key in keys:
        va, vb = fa.get(key), fb.get(key)
        label, unit = PARAXIAL_LABELS.get(key, (key, ""))
        delta = None
        if (
            _is_number(va)
            and _is_number(vb)
            and math.isfinite(float(va))
            and math.isfinite(float(vb))
        ):
            delta = fmt_number(float(vb) - float(va), 10)

        def text(v: Any) -> str:
            if isinstance(v, list):
                return "[" + ", ".join(fmt_number(x, 10) for x in v) + "]"
            return fmt_number(v, 10)

        rows.append(
            {
                "Größe": label,
                "A": text(va),
                "B": text(vb),
                "Δ B − A": delta or "",
                "Einheit": unit,
                "Schlüssel": key,
            }
        )
    return rows
