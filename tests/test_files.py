import os
from pathlib import Path

import pytest

from gui_mikroptim.backend import files


def test_resolve_inside_accepts_subpaths(tmp_path: Path):
    assert files.resolve_inside(tmp_path, "a/b.json") == (tmp_path / "a" / "b.json").resolve()
    assert files.resolve_inside(tmp_path, ".") == tmp_path.resolve()


@pytest.mark.parametrize("bad", ["../x.json", "a/../../x.json"])
def test_resolve_inside_rejects_traversal(tmp_path: Path, bad: str):
    with pytest.raises(files.PathError):
        files.resolve_inside(tmp_path / "root", bad)


def test_resolve_inside_rejects_absolute(tmp_path: Path):
    with pytest.raises(files.PathError):
        files.resolve_inside(tmp_path, str(tmp_path / "x.json"))


@pytest.mark.skipif(os.name == "nt", reason="Symlinks brauchen unter Windows Rechte")
def test_symlink_out_of_root_is_rejected_and_not_listed(tmp_path: Path):
    root = tmp_path / "root"
    outside = tmp_path / "geheim"
    root.mkdir()
    outside.mkdir()
    (outside / "x.json").write_text("{}")
    (root / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(files.PathError):
        files.resolve_inside(root, "link/x.json")
    assert files.list_files(root) == []


def test_list_files_filters_and_sorts(tmp_path: Path):
    (tmp_path / "b").mkdir()
    (tmp_path / ".versteckt").mkdir()
    (tmp_path / "b" / "z.json").write_text("{}")
    (tmp_path / "a.json").write_text("{}")
    (tmp_path / "notiz.txt").write_text("x")
    (tmp_path / ".versteckt" / "c.json").write_text("{}")
    labels = [e.label for e in files.list_files(tmp_path)]
    assert labels == ["a.json", "b/z.json"]


def test_list_files_missing_root(tmp_path: Path):
    assert files.list_files(tmp_path / "fehlt") == []


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("system.json", "system.json"),
        ("../../etc/passwd", "passwd"),
        ("C:\\temp\\linse 1.json", "linse_1.json"),
        ("Glas (neu).json", "Glas_neu_.json"),
    ],
)
def test_safe_filename(name: str, expected: str):
    assert files.safe_filename(name) == expected


@pytest.mark.parametrize("name", ["", "..", "///"])
def test_safe_filename_rejects_empty(name: str):
    with pytest.raises(files.PathError):
        files.safe_filename(name)


def test_write_new_file_never_overwrites(tmp_path: Path):
    first = files.write_new_file(tmp_path, "uploads", "s.json", b"1")
    second = files.write_new_file(tmp_path, "uploads", "s.json", b"2")
    assert first.name == "s.json"
    assert second.name == "s-2.json"
    assert first.read_bytes() == b"1"
    assert second.read_bytes() == b"2"


def test_write_new_file_rejects_subdir_outside(tmp_path: Path):
    with pytest.raises(files.PathError):
        files.write_new_file(tmp_path / "ws", "../draussen", "s.json", b"")
