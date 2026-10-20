"""Gemeinsame Fixtures der Tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_DATA = Path(__file__).resolve().parent / "daten"
APP_FILE = REPO_ROOT / "src" / "gui_mikroptim" / "app.py"


@pytest.fixture
def test_data() -> Path:
    return TEST_DATA


@pytest.fixture
def app_file() -> Path:
    return APP_FILE


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Leerer Arbeitsbereich, über MKO_GUI_WORKSPACE eingestellt."""
    ws = tmp_path / "arbeitsbereich"
    monkeypatch.setenv("MKO_GUI_WORKSPACE", str(ws))
    monkeypatch.delenv("MKO_GUI_CLI", raising=False)
    monkeypatch.delenv("MKO_GUI_MAX_JOBS", raising=False)
    return ws


@pytest.fixture
def without_mikroptim(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simuliert eine Umgebung ohne Mikroptim: ``import mikroptim`` wirft ImportError."""
    monkeypatch.setitem(sys.modules, "mikroptim", None)


@pytest.fixture(autouse=True)
def _clear_streamlit_caches():
    """Streamlit-Caches leben im Prozess; jeder Test beginnt ohne Cache."""
    import streamlit as st

    st.cache_resource.clear()
    st.cache_data.clear()
    yield
    st.cache_resource.clear()
    st.cache_data.clear()


def _apptest_supports_uploader() -> bool:
    from streamlit.testing.v1 import element_tree

    return hasattr(element_tree, "FileUploader")


#: Ältere Streamlit-Versionen (z. B. 1.51) kennen ``st.file_uploader`` in AppTest nicht und
#: scheitern bei jeder Interaktion auf Seiten mit Upload. Die App selbst ist nicht betroffen.
needs_uploader = pytest.mark.skipif(
    not _apptest_supports_uploader(),
    reason="AppTest dieser Streamlit-Version unterstützt st.file_uploader nicht",
)


def pytest_runtest_logreport(report):
    """In GitHub Actions jeden Fehlschlag zusätzlich als Annotation ausgeben (über die API
    lesbar, ohne Log-Download)."""
    import os

    if not os.environ.get("GITHUB_ACTIONS") or not report.failed:
        return
    text = str(report.longrepr)[-3000:]
    text = text.replace("%", "%25").replace("\r", "").replace("\n", "%0A")
    title = report.nodeid.replace(":", "_").replace(",", "_")[:200]
    print(f"\n::error title={title}::{text}", flush=True)
