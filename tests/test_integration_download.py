"""G6-T2: Heruntergeladene Ergebnisse lassen sich in einer anderen Sitzung wieder verwenden."""

import json
import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import needs_uploader
from gui_mikroptim.backend import catalogs, compute, export, optimize_run
from gui_mikroptim.backend.optimize_options import OptimizeOptions

pytestmark = pytest.mark.integration

REPO = os.environ.get("MKO_GUI_MIKROPTIM_REPO")


@pytest.fixture
def repo(monkeypatch) -> Path:
    if not REPO:
        pytest.skip("MKO_GUI_MIKROPTIM_REPO nicht gesetzt")
    monkeypatch.setenv("MKO_GUI_MIKROPTIM_REPO", REPO)
    return Path(REPO)


def test_downloaded_result_is_portable(repo, tmp_path):
    source = repo / "data" / "systems" / "einzellinse_bk7_biegung.json"
    out = optimize_run.run_optimize(compute.load_system(source), OptimizeOptions())
    data = json.loads(export.system_download(out.result.system, repo, tmp_path / "ws_a"))
    assert data["glass_catalogs"] == ["data/glass/basis.json"]
    # in einer anderen Sitzung hochgeladen: Zuordnung über den Mikroptim-Checkout, Merit gleich
    other = tmp_path / "ws_b" / "uploads"
    other.mkdir(parents=True)
    (other / "ergebnis.json").write_text(json.dumps(data), encoding="utf-8")
    res = catalogs.resolve_entries(data["glass_catalogs"], other, repo, tmp_path / "ws_b")
    assert [r.origin for r in res] == ["Mikroptim"]
    repaired = compute.repair_catalogs(other / "ergebnis.json", tmp_path / "ws_b", repo)
    again = optimize_run.run_optimize(
        compute.load_system(repaired), OptimizeOptions(max_iterations=0)
    )
    assert again.result.start_merit == out.result.merit


@needs_uploader
def test_optimization_page_offers_download(app_file, workspace, repo):
    at = AppTest.from_file(str(app_file), default_timeout=120).run()
    at.switch_page("pages/optimierung.py").run()
    source = at.selectbox(key="optimierung.quelle")
    source.select_index(source.options.index("Beispielsysteme (Mikroptim)")).run()
    box = at.selectbox(key="optimierung.datei.Beispielsysteme (Mikroptim)")
    box.select_index(box.options.index("einzellinse_bk7_biegung.json")).run()
    at.number_input(key="optimierung.laeufe").set_value(6).run()
    at.button(key="optimierung.start").click().run()
    assert not at.exception, [e.value for e in at.exception]
    labels = [d.proto.label for d in at.get("download_button")]
    assert "Herunterladen" in labels
    keys = [c.key for c in at.get("plotly_chart")]
    assert "optimierung.verlauf" in keys and "optimierung.endmerit" in keys  # Multistart: 2 Diagramme
