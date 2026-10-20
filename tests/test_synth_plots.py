from pathlib import Path

from gui_mikroptim.backend import protocols
from gui_mikroptim.views.synth_plots import synth_progress_figure


def _steps(test_data: Path):
    return protocols.load_synth(test_data / "synth_beispiel.json").steps


def test_progress_figure_traces(test_data: Path):
    fig = synth_progress_figure(_steps(test_data))
    names = [t.name for t in fig.data]
    assert names == ["NA", "Feldanteil", "RMS angenommen", "RMS abgelehnt", "Elemente"]
    by_name = {t.name: t for t in fig.data}
    assert list(by_name["NA"].x) == [0, 2]  # nur angenommene Schritte
    assert list(by_name["RMS abgelehnt"].x) == [1]
    # nicht endlicher Wert (null) erscheint als Lücke
    assert list(by_name["RMS angenommen"].y) == [0.3, None]
    assert list(by_name["Elemente"].y) == [1, 2, 2]


def test_progress_figure_axes_and_insert_markers(test_data: Path):
    fig = synth_progress_figure(_steps(test_data))
    assert fig.layout.yaxis2.type == "log"
    # eine Einfügung (Schritt 1), markiert in allen drei Zeilen
    vlines = [s for s in fig.layout.shapes if s.type == "line"]
    assert len(vlines) == 3
    assert {s.x0 for s in vlines} == {1}
    assert {s.xref for s in vlines} == {"x", "x2", "x3"}


def test_progress_figure_empty():
    fig = synth_progress_figure([])
    assert len(fig.data) == 5
    assert all(len(t.x) == 0 for t in fig.data)
