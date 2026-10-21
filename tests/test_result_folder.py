"""G4-T4: Gliederung eines Ergebnisordners (ohne Mikroptim)."""

import json
import os
from pathlib import Path

import pytest

from gui_mikroptim.backend import result_folder as rf


def _system(name="S"):
    return {
        "format": "mikroptim.system/1",
        "name": name,
        "surfaces": [{}, {}],
        "source": {"field_angles_deg": [0, 1]},
        "spectrum": {"wavelengths_nm": [546.07]},
    }


def _eval():
    return {
        "format": "mikroptim.eval/1", "system": "S", "grid": 64, "reference_sphere": "vertex",
        "psf": {"model": "scalar"}, "failed_rays": 2,
        "tuples": [{"rms_opd_waves": 0.2, "psf": {"strehl": 0.8}},
                   {"rms_opd_waves": None, "psf": {"strehl": 0.5}}, {"rms_opd_waves": 0.05}],
    }  # fmt: skip


@pytest.fixture
def folder(tmp_path: Path, test_data: Path) -> Path:
    root = tmp_path / "lauf1"
    root.mkdir()
    (root / "p1_final.json").write_text(json.dumps(_system("Stufe 1")), encoding="utf-8")
    (root / "p10_final.json").write_text(json.dumps(_system("Stufe 10")), encoding="utf-8")
    (root / "p2_r0_log.json").write_bytes((test_data / "synth_beispiel.json").read_bytes())
    (root / "a3_psf.json").write_text(json.dumps(_eval()), encoding="utf-8")
    (root / "p2_r0.txt").write_text("Textausgabe", encoding="utf-8")
    (root / "lauf.json").write_text('{"stages": {}}', encoding="utf-8")
    (root / "baum.dot").write_text("digraph {}", encoding="utf-8")
    (root / ".versteckt.json").write_text("{}", encoding="utf-8")
    (tmp_path / "lauf1-bericht.md").write_text("# Bericht", encoding="utf-8")
    return root


def test_scan_and_counts(folder):
    inv = rf.scan(folder)
    assert inv.counts() == {
        rf.SYSTEM: 2, rf.SYNTH: 1, rf.EVAL: 1, rf.TEXT: 1, rf.JSON: 1, rf.DOT: 1,
    }  # fmt: skip
    assert ".versteckt.json" not in [f.relative for f in inv.files]
    assert inv.stages() == ["a3", "p1", "p2", "p10", "–"]  # natürliche Reihenfolge


@pytest.mark.parametrize(
    ("name", "stage"),
    [("p3_r15_restart.json", "p3"), ("z2_s0.json", "z2"), ("a1_r0.txt", "a1"),
     ("p7.json", "p7"), ("m6t6_lauf.json", "–"), ("ergebnis.json", "–")],
)  # fmt: skip
def test_stage_of(name, stage):
    assert rf.stage_of(name) == stage


def test_report(folder):
    assert rf.find_report(folder).name == "lauf1-bericht.md"
    (folder / "README.md").write_text("innen", encoding="utf-8")
    assert rf.find_report(folder).name == "README.md"  # Bericht im Ordner hat Vorrang


def test_candidate_folders(folder):
    (folder.parent / "leer").mkdir()
    (folder.parent / "nur_text").mkdir()
    (folder.parent / "nur_text" / "a.txt").write_text("x")
    assert rf.candidate_folders(folder.parent) == [folder]
    assert rf.candidate_folders(folder.parent / "fehlt") == []


def test_rows(folder):
    inv = rf.scan(folder)
    system = rf.system_row(inv.of(rf.SYSTEM)[0])
    assert system == {"Datei": "p1_final.json", "Stufe": "p1", "Name": "Stufe 1", "Flächen": 2,
                      "Felder": 2, "Wellenlängen": 1, "Geisterplatten": 0}  # fmt: skip
    synth = rf.synth_row(inv.of(rf.SYNTH)[0])
    assert synth["Status"] == "Ziel erreicht" and synth["Elemente"] == "1 → 2"
    ev = rf.eval_row(inv.of(rf.EVAL)[0])
    assert ev["RMS-OPD max [W]"] == 0.2 and ev["RMS-OPD min [W]"] == 0.05  # None ignoriert
    assert (ev["Strehl min"], ev["Strehl max"]) == (0.5, 0.8)
    assert ev["Referenz"] == "vertex" and ev["Tupel"] == 3 and ev["versagt"] == 2
    stages = {r["Stufe"]: r for r in rf.stage_rows(inv)}
    assert stages["p2"]["Protokolle"] == 1 and stages["p2"]["Texte"] == 1
    assert stages["–"]["weitere"] == 2  # lauf.json, baum.dot


def test_unreadable_protocol_row(folder):
    (folder / "p5_log.json").write_text('{"format": "mikroptim.synth/1", ', encoding="utf-8")
    inv = rf.scan(folder)
    row = next(rf.synth_row(f) for f in inv.of(rf.SYNTH) if f.relative == "p5_log.json")
    assert row["Status"] == "nicht lesbar"


@pytest.mark.skipif(os.name == "nt", reason="Symlinks brauchen unter Windows Rechte")
def test_symlink_outside_is_skipped(folder, tmp_path):
    outside = tmp_path / "draussen.json"
    outside.write_text(json.dumps(_system()), encoding="utf-8")
    (folder / "p9_link.json").symlink_to(outside)
    assert "p9_link.json" not in [f.relative for f in rf.scan(folder).files]
