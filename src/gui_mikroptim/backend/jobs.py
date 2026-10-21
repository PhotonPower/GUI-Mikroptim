"""Jobs: lange Läufe als eigene Prozesse (ADR-0003, docs/architektur.md, „Jobs“).

Ablage pro Job unter ``<Arbeitsbereich>/jobs/<JJJJMMTT-hhmmss>-<kurz>/``:

- ``job.json`` – Beschreibung im Format ``gui-mikroptim.job/1``; nach dem Start schreibt nur
  noch der Wrapper (:mod:`gui_mikroptim.backend.job_runner`) hinein.
- ``eingabe/`` – Kopien der Eingabedateien; ``argv`` verweist relativ darauf.
- ``ausgabe.txt``, ``fehler.txt`` – stdout und stderr des Befehls.
- ``.gestartet`` – vom Starter angelegt (verhindert doppelten Start), ``.abbrechen`` – von der
  Oberfläche angelegt; der Wrapper beendet den Befehl dann samt Kindprozessen.

Höchstens ``max_jobs`` Jobs laufen gleichzeitig; weitere warten und werden gestartet, sobald ein
Platz frei ist – vom Wrapper eines endenden Jobs oder von der Oberfläche.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gui_mikroptim.backend import files

FORMAT = "gui-mikroptim.job/1"
JOBS_SUBDIR = "jobs"
JOB_FILE = "job.json"
INPUT_DIR = "eingabe"
STDOUT_FILE = "ausgabe.txt"
STDERR_FILE = "fehler.txt"
STARTED_MARKER = ".gestartet"
CANCEL_MARKER = ".abbrechen"
LOCK_FILE = ".sperre"

WAITING, RUNNING, DONE, FAILED, CANCELLED = "wartend", "läuft", "fertig", "fehler", "abgebrochen"
FINAL_STATES = (DONE, FAILED, CANCELLED)

#: Sperre gilt nach so vielen Sekunden als verwaist (abgestürzter Starter)
LOCK_STALE_SECONDS = 30.0

_KIND = re.compile(r"^[a-z][a-z0-9-]{0,30}$")


class JobError(RuntimeError):
    """Ungültiger Job oder Job nicht gefunden."""


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def jobs_root(workspace: Path) -> Path:
    root = files.resolve_inside(workspace, JOBS_SUBDIR)
    root.mkdir(parents=True, exist_ok=True)
    return root


# --- Dateien ------------------------------------------------------------------------------------


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    """Schreibt JSON über eine temporäre Datei und ``os.replace`` (nie halb geschrieben)."""
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for attempt in range(20):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:  # Windows: Ziel kurz von einem Leser geöffnet
            time.sleep(0.05 * (attempt + 1))
    os.replace(tmp, path)


def read_job(job_dir: Path) -> dict[str, Any]:
    for attempt in range(10):
        try:
            data = json.loads((job_dir / JOB_FILE).read_text(encoding="utf-8"))
            break
        except (json.JSONDecodeError, PermissionError):  # gerade ersetzt
            time.sleep(0.05 * (attempt + 1))
    else:
        raise JobError(f"{job_dir.name}: job.json nicht lesbar")
    if data.get("format") != FORMAT:
        raise JobError(f"{job_dir.name}: kein {FORMAT}")
    return data


@contextlib.contextmanager
def _lock(root: Path, timeout: float = 10.0) -> Iterator[None]:
    """Exklusive Sperre über eine Datei, die mit O_EXCL angelegt wird (Linux und Windows)."""
    path = root / LOCK_FILE
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > LOCK_STALE_SECONDS:
                    path.unlink(missing_ok=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() > deadline:
                raise JobError(
                    f"Jobverwaltung gesperrt ({path}); später erneut versuchen"
                ) from None
            time.sleep(0.05)
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


# --- Prozesse -----------------------------------------------------------------------------------


def pid_alive(pid: int | None) -> bool:
    """Läuft ein Prozess mit dieser ID? (POSIX: Signal 0; Windows: OpenProcess.)"""
    if not pid:
        return False
    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.OpenProcess(0x1000, False, int(pid))  # QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # Zombie (beendet, noch nicht abgeholt) zählt nicht als laufend
    try:
        stat = Path(f"/proc/{int(pid)}/stat").read_text()
        return stat.rsplit(")", 1)[1].split()[0] != "Z"
    except (OSError, IndexError):
        return True


def detached_popen_kwargs() -> dict[str, Any]:
    """Prozess unabhängig vom Streamlit-Server starten (überlebt dessen Neustart)."""
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008  # DETACHED_PROCESS
        return {"creationflags": flags}
    return {"start_new_session": True}


def _launch(job_dir: Path, max_jobs: int, queue_root: Path | None = None) -> None:
    env = dict(os.environ)
    if queue_root is not None:
        env["MKO_GUI_SESSIONS"] = str(queue_root)  # Wrapper startet danach Jobs aller Sitzungen
    env["PYTHONUNBUFFERED"] = "1"
    # Python-Befehle (z. B. python -m mikroptim) schreiben auch unter Windows UTF-8 in die
    # umgeleiteten Ausgaben; sonst würden Umlaute in ausgabe.txt in cp1252 landen
    env["PYTHONUTF8"] = "1"
    env["MKO_GUI_MAX_JOBS"] = str(max_jobs)
    log = (job_dir / ".wrapper.txt").open("ab")
    try:
        subprocess.Popen(
            [sys.executable, "-m", "gui_mikroptim.backend.job_runner", str(job_dir)],
            cwd=job_dir,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            env=env,
            close_fds=True,
            **detached_popen_kwargs(),
        )
    finally:
        log.close()


# --- Jobs ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Job:
    """Ein Job mit dem Status, wie ihn die Oberfläche zeigt."""

    path: Path
    data: dict[str, Any]
    status: str
    note: str | None = None

    @property
    def id(self) -> str:
        return str(self.data.get("id", self.path.name))

    @property
    def final(self) -> bool:
        return self.status in FINAL_STATES

    def duration_seconds(self) -> float | None:
        start = self.data.get("started")
        if not start:
            return None
        end = self.data.get("finished")
        t0 = dt.datetime.fromisoformat(start)
        t1 = dt.datetime.fromisoformat(end) if end else dt.datetime.now(dt.timezone.utc)
        return max(0.0, (t1 - t0).total_seconds())

    def tail(self, name: str = STDOUT_FILE, lines: int = 200) -> str:
        """Ende von ``ausgabe.txt`` bzw. ``fehler.txt`` (höchstens ``lines`` Zeilen, 256 kB)."""
        path = self.path / name
        if not path.is_file():
            return ""
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - 262144))
            text = handle.read().decode("utf-8", "replace")
        return "\n".join(text.splitlines()[-lines:])

    def command_line(self) -> str:
        """Befehl zum Wiederholen von Hand (im Jobordner auszuführen)."""
        return (
            subprocess.list2cmdline(self.data["argv"])
            if os.name == "nt"
            else " ".join(_shell_quote(a) for a in self.data["argv"])
        )


def _shell_quote(arg: str) -> str:
    import shlex

    return shlex.quote(arg)


def effective_status(job_dir: Path, data: dict[str, Any]) -> tuple[str, str | None]:
    """Status aus ``job.json``, Markierungen und Prozess; verwaiste Läufe werden zu „fehler“."""
    status = str(data.get("status", WAITING))
    if status == RUNNING and not pid_alive(data.get("pid")):
        return FAILED, "Wrapper-Prozess nicht mehr vorhanden (Rechner neu gestartet?)"
    if status == WAITING and (job_dir / STARTED_MARKER).exists():
        if time.time() - (job_dir / STARTED_MARKER).stat().st_mtime > 60:
            return FAILED, "gestartet, aber der Wrapper hat sich nicht gemeldet (.wrapper.txt)"
        return RUNNING, "startet"
    return status, None


def load(job_dir: Path) -> Job:
    data = read_job(job_dir)
    status, note = effective_status(job_dir, data)
    return Job(job_dir, data, status, note)


def list_jobs(workspace: Path) -> list[Job]:
    """Alle Jobs, neueste zuerst; unlesbare Ordner werden übersprungen."""
    root = jobs_root(workspace)
    result = []
    for job_dir in root.iterdir():
        if job_dir.is_dir() and (job_dir / JOB_FILE).is_file():
            with contextlib.suppress(JobError):
                result.append(load(job_dir))
    result.sort(key=_queue_key, reverse=True)
    return result


def _queue_key(job: Job) -> tuple[int, str, str]:
    return (int(job.data.get("created_ns") or 0), str(job.data.get("created", "")), job.id)


def queue_jobs(workspace: Path, queue_root: Path | None = None) -> list[Job]:
    """Alle Jobs der Warteschlange: mit Sitzungen (``queue_root``) die aller Sitzungsordner,
    sonst die des Arbeitsbereichs (G6-T1)."""
    if queue_root is None:
        return list_jobs(workspace)
    from gui_mikroptim.backend import sessions

    result: list[Job] = []
    for folder in sessions.all_sessions(queue_root):
        if (folder / JOBS_SUBDIR).is_dir():
            result.extend(list_jobs(folder))
    return result


def running_count(workspace: Path, queue_root: Path | None = None) -> int:
    return sum(1 for j in queue_jobs(workspace, queue_root) if j.status == RUNNING)


def start_pending(workspace: Path, max_jobs: int, queue_root: Path | None = None) -> list[str]:
    """Startet wartende Jobs (älteste zuerst), solange weniger als ``max_jobs`` laufen.

    Mit ``queue_root`` (Wurzel der Sitzungsordner) gilt die Grenze für alle Sitzungen zusammen,
    und es startet der älteste wartende Job aller Sitzungen.
    """
    root = jobs_root(workspace) if queue_root is None else queue_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    started = []
    with _lock(root):
        jobs = queue_jobs(workspace, queue_root)
        free = max_jobs - sum(1 for j in jobs if j.status == RUNNING)
        waiting = sorted((j for j in jobs if j.status == WAITING), key=_queue_key)
        for job in waiting:
            if free <= 0:
                break
            try:
                fd = os.open(job.path / STARTED_MARKER, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
            except FileExistsError:
                continue
            _launch(job.path, max_jobs, queue_root)
            started.append(job.id)
            free -= 1
    return started


def _new_job_dir(root: Path, kind: str) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    for n in range(1, 1000):
        name = f"{stamp}-{kind}" if n == 1 else f"{stamp}-{kind}-{n}"
        path = root / name
        try:
            path.mkdir()
            return path
        except FileExistsError:
            continue
    raise JobError("kein freier Jobname")


def _check_input(source: Path, allowed_roots: list[Path]) -> Path:
    resolved = source.resolve()
    for root in allowed_roots:
        try:
            files.resolve_inside(root, resolved.relative_to(root.resolve()))
            return resolved
        except (ValueError, files.PathError):
            continue
    raise JobError(f"Eingabe liegt außerhalb der erlaubten Verzeichnisse: {source}")


def submit(
    workspace: Path,
    kind: str,
    argv: list[str],
    max_jobs: int,
    inputs: list[Path] | None = None,
    allowed_roots: list[Path] | None = None,
    options: dict[str, Any] | None = None,
    mikroptim_version: str | None = None,
    copy_system: Any = None,
    start: bool = True,
    queue_root: Path | None = None,
) -> Job:
    """Legt einen Job an und startet ihn, wenn ein Platz frei ist.

    Args:
        kind: Art (``synth``, ``eval``, …), kleingeschrieben, wird Teil des Ordnernamens.
        argv: vollständiger Befehl; ``{eingabe:i}`` wird durch den relativen Pfad der i-ten
            kopierten Eingabe ersetzt (z. B. ``eingabe/system.json``).
        inputs: Dateien, die nach ``eingabe/`` kopiert werden (nur aus ``allowed_roots``).
        copy_system: ``Callable(source, target)`` für Systemdateien (z. B. über Mikroptim
            ``System.save``, damit Glaskataloge vom Jobordner aus gefunden werden); sonst Kopie.
        options, mikroptim_version: werden zur Nachvollziehbarkeit in ``job.json`` abgelegt.
    """
    if not _KIND.match(kind):
        raise JobError(f"ungültige Job-Art {kind!r}")
    if not argv:
        raise JobError("leerer Befehl")
    if max_jobs < 1:
        raise JobError("max_jobs muss mindestens 1 sein")
    inputs = list(inputs or [])
    allowed = list(allowed_roots or [workspace])
    checked = [_check_input(p, allowed) for p in inputs]

    root = jobs_root(workspace)
    job_dir = _new_job_dir(root, kind)
    (job_dir / INPUT_DIR).mkdir()
    copied = []
    for source in checked:
        target = files.unique_path(job_dir / INPUT_DIR, source.name)
        if copy_system is not None and source.suffix.lower() == ".json":
            copy_system(source, target)
        else:
            shutil.copy2(source, target)
        copied.append(f"{INPUT_DIR}/{target.name}")

    final_argv = []
    for arg in argv:
        for i, rel in enumerate(copied):
            arg = arg.replace(f"{{eingabe:{i}}}", rel)
        final_argv.append(arg)

    data = {
        "format": FORMAT,
        "id": job_dir.name,
        "kind": kind,
        "argv": final_argv,
        "inputs": copied,
        "sources": [str(p) for p in checked],
        "options": options or {},
        "mikroptim_version": mikroptim_version,
        "created": now_iso(),
        "created_ns": time.time_ns(),  # Reihenfolge der Warteschlange
        "started": None,
        "finished": None,
        "pid": None,
        "exit_code": None,
        "status": WAITING,
    }
    write_json_atomic(job_dir / JOB_FILE, data)
    if start:
        start_pending(workspace, max_jobs, queue_root)
    return load(job_dir)


def cancel(workspace: Path, job_id: str) -> Job:
    """Bricht einen Job ab: wartend sofort, laufend über ``.abbrechen`` (der Wrapper beendet
    den Befehl samt Kindprozessen und schreibt „abgebrochen“)."""
    job_dir = files.resolve_inside(jobs_root(workspace), job_id)
    if not (job_dir / JOB_FILE).is_file():
        raise JobError(f"Job {job_id} nicht gefunden")
    root = jobs_root(workspace)
    with _lock(root):
        job = load(job_dir)
        if job.final:
            return job
        (job_dir / CANCEL_MARKER).touch()
        if job.status == WAITING and not (job_dir / STARTED_MARKER).exists():
            data = dict(job.data)
            data.update(status=CANCELLED, finished=now_iso())
            write_json_atomic(job_dir / JOB_FILE, data)
            # Starter blockieren, falls er gleich nach der Sperre noch einmal schaut
            (job_dir / STARTED_MARKER).touch()
    return load(job_dir)


def mikroptim_argv(cli: Path | None, args: list[str]) -> list[str]:
    """Befehl für Mikroptim: das Programm ``mikroptim`` (``MKO_GUI_CLI``) oder
    ``python -m mikroptim`` (Ausgabe erst am Ende, docs/schnittstelle-mikroptim.md)."""
    if cli is not None:
        return [str(cli), *args]
    return [sys.executable, "-m", "mikroptim", *args]
