"""G4-T3 gegen ein installiertes Mikroptim (``python -m pytest -m integration``)."""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import needs_uploader
from gui_mikroptim.backend import jobs, mko, synth_job

pytestmark = pytest.mark.integration

REPO = os.environ.get("MKO_GUI_MIKROPTIM_REPO")
START = "einzellinse_homotopie_start.json"
#: kurzer Lauf: NA 0,3 → 0,33 (ein paar Optimierungen, wenige Sekunden)
OPTIONS = synth_job.SynthOptions(target_na=0.33, max_steps=40)


@pytest.fixture
def repo(monkeypatch) -> Path:
    if not REPO:
        pytest.skip("MKO_GUI_MIKROPTIM_REPO nicht gesetzt")
    monkeypatch.setenv("MKO_GUI_MIKROPTIM_REPO", REPO)
    return Path(REPO)


def _wait(job, timeout=180):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current = jobs.load(job.path)
        if current.final:
            return current
        time.sleep(0.2)
    raise AssertionError(f"Job {job.id} nicht fertig")


def _without_seconds(value):
    """Laufzeiten entfernen; sonst muss ein Protokoll bitgleich wiederholbar sein."""
    if isinstance(value, dict):
        return {k: _without_seconds(v) for k, v in value.items() if k != "seconds"}
    if isinstance(value, list):
        return [_without_seconds(v) for v in value]
    return value


def test_synth_job_matches_manual_run(repo, workspace, tmp_path):
    source = repo / "data" / "systems" / START
    job = synth_job.submit_synth(workspace, source, OPTIONS, 1, [workspace, repo])
    assert job.data["inputs"] == [f"eingabe/{START}"]
    assert "--target-na" in job.data["argv"] and "0.33" in job.data["argv"]
    assert job.data["options"]["synth"]["target_na"] == 0.33
    done = _wait(job)
    assert done.status == jobs.DONE, (done.tail(jobs.STDERR_FILE), done.data)
    found = synth_job.outputs(done)
    assert {"ergebnis", "protokoll"} <= set(found)
    protocol = json.loads(found["protokoll"].read_text(encoding="utf-8"))
    assert protocol["format"] == "mikroptim.synth/1"
    # Ergebnis lädt vom Jobordner aus (Glaskataloge über System.save neu verknüpft)
    mko.require().load_system(str(found["ergebnis"]))

    # derselbe Befehl von Hand in einer Kopie des Jobordners ergibt dasselbe Protokoll
    manual = tmp_path / "von-hand"
    shutil.copytree(done.path / jobs.INPUT_DIR, manual / jobs.INPUT_DIR)
    subprocess.run(done.data["argv"], cwd=manual, check=True, capture_output=True, timeout=300)
    again = json.loads((manual / synth_job.LOG_FILE).read_text(encoding="utf-8"))
    assert _without_seconds(again) == _without_seconds(protocol)


@needs_uploader
def test_form_starts_job_and_shows_protocol(app_file, workspace, repo):
    at = AppTest.from_file(str(app_file), default_timeout=120).run()
    at.switch_page("pages/synthese.py").run()
    source = at.selectbox(key="synthese.neu.start.quelle")
    source.select_index(source.options.index("Beispielsysteme (Mikroptim)")).run()
    box = at.selectbox(key="synthese.neu.start.datei.Beispielsysteme (Mikroptim)")
    box.select_index(box.options.index(START)).run()
    ziel = next(n for n in at.number_input if n.label == "Ziel-NA")
    ziel.set_value(0.33)
    next(n for n in at.number_input if n.label == "max. Optimierungen").set_value(40)
    next(b for b in at.button if b.label == "Synthese starten").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("angelegt" in s.value for s in at.success)

    created = jobs.list_jobs(workspace)
    assert len(created) == 1
    job = _wait(created[0])
    assert job.status == jobs.DONE
    assert at.selectbox(key="jobs.auswahl").value == job.id  # neuer Job vorausgewählt

    at.run()
    assert not at.exception, [e.value for e in at.exception]
    keys = [c.key for c in at.get("plotly_chart")]
    assert f"jobs.synth.{job.id}.verlauf" in keys  # Protokoll direkt in den Jobdetails
    at.button(key=f"jobs.uebernehmen.{job.id}").click().run()
    assert at.session_state["aktuell.datei"].endswith(synth_job.RESULT_FILE)
    at.button(key=f"jobs.protokoll.{job.id}").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.selectbox(key="synthese.protokoll.quelle").value.label == "Arbeitsbereich"
