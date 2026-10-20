"""Darstellung eines Protokolls ``mikroptim.synth/1`` (G4-T2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from gui_mikroptim.backend import protocols
from gui_mikroptim.views.synth_plots import synth_progress_figure

STEP_COLUMNS = [
    "schritt",
    "art",
    "kandidat",
    "na",
    "feld",
    "spektrum",
    "delta",
    "angenommen",
    "aktion",
    "empfehlung",
    "elemente",
    "rms_wellen",
    "merit",
    "geister_summe_mm",
    "versagte_strahlen",
    "lm_status",
    "lm_iterationen",
    "sekunden",
    "operation",
]


@st.cache_data(show_spinner="Protokoll wird gelesen …")
def load_cached(path: str, mtime: float, size: int) -> protocols.SynthProtocol:
    """Protokoll laden; Änderungszeit und Größe sind Teil des Cache-Schlüssels."""
    del mtime, size  # nur Schlüssel
    return protocols.load_synth(Path(path))


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "–"
    if isinstance(value, bool):
        return "ja" if value else "nein"
    if isinstance(value, float):
        return f"{value:.{digits}g}"
    return str(value)


def header(proto: protocols.SynthProtocol, path: Path) -> None:
    """Kopfzeile: Ergebnis, Endpunkt, Elemente, Laufzeit."""
    data = proto.data
    summary = proto.summary()
    backend = data.get("backend") or {}
    gpu = backend.get("device_name") or ("GPU" if backend.get("gpu") else "CPU")
    version = data.get("version", "–")
    st.caption(f"{path.name} · Eingabe {data.get('input', '–')} · {gpu} · Mikroptim {version}")

    status = summary["status"]
    text = f"**{summary['status_text'] or '–'}**"
    if summary.get("meldung"):
        text += f": {summary['meldung']}"
    if status == "goal_reached":
        st.success(text)
    elif status in ("start_rejected",):
        st.error(text)
    else:
        st.warning(text)

    cols = st.columns(5)
    na_text = _fmt(summary["na_ende"])
    if summary.get("na_ziel") is not None:
        na_text += f" / {_fmt(summary['na_ziel'])}"
    cols[0].metric("NA (Ende / Ziel)", na_text)
    cols[1].metric("Feldanteil", _fmt(summary["feld_ende"]))
    cols[2].metric("Elemente", f"{_fmt(summary['elemente_start'])} → {_fmt(summary['elemente'])}")
    cols[3].metric(
        "Einfügungen / Optimierungen",
        f"{_fmt(summary['einfuegungen'])} / {_fmt(summary['optimierungen'])}",
    )
    seconds = summary.get("sekunden")
    cols[4].metric(
        "Laufzeit", f"{seconds / 60:.1f} min" if isinstance(seconds, (int, float)) else "–"
    )


def steps_section(proto: protocols.SynthProtocol, key: str) -> None:
    """Verlauf und filterbare Schritttabelle."""
    steps = proto.steps
    if not steps:
        st.info("Das Protokoll enthält keine Schritte.")
        return
    st.plotly_chart(synth_progress_figure(steps), width="stretch", key=f"{key}.verlauf")

    st.markdown("**Schritte**")
    c1, c2, c3, c4 = st.columns(4)
    kinds = c1.multiselect("Art", protocols.distinct(steps, "art"), key=f"{key}.art")
    actions = c2.multiselect("Aktion", protocols.distinct(steps, "aktion"), key=f"{key}.aktion")
    accepted_choice = c3.selectbox("Angenommen", ["alle", "ja", "nein"], key=f"{key}.angenommen")
    candidate = None
    candidates = protocols.distinct(steps, "kandidat")
    if candidates:
        picked = c4.selectbox("Kandidat", ["alle", *candidates], key=f"{key}.kandidat")
        candidate = None if picked == "alle" else picked
    accepted = {"alle": None, "ja": True, "nein": False}[accepted_choice]
    rows = protocols.filter_steps(steps, kinds, actions, accepted, candidate)
    st.caption(f"{len(rows)} von {len(steps)} Schritten")
    st.dataframe(
        [{k: r.get(k) for k in STEP_COLUMNS if k != "kandidat" or candidates} for r in rows],
        hide_index=True,
        width="stretch",
    )

    inserts = [r for r in steps if r.get("aktion") == "insert"]
    if inserts:
        with st.expander(f"Einfügungen ({len(inserts)})", expanded=False):
            for r in inserts:
                st.markdown(
                    f"- Schritt {r['schritt']} bei NA {_fmt(r.get('na'))}, "
                    f"Empfehlung {_fmt(r.get('empfehlung'))}: {r.get('operation') or '–'}"
                )


def beam_section(proto: protocols.SynthProtocol, path: Path) -> None:
    """Stammbaum und Kandidatentabelle der Strahlsuche."""
    if not proto.has_beam_search:
        return
    st.markdown(f"**Strahlsuche** (bester Kandidat: #{proto.best_candidate_id})")
    dot_file = path.with_suffix(".dot")
    dot = dot_file.read_text(encoding="utf-8") if dot_file.is_file() else None
    if dot is None:
        dot = protocols.candidate_tree_dot(proto)
    else:
        st.caption(f"Stammbaum aus {dot_file.name}")
    st.graphviz_chart(dot, width="stretch")
    st.dataframe(proto.candidate_rows(), hide_index=True, width="stretch")


def goal_section(proto: protocols.SynthProtocol) -> None:
    rows = proto.goal_rows()
    if rows:
        st.markdown("**Ziel-Tupel** (Feld × Wellenlänge)")
        st.dataframe(rows, hide_index=True, width="stretch")


def raw_section(proto: protocols.SynthProtocol) -> None:
    with st.expander("Optionen und Rohdaten", expanded=False):
        st.markdown("**Optionen**")
        st.json(proto.data.get("options") or {}, expanded=False)
        st.markdown("**Ergebnis** (ohne Schritte und Kandidaten)")
        result = {k: v for k, v in proto.result.items() if k not in ("steps", "beam_search")}
        st.json(result, expanded=False)


def render(path: Path, key: str = "synth") -> None:
    """Ganzes Protokoll darstellen; Lesefehler erscheinen als Meldung."""
    stat = path.stat()
    try:
        proto = load_cached(str(path), stat.st_mtime, stat.st_size)
    except protocols.ProtocolError as exc:
        st.error(str(exc))
        return
    header(proto, path)
    steps_section(proto, key)
    beam_section(proto, path)
    goal_section(proto)
    raw_section(proto)
