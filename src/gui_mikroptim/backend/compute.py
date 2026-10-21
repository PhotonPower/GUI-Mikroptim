"""Dünne Hüllen um Mikroptim-Aufrufe der Seiten (ADR-0002).

Ruft nur öffentliche Funktionen von ``mikroptim`` auf (über :func:`mko.require`) und bündelt
die Fehlerbehandlung. Ohne Streamlit; das Zwischenspeichern übernehmen die Seiten.
"""

from __future__ import annotations

import json
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


def repair_catalogs(path: Path, workspace: Path, repo: Path | None) -> Path:
    """Speichert eine Systemdatei neu, deren Glaskataloge vom eigenen Ort aus nicht zu finden sind.

    Nicht gefundene Einträge von ``glass_catalogs`` ordnet :func:`catalogs.resolve_entries` dem
    Mikroptim-Checkout oder den hochgeladenen Katalogen zu (ADR-0006). Mikroptim lädt den Text mit
    diesen Pfaden (``System.from_json``) und schreibt ihn mit ``System.save`` nach
    ``uploads/<name>-kataloge.json``; ``save`` macht die Pfade relativ zum neuen Ort. Die Eingabe
    bleibt unverändert, nichts wird überschrieben.

    Raises:
        catalogs.CatalogError: wenn ein Katalog nirgends zu finden ist (Meldung nennt ihn).
    """
    from gui_mikroptim.backend import catalogs

    m = mko.require()
    text = path.read_text(encoding="utf-8")
    entries = list(json.loads(text).get("glass_catalogs") or [])
    resolved = catalogs.resolve_entries(entries, path.parent, repo, workspace)
    missing = [r.entry for r in resolved if r.path is None]
    if missing:
        raise catalogs.CatalogError(
            "nicht gefunden: " + ", ".join(missing) + " – unter „Glaskataloge“ hochladen"
        )
    system = m.System.from_json(catalogs.with_absolute_catalogs(text, resolved), str(path.parent))
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


# --- PSF, MTF, Strehl (G2-T3) -------------------------------------------------------------------

POLARIZATIONS = ("x", "y", "circular", "unpolarized")
#: oberhalb dieser NA ist die skalare PSF ungenau (Mikroptim docs/numerik.md, M8-T2)
SCALAR_NA_LIMIT = 0.6
#: größtes Raster, für das die vektorielle PSF direkt in der Seite gerechnet wird
VECTOR_GRID_LIMIT = 256


@dataclass(frozen=True)
class PsfOptions:
    """Optionen der PSF wie ``mikroptim eval --psf`` (Standardwerte wie in Mikroptim)."""

    padding: float = 4.0
    numerical_aperture: float = 0.0  # 0: aus den Feldstrahlen
    gpu: bool = False
    device: int = 0

    def validate(self) -> None:
        if self.padding < 2.0:
            raise ValueError(f"Zero-Padding muss mindestens 2 sein, nicht {self.padding}")
        if self.numerical_aperture < 0.0:
            raise ValueError("NA muss ≥ 0 sein (0: aus den Feldstrahlen)")

    def cli_args(self) -> list[str]:
        args = ["--psf", "--padding", repr(float(self.padding))]
        if self.numerical_aperture > 0.0:
            args += ["--na", repr(float(self.numerical_aperture))]
        return args


@dataclass(frozen=True)
class VectorOptions:
    """Zusätze der vektoriellen PSF (``--vector``)."""

    polarization: str = "x"
    defocus_mm: float = 0.0

    def validate(self) -> None:
        if self.polarization not in POLARIZATIONS:
            raise ValueError(f"Polarisation {self.polarization!r} unbekannt")

    def cli_args(self) -> list[str]:
        return [
            "--vector",
            "--polarization",
            self.polarization,
            "--defocus",
            repr(float(self.defocus_mm)),
        ]


