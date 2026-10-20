"""Optionen von ``mikroptim.optimize`` bzw. ``mikroptim optimize`` (G3-T1).

Standardwerte und Regeln wie in Mikroptim ``docs/cli.md``, Abschnitt „mikroptim optimize“:
Störung und Seed wirken nur mit ``runs ≥ 2``; ein eigenes Strafgewicht ``fail_weight`` gibt es
nur beim weichen Strahlversagen (nicht mit ``hard_failure``); ``device`` nur mit ``gpu``.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

JACOBIANS = ("fd", "adjoint")


@dataclass(frozen=True)
class OptimizeOptions:
    max_iterations: int = 100
    rings: int = 10
    spokes: int = 8
    runs: int = 1
    perturbation: float = 0.05
    seed: int = 0
    fail_weight: float | None = None  # None: Standard von Mikroptim
    hard_failure: bool = False
    gpu: bool = False
    device: int = 0
    jacobian: str = "fd"

    def validate(self) -> None:
        if self.max_iterations < 0:
            raise ValueError("Zyklen pro Lauf müssen ≥ 0 sein (0: nur Startpunkt auswerten)")
        if self.rings < 1 or self.spokes < 1:
            raise ValueError("Ringe und Speichen müssen mindestens 1 sein")
        if self.runs < 1:
            raise ValueError("Läufe müssen mindestens 1 sein")
        if not (self.perturbation >= 0 and math.isfinite(self.perturbation)):
            raise ValueError("Störung muss endlich und ≥ 0 sein")
        if self.seed < 0:
            raise ValueError("Seed muss ≥ 0 sein")
        if self.fail_weight is not None:
            if not (math.isfinite(self.fail_weight) and self.fail_weight > 0):
                raise ValueError("Strafgewicht muss endlich und > 0 sein")
            if self.hard_failure:
                raise ValueError("Strafgewicht nur beim weichen Strahlversagen (nicht mit hartem)")
        if self.jacobian not in JACOBIANS:
            raise ValueError(f"Jacobi-Matrix {self.jacobian!r} unbekannt")
        if self.device < 0:
            raise ValueError("Gerät muss ≥ 0 sein")

    @property
    def multistart(self) -> bool:
        return self.runs >= 2

    def kwargs(self) -> dict[str, Any]:
        """Schlüsselwortargumente für ``mikroptim.optimize`` (ohne ``callback``)."""
        self.validate()
        d = OptimizeOptions()
        return {
            "max_iterations": self.max_iterations,
            "rings": self.rings,
            "spokes": self.spokes,
            "runs": self.runs,
            "perturbation": self.perturbation if self.multistart else d.perturbation,
            "seed": self.seed if self.multistart else d.seed,
            "fail_weight": self.fail_weight,
            "hard_failure": self.hard_failure,
            "gpu": self.gpu,
            "device": self.device if self.gpu else d.device,
            "jacobian": self.jacobian,
        }

    def cli_args(self) -> list[str]:
        """Dieselben Optionen für ``mikroptim optimize`` (nur Abweichungen vom Standard)."""
        self.validate()
        d = OptimizeOptions()
        args: list[str] = []
        if self.max_iterations != d.max_iterations:
            args += ["--max-iterations", str(self.max_iterations)]
        if self.rings != d.rings:
            args += ["--rings", str(self.rings)]
        if self.spokes != d.spokes:
            args += ["--spokes", str(self.spokes)]
        if self.multistart:
            args += ["--runs", str(self.runs)]
            if self.perturbation != d.perturbation:
                args += ["--perturbation", repr(float(self.perturbation))]
            if self.seed != d.seed:
                args += ["--seed", str(self.seed)]
        if self.hard_failure:
            args.append("--hard-failure")
        elif self.fail_weight is not None:
            args += ["--fail-weight", repr(float(self.fail_weight))]
        if self.jacobian != d.jacobian:
            args += ["--jacobian", self.jacobian]
        if self.gpu:
            args.append("--gpu")
            if self.device != d.device:
                args += ["--device", str(self.device)]
        return args

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
