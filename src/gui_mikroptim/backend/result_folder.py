"""Ergebnisordner von Läufen als Ganzes (G4-T4), z. B. ``docs/ergebnisse/m6-t6/`` in Mikroptim.

Ohne Streamlit. Dateien werden nach ihrem Mikroptim-Format (Feld ``format``) und nach dem
Stufenkürzel am Anfang des Namens (``p1``, ``a3``, ``z2`` …) gegliedert; Kennzahlen kommen
unverändert aus den Dateien (ADR-0002). Ein Bericht wird gefunden, wenn er im Ordner liegt
(``README.md``, ``bericht.md``) oder daneben mit dem Ordnernamen beginnt
(``m6-t6-zielspezifikation.md`` neben ``m6-t6/``).
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gui_mikroptim.backend import files, protocols

SYSTEM, SYNTH, EVAL, OTHER_DOC, JSON, TEXT, DOT, OTHER = (
    "System", "Protokoll", "Auswertung", "Mikroptim-Datei", "JSON", "Text", "Stammbaum", "sonstig",
)  # fmt: skip
TEXT_SUFFIXES = (".txt", ".md", ".csv", ".log")
_STAGE = re.compile(r"^([a-z]+\d+)(?=[_.\-]|$)", re.IGNORECASE)


@dataclass(frozen=True)
class FolderFile:
    path: Path
    relative: str
    kind: str
    format: str | None
    stage: str
    size: int


@dataclass(frozen=True)
class Inventory:
    folder: Path
    files: list[FolderFile] = field(default_factory=list)

    def of(self, kind: str) -> list[FolderFile]:
        return [f for f in self.files if f.kind == kind]

    def counts(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for f in self.files:
            result[f.kind] = result.get(f.kind, 0) + 1
        return result

    def stages(self) -> list[str]:
        """Stufen in natürlicher Reihenfolge (p2 vor p10), „–“ zuletzt."""
        names = {f.stage for f in self.files}
        return sorted(names, key=_stage_key)


def _stage_key(stage: str) -> tuple:
    match = re.match(r"^([a-z]+)(\d+)$", stage, re.IGNORECASE)
    if not match:
        return (1, stage, 0)
    return (0, match.group(1).lower(), int(match.group(2)))


def stage_of(name: str) -> str:
    match = _STAGE.match(name)
    return match.group(1).lower() if match else "–"


def classify(path: Path) -> tuple[str, str | None]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        fmt = protocols.peek_format(path)
        if fmt is None:
            return JSON, None
        kind = {
            "mikroptim.system": SYSTEM,
            "mikroptim.synth": SYNTH,
            "mikroptim.eval": EVAL,
        }.get(fmt.name, OTHER_DOC)
        return kind, str(fmt)
    if suffix == ".dot":
        return DOT, None
    if suffix in TEXT_SUFFIXES:
        return TEXT, None
    return OTHER, None


def scan(folder: Path) -> Inventory:
    """Alle Dateien des Ordners (rekursiv, ohne versteckte), sortiert nach Stufe und Name."""
    root = folder.resolve()
    found = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part.startswith(".") for part in rel.parts) or not path.is_file():
            continue
        try:
            files.resolve_inside(root, rel)  # keine Symlinks nach außen
        except files.PathError:
            continue
        kind, fmt = classify(path)
        found.append(
            FolderFile(path, rel.as_posix(), kind, fmt, stage_of(path.name), path.stat().st_size)
        )
    found.sort(key=lambda f: (_stage_key(f.stage), f.relative))
    return Inventory(root, found)


def candidate_folders(root: Path, limit: int = 500) -> list[Path]:
    """Unterordner von ``root`` (bis Tiefe 2), die Mikroptim-Dateien enthalten."""
    if not root.is_dir():
        return []
    result = []
    for path in sorted(root.glob("*")) + sorted(root.glob("*/*")):
        if not path.is_dir() or path.name.startswith("."):
            continue
        if any(protocols.peek_format(p) for p in path.glob("*.json")):
            result.append(path)
        if len(result) >= limit:
            break
    return result


def find_report(folder: Path) -> Path | None:
    for name in ("README.md", "bericht.md", "BERICHT.md"):
        if (folder / name).is_file():
            return folder / name
    matches = sorted(folder.parent.glob(f"{folder.name}*.md"))
    return matches[0] if matches else None


# --- Kennzahlen pro Datei (unverändert aus den Dateien) -----------------------------------------


def _load(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def system_row(f: FolderFile) -> dict[str, Any]:
    data = _load(f.path) or {}
    source = data.get("source") or {}
    spectrum = data.get("spectrum") or {}
    return {
        "Datei": f.relative,
        "Stufe": f.stage,
        "Name": data.get("name"),
        "Flächen": len(data.get("surfaces") or []),
        "Felder": len(source.get("field_angles_deg") or []),
        "Wellenlängen": len(spectrum.get("wavelengths_nm") or []),
        "Geisterplatten": len(data.get("ghost_plates") or []),
    }


def synth_row(f: FolderFile) -> dict[str, Any]:
    data = _load(f.path)
    row: dict[str, Any] = {"Datei": f.relative, "Stufe": f.stage}
    if data is None:
        row["Status"] = "nicht lesbar"
        return row
    s = protocols.read_synth(data).summary()
    row.update(
        {
            "Status": s["status_text"],
            "NA Ende": s["na_ende"],
            "Feld Ende": s["feld_ende"],
            "Elemente": f"{s['elemente_start']} → {s['elemente']}",
            "Einfügungen": s["einfuegungen"],
            "Optimierungen": s["optimierungen"],
            "max. RMS [W]": s["max_rms_wellen"],
            "Sekunden": s["sekunden"],
        }
    )
    return row


def _finite(values: list[Any]) -> list[float]:
    return [float(v) for v in values if isinstance(v, (int, float)) and math.isfinite(v)]


def eval_row(f: FolderFile) -> dict[str, Any]:
    data = _load(f.path) or {}
    tuples = [t for t in data.get("tuples") or [] if isinstance(t, dict)]
    rms = _finite([t.get("rms_opd_waves") for t in tuples])
    strehl = _finite([(t.get("psf") or {}).get("strehl") for t in tuples])
    psf = data.get("psf") or {}
    return {
        "Datei": f.relative,
        "Stufe": f.stage,
        "System": data.get("system"),
        "Raster": data.get("grid"),
        "Referenz": data.get("reference_sphere"),
        "PSF": psf.get("model") if isinstance(psf, dict) else None,
        "Tupel": len(tuples),
        "RMS-OPD max [W]": max(rms) if rms else None,
        "RMS-OPD min [W]": min(rms) if rms else None,
        "Strehl min": min(strehl) if strehl else None,
        "Strehl max": max(strehl) if strehl else None,
        "versagt": data.get("failed_rays"),
    }


def stage_rows(inventory: Inventory) -> list[dict[str, Any]]:
    rows = []
    for stage in inventory.stages():
        members = [f for f in inventory.files if f.stage == stage]
        kinds = {k: sum(1 for f in members if f.kind == k) for k in (SYSTEM, SYNTH, EVAL, TEXT)}
        rows.append(
            {
                "Stufe": stage,
                "Systeme": kinds[SYSTEM],
                "Protokolle": kinds[SYNTH],
                "Auswertungen": kinds[EVAL],
                "Texte": kinds[TEXT],
                "weitere": len(members) - sum(kinds.values()),
                "Dateien": ", ".join(f.relative for f in members[:6])
                + (" …" if len(members) > 6 else ""),
            }
        )
    return rows
