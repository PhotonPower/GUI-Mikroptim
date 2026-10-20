"""Anbindung an Mikroptim: Verfügbarkeit, Version, Geräte (ADR-0002).

Einzige Stelle, an der die GUI ``mikroptim`` importiert. Fehlt Mikroptim oder lässt es sich
nicht laden, liefert :func:`status` einen Status mit Fehlermeldung statt einer Ausnahme.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any

#: Älteste Mikroptim-Version, gegen die die GUI getestet ist (docs/schnittstelle-mikroptim.md)
MIN_MIKROPTIM_VERSION = (0, 1, 0)

#: Öffentliche Namen, die die GUI braucht; fehlt einer, ist Mikroptim zu alt
REQUIRED_NAMES = (
    "__version__",
    "load_system",
    "paraxial",
    "trace",
    "evaluate",
    "optimize",
    "has_cuda",
    "device_count",
    "devices",
    "run_cli",
)


class MikroptimUnavailable(RuntimeError):
    """Mikroptim ist nicht installiert, nicht ladbar oder zu alt."""


@dataclass(frozen=True)
class MikroptimStatus:
    """Ergebnis der Prüfung, ob Mikroptim nutzbar ist."""

    available: bool
    version: str | None = None
    has_cuda: bool = False
    devices: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    @property
    def gpu_count(self) -> int:
        return len(self.devices)


def parse_version(text: str) -> tuple[int, ...]:
    """``"0.1.0"`` → ``(0, 1, 0)``; Anhänge wie ``"0.2.0.dev1"`` werden ignoriert."""
    parts: list[int] = []
    for piece in text.split("."):
        digits = ""
        for char in piece:
            if not char.isdigit():
                break
            digits += char
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)


def _import(name: str = "mikroptim") -> ModuleType:
    return importlib.import_module(name)


def _device_dicts(module: ModuleType) -> list[dict[str, Any]]:
    """Geräteliste als Liste von dicts; Form der Einträge kommt aus Mikroptim."""
    if not module.has_cuda:
        return []
    result: list[dict[str, Any]] = []
    for index, dev in enumerate(module.devices()):
        if isinstance(dev, dict):
            result.append(dict(dev))
        elif hasattr(dev, "to_dict"):
            result.append(dict(dev.to_dict()))
        else:
            result.append({"index": index, "beschreibung": str(dev)})
    return result


def status(module_name: str = "mikroptim") -> MikroptimStatus:
    """Prüft Mikroptim, ohne Ausnahmen nach außen zu geben."""
    try:
        module = _import(module_name)
    except Exception as exc:  # ImportError, aber auch fehlende DLLs unter Windows (OSError)
        return MikroptimStatus(False, error=f"{type(exc).__name__}: {exc}")

    missing = [name for name in REQUIRED_NAMES if not hasattr(module, name)]
    version = str(getattr(module, "__version__", "")) or None
    if missing:
        return MikroptimStatus(
            False, version=version, error="es fehlen öffentliche Namen: " + ", ".join(missing)
        )
    if version is None or parse_version(version) < MIN_MIKROPTIM_VERSION:
        need = ".".join(map(str, MIN_MIKROPTIM_VERSION))
        return MikroptimStatus(
            False, version=version, error=f"Version {version} ist älter als {need}"
        )

    try:
        devices = _device_dicts(module)
    except Exception as exc:  # GPU-Abfrage darf die GUI nie stoppen
        return MikroptimStatus(
            True,
            version=version,
            has_cuda=bool(module.has_cuda),
            error=f"GPU-Abfrage fehlgeschlagen: {type(exc).__name__}: {exc}",
        )
    return MikroptimStatus(True, version=version, has_cuda=bool(module.has_cuda), devices=devices)


def require(module_name: str = "mikroptim") -> ModuleType:
    """Das Modul ``mikroptim``; :class:`MikroptimUnavailable`, wenn es nicht nutzbar ist."""
    st = status(module_name)
    if not st.available:
        raise MikroptimUnavailable(st.error or "Mikroptim nicht verfügbar")
    return _import(module_name)
