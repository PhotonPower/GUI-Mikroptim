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


def test_peek_format(tmp_path: Path, test_data: Path):
    assert str(protocols.peek_format(test_data / "synth_beispiel.json")) == "mikroptim.synth/1"
    plain = tmp_path / "x.json"
    plain.write_text('{"name": "ohne Format"}', encoding="utf-8")
    assert protocols.peek_format(plain) is None
    assert protocols.peek_format(tmp_path / "fehlt.json") is None


def test_list_documents_filters_by_format(tmp_path: Path, test_data: Path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "lauf.json").write_bytes((test_data / "synth_beispiel.json").read_bytes())
    (tmp_path / "system.json").write_text('{"format": "mikroptim.system/1"}', encoding="utf-8")
    (tmp_path / "sonst.json").write_text("{}", encoding="utf-8")
    found = protocols.list_documents(tmp_path, ("mikroptim.synth",))
    assert [e.label for e in found] == ["a/lauf.json"]
    both = protocols.list_documents(tmp_path, ("mikroptim.synth", "mikroptim.system"))
    assert len(both) == 2


def test_summary_status_text_and_endpoint(test_data: Path):
    proto = protocols.load_synth(test_data / "synth_beispiel.json")
    s = proto.summary()
    assert s["status_text"] == "Ziel erreicht"
    assert s["na_ende"] is None  # Testprotokoll hat keinen result.point


def test_best_candidate_as_number_or_object(test_data: Path):
    data = json.loads((test_data / "synth_beispiel.json").read_text(encoding="utf-8"))
    assert protocols.read_synth(data).best_candidate_id == 2
    data["result"]["beam_search"]["best"] = 1  # so schreibt es Mikroptim (M6-T4)
    proto = protocols.read_synth(data)
    assert proto.best_candidate_id == 1
    rows = proto.candidate_rows()
    assert [r["bester"] for r in rows] == [False, True, False]
    assert rows[1]["eltern"] == 0


def test_goal_rows(test_data: Path):
    data = json.loads((test_data / "synth_beispiel.json").read_text(encoding="utf-8"))
    assert protocols.read_synth(data).goal_rows() == []
    data["result"]["goal"]["tuples"] = [{"field": 0, "wavelength": 0, "rms_waves": 0.03}, "x"]
    assert protocols.read_synth(data).goal_rows() == [
        {"field": 0, "wavelength": 0, "rms_waves": 0.03}
    ]


def test_filter_steps_and_distinct(test_data: Path):
    steps = protocols.load_synth(test_data / "synth_beispiel.json").steps
    assert protocols.distinct(steps, "art") == ["start", "aperture"]
    assert protocols.distinct(steps, "empfehlung") == ["A"]
    assert len(protocols.filter_steps(steps)) == 3
    assert [r["schritt"] for r in protocols.filter_steps(steps, kinds=["aperture"])] == [1, 2]
    assert [r["schritt"] for r in protocols.filter_steps(steps, accepted=False)] == [1]
    assert [r["schritt"] for r in protocols.filter_steps(steps, actions=["insert"])] == [1]
    assert [r["schritt"] for r in protocols.filter_steps(steps, candidate=2)] == [2]
    assert protocols.filter_steps(steps, kinds=["aperture"], accepted=False, candidate=2) == []
