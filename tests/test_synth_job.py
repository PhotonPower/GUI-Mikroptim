"""G4-T3: Optionen und Befehl von ``mikroptim synth`` (ohne Mikroptim)."""

from pathlib import Path

import pytest

from gui_mikroptim.backend import synth_job as sj


def test_defaults_give_minimal_command():
    o = sj.SynthOptions()
    assert o.cli_args() == []
    argv = sj.synth_argv(None, o)
    assert argv[1:4] == ["-m", "mikroptim", "synth"]
    assert argv[4:] == ["{eingabe:0}", "-o", "ergebnis.json", "--log", "protokoll.json"]


def test_non_defaults_and_beam():
    o = sj.SynthOptions(
        target_na=0.6,
        target_field=0.5,
        rms_target=0.05,
        step=(0.01, 0.001, 0.05),
        max_elements=8,
        curvature_bound=1.0,
        jacobian="adjoint",
        gpu=True,
        device=1,
        beam=3,
        alternatives=2,
        starts=4,
        seed=7,
        prefilter=True,
    )
    args = o.cli_args()
    assert args == [
        "--target-na", "0.6", "--target-field", "0.5", "--rms-target", "0.05",
        "--step", "0.01,0.001,0.05", "--max-elements", "8", "--curvature-bound", "1.0",
        "--gpu", "--device", "1", "--jacobian", "adjoint", "--beam", "3",
        "--alternatives", "2", "--starts", "4", "--seed", "7", "--prefilter",
    ]  # fmt: skip
    argv = sj.synth_argv(Path("/opt/mikroptim"), o)
    assert argv[0] == str(Path("/opt/mikroptim"))
    assert argv[-2:] == ["--dot", "stammbaum.dot"]


def test_beam_options_only_with_beam():
    o = sj.SynthOptions(alternatives=3, starts=2, seed=5, prefilter=True)
    assert o.cli_args() == []
    assert "--dot" not in sj.synth_argv(None, o)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"target_na": 0.0}, "Ziel-NA"),
        ({"step": (0.02, 0.05, 0.1)}, "Schrittweite"),
        ({"max_steps": 0}, "max_steps"),
        ({"jacobian": "exakt"}, "Jacobi"),
        ({"beam": -1}, "Strahlsuche"),
        ({"min_air_gap": -0.1}, "Luftspalt"),
    ],
)
def test_validation(kwargs, message):
    with pytest.raises(ValueError, match=message):
        sj.SynthOptions(**kwargs).cli_args()


def test_to_dict_complete():
    d = sj.SynthOptions().to_dict()
    assert set(d) == set(sj.option_names())
    assert d["step"] == [0.02, 0.002, 0.1]
