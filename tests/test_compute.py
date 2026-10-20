import types

import pytest

from gui_mikroptim.backend import compute, mko


class FormatError(ValueError):
    def __init__(self, json_path, message):
        super().__init__(f"{json_path}: {message}")
        self.json_path = json_path
        self.message = message


def test_load_error_catalog():
    err = compute.load_error(FormatError("glass_catalogs[0]", "nicht gefunden"))
    assert err.kind == "FormatError"
    assert err.json_path == "glass_catalogs[0]"
    assert err.message == "nicht gefunden"
    assert err.is_catalog_error


@pytest.mark.parametrize(
    "exc",
    [FormatError("surfaces[1].curvature", "keine Zahl"), ValueError("anders"), OSError("weg")],
)
def test_load_error_other(exc):
    err = compute.load_error(exc)
    assert not err.is_catalog_error


def test_details_reports_partial_errors(monkeypatch):
    class FakeSystem:
        def variables(self):
            raise ValueError("Glasvariable auf Katalog-Glas")

    fake = types.SimpleNamespace(
        system_to_dict=lambda s: {"format": "mikroptim.system/1"},
        paraxial=lambda s: (_ for _ in ()).throw(RuntimeError("kaputt")),
    )
    monkeypatch.setattr(mko, "require", lambda name="mikroptim": fake)
    info = compute.details(FakeSystem())
    assert info.data == {"format": "mikroptim.system/1"}
    assert info.paraxial is None
    assert "kaputt" in info.paraxial_error
    assert info.variables == []
    assert "Katalog-Glas" in info.variables_error
