"""Wrapper eines Jobs: ``python -m gui_mikroptim.backend.job_runner <jobordner>``.

Startet den Befehl aus ``job.json`` im Jobordner, leitet stdout/stderr nach ``ausgabe.txt`` und
``fehler.txt``, überwacht ``.abbrechen`` und beendet den Befehl dann samt Kindprozessen, schreibt
Status, Exit-Code und Zeiten zurück und startet danach wartende Jobs. Ohne Streamlit.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from gui_mikroptim.backend import jobs

POLL_SECONDS = 0.2
GRACE_SECONDS = 5.0


def _kill_tree(proc: subprocess.Popen) -> None:
    """Befehl samt Kindprozessen beenden (POSIX: Prozessgruppe, Windows: taskkill /T)."""
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        deadline = time.monotonic() + GRACE_SECONDS
        while proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        if proc.poll() is None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
    proc.wait()


def run(job_dir: Path) -> int:
    data = jobs.read_job(job_dir)
    if data.get("status") != jobs.WAITING:
        return 0  # schon gelaufen oder abgebrochen
    data.update(status=jobs.RUNNING, started=jobs.now_iso(), pid=os.getpid())
    jobs.write_json_atomic(job_dir / jobs.JOB_FILE, data)

    cancelled = False
    exit_code: int | None = None
    error: str | None = None
    with (
        (job_dir / jobs.STDOUT_FILE).open("wb") as out,
        (job_dir / jobs.STDERR_FILE).open("wb") as err,
    ):
        try:
            kwargs = (
                {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
                if os.name == "nt"
                else {"start_new_session": True}
            )
            proc = subprocess.Popen(
                data["argv"], cwd=job_dir, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                **kwargs,
            )  # fmt: skip
        except OSError as exc:
            error = f"Start fehlgeschlagen: {exc}"
            err.write((error + "\n").encode())
        else:
            while proc.poll() is None:
                if (job_dir / jobs.CANCEL_MARKER).exists():
                    cancelled = True
                    _kill_tree(proc)
                    break
                time.sleep(POLL_SECONDS)
            exit_code = proc.returncode

    data = jobs.read_job(job_dir)
    if cancelled:
        status = jobs.CANCELLED
    elif error is not None or exit_code != 0:
        status = jobs.FAILED
    else:
        status = jobs.DONE
    data.update(status=status, exit_code=exit_code, finished=jobs.now_iso())
    if error:
        data["error"] = error
    jobs.write_json_atomic(job_dir / jobs.JOB_FILE, data)

    # Platz frei: wartende Jobs starten (Warteschlange läuft ohne Oberfläche weiter)
    workspace = job_dir.parent.parent
    max_jobs = int(os.environ.get("MKO_GUI_MAX_JOBS", "1") or "1")
    try:
        jobs.start_pending(workspace, max_jobs)
    except jobs.JobError as exc:
        print(f"wartende Jobs nicht gestartet: {exc}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("Aufruf: python -m gui_mikroptim.backend.job_runner <jobordner>", file=sys.stderr)
        return 2
    return run(Path(args[0]).resolve())


if __name__ == "__main__":
    sys.exit(main())
