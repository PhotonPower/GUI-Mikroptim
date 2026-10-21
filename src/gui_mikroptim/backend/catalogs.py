"""Glaskataloge im Arbeitsbereich (ADR-0006): hochladen, prüfen, auflisten, zuordnen.

Nutzer der GUI haben keinen Zugang zum Server; eigene Kataloge (z. B. Herstellerdaten, die nicht
ins Mikroptim-Repository dürfen) laden sie deshalb hoch. Sie liegen unter ``<Arbeitsbereich>/
kataloge/``. Mikroptim sucht ``glass_catalogs`` nur vom Ordner der Systemdatei aus aufwärts;
:func:`resolve_entries` ordnet nicht gefundene Einträge zusätzlich dem Mikroptim-Checkout und
den hochgeladenen Katalogen (nach Dateiname) zu. Ohne Streamlit.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gui_mikroptim.backend import files, protocols

CATALOG_SUBDIR = "kataloge"
FORMAT = "mikroptim.glass"


class CatalogError(ValueError):
    """Katalog abgelehnt; die Meldung ist für die Oberfläche gedacht."""


@dataclass(frozen=True)
class CatalogInfo:
    path: Path
    glasses: list[dict[str, Any]]

    @property
    def names(self) -> list[str]:
        return [str(g.get("name")) for g in self.glasses]


def catalog_dir(workspace: Path) -> Path:
    directory = files.resolve_inside(workspace, CATALOG_SUBDIR)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _number_list(value: Any, length: int) -> bool:
    return (
        isinstance(value, list)
        and len(value) == length
        and all(
            isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
            for v in value
        )
    )


def check_catalog(data: dict[str, Any], source: str) -> list[dict[str, Any]]:
    """Prüft den Aufbau von ``mikroptim.glass/1`` (Mikroptim docs/dateiformat.md, „Glasdaten“).

    Die endgültige Prüfung macht Mikroptim beim Laden (:func:`validate_with_mikroptim`); diese
    Prüfung gibt vorher verständliche Meldungen und läuft auch ohne Mikroptim.
    """
    fmt = protocols.parse_format(data.get("format"))
    if fmt is None or fmt.name != FORMAT:
        raise CatalogError(f"{source}: kein Glaskatalog (Feld format muss mikroptim.glass/1 sein)")
    glasses = data.get("glasses")
    if not isinstance(glasses, list) or not glasses:
        raise CatalogError(f"{source}: Liste glasses fehlt oder ist leer")
    seen: set[str] = set()
    for i, glass in enumerate(glasses):
        where = f"{source}: glasses[{i}]"
        if not isinstance(glass, dict):
            raise CatalogError(f"{where}: kein Objekt")
        name = glass.get("name")
        if not isinstance(name, str) or not name.strip():
            raise CatalogError(f"{where}: name fehlt")
        if name in seen:
            raise CatalogError(f"{where}: Glas {name} kommt doppelt vor")
        seen.add(name)
        if glass.get("model") != "sellmeier":
            raise CatalogError(f"{where} ({name}): model muss sellmeier sein")
        if not _number_list(glass.get("B"), 3) or not _number_list(glass.get("C"), 3):
            raise CatalogError(f"{where} ({name}): B und C brauchen je drei Zahlen")
        if not _number_list(glass.get("range_nm"), 2) or not (
            0 < glass["range_nm"][0] < glass["range_nm"][1]
        ):
            raise CatalogError(f"{where} ({name}): range_nm braucht [von, bis] in nm")
    return glasses


def list_catalogs(workspace: Path) -> list[CatalogInfo]:
    """Hochgeladene Kataloge; unlesbare Dateien werden übersprungen."""
    result = []
    for entry in files.list_files(catalog_dir(workspace)):
        try:
            data = json.loads(entry.path.read_text(encoding="utf-8"))
            result.append(CatalogInfo(entry.path, check_catalog(data, entry.label)))
        except (OSError, ValueError):
            continue
    return result


def glass_names_in(paths: list[Path]) -> dict[str, Path]:
    """Glasname → Katalog für mehrere Kataloge (zum Erkennen doppelter Namen)."""
    names: dict[str, Path] = {}
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for glass in data.get("glasses") or []:
            if isinstance(glass, dict) and isinstance(glass.get("name"), str):
                names.setdefault(glass["name"], path)
    return names


def save_catalog(workspace: Path, filename: str, data: bytes) -> CatalogInfo:
    """Prüft und speichert einen hochgeladenen Katalog unter ``kataloge/``.

    Der Dateiname bleibt erhalten, weil Systemdateien ihre Kataloge über ihn finden; ein
    vorhandener Katalog gleichen Namens wird deshalb nicht überschrieben, sondern abgelehnt.
    """
    try:
        name = files.safe_filename(filename)
    except files.PathError as exc:
        raise CatalogError(str(exc)) from exc
    if not name.lower().endswith(".json"):
        raise CatalogError(f"{filename}: nur JSON-Dateien (.json)")
    try:
        parsed = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CatalogError(f"{filename}: nicht lesbar: {exc}") from exc
    if not isinstance(parsed, dict):
        raise CatalogError(f"{filename}: kein JSON-Objekt")
    glasses = check_catalog(parsed, filename)
    target = catalog_dir(workspace) / name
    if target.exists():
        raise CatalogError(
            f"Ein Katalog {name} ist schon vorhanden. Systemdateien finden Kataloge über den "
            "Dateinamen; den alten zuerst löschen, wenn er ersetzt werden soll."
        )
    with target.open("xb") as handle:
        handle.write(data.removeprefix(b"\xef\xbb\xbf"))
    return CatalogInfo(target, glasses)


def delete_catalog(workspace: Path, name: str) -> None:
    path = files.resolve_inside(catalog_dir(workspace), name)
    if path.suffix.lower() != ".json" or not path.is_file():
        raise CatalogError(f"Katalog {name} nicht gefunden")
    path.unlink()


# --- Zuordnung von glass_catalogs ----------------------------------------------------------------


@dataclass(frozen=True)
class Resolution:
    entry: str
    path: Path | None
    origin: str  # "Datei", "Mikroptim", "Arbeitsbereich" oder "fehlt"


def _upward(entry: Path, start: Path) -> Path | None:
    """Mikroptims Regel: relativ zum Ordner der Systemdatei, dann in den Elternordnern."""
    for base in (start, *start.parents):
        candidate = base / entry
        if candidate.is_file():
            return candidate.resolve()
    return None


def resolve_entries(
    entries: list[str], file_dir: Path, repo: Path | None, workspace: Path
) -> list[Resolution]:
    """Ordnet jeden Eintrag von ``glass_catalogs`` einer Datei zu.

    Reihenfolge: wie Mikroptim vom Ordner der Systemdatei aufwärts, dann im Mikroptim-Checkout
    (``<repo>/<eintrag>``), dann unter den hochgeladenen Katalogen nach Dateiname.
    """
    uploaded = catalog_dir(workspace)
    result = []
    for entry in entries:
        rel = Path(entry)
        found = rel.resolve() if rel.is_absolute() and rel.is_file() else None
        if found is None and not rel.is_absolute():
            found = _upward(rel, file_dir)
        if found is not None:
            result.append(Resolution(entry, found, "Datei"))
            continue
        if repo is not None and not rel.is_absolute() and (repo / rel).is_file():
            result.append(Resolution(entry, (repo / rel).resolve(), "Mikroptim"))
            continue
        candidate = uploaded / rel.name
        if candidate.is_file():
            result.append(Resolution(entry, candidate.resolve(), "Arbeitsbereich"))
            continue
        result.append(Resolution(entry, None, "fehlt"))
    return result


def with_absolute_catalogs(text: str, resolutions: list[Resolution]) -> str:
    """Systemtext mit absoluten Katalogpfaden (für ``System.from_json``)."""
    data = json.loads(text)
    data["glass_catalogs"] = [str(r.path) for r in resolutions]
    return json.dumps(data, ensure_ascii=False)
