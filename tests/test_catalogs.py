"""ADR-0006: Glaskataloge im Arbeitsbereich (ohne Mikroptim, frei erfundene Gläser)."""

import json
from pathlib import Path

import pytest

from gui_mikroptim.backend import catalogs


def _glass(name="ERF-1"):
    return {
        "name": name,
        "model": "sellmeier",
        "B": [1.1, 0.2, 1.0],
        "C": [0.006, 0.02, 100.0],
        "range_nm": [365, 2325],
        "reference": {"n_d": 1.53},
        "source": "frei erfunden",
    }


def _catalog(*names):
    return {"format": "mikroptim.glass/1", "glasses": [_glass(n) for n in names or ("ERF-1",)]}


def _bytes(data):
    return json.dumps(data).encode("utf-8")


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"format": "mikroptim.system/1"}, "kein Glaskatalog"),
        ({"format": "mikroptim.glass/1", "glasses": []}, "leer"),
        ({"format": "mikroptim.glass/1", "glasses": [_glass(), _glass()]}, "doppelt"),
        (
            {"format": "mikroptim.glass/1", "glasses": [{**_glass(), "model": "schott"}]},
            "sellmeier",
        ),
        (
            {"format": "mikroptim.glass/1", "glasses": [{**_glass(), "B": [1.0, 2.0]}]},
            "drei Zahlen",
        ),
        (
            {"format": "mikroptim.glass/1", "glasses": [{**_glass(), "range_nm": [700, 400]}]},
            "range_nm",
        ),
        ({"format": "mikroptim.glass/1", "glasses": [{**_glass(), "name": ""}]}, "name fehlt"),
    ],
)
def test_check_catalog_rejects(data, message):
    with pytest.raises(catalogs.CatalogError, match=message):
        catalogs.check_catalog(data, "k.json")


def test_save_list_and_delete(tmp_path: Path):
    info = catalogs.save_catalog(
        tmp_path, "meine_glaeser.json", b"\xef\xbb\xbf" + _bytes(_catalog("A-1", "A-2"))
    )
    assert info.path == (tmp_path / "kataloge" / "meine_glaeser.json").resolve()
    assert info.names == ["A-1", "A-2"]
    assert not info.path.read_bytes().startswith(b"\xef\xbb\xbf")
    listed = catalogs.list_catalogs(tmp_path)
    assert [c.path.name for c in listed] == ["meine_glaeser.json"]
    with pytest.raises(catalogs.CatalogError, match="schon vorhanden"):
        catalogs.save_catalog(tmp_path, "meine_glaeser.json", _bytes(_catalog("B-1")))
    assert catalogs.list_catalogs(tmp_path)[0].names == ["A-1", "A-2"]  # nicht überschrieben
    catalogs.delete_catalog(tmp_path, "meine_glaeser.json")
    assert catalogs.list_catalogs(tmp_path) == []


@pytest.mark.parametrize(
    ("name", "data", "message"),
    [
        ("k.txt", _bytes(_catalog()), "nur JSON"),
        ("k.json", b"{kein json", "nicht lesbar"),
        ("k.json", b"[1]", "kein JSON-Objekt"),
        ("k.json", _bytes({"format": "mikroptim.system/1"}), "kein Glaskatalog"),
    ],
)
def test_save_rejects_and_writes_nothing(tmp_path: Path, name, data, message):
    with pytest.raises(catalogs.CatalogError, match=message):
        catalogs.save_catalog(tmp_path, name, data)
    folder = tmp_path / "kataloge"
    assert not folder.exists() or not any(folder.iterdir())


def test_delete_outside_rejected(tmp_path: Path):
    (tmp_path / "geheim.json").write_text("{}")
    with pytest.raises(Exception):  # noqa: B017 - PathError oder CatalogError
        catalogs.delete_catalog(tmp_path / "ws", "../../geheim.json")
    assert (tmp_path / "geheim.json").exists()


def test_resolve_entries_order(tmp_path: Path):
    ws, repo = tmp_path / "ws", tmp_path / "Mikroptim"
    system_dir = ws / "uploads"
    system_dir.mkdir(parents=True)
    (repo / "data" / "glass").mkdir(parents=True)
    (repo / "data" / "glass" / "basis.json").write_text("{}")
    catalogs.save_catalog(ws, "schott.json", _bytes(_catalog()))
    (ws / "lokal.json").write_text("{}")  # vom Ordner der Datei aufwärts erreichbar
    entries = [
        "lokal.json",
        "data/glass/basis.json",
        "data/glass/private/schott.json",
        "fehlt.json",
    ]
    res = catalogs.resolve_entries(entries, system_dir, repo, ws)
    assert [r.origin for r in res] == ["Datei", "Mikroptim", "Arbeitsbereich", "fehlt"]
    assert res[2].path == (ws / "kataloge" / "schott.json").resolve()
    assert res[3].path is None
    no_repo = catalogs.resolve_entries(["data/glass/basis.json"], system_dir, None, ws)
    assert no_repo[0].origin == "fehlt"
    text = catalogs.with_absolute_catalogs('{"glass_catalogs": ["a"], "name": "x"}', res[1:2])
    assert json.loads(text) == {"glass_catalogs": [str(res[1].path)], "name": "x"}


def test_glass_names_in(tmp_path: Path):
    a = tmp_path / "a.json"
    a.write_text(json.dumps(_catalog("X-1", "N-BK7")))
    assert set(catalogs.glass_names_in([a, tmp_path / "fehlt.json"])) == {"X-1", "N-BK7"}
