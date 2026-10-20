import json
from pathlib import Path

import pytest

from gui_mikroptim.backend import uploads

SYSTEM = ("mikroptim.system",)


def _doc(fmt: str = "mikroptim.system/1", **extra) -> bytes:
    return json.dumps({"format": fmt, "name": "frei erfunden", **extra}).encode("utf-8")


def test_save_upload_writes_into_uploads(tmp_path: Path):
    result = uploads.save_upload(tmp_path, "linse.json", _doc(), SYSTEM)
    assert result.path == (tmp_path / "uploads" / "linse.json").resolve()
    assert str(result.format) == "mikroptim.system/1"
    assert result.name == "frei erfunden"


def test_same_name_twice_never_overwrites(tmp_path: Path):
    first = uploads.save_upload(tmp_path, "linse.json", _doc(name="eins"), SYSTEM)
    second = uploads.save_upload(tmp_path, "linse.json", _doc(name="zwei"), SYSTEM)
    assert (first.path.name, second.path.name) == ("linse.json", "linse-2.json")
    assert json.loads(first.path.read_text(encoding="utf-8"))["name"] == "eins"


def test_unsafe_filename_is_cleaned(tmp_path: Path):
    result = uploads.save_upload(tmp_path, "../../böse name.json", _doc(), SYSTEM)
    assert result.path.parent == (tmp_path / "uploads").resolve()
    assert result.path.name == "b_se_name.json"


def test_bom_is_removed(tmp_path: Path):
    result = uploads.save_upload(tmp_path, "bom.json", b"\xef\xbb\xbf" + _doc(), SYSTEM)
    assert not result.path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert result.name == "frei erfunden"


@pytest.mark.parametrize(
    ("name", "data", "message"),
    [
        ("system.txt", _doc(), "nur JSON"),
        ("glas.json", _doc("mikroptim.glass/1"), "Glaskatalog"),
        ("fremd.json", _doc("anderes.format/1"), "unbekanntes Format"),
        ("neu.json", _doc("mikroptim.system/2"), "Hauptversion 2"),
        ("kaputt.json", b"{nicht json", "nicht lesbar"),
        ("liste.json", b"[1, 2]", "kein JSON-Objekt"),
        ("ohne.json", b'{"name": "x"}', "format"),
        ("latin.json", '{"format": "mikroptim.system/1", "name": "ä"}'.encode("latin-1"), "UTF-8"),
    ],
)
def test_rejected_uploads_are_not_saved(tmp_path: Path, name: str, data: bytes, message: str):
    with pytest.raises(uploads.UploadError, match=message):
        uploads.save_upload(tmp_path, name, data, SYSTEM)
    assert not (tmp_path / "uploads").exists() or not any((tmp_path / "uploads").iterdir())


def test_too_large(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(uploads, "MAX_UPLOAD_BYTES", 10)
    with pytest.raises(uploads.UploadError, match="zu groß"):
        uploads.check_upload("a.json", _doc(), SYSTEM)


def test_several_allowed_formats():
    fmt = uploads.check_upload("p.json", _doc("mikroptim.synth/1"), ("mikroptim.synth",))
    assert fmt.name == "mikroptim.synth"
