"""G3-T1: Optionen von mikroptim.optimize (ohne Mikroptim)."""

import math

import pytest

from gui_mikroptim.backend.optimize_options import OptimizeOptions


def test_defaults():
    o = OptimizeOptions()
    assert o.cli_args() == []
    assert o.kwargs() == {
        "max_iterations": 100, "rings": 10, "spokes": 8, "runs": 1, "perturbation": 0.05,
        "seed": 0, "fail_weight": None, "hard_failure": False, "gpu": False, "device": 0,
        "jacobian": "fd",
    }  # fmt: skip


def test_non_defaults():
    o = OptimizeOptions(
        max_iterations=20, rings=6, spokes=12, runs=4, perturbation=0.1, seed=7,
        fail_weight=2.5, jacobian="adjoint", gpu=True, device=1,
    )  # fmt: skip
    assert o.cli_args() == [
        "--max-iterations", "20", "--rings", "6", "--spokes", "12", "--runs", "4",
        "--perturbation", "0.1", "--seed", "7", "--fail-weight", "2.5",
        "--jacobian", "adjoint", "--gpu", "--device", "1",
    ]  # fmt: skip


def test_perturbation_and_seed_only_with_multistart():
    o = OptimizeOptions(runs=1, perturbation=0.3, seed=9)
    assert o.cli_args() == []
    assert o.kwargs()["perturbation"] == 0.05 and o.kwargs()["seed"] == 0
    assert OptimizeOptions(runs=2).cli_args() == ["--runs", "2"]


def test_hard_failure_and_device_without_gpu():
    assert OptimizeOptions(hard_failure=True).cli_args() == ["--hard-failure"]
    o = OptimizeOptions(device=2)  # ohne GPU wirkungslos
    assert o.cli_args() == [] and o.kwargs()["device"] == 0
    assert OptimizeOptions(max_iterations=0).cli_args() == ["--max-iterations", "0"]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"max_iterations": -1}, "Zyklen"),
        ({"rings": 0}, "Ringe"),
        ({"runs": 0}, "Läufe"),
        ({"perturbation": -0.1}, "Störung"),
        ({"perturbation": math.inf}, "Störung"),
        ({"fail_weight": 0.0}, "Strafgewicht"),
        ({"fail_weight": 1.0, "hard_failure": True}, "weichen"),
        ({"jacobian": "analytisch"}, "Jacobi"),
    ],
)
def test_validation(kwargs, message):
    with pytest.raises(ValueError, match=message):
        OptimizeOptions(**kwargs).cli_args()
