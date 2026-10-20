"""Sicherer Dateizugriff: lesen aus erlaubten Wurzeln, schreiben nur im Arbeitsbereich.

Jeder Pfad aus der Oberfläche läuft über :func:`resolve_inside`. Pfade mit ``..`` oder
Symlinks, die aus der Wurzel herausführen, werden abgelehnt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

#: Dateiendungen, die die GUI als Mikroptim-Dateien anbietet
JSON_SUFFIXES = (".json",)

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class PathError(ValueError):
    """Pfad liegt außerhalb der erlaubten Wurzel oder ist ungültig."""


@dataclass(frozen=True)
class FileEntry:
    """Eine Datei unter einer Wurzel, für Auswahllisten."""

    root: Path
    relative: Path
    size: int
    mtime: float

    @property
    def path(self) -> Path:
        return self.root / self.relative

    @property
    def label(self) -> str:
        return self.relative.as_posix()


def resolve_inside(root: Path, relative: str | Path) -> Path:
    """Absoluter, aufgelöster Pfad von ``relative`` unter ``root``.

    Raises:
        PathError: wenn das Ergebnis nicht unter ``root`` liegt (auch über Symlinks)
            oder ``relative`` absolut ist.
    """
    rel = Path(relative)
    if rel.is_absolute() or rel.drive:
        raise PathError(f"absoluter Pfad nicht erlaubt: {relative}")
    root_resolved = root.resolve()
    target = (root_resolved / rel).resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise PathError(f"Pfad liegt außerhalb von {root_resolved}: {relative}")
    return target


def list_files(root: Path, suffixes: tuple[str, ...] = JSON_SUFFIXES) -> list[FileEntry]:
    """Alle Dateien mit passender Endung unter ``root``, sortiert nach relativem Pfad.

    Versteckte Verzeichnisse und Dateien (Name beginnt mit ``.``) und Symlinks, die aus
    ``root`` herausführen, werden übersprungen. Fehlt ``root``, ist die Liste leer.
    """
    if not root.is_dir():
        return []
    root_resolved = root.resolve()
    entries: list[FileEntry] = []
    for path in root_resolved.rglob("*"):
        rel = path.relative_to(root_resolved)
        if any(part.startswith(".") for part in rel.parts):
            continue
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        try:
            resolve_inside(root_resolved, rel)
        except PathError:
            continue
        stat = path.stat()
        entries.append(FileEntry(root_resolved, rel, stat.st_size, stat.st_mtime))
    entries.sort(key=lambda e: e.label)
    return entries


def safe_filename(name: str) -> str:
    """Dateiname ohne Verzeichnisanteile und Sonderzeichen (für Uploads und Ergebnisse)."""
    base = Path(name.replace("\\", "/")).name
    cleaned = _SAFE_NAME.sub("_", base).strip("._")
    if not cleaned:
        raise PathError(f"ungültiger Dateiname: {name!r}")
    return cleaned


def unique_path(directory: Path, filename: str) -> Path:
    """Pfad in ``directory``, der noch nicht existiert (``name.json``, ``name-2.json``, …).

    Eingabedateien werden so nie überschrieben (AGENTS.md, Abschnitt 6).
    """
    name = safe_filename(filename)
    candidate = directory / name
    stem, suffix = candidate.stem, candidate.suffix
    counter = 2
    while candidate.exists():
        candidate = directory / f"{stem}-{counter}{suffix}"
        counter += 1
    return candidate


def write_new_file(workspace: Path, subdir: str, filename: str, data: bytes) -> Path:
    """Schreibt ``data`` als neue Datei unter ``workspace/subdir`` und gibt den Pfad zurück."""
    directory = resolve_inside(workspace, subdir)
    directory.mkdir(parents=True, exist_ok=True)
    target = unique_path(directory, filename)
    # "xb": nie eine bestehende Datei überschreiben, auch nicht bei einem Wettlauf
    with target.open("xb") as handle:
        handle.write(data)
    return target
