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


# --- Wellenfront (G2-T1) -----------------------------------------------------------------------

PRECISIONS = ("fp64", "df64")


@dataclass(frozen=True)
class TraceOptions:
    """Optionen von ``mikroptim.trace`` (Standardwerte wie in Mikroptim)."""

    rings: int = 10
    spokes: int = 8
    gpu: bool = False
    device: int = 0
    precision: str = "fp64"

    def validate(self) -> None:
        if not 1 <= self.rings <= 256:
            raise ValueError(f"Ringe müssen zwischen 1 und 256 liegen, nicht {self.rings}")
        if not 1 <= self.spokes <= 256:
            raise ValueError(f"Speichen müssen zwischen 1 und 256 liegen, nicht {self.spokes}")
        if self.precision not in PRECISIONS:
            raise ValueError(f"Genauigkeit {self.precision!r} unbekannt")
        if self.precision != "fp64" and not self.gpu:
            raise ValueError(f'precision="{self.precision}" nur mit GPU (die CPU rechnet in FP64)')

    def cli_args(self) -> list[str]:
        """Dieselben Optionen für ``mikroptim trace`` (zum Nachrechnen auf der Kommandozeile)."""
        args = ["--rings", str(self.rings), "--spokes", str(self.spokes)]
        if self.gpu:
            args += ["--gpu", "--device", str(self.device), "--precision", self.precision]
        return args

    def label(self) -> str:
        backend = f"GPU {self.device}, {self.precision}" if self.gpu else "CPU, fp64"
        return f"{self.rings} Ringe × {self.spokes} Speichen, {backend}"


@dataclass(frozen=True)
class WavefrontResult:
    """Ergebnis von ``mikroptim.trace`` als NumPy-Arrays [Feld, Wellenlänge] (picklebar)."""

    rms_waves: Any
    rms_mm: Any
    piston_mm: Any
    rays: Any
    failed: Any
    image_points: Any  # [Feld, 3] in mm
    pupil_modes: list[str]
    wavelengths_nm: Any
    reference_nm: float
    target_focal_length: float | None
    backend: str
    device_name: str
    precision: str
    rings: int
    spokes: int

    @property
    def total_rays(self) -> int:
        return int(self.rays.sum())

    @property
    def total_failed(self) -> int:
        return int(self.failed.sum())


def trace_wavefront(system: Any, options: TraceOptions) -> WavefrontResult:
    """``mikroptim.trace``; Ausnahmen (``ValueError`` bei afokalen Systemen,
    ``GpuUnavailableError``, ``CudaError``) werden durchgereicht."""
    import numpy as np

    options.validate()
    m = mko.require()
    w = m.trace(
        system,
        rings=options.rings,
        spokes=options.spokes,
        gpu=options.gpu,
        device=options.device,
        precision=options.precision,
    )
    target = getattr(w, "target_focal_length", None)
    return WavefrontResult(
        rms_waves=np.array(w.rms_waves, dtype=float),
        rms_mm=np.array(w.rms_mm, dtype=float),
        piston_mm=np.array(w.piston_mm, dtype=float),
        rays=np.array(w.rays, dtype=int),
        failed=np.array(w.failed, dtype=int),
        image_points=np.array(w.image_points, dtype=float),
        pupil_modes=list(w.pupil_modes),
        wavelengths_nm=np.array(w.wavelengths_nm, dtype=float),
        reference_nm=float(w.reference_nm),
        target_focal_length=None if target is None else float(target),
        backend=str(w.backend),
        device_name=str(getattr(w, "device_name", "") or ""),
        precision=str(w.precision),
        rings=int(w.rings),
        spokes=int(w.spokes),
    )


# --- EVAL: OPD-Karten und Spots (G2-T2) ---------------------------------------------------------

REFERENCES = ("exit-pupil", "vertex")
REMOVALS = ("piston", "tilt", "defocus")


@dataclass(frozen=True)
class EvalOptions:
    """Optionen von ``mikroptim.evaluate`` (Standardwerte wie ``mikroptim eval``)."""

    grid: int = 64
    half: bool = False
    reference: str = "exit-pupil"
    gpu: bool = False
    device: int = 0

    def validate(self) -> None:
        if not 1 <= self.grid <= 2048:
            raise ValueError(f"Raster muss zwischen 1 und 2048 liegen, nicht {self.grid}")
        if self.reference not in REFERENCES:
            raise ValueError(f"Referenz {self.reference!r} unbekannt")

    def cli_args(self) -> list[str]:
        """Dieselben Optionen für ``mikroptim eval``."""
        args = ["--grid", str(self.grid), "--reference", self.reference]
        if self.half:
            args.append("--half")
        if self.gpu:
            args += ["--gpu", "--device", str(self.device)]
        return args


def mm_to_waves(value_mm: Any, reference_nm: float) -> Any:
    """OPD in mm → Wellen bei λ_ref, genau wie ``mikroptim eval`` (bitgleich): mm / (λ·10⁻⁶)."""
    return value_mm / (reference_nm * 1e-6)


def evaluate(system: Any, options: EvalOptions) -> Any:
    """``mikroptim.evaluate``; gibt das ``Evaluation``-Objekt zurück (OPD-Karten und Spots
    werden pro Tupel daraus gelesen). Ausnahmen werden durchgereicht."""
    options.validate()
    return mko.require().evaluate(
        system,
        grid=options.grid,
        half=options.half,
        reference=options.reference,
        gpu=options.gpu,
        device=options.device,
    )
