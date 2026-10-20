"""G4-T1: Jobverwaltung mit harmlosen Python-Befehlen (Linux und Windows, ohne Mikroptim)."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from gui_mikroptim.backend import jobs

PY = sys.executable


def py(code: str) -> list[str]:
    return [PY, "-c", code]


def wait_for(predicate, timeout: float = 30.0, step: float = 0.1):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(step)
    raise AssertionError("Zeitüberschreitung")


def wait_final(job: jobs.Job, timeout: float = 30.0) -> jobs.Job:
    return wait_for(lambda: (j := jobs.load(job.path)).final and j, timeout)


@pytest.fixture
def ws(tmp_path: Path) -> Path:
    return tmp_path / "arbeitsbereich"


@pytest.fixture(autouse=True)
def _cleanup(ws):
    yield
    # laufende Testjobs nie stehen lassen
    if (ws / "jobs").is_dir():
        for job in jobs.list_jobs(ws):
            if not job.final:
                jobs.cancel(ws, job.id)
        for job in jobs.list_jobs(ws):
            if job.status == jobs.RUNNING:
                wait_final(job, 15)


def test_job_done(ws):
    job = jobs.submit(ws, "test", py("print('hallo')"), max_jobs=1, options={"seed": 7})
    assert job.path.parent == (ws / "jobs").resolve()
    done = wait_final(job)
    assert done.status == jobs.DONE and done.data["exit_code"] == 0
    assert done.tail() == "hallo"
    data = json.loads((job.path / "job.json").read_text(encoding="utf-8"))
    assert data["format"] == "gui-mikroptim.job/1"
    assert data["kind"] == "test" and data["options"] == {"seed": 7}
    assert data["created"] <= data["started"] <= data["finished"]
    assert isinstance(data["pid"], int)


def test_job_failed_exit_code(ws):
    job = jobs.submit(
        ws, "test", py("import sys; print('kaputt', file=sys.stderr); sys.exit(3)"), 1
    )
    done = wait_final(job)
    assert done.status == jobs.FAILED and done.data["exit_code"] == 3
    assert done.tail(jobs.STDERR_FILE) == "kaputt"


def test_start_failure(ws):
    done = wait_final(jobs.submit(ws, "test", ["gibt-es-sicher-nicht-12345"], 1))
    assert done.status == jobs.FAILED
    assert "Start fehlgeschlagen" in done.data["error"]


def test_cancel_running_kills_process_tree(ws):
    code = (
        "import subprocess, sys, time\n"
        "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        "open('kind.pid', 'w').write(str(p.pid))\n"
        "time.sleep(60)\n"
    )
    job = jobs.submit(ws, "test", py(code), 1)
    child = int(wait_for(lambda: ((job.path / "kind.pid").is_file() and (
        job.path / "kind.pid").read_text()) or None))  # fmt: skip
    assert jobs.pid_alive(child)
    jobs.cancel(ws, job.id)
    done = wait_final(job, 20)
    assert done.status == jobs.CANCELLED
    wait_for(lambda: not jobs.pid_alive(child), 10)
    wait_for(lambda: not jobs.pid_alive(done.data["pid"]), 10)  # Wrapper beendet sich danach


def test_cancel_waiting_job_never_starts(ws):
    long = jobs.submit(ws, "test", py("import time; time.sleep(60)"), 1)
    waiting = jobs.submit(ws, "test", py("print('nie')"), 1)
    assert jobs.load(waiting.path).status == jobs.WAITING
    cancelled = jobs.cancel(ws, waiting.id)
    assert cancelled.status == jobs.CANCELLED and cancelled.data["started"] is None
    jobs.cancel(ws, long.id)
    wait_final(long, 20)
    time.sleep(0.5)
    assert jobs.load(waiting.path).data["started"] is None
    assert not (waiting.path / jobs.STDOUT_FILE).exists()


@pytest.mark.parametrize("max_jobs", [1, 2])
def test_limit_and_queue_order(ws, max_jobs):
    created = [
        jobs.submit(ws, "test", py("import time; time.sleep(0.8)"), max_jobs) for _ in range(4)
    ]
    peak = 0
    while not all(jobs.load(j.path).final for j in created):
        peak = max(peak, jobs.running_count(ws))
        assert peak <= max_jobs
        time.sleep(0.05)
    finished = [jobs.load(j.path) for j in created]
    assert all(j.status == jobs.DONE for j in finished)
    assert peak == max_jobs  # die Grenze wird auch genutzt
    starts = [j.data["started"] for j in finished]
    assert starts == sorted(starts)  # Reihenfolge der Anlage


def test_job_survives_gui_restart(ws):
    """Der anlegende Prozess (die GUI) endet; der Job läuft weiter und wird danach korrekt
    angezeigt."""
    script = (
        "import sys\n"
        "from pathlib import Path\n"
        "from gui_mikroptim.backend import jobs\n"
        f"job = jobs.submit(Path({str(ws)!r}), 'test', "
        f"[sys.executable, '-c', 'import time; time.sleep(2); print(\"überlebt\")'], 1)\n"
        "print(job.id)\n"
    )
    out = subprocess.run([PY, "-c", script], capture_output=True, text=True, check=True, timeout=60)
    job_id = out.stdout.strip().splitlines()[-1]
    job = jobs.load(ws / "jobs" / job_id)
    assert job.status == jobs.RUNNING
    done = wait_final(job)
    assert done.status == jobs.DONE and done.tail() == "überlebt"


def test_orphaned_running_job_is_failed(ws):
    job = jobs.submit(ws, "test", py("print(1)"), 1, start=False)
    dead = subprocess.Popen([PY, "-c", "pass"])
    dead.wait()
    data = jobs.read_job(job.path)
    data.update(status=jobs.RUNNING, pid=dead.pid, started=jobs.now_iso())
    jobs.write_json_atomic(job.path / jobs.JOB_FILE, data)
    loaded = jobs.load(job.path)
    assert loaded.status == jobs.FAILED and "nicht mehr vorhanden" in loaded.note


def test_inputs_are_copied(ws, tmp_path):
    source = ws / "uploads" / "lauf.json"
    source.parent.mkdir(parents=True)
    source.write_text('{"x": 1}', encoding="utf-8")
    other = ws / "uploads" / "daten.txt"
    other.write_text("abc", encoding="utf-8")
    calls = []

    def copy_system(src, dst):
        calls.append((src, dst))
        dst.write_text('{"x": 2}', encoding="utf-8")

    job = jobs.submit(
        ws,
        "test",
        [
            *py("import sys; print(open(sys.argv[1]).read(), open(sys.argv[2]).read())"),
            "{eingabe:0}",
            "{eingabe:1}",
        ],
        1,
        inputs=[source, other],
        copy_system=copy_system,
    )
    assert job.data["inputs"] == ["eingabe/lauf.json", "eingabe/daten.txt"]
    assert job.data["argv"][-2:] == ["eingabe/lauf.json", "eingabe/daten.txt"]
    assert len(calls) == 1  # nur die JSON-Datei über copy_system
    assert wait_final(job).tail() == '{"x": 2} abc'
    assert source.read_text(encoding="utf-8") == '{"x": 1}'  # Eingabe unverändert


def test_inputs_outside_allowed_roots_rejected(ws, tmp_path):
    outside = tmp_path / "draussen.json"
    outside.write_text("{}", encoding="utf-8")
    with pytest.raises(jobs.JobError, match="außerhalb"):
        jobs.submit(ws, "test", py("pass"), 1, inputs=[outside])
    assert not (ws / "jobs").exists() or not list((ws / "jobs").iterdir())


@pytest.mark.parametrize(
    ("kind", "argv", "max_jobs", "message"),
    [("Synth!", ["x"], 1, "Job-Art"), ("test", [], 1, "leer"), ("test", ["x"], 0, "max_jobs")],
)
def test_invalid_submit(ws, kind, argv, max_jobs, message):
    with pytest.raises(jobs.JobError, match=message):
        jobs.submit(ws, kind, argv, max_jobs)


def test_lock_stale_and_busy(ws):
    root = jobs.jobs_root(ws)
    lock = root / jobs.LOCK_FILE
    lock.write_text("123")
    old = time.time() - jobs.LOCK_STALE_SECONDS - 5
    os.utime(lock, (old, old))
    assert jobs.start_pending(ws, 1) == []  # verwaiste Sperre wird übernommen
    assert not lock.exists()
    lock.write_text("123")
    with pytest.raises(jobs.JobError, match="gesperrt"), jobs._lock(root, timeout=0.3):
        pass
    lock.unlink()


def test_command_line_and_mikroptim_argv(ws):
    assert jobs.mikroptim_argv(None, ["trace", "a.json"])[1:] == [
        "-m",
        "mikroptim",
        "trace",
        "a.json",
    ]
    assert jobs.mikroptim_argv(Path("/opt/mikroptim"), ["eval"]) == [
        str(Path("/opt/mikroptim")),
        "eval",
    ]
    job = jobs.submit(ws, "test", py("print('a b')"), 1, start=False)
    assert "print" in job.command_line()
