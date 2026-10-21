"""G6-T1: Sitzungsordner, Aufräumen und gemeinsame Warteschlange (ohne Mikroptim)."""

import os
import sys
import time
from pathlib import Path

import pytest

from gui_mikroptim.backend import jobs, sessions
from gui_mikroptim.config import ConfigError, load_settings

PY = sys.executable


def test_ids():
    a, b = sessions.new_id(), sessions.new_id()
    assert a != b and sessions.valid_id(a) and len(a) >= 16
    for bad in ("", None, "kurz", "../../etc", "a" * 65, "mit leerzeichen 1234567"):
        assert not sessions.valid_id(bad)


def test_session_dir(tmp_path: Path):
    sid = sessions.new_id()
    folder = sessions.session_dir(tmp_path, sid)
    assert folder == (tmp_path / sid).resolve()
    for name in ("uploads", "ergebnisse", "jobs", "kataloge"):
        assert (folder / name).is_dir()
    assert (folder / sessions.SEEN_MARKER).is_file()
    with pytest.raises(sessions.SessionError):
        sessions.session_dir(tmp_path, "../draussen-1234567890")


def _age(folder: Path, days: float) -> None:
    old = time.time() - days * 86400
    os.utime(folder / sessions.SEEN_MARKER, (old, old))


def test_cleanup(tmp_path: Path):
    old, fresh, keep = (sessions.session_dir(tmp_path, sessions.new_id()) for _ in range(3))
    busy = sessions.session_dir(tmp_path, sessions.new_id())
    jobs.submit(busy, "test", [PY, "-c", "print(1)"], 1, start=False)  # wartender Job
    for f in (old, keep, busy):
        _age(f, 30)
    (tmp_path / "fremder-ordner").mkdir()
    removed = sessions.cleanup(tmp_path, 14, keep=keep.name)
    assert removed == [old.name]
    assert (
        fresh.exists()
        and keep.exists()
        and busy.exists()
        and (tmp_path / "fremder-ordner").exists()
    )
    _age(fresh, 30)
    assert sessions.cleanup(tmp_path, 14) == []  # höchstens stündlich
    assert fresh.name in sessions.cleanup(tmp_path, 14, force=True)


def test_settings_sessions(tmp_path: Path):
    cfg = load_settings({"MKO_GUI_SESSIONS": str(tmp_path / "s"), "MKO_GUI_SESSION_DAYS": "3"})
    assert cfg.sessions_root == (tmp_path / "s").resolve() and cfg.session_days == 3.0
    assert cfg.for_session(tmp_path / "x").workspace == tmp_path / "x"
    assert load_settings({}).sessions_root is None
    with pytest.raises(ConfigError, match="MKO_GUI_SESSION_DAYS"):
        load_settings({"MKO_GUI_SESSION_DAYS": "0"})


def _wait(job, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current = jobs.load(job.path)
        if current.final:
            return current
        time.sleep(0.1)
    raise AssertionError("Zeitüberschreitung")


def test_queue_across_sessions(tmp_path: Path, monkeypatch):
    """Die Höchstzahl gilt für alle Sitzungen zusammen; endet A, startet der Job von B."""
    root = tmp_path / "sitzungen"
    monkeypatch.setenv("MKO_GUI_SESSIONS", str(root))
    a = sessions.session_dir(root, sessions.new_id())
    b = sessions.session_dir(root, sessions.new_id())
    long = jobs.submit(a, "test", [PY, "-c", "import time; time.sleep(60)"], 1, queue_root=root)
    other = jobs.submit(b, "test", [PY, "-c", "print('B')"], 1, queue_root=root)
    try:
        assert jobs.load(other.path).status == jobs.WAITING  # A belegt den einzigen Platz
        assert jobs.running_count(b, root) == 1 and jobs.running_count(b) == 0
        assert [j.id for j in jobs.list_jobs(b)] == [other.id]  # B sieht nur eigene Jobs
        jobs.cancel(a, long.id)
        done = _wait(other)  # vom Wrapper des abgebrochenen Jobs aus A gestartet
        assert done.status == jobs.DONE and done.tail() == "B"
    finally:
        jobs.cancel(a, long.id)
        _wait(long)
