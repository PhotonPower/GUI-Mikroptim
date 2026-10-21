"""Synthese als Job (G4-T3): Optionen von ``mikroptim synth`` und Anlegen des Jobs.

Optionen und Standardwerte wie in Mikroptim ``docs/cli.md``, Abschnitt „mikroptim synth“. In den
Befehl kommen nur Optionen, die vom Standard abweichen; alle Werte stehen zusätzlich in
``job.json`` (``options``).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from gui_mikroptim.backend import jobs, mko

RESULT_FILE = "ergebnis.json"
LOG_FILE = "protokoll.json"
DOT_FILE = "stammbaum.dot"
JACOBIANS = ("fd", "adjoint")


@dataclass(frozen=True)
class SynthOptions:
    """Optionen von ``mikroptim synth``; ``None`` bzw. der Standardwert lässt die Option weg."""

    target_na: float | None = None  # Standard: NA des Starts
    start_field: float = 1.0
    target_field: float | None = None  # Standard: wie am Start
    rms_target: float = 1.0 / 14.0
    merit_factor: float = 1.0
    step: tuple[float, float, float] = (0.02, 0.002, 0.1)
    max_elements: int = 6
    max_steps: int = 400
    max_iterations: int = 500
    rings: int = 10
    spokes: int = 8
    element_thickness: float = 0.5
    element_max_thickness: float = 5.0
    element_stages: int = 5
    min_air_gap: float = 0.1
    saddle_delta: float = 0.002
    curvature_bound: float | None = None  # Standard offen
    gpu: bool = False
    device: int = 0
    jacobian: str = "fd"
    # Strahlsuche (--beam, Mikroptim M6-T4); 0 = aus
    beam: int = 0
    alternatives: int = 1
    starts: int = 0
    start_perturbation: float = 0.01
    seed: int = 0
    prefilter: bool = False
    dedup: float = 1e-4

    def validate(self) -> None:
        def positive(name: str, value: float) -> None:
            if not value > 0:
                raise ValueError(f"{name} muss positiv sein, nicht {value}")

        if self.target_na is not None:
            positive("Ziel-NA", self.target_na)
        positive("Start-Feldanteil", self.start_field)
        if self.target_field is not None:
            positive("Ziel-Feldanteil", self.target_field)
        positive("RMS-Ziel", self.rms_target)
        positive("Merit-Faktor", self.merit_factor)
        d0, dmin, dmax = self.step
        if not 0 < dmin <= d0 <= dmax:
            raise ValueError(f"Schrittweite: 0 < D_min ≤ D₀ ≤ D_max verlangt, nicht {self.step}")
        for name in ("max_elements", "max_steps", "max_iterations", "rings", "spokes"):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} muss mindestens 1 sein")
        positive("Elementdicke", self.element_thickness)
        if self.element_stages < 1:
            raise ValueError("Dickenstufen müssen mindestens 1 sein")
        if self.min_air_gap < 0 or self.saddle_delta < 0:
            raise ValueError("Luftspalt und Sattel-Δ dürfen nicht negativ sein")
        if self.curvature_bound is not None:
            positive("Krümmungsschranke", self.curvature_bound)
        if self.jacobian not in JACOBIANS:
            raise ValueError(f"Jacobi-Matrix {self.jacobian!r} unbekannt")
        if self.beam < 0 or self.alternatives < 1 or self.starts < 0 or self.seed < 0:
            raise ValueError("Strahlsuche: Breite ≥ 0, Alternativen ≥ 1, Starts ≥ 0, Seed ≥ 0")

    def cli_args(self) -> list[str]:
        """Argumente für ``mikroptim synth`` (ohne Eingabe und Ausgabedateien)."""
        self.validate()
        default = SynthOptions()
        args: list[str] = []

        def add(flag: str, value: Any, base: Any) -> None:
            if value is not None and value != base:
                args.extend([flag, _num(value)])

        add("--target-na", self.target_na, None)
        add("--start-field", self.start_field, default.start_field)
        add("--target-field", self.target_field, None)
        add("--rms-target", self.rms_target, default.rms_target)
        add("--merit-factor", self.merit_factor, default.merit_factor)
        if tuple(self.step) != default.step:
            args.extend(["--step", ",".join(_num(v) for v in self.step)])
        for name in ("max_elements", "max_steps", "max_iterations", "rings", "spokes"):
            add("--" + name.replace("_", "-"), getattr(self, name), getattr(default, name))
        for name in (
            "element_thickness",
            "element_max_thickness",
            "element_stages",
            "min_air_gap",
            "saddle_delta",
        ):
            add("--" + name.replace("_", "-"), getattr(self, name), getattr(default, name))
        add("--curvature-bound", self.curvature_bound, None)
        if self.gpu:
            args.extend(["--gpu", "--device", str(self.device)])
        add("--jacobian", self.jacobian, default.jacobian)
        if self.beam >= 1:
            args.extend(["--beam", str(self.beam)])
            add("--alternatives", self.alternatives, default.alternatives)
            add("--starts", self.starts, default.starts)
            add("--start-perturbation", self.start_perturbation, default.start_perturbation)
            add("--seed", self.seed, default.seed)
            if self.prefilter:
                args.append("--prefilter")
            add("--dedup", self.dedup, default.dedup)
        return args

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["step"] = list(self.step)
        return data


def _num(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    return str(value)


def option_names() -> list[str]:
    return [f.name for f in fields(SynthOptions)]


def synth_argv(cli: Path | None, options: SynthOptions) -> list[str]:
    """Vollständiger Befehl; die Eingabe ist ``{eingabe:0}`` (Kopie im Jobordner)."""
    args = ["synth", "{eingabe:0}", *options.cli_args(), "-o", RESULT_FILE, "--log", LOG_FILE]
    if options.beam >= 1:
        args += ["--dot", DOT_FILE]
    return jobs.mikroptim_argv(cli, args)


def copy_system_with_catalogs(source: Path, target: Path) -> None:
    """Systemdatei in den Jobordner kopieren, sodass Glaskataloge von dort gefunden werden:
    Mikroptim lädt sie am alten Ort und schreibt sie mit ``System.save`` neu (die Pfade unter
    ``glass_catalogs`` werden relativ zur neuen Datei)."""
    m = mko.require()
    m.load_system(str(source)).save(str(target))


def submit_synth(
    workspace: Path,
    system_path: Path,
    options: SynthOptions,
    max_jobs: int,
    allowed_roots: list[Path],
    cli: Path | None = None,
    queue_root: Path | None = None,
) -> jobs.Job:
    """Legt den Synthese-Job an (und startet ihn, wenn ein Platz frei ist)."""
    status = mko.status()
    return jobs.submit(
        workspace,
        "synth",
        synth_argv(cli, options),
        max_jobs,
        inputs=[system_path],
        allowed_roots=allowed_roots,
        options={"synth": options.to_dict(), "system": system_path.name},
        mikroptim_version=status.version,
        copy_system=copy_system_with_catalogs,
        queue_root=queue_root,
    )


def outputs(job: jobs.Job) -> dict[str, Path]:
    """Vorhandene Ergebnisdateien eines Synthese-Jobs."""
    found = {}
    for key, name in (("ergebnis", RESULT_FILE), ("protokoll", LOG_FILE), ("dot", DOT_FILE)):
        path = job.path / name
        if path.is_file():
            found[key] = path
    return found
