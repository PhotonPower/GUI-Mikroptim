"""Dünne Hüllen um Mikroptim-Aufrufe der Seiten (ADR-0002).

Ruft nur öffentliche Funktionen von ``mikroptim`` auf (über :func:`mko.require`) und bündelt
die Fehlerbehandlung. Ohne Streamlit; das Zwischenspeichern übernehmen die Seiten.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gui_mikroptim.backend import files, mko, uploads


@dataclass(frozen=True)
class LoadError:
    """Fehler beim Laden einer Systemdatei, aufbereitet für die Oberfläche."""

    kind: str  # Klassenname der Ausnahme, z. B. "FormatError"
    message: str
    json_path: str | None = None

    @property
    def is_catalog_error(self) -> bool:
        """Glaskatalog nicht gefunden: ``FormatError`` mit JSON-Pfad ``glass_catalogs[…]``."""
        return self.kind == "FormatError" and (self.json_path or "").startswith("glass_catalogs")


def load_error(exc: BaseException) -> LoadError:
    json_path = getattr(exc, "json_path", None)
    message = getattr(exc, "message", None) or str(exc)
    return LoadError(type(exc).__name__, str(message), json_path or None)


def load_system(path: Path) -> Any:
    """``mikroptim.load_system``; Ausnahmen von Mikroptim werden durchgereicht."""
    return mko.require().load_system(str(path))


@dataclass(frozen=True)
class SystemDetails:
    """Was die Seite „System“ aus einem geladenen System braucht."""

    data: dict[str, Any]
    paraxial: dict[str, Any] | None
    paraxial_error: str | None
    variables: list[dict[str, Any]] = field(default_factory=list)
    variables_error: str | None = None


def details(system: Any) -> SystemDetails:
    """Systembeschreibung, Paraxialdaten und Variablen; Teilfehler werden gemeldet, nicht geworfen.

    ``System.variables()`` scheitert z. B. bei Glasvariablen auf Katalog-Gläsern (Mikroptim
    wandelt sie erst bei ``optimize`` in Buchdahl-Gläser um); die Seite zeigt dann die
    Variablen aus der Datei.
    """
    m = mko.require()
    data = m.system_to_dict(system)
    try:
        paraxial, paraxial_error = m.paraxial(system).to_dict(), None
    except Exception as exc:  # Paraxialdaten dürfen die Seite nicht stoppen
        paraxial, paraxial_error = None, f"{type(exc).__name__}: {exc}"
    try:
        variables, variables_error = list(system.variables()), None
    except Exception as exc:
        variables, variables_error = [], f"{type(exc).__name__}: {exc}"
    return SystemDetails(data, paraxial, paraxial_error, variables, variables_error)


def repair_catalogs(path: Path, base_dir: Path, workspace: Path) -> Path:
    """Speichert eine Systemdatei neu, deren Glaskataloge vom eigenen Ort aus nicht zu finden sind.

    Mikroptim lädt den Text mit Katalogsuche ab ``base_dir`` (``System.from_json``) und schreibt
    ihn mit ``System.save`` nach ``uploads/<name>-kataloge.json``; ``save`` passt die Pfade unter
    ``glass_catalogs`` an den neuen Ort an. Die Eingabe bleibt unverändert, nichts wird
    überschrieben.
    """
    m = mko.require()
    text = path.read_text(encoding="utf-8")
    system = m.System.from_json(text, str(base_dir))
    directory = files.resolve_inside(workspace, uploads.UPLOAD_SUBDIR)
    directory.mkdir(parents=True, exist_ok=True)
    target = files.unique_path(directory, f"{path.stem}-kataloge.json")
    system.save(str(target))
    return target
