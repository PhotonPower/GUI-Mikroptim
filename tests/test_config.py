from pathlib import Path

import pytest

from gui_mikroptim.config import ConfigError, load_settings


def test_defaults_without_env():
    cfg = load_settings({})
    assert cfg.workspace.name == "arbeitsbereich"
    assert cfg.mikroptim_repo is None
    assert cfg.cli is None
    assert cfg.max_jobs == 1
    assert cfg.example_systems_dir is None


def test_paths_are_absolute(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "repo" / "data" / "systems").mkdir(parents=True)
    cfg = load_settings({"MKO_GUI_WORKSPACE": "ws", "MKO_GUI_MIKROPTIM_REPO": "repo"})
    assert cfg.workspace == (tmp_path / "ws").resolve()
    assert cfg.example_systems_dir == (tmp_path / "repo" / "data" / "systems").resolve()


def test_ensure_workspace_creates_subdirs(tmp_path: Path):
    cfg = load_settings({"MKO_GUI_WORKSPACE": str(tmp_path / "ws")})
    cfg.ensure_workspace()
    for name in ("uploads", "ergebnisse", "jobs"):
        assert (tmp_path / "ws" / name).is_dir()


def test_workspace_must_be_directory(tmp_path: Path):
    file = tmp_path / "datei"
    file.write_text("x")
    with pytest.raises(ConfigError, match="MKO_GUI_WORKSPACE"):
        load_settings({"MKO_GUI_WORKSPACE": str(file)})


@pytest.mark.parametrize("value", ["0", "-1", "zwei"])
def test_invalid_max_jobs(value: str):
    with pytest.raises(ConfigError, match="MKO_GUI_MAX_JOBS"):
        load_settings({"MKO_GUI_MAX_JOBS": value})


def test_cli_path_and_missing_program(tmp_path: Path):
    exe = tmp_path / "mikroptim"
    exe.write_text("")
    assert load_settings({"MKO_GUI_CLI": str(exe)}).cli == exe.resolve()
    with pytest.raises(ConfigError, match="MKO_GUI_CLI"):
        load_settings({"MKO_GUI_CLI": "gibt-es-sicher-nicht-12345"})


def test_read_roots(tmp_path: Path):
    cfg = load_settings({"MKO_GUI_WORKSPACE": str(tmp_path / "ws")})
    assert cfg.read_roots == [(tmp_path / "ws").resolve()]
    cfg = load_settings(
        {"MKO_GUI_WORKSPACE": str(tmp_path / "ws"), "MKO_GUI_MIKROPTIM_REPO": str(tmp_path / "r")}
    )
    assert cfg.read_roots == [(tmp_path / "ws").resolve(), (tmp_path / "r").resolve()]
