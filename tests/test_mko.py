import sys
import types

import pytest

from gui_mikroptim.backend import mko


def _fake_module(**overrides) -> types.ModuleType:
    module = types.ModuleType("mikroptim_fake")
    for name in mko.REQUIRED_NAMES:
        setattr(module, name, lambda *a, **k: None)
    module.__version__ = "0.1.0"
    module.has_cuda = False
    module.devices = lambda: []
    for key, value in overrides.items():
        setattr(module, key, value)
    return module


@pytest.fixture
def install(monkeypatch: pytest.MonkeyPatch):
    def _install(module: types.ModuleType | None) -> str:
        monkeypatch.setitem(sys.modules, "mikroptim_fake", module)
        return "mikroptim_fake"

    return _install


@pytest.mark.parametrize(
    ("text", "expected"),
    [("0.1.0", (0, 1, 0)), ("1.2", (1, 2)), ("0.2.0.dev1", (0, 2, 0)), ("1.0rc1", (1, 0))],
)
def test_parse_version(text: str, expected: tuple[int, ...]):
    assert mko.parse_version(text) == expected


def test_status_missing_module(install):
    st = mko.status(install(None))
    assert not st.available
    assert "ModuleNotFoundError" in (st.error or "")
    with pytest.raises(mko.MikroptimUnavailable):
        mko.require("mikroptim_fake")


def test_status_cpu_build(install):
    st = mko.status(install(_fake_module()))
    assert st.available
    assert st.version == "0.1.0"
    assert not st.has_cuda
    assert st.gpu_count == 0
    assert mko.require("mikroptim_fake") is sys.modules["mikroptim_fake"]


def test_status_with_devices(install):
    devs = [{"index": 0, "name": "RTX 3090", "total_bytes": 24e9, "free_bytes": 20e9}]
    st = mko.status(install(_fake_module(has_cuda=True, devices=lambda: devs)))
    assert st.available
    assert st.gpu_count == 1
    assert st.devices[0]["name"] == "RTX 3090"


def test_status_missing_names(install):
    module = _fake_module()
    del module.evaluate
    st = mko.status(install(module))
    assert not st.available
    assert "evaluate" in (st.error or "")


def test_status_too_old(install):
    st = mko.status(install(_fake_module(__version__="0.0.9")))
    assert not st.available
    assert "älter" in (st.error or "")


def test_device_query_failure_keeps_available(install):
    def broken():
        raise RuntimeError("Treiber weg")

    st = mko.status(install(_fake_module(has_cuda=True, devices=broken)))
    assert st.available
    assert "Treiber weg" in (st.error or "")
