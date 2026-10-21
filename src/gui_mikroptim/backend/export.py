"""Exporte (G5-T3): Tabellen als CSV, Systembericht als Markdown, Bildoptionen für Plotly.

Ohne Streamlit; alles wird im Speicher erzeugt und über Download-Knöpfe ausgeliefert, nichts
wird im Arbeitsbereich geschrieben. Zahlen werden nicht neu berechnet, nur formatiert.
"""

from __future__ import annotations

import csv
import io
import math
import re
from typing import Any

from gui_mikroptim.backend import system_tables

#: Kamera-Schaltfläche der Plotly-Diagramme: SVG (verlustfrei, für Berichte) in doppelter Größe
IMAGE_FORMAT = "svg"
IMAGE_SCALE = 2


def safe_stem(text: str) -> str:
    """Dateiname ohne Endung aus einem Schlüssel oder Titel (``auswertung.eval.opd`` → …)."""
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", text.replace(".", "_")).strip("_")
    return stem or "export"


def plotly_config(name: str) -> dict[str, Any]:
    """``config`` für ``st.plotly_chart``: Bildexport mit Dateinamen, ohne Plotly-Logo."""
    return {
        "displaylogo": False,
        "toImageButtonOptions": {
            "format": IMAGE_FORMAT,
            "filename": safe_stem(name),
            "scale": IMAGE_SCALE,
        },
    }


def _cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, float) and not math.isfinite(value):
        return "nan" if math.isnan(value) else ("inf" if value > 0 else "-inf")
    if isinstance(value, float):
        return repr(value)  # volle Genauigkeit, wie in den JSON-Dateien von Mikroptim
    return value


def rows_to_csv(rows: list[dict[str, Any]]) -> str:
    """Zeilen (dicts) als CSV mit Kopfzeile; Spalten in der Reihenfolge des ersten Auftretens.

    Zahlen in voller Genauigkeit (``repr``), leere Werte als leeres Feld, Komma als Trenner,
    Punkt als Dezimalzeichen (maschinenlesbar, z. B. für pandas oder Excel mit Import).
    """
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow([_cell(row.get(c)) for c in columns])
    return buffer.getvalue()


def _md_cell(value: Any) -> str:
    if isinstance(value, float):
        text = system_tables.fmt_number(value, 8)
    elif value is None:
        text = "–"
    else:
        text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def markdown_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_keine Einträge_\n"
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "---|" * len(columns),
    ]
    for row in rows:
        lines.append("| " + " | ".join(_md_cell(row.get(c)) for c in columns) + " |")
    return "\n".join(lines) + "\n"


def system_report(
    system: Any,
    data: dict[str, Any],
    paraxial: dict[str, Any] | None,
    variables: list[dict[str, Any]] | None = None,
    wavefront: Any = None,
    source_name: str | None = None,
    mikroptim_version: str | None = None,
) -> str:
    """Kurzer Bericht eines Systems als Markdown (Tabellen wie auf den Seiten der GUI)."""
    parts = [f"# {system.name or source_name or 'System'}\n"]
    if getattr(system, "description", ""):
        parts.append(system.description + "\n")
    meta = [
        f"Datei: `{source_name}`" if source_name else None,
        f"Mikroptim {mikroptim_version}" if mikroptim_version else None,
        f"λ_ref = {system_tables.fmt_number(system.reference_nm)} nm",
        f"Quelle: {system.source_type}",
    ]
    parts.append(" · ".join(m for m in meta if m) + "\n")
    for warning in getattr(system, "warnings", []) or []:
        parts.append(f"> **Warnung:** {warning}\n")
    parts.append("## Flächen\n")
    parts.append(markdown_table(system_tables.surface_rows(system, data)))
    parts.append("## Spektrum\n")
    parts.append(markdown_table(system_tables.spectrum_rows(system)))
    parts.append("## Felder\n")
    parts.append(markdown_table(system_tables.field_rows(system)))
    parts.append("## Paraxialdaten\n")
    if paraxial is None:
        parts.append("_nicht verfügbar_\n")
    else:
        rows = system_tables.paraxial_rows(paraxial)
        parts.append(
            markdown_table([{k: r[k] for k in ("Größe", "Wert", "Einheit")} for r in rows])
        )
    if variables:
        parts.append("## Variablen\n")
        parts.append(markdown_table(system_tables.variable_rows(variables)))
    if wavefront is not None:
        parts.append(
            f"## RMS-Wellenfront\n\n{wavefront.rings} Ringe × {wavefront.spokes} Speichen, "
            f"{wavefront.backend}, {wavefront.precision}; RMS in Wellen bei λ_ref.\n\n"
        )
        rows = system_tables.wavefront_rows(wavefront, system.field_angles_deg)
        keep = ("Feld", "Feldwinkel [°]", "λ [nm]", "Strahlen", "versagt", "RMS [Wellen]")
        parts.append(markdown_table([{k: r[k] for k in keep} for r in rows]))
    parts.append("\n_Erzeugt mit GUI-Mikroptim; alle Zahlen aus Mikroptim._\n")
    return "\n".join(parts)
