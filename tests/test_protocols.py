import json
from pathlib import Path

import pytest

from gui_mikroptim.backend import protocols


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("mikroptim.synth/1", ("mikroptim.synth", 1)),
        ("mikroptim.system/1.2", ("mikroptim.system", 1)),
        ("mikroptim.system", None),
        ("/1", None),
        (3, None),
        (None, None),
    ],
)
def test_parse_format(value, expected):
    fmt = protocols.parse_format(value)
    assert (fmt.name, fmt.major) == expected if expected else fmt is None


def _write(tmp_path: Path, data) -> Path:
    path = tmp_path / "d.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_load_document_accepts_known_format(tmp_path: Path):
    fmt, data = protocols.load_document(_write(tmp_path, {"format": "mikroptim.system/1"}))
    assert str(fmt) == "mikroptim.system/1"
    assert fmt.label == "Systembeschreibung"
    assert data["format"] == "mikroptim.system/1"


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ([1, 2], "kein JSON-Objekt"),
        ({"name": "x"}, "format"),
        ({"format": "fremd.format/1"}, "unbekanntes Format"),
        ({"format": "mikroptim.synth/2"}, "Hauptversion 2"),
    ],
)
def test_load_document_errors(tmp_path: Path, data, message: str):
    with pytest.raises(protocols.ProtocolError, match=message):
        protocols.load_document(_write(tmp_path, data))


def test_load_document_invalid_json(tmp_path: Path):
    path = tmp_path / "kaputt.json"
    path.write_text("{nicht json", encoding="utf-8")
    with pytest.raises(protocols.ProtocolError, match="nicht lesbar"):
        protocols.load_document(path)


def test_load_synth_steps_and_summary(test_data: Path):
    proto = protocols.load_synth(test_data / "synth_beispiel.json")
    assert proto.status == "goal_reached"
    assert [s["schritt"] for s in proto.steps] == [0, 1, 2]
    second = proto.steps[1]
    assert second["na"] == 0.31
    assert second["aktion"] == "insert"
    assert second["empfehlung"] == "A"
    assert second["lm_iterationen"] == 500
    assert proto.steps[2]["rms_wellen"] is None  # nicht endlich steht als null
    summary = proto.summary()
    assert summary["elemente"] == 2
    assert summary["ziel_erreicht"] is True


def test_load_synth_rejects_other_format(tmp_path: Path):
    with pytest.raises(protocols.ProtocolError, match=r"erwartet mikroptim\.synth"):
        protocols.load_synth(_write(tmp_path, {"format": "mikroptim.system/1"}))


def test_synth_without_steps_and_beam(tmp_path: Path):
    proto = protocols.load_synth(_write(tmp_path, {"format": "mikroptim.synth/1"}))
    assert proto.steps == []
    assert not proto.has_beam_search


def test_candidate_tree_dot(test_data: Path):
    proto = protocols.load_synth(test_data / "synth_beispiel.json")
    assert proto.has_beam_search
    dot = protocols.candidate_tree_dot(proto)
    assert dot.startswith("digraph kandidaten {")
    assert "k0 -> k1;" in dot
    assert "k0 -> k2;" in dot
    assert '\\"Zweig +\\"' in dot  # Anführungszeichen maskiert
    best_line = next(line for line in dot.splitlines() if line.strip().startswith("k2 ["))
    assert "penwidth=3" in best_line
    assert dot.rstrip().endswith("}")
