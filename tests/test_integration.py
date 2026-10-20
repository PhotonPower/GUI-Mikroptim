"""Integrationstests gegen ein installiertes Mikroptim (``python -m pytest -m integration``).

``MKO_GUI_MIKROPTIM_REPO`` muss auf einen Mikroptim-Checkout zeigen (Beispielsysteme).
"""

import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from gui_mikroptim.backend import mko

pytestmark = pytest.mark.integration


@pytest.fixture
def repo() -> Path:
    value = os.environ.get("MKO_GUI_MIKROPTIM_REPO")
    if not value:
        pytest.skip("MKO_GUI_MIKROPTIM_REPO nicht gesetzt")
    return Path(value)


def test_mikroptim_is_usable():
    st = mko.status()
    assert st.available, st.error


def test_public_api_on_example_system(repo: Path):
    m = mko.require()
    system = m.load_system(str(repo / "data" / "systems" / "einzellinse_bk7.json"))
    assert system.num_surfaces > 0
    assert m.paraxial(system).focal_length == pytest.approx(101.05, abs=0.01)
    wf = m.trace(system, rings=4, spokes=4)
    assert wf.rms_waves.ndim == 2


def test_start_page_with_mikroptim(app_file: Path, workspace: Path, repo: Path, monkeypatch):
    monkeypatch.setenv("MKO_GUI_MIKROPTIM_REPO", str(repo))
    at = AppTest.from_file(str(app_file), default_timeout=60).run()
    assert not at.exception
    assert any("geladen" in s.value for s in at.success)
    labels = [m.label for m in at.metric]
    values = dict(zip(labels, [m.value for m in at.metric], strict=True))
    assert int(values["Beispielsysteme"]) > 0