@dataclass(frozen=True)
class PsfResult:
    """PSF eines Tupels als NumPy-Arrays und Zahlen (picklebar).

    ``psf`` [M, M] in Strehl-Einheiten, Zeile j = y, Spalte i = x, Bildpunkt bei Index M/2:
    x = (i − M/2)·dx, y = (j − M/2)·dy relativ zum idealen Bildpunkt (Mikroptim docs/cli.md).
    """

    field: int
    wavelength: int
    wavelength_nm: float
    model: str  # "scalar" oder "vector"
    psf: Any
    dx: float
    dy: float
    fft_size: int
    frequencies: Any  # ν = f/f_c
    mtf_sagittal: Any
    mtf_tangential: Any
    cutoff_x: float
    cutoff_y: float
    na_x: float
    na_y: float
    airy_radius: float
    strehl: float
    strehl_fft: float
    strehl_origin: float
    peak: float
    peak_position: tuple[float, float]
    energy: float
    backend: str
    #: nur bei model == "vector": Feld ``vector`` von ``eval --json`` und |E_x|², |E_y|², |E_z|²
    vector: dict[str, Any] | None = None
    components: tuple[Any, Any, Any] | None = None

    @property
    def mtf_half_cutoff(self) -> tuple[float, float]:
        """MTF bei f_c/2 (Stützstelle ν = 0,5, wie ``mtf_half_cutoff`` der CLI)."""
        import numpy as np

        index = int(np.flatnonzero(np.asarray(self.frequencies) == 0.5)[0])
        return float(self.mtf_sagittal[index]), float(self.mtf_tangential[index])

    @property
    def scalar_na_too_high(self) -> bool:
        return self.model == "scalar" and max(self.na_x, self.na_y) > SCALAR_NA_LIMIT


def scalar_psf(evaluation: Any, field_index: int, wavelength: int, options: PsfOptions):
    """Skalare PSF über ``Evaluation.psf`` (wie ``mikroptim eval --psf``)."""
    import numpy as np

    options.validate()
    p = evaluation.psf(
        field_index,
        wavelength,
        padding=options.padding,
        numerical_aperture=options.numerical_aperture,
        gpu=options.gpu,
        device=options.device,
    )
    return PsfResult(
        field=int(p.field),
        wavelength=int(p.wavelength),
        wavelength_nm=float(p.wavelength_nm),
        model="scalar",
        psf=np.array(p.psf, dtype=float),
        dx=float(p.dx),
        dy=float(p.dy),
        fft_size=int(p.fft_size),
        frequencies=np.array(p.frequencies(), dtype=float),
        mtf_sagittal=np.array(p.mtf_sagittal, dtype=float),
        mtf_tangential=np.array(p.mtf_tangential, dtype=float),
        cutoff_x=float(p.cutoff_x),
        cutoff_y=float(p.cutoff_y),
        na_x=float(p.na_x),
        na_y=float(p.na_y),
        airy_radius=float(p.airy_radius),
        strehl=float(p.strehl),
        strehl_fft=float(p.strehl_fft),
        strehl_origin=float(p.strehl_origin),
        peak=float(p.peak),
        peak_position=(float(p.peak_position[0]), float(p.peak_position[1])),
        energy=float(p.energy),
        backend=str(p.backend),
    )


def window_warning(result: PsfResult, stats: dict[str, Any]) -> tuple[float, float] | None:
    """Bildfenster zu klein? Dieselbe Regel wie ``mikroptim eval`` (``psf_window_warnings``):

    Reicht der geometrische Spot (|Schwerpunkt| + 3 RMS-Radien, je Richtung) über das halbe
    Fenster M·Δ/2 hinaus, faltet die FFT die PSF zurück. Rückgabe (Reichweite, halbes Fenster)
    in mm wie in der Meldung der CLI, sonst ``None``. Die Python-API liefert diese Warnung nicht
    (Wunsch W7 in docs/schnittstelle-mikroptim.md).
    """
    f, j = result.field, result.wavelength
    half_x = 0.5 * result.fft_size * result.dx
    half_y = 0.5 * result.fft_size * result.dy
    reach_x = abs(float(stats["centroid_x"][f, j])) + 3.0 * float(stats["rms_spot"][f, j])
    reach_y = abs(float(stats["centroid_y"][f, j])) + 3.0 * float(stats["rms_spot"][f, j])
    if reach_x > half_x or reach_y > half_y:
        return max(reach_x, reach_y), min(half_x, half_y)
    return None


def _read_csv_matrix(path: Path) -> Any:
    """CSV-Matrix von ``mikroptim eval`` (erste Zeile = größtes y) als Array mit Zeile j = y."""
    import csv

    import numpy as np

    with path.open(encoding="utf-8") as handle:
        rows = [[float(v) if v.strip() else float("nan") for v in r] for r in csv.reader(handle)]
    return np.array(rows[::-1], dtype=float)


