"""Einstellungen aus Umgebungsvariablen (docs/betrieb.md, „Konfiguration“).

Alle Pfade werden beim Laden absolut gemacht. Fehlt ein optionales Verzeichnis, bleibt die
Einstellung erhalten und die Startseite meldet es; nur der Arbeitsbereich wird bei Bedarf angelegt.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

ENV_WORKSPACE = "MKO_GUI_WORKSPACE"
ENV_MIKROPTIM_REPO = "MKO_GUI_MIKROPTIM_REPO"
ENV_CLI = "MKO_GUI_CLI"
ENV_MAX_JOBS = "MKO_GUI_MAX_JOBS"

#: Unterverzeichnisse des Arbeitsbereichs (arbeitsbereich/README.md)
WORKSPACE_SUBDIRS = ("uploads", "ergebnisse", "jobs")

_DEFAULT_WORKSPACE = Path(__file__).resolve().parents[2] / "arbeitsbereich"


class ConfigError(ValueError):
    """Ungültige Einstellung; die Meldung nennt die Umgebungsvariable."""


@dataclass(frozen=True)
class Settings:
    """Einstellungen der GUI.

    Attributes:
        workspace: Arbeitsbereich, einziges Verzeichnis, in das die GUI schreibt.
        mikroptim_repo: Checkout von Mikroptim (Beispielsysteme unter ``data/systems``,
            Glaskataloge) oder ``None``.
        cli: Programm ``mikroptim`` für Jobs, oder ``None`` (dann ``python -m mikroptim``).
        max_jobs: höchstens gleichzeitig laufende Jobs (ab G4).
    """

    workspace: Path
    mikroptim_repo: Path | None
    cli: Path | None
    max_jobs: int

    @property
    def example_systems_dir(self) -> Path | None:
        """``data/systems`` im Mikroptim-Checkout, falls vorhanden."""
        if self.mikroptim_repo is None:
            return None
        path = self.mikroptim_repo / "data" / "systems"
        return path if path.is_dir() else None

    def ensure_workspace(self) -> None:
        """Legt den Arbeitsbereich und seine Unterverzeichnisse an."""
        for name in WORKSPACE_SUBDIRS:
            (self.workspace / name).mkdir(parents=True, exist_ok=True)


def _optional_path(env: Mapping[str, str], name: str) -> Path | None:
    value = env.get(name, "").strip()
    return Path(value).expanduser().resolve() if value else None


def _resolve_cli(env: Mapping[str, str]) -> Path | None:
    value = env.get(ENV_CLI, "").strip()
    if not value:
        return None
    candidate = Path(value).expanduser()
    if candidate.parent != Path(".") or candidate.is_file():
        return candidate.resolve()
    found = shutil.which(value)
    if found is None:
        raise ConfigError(f"{ENV_CLI}: Programm '{value}' nicht gefunden")
    return Path(found).resolve()


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Liest die Einstellungen aus ``env`` (Standard: ``os.environ``)."""
    env = os.environ if env is None else env

    workspace = _optional_path(env, ENV_WORKSPACE) or _DEFAULT_WORKSPACE.resolve()
    if workspace.exists() and not workspace.is_dir():
        raise ConfigError(f"{ENV_WORKSPACE}: '{workspace}' ist kein Verzeichnis")

    raw_jobs = env.get(ENV_MAX_JOBS, "1").strip() or "1"
    try:
        max_jobs = int(raw_jobs)
    except ValueError as exc:
        raise ConfigError(f"{ENV_MAX_JOBS}: '{raw_jobs}' ist keine ganze Zahl") from exc
    if max_jobs < 1:
        raise ConfigError(f"{ENV_MAX_JOBS}: muss mindestens 1 sein, ist {max_jobs}")

    return Settings(
        workspace=workspace,
        mikroptim_repo=_optional_path(env, ENV_MIKROPTIM_REPO),
        cli=_resolve_cli(env),
        max_jobs=max_jobs,
    )
