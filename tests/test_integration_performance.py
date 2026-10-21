"""G5-T2: Seitenwechsel mit gecachten Ergebnissen unter 1 s (Integration, Messwerte im Log)."""

import os
import time
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import needs_uploader

pytestmark = pytest.mark.integration

REPO = os.environ.get("MKO_GUI_MIKROPTIM_REPO")
LIMIT_S = 1.0


@needs_uploader
def test_cached_page_switch_under_one_second(app_file, workspace, monkeypatch):
    if not REPO:
        pytest.skip("MKO_GUI_MIKROPTIM_REPO nicht gesetzt")
    monkeypatch.setenv("MKO_GUI_MIKROPTIM_REPO", REPO)
    at = AppTest.from_file(str(app_file), default_timeout=300).run()
    at.switch_page("pages/auswertung.py").run()
    source = at.selectbox(key="auswertung.quelle")
    source.select_index(source.options.index("Beispielsysteme (Mikroptim)")).run()
    box = at.selectbox(key="auswertung.datei.Beispielsysteme (Mikroptim)")
    box.select_index(box.options.index("testsystem_mehrlinser.json")).run()  # rechnet, füllt Cache
    assert not at.exception

    times = {}
    for page in ("pages/start.py", "pages/system.py", "pages/auswertung.py",
                 "pages/optimierung.py", "pages/synthese.py", "pages/auswertung.py"):  # fmt: skip
        start = time.perf_counter()
        at.switch_page(page).run()
        times[page] = time.perf_counter() - start
        assert not at.exception, (page, [e.value for e in at.exception])
    print("Seitenwechsel [s]:", {Path(k).stem: round(v, 3) for k, v in times.items()})
    assert max(times.values()) < LIMIT_S, times