def vector_psf(
    system_path: Path,
    eval_options: EvalOptions,
    psf_options: PsfOptions,
    vector_options: VectorOptions,
    field_index: int,
    wavelength: int,
) -> PsfResult:
    """Vektorielle PSF über ``mikroptim eval --vector`` (bis Mikroptim-Wunsch W3 ohne Bindung).

    Läuft im Prozess über ``run_cli`` mit einem temporären Verzeichnis für PSF, MTF und
    Feldkomponenten; das Raster ist auf :data:`VECTOR_GRID_LIMIT` begrenzt, größere Läufe
    gehören in einen Job (ADR-0003).

    Raises:
        ValueError: ungültige Optionen oder Raster zu groß.
        RuntimeError: Exit-Code ≠ 0, mit der Meldung von Mikroptim.
    """
    import csv
    import json
    import tempfile

    import numpy as np

    eval_options.validate()
    psf_options.validate()
    vector_options.validate()
    if eval_options.grid > VECTOR_GRID_LIMIT:
        raise ValueError(
            f"Raster {eval_options.grid} zu groß für die direkte Rechnung "
            f"(höchstens {VECTOR_GRID_LIMIT}); als Job rechnen (ab G4-T1)"
        )
    m = mko.require()
    with tempfile.TemporaryDirectory(prefix="gui-mikroptim-psf-") as tmp:
        tmp_path = Path(tmp)
        args = [
            "eval",
            str(system_path),
            "--json",
            *eval_options.cli_args(),
            *psf_options.cli_args(),
            *vector_options.cli_args(),
            "--psf-tuple",
            f"{field_index},{wavelength}",
            "--psf-file",
            str(tmp_path / "psf.csv"),
            "--mtf-file",
            str(tmp_path / "mtf.csv"),
            "--component-files",
            str(tmp_path / "komponente"),
        ]
        code, out, err = m.run_cli(args)
        if code != 0:
            raise RuntimeError(f"mikroptim eval --vector endete mit {code}: {err.strip()}")
        doc = json.loads(out)
        tup = next(
            t for t in doc["tuples"] if t["field"] == field_index and t["wavelength"] == wavelength
        )
        p = tup["psf"]
        with (tmp_path / "mtf.csv").open(encoding="utf-8") as handle:
            mtf = list(csv.DictReader(handle))
        psf = _read_csv_matrix(tmp_path / "psf.csv")
        components = tuple(
            _read_csv_matrix(tmp_path / f"komponente_{c}.csv") for c in ("ex", "ey", "ez")
        )
    return PsfResult(
        field=field_index,
        wavelength=wavelength,
        wavelength_nm=float(tup["wavelength_nm"]),
        model="vector",
        psf=psf,
        dx=float(p["pixel_mm"][0]),
        dy=float(p["pixel_mm"][1]),
        fft_size=int(doc["psf"]["fft_size"]),
        frequencies=np.array([float(r["nu"]) for r in mtf]),
        mtf_sagittal=np.array([float(r["mtf_sagittal"]) for r in mtf]),
        mtf_tangential=np.array([float(r["mtf_tangential"]) for r in mtf]),
        cutoff_x=float(p["cutoff_lpmm"][0]),
        cutoff_y=float(p["cutoff_lpmm"][1]),
        na_x=float(p["na"][0]),
        na_y=float(p["na"][1]),
        airy_radius=float(p["airy_radius_mm"]),
        strehl=float(p["strehl"]),
        strehl_fft=float(p["strehl_fft"]),
        strehl_origin=float(p["strehl_origin"]),
        peak=float(p["peak"]),
        peak_position=(float(p["peak_mm"][0]), float(p["peak_mm"][1])),
        energy=float(p["energy"]),
        backend=str(doc.get("backend", "cpu")),
        vector=dict(p.get("vector") or {}),
        components=components,  # type: ignore[arg-type]
    )


def validate_catalog_with_mikroptim(path: Path) -> None:
    """Lässt Mikroptim einen Glaskatalog laden: ein Prüfsystem mit jedem Glas als Medium.

    Raises:
        Exception von Mikroptim (``FormatError``, ``GlassError``), wenn der Katalog oder ein Glas
        nicht verwendbar ist.
    """
    m = mko.require()
    data = json.loads(path.read_text(encoding="utf-8"))
    surfaces = [{"type": "stop", "thickness": 1.0, "material": "AIR", "semi_diameter": 1.0}]
    for glass in data["glasses"]:
        surfaces.append(
            {"type": "plane", "thickness": 1.0, "material": glass["name"], "semi_diameter": 1.0}
        )
    surfaces.append({"type": "plane", "thickness": 1.0, "material": "AIR", "semi_diameter": 1.0})
    probe = {
        "format": "mikroptim.system/1",
        "name": "Katalogprüfung",
        "units": "mm",
        "glass_catalogs": [str(path.resolve())],
        "spectrum": {"wavelengths_nm": [546.07], "weights": [1.0], "reference_nm": 546.07},
        "source": {"type": "collimated", "field_angles_deg": [0.0], "field_weights": [1.0]},
        "surfaces": surfaces,
    }
    m.System.from_json(json.dumps(probe), str(path.parent))
