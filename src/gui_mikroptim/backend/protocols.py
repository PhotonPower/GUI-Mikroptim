"""JSON-Dateien von Mikroptim erkennen und für die Darstellung aufbereiten.

Formate und Felder stehen in Mikroptim, ``docs/cli.md`` und ``docs/dateiformat.md``. Hier wird nur
gelesen und umgeordnet (Tabellenzeilen, Stammbaum als DOT), nichts nachgerechnet (ADR-0002).
Unbekannte Felder werden ignoriert; neuere Nebenversionen eines Formats bleiben lesbar.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: Bekannte Formate (Hauptname ohne Version) mit deutscher Bezeichnung
KNOWN_FORMATS: dict[str, str] = {
    "mikroptim.system": "Systembeschreibung",
    "mikroptim.glass": "Glaskatalog",
    "mikroptim.trace": "Ergebnis von trace",
    "mikroptim.optimize": "Ergebnis von optimize",
    "mikroptim.eval": "Ergebnis von eval",
    "mikroptim.snap": "Ergebnis von snap",
    "mikroptim.synth": "Protokoll von synth",
}

#: Hauptversionen, die diese GUI versteht
SUPPORTED_MAJOR: dict[str, int] = {name: 1 for name in KNOWN_FORMATS}


class ProtocolError(ValueError):
    """Datei ist kein lesbares Mikroptim-JSON oder hat eine unbekannte Hauptversion."""


@dataclass(frozen=True)
class FormatId:
    """``"mikroptim.synth/1"`` → name ``"mikroptim.synth"``, major ``1``."""

    name: str
    major: int

    @property
    def label(self) -> str:
        return KNOWN_FORMATS.get(self.name, self.name)

    def __str__(self) -> str:
        return f"{self.name}/{self.major}"


def parse_format(value: Any) -> FormatId | None:
    """Liest das Feld ``format``; ``None``, wenn es fehlt oder nicht passt."""
    if not isinstance(value, str) or "/" not in value:
        return None
    name, _, major = value.partition("/")
    major_digits = major.split(".", 1)[0]
    if not name or not major_digits.isdigit():
        return None
    return FormatId(name, int(major_digits))


def load_document(path: Path) -> tuple[FormatId, dict[str, Any]]:
    """Lädt eine JSON-Datei von Mikroptim und prüft das Format.

    Raises:
        ProtocolError: kein JSON-Objekt, kein ``format``-Feld, unbekanntes Format oder
            nicht unterstützte Hauptversion.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"{path.name}: nicht lesbar: {exc}") from exc
    if not isinstance(data, dict):
        raise ProtocolError(f"{path.name}: kein JSON-Objekt")
    fmt = parse_format(data.get("format"))
    if fmt is None:
        raise ProtocolError(f"{path.name}: Feld 'format' fehlt oder ist ungültig")
    if fmt.name not in KNOWN_FORMATS:
        raise ProtocolError(f"{path.name}: unbekanntes Format {fmt}")
    if fmt.major != SUPPORTED_MAJOR[fmt.name]:
        raise ProtocolError(
            f"{path.name}: Hauptversion {fmt.major} von {fmt.name} wird nicht unterstützt "
            f"(erwartet {SUPPORTED_MAJOR[fmt.name]})"
        )
    return fmt, data


# --- mikroptim.synth/1 -------------------------------------------------------------------------


@dataclass(frozen=True)
class SynthProtocol:
    """Aufbereitetes Protokoll ``mikroptim.synth/1`` (Mikroptim, docs/cli.md, „synth“)."""

    data: dict[str, Any]
    steps: list[dict[str, Any]] = field(default_factory=list)
    candidates: list[dict[str, Any]] = field(default_factory=list)

    @property
    def result(self) -> dict[str, Any]:
        return self.data.get("result") or {}

    @property
    def status(self) -> str | None:
        return self.result.get("status")

    @property
    def has_beam_search(self) -> bool:
        return bool(self.candidates)

    def summary(self) -> dict[str, Any]:
        """Kennzahlen für die Kopfzeile (Werte unverändert aus ``result``)."""
        res = self.result
        goal = res.get("goal") or {}
        return {
            "status": res.get("status"),
            "meldung": res.get("message"),
            "elemente_start": res.get("start_elements"),
            "elemente": res.get("elements"),
            "einfuegungen": res.get("insertions"),
            "optimierungen": res.get("solves"),
            "ziel_erreicht": goal.get("reached"),
            "max_rms_wellen": goal.get("max_rms_waves"),
            "sekunden": res.get("seconds"),
        }


def _step_row(step: dict[str, Any]) -> dict[str, Any]:
    point = step.get("point") or {}
    lm = step.get("lm") or {}
    return {
        "schritt": step.get("index"),
        "art": step.get("kind"),
        "kandidat": step.get("candidate"),
        "na": point.get("aperture"),
        "feld": point.get("field"),
        "spektrum": point.get("spectrum"),
        "delta": step.get("delta"),
        "angenommen": step.get("accepted"),
        "aktion": step.get("action"),
        "empfehlung": step.get("recommendation"),
        "elemente": step.get("elements"),
        "merit": lm.get("merit"),
        "rms_wellen": lm.get("rms_waves"),
        "geister_summe_mm": lm.get("ghost_sum_mm"),
        "versagte_strahlen": lm.get("failed_rays"),
        "lm_status": lm.get("status"),
        "lm_iterationen": lm.get("iterations"),
        "operation": step.get("operation"),
        "sekunden": step.get("seconds"),
    }


def read_synth(data: dict[str, Any]) -> SynthProtocol:
    """Bereitet ein bereits geladenes ``mikroptim.synth/1`` auf.

    Schritte stehen unter ``result.steps``; der Kandidaten-Stammbaum der Strahlsuche
    (ab Mikroptim M6-T4) unter ``result.beam_search.candidates``.
    """
    result = data.get("result") or {}
    steps = [_step_row(s) for s in result.get("steps") or [] if isinstance(s, dict)]
    beam = result.get("beam_search") or {}
    candidates = [c for c in beam.get("candidates") or [] if isinstance(c, dict)]
    return SynthProtocol(data=data, steps=steps, candidates=candidates)


def load_synth(path: Path) -> SynthProtocol:
    """Lädt und prüft ein Protokoll ``mikroptim.synth/1``."""
    fmt, data = load_document(path)
    if fmt.name != "mikroptim.synth":
        raise ProtocolError(f"{path.name}: erwartet mikroptim.synth, gefunden {fmt}")
    return read_synth(data)


def _dot_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


_STATUS_COLORS = {
    "finished": "palegreen",
    "kept": "lightblue",
    "expanded": "lightgrey",
    "discarded": "mistyrose",
}


def candidate_tree_dot(protocol: SynthProtocol) -> str:
    """Stammbaum der Kandidaten als Graphviz-DOT (für ``st.graphviz_chart``).

    Mikroptim schreibt mit ``--dot`` selbst eine DOT-Datei; diese Funktion erlaubt die
    Darstellung, wenn nur das JSON-Protokoll vorliegt.
    """
    best = (protocol.result.get("beam_search") or {}).get("best")
    best_id = best.get("id") if isinstance(best, dict) else best
    lines = [
        "digraph kandidaten {",
        "  rankdir=TB;",
        "  node [shape=box, style=filled, fontsize=10];",
    ]
    for cand in protocol.candidates:
        cid = cand.get("id")
        rms = cand.get("rms_waves")
        rms_text = f"{rms:.4g} W" if isinstance(rms, (int, float)) else "–"
        label = (
            f"#{cid} {cand.get('operation') or 'start'}\n"
            f"El {cand.get('elements', '–')}, RMS {rms_text}\n{cand.get('status', '')}"
        )
        color = _STATUS_COLORS.get(str(cand.get("status")), "white")
        extra = ", penwidth=3" if cid == best_id else ""
        lines.append(f'  k{cid} [label="{_dot_escape(label)}", fillcolor="{color}"{extra}];')
    for cand in protocol.candidates:
        parent = cand.get("parent")
        if parent is not None:
            lines.append(f"  k{parent} -> k{cand.get('id')};")
    lines.append("}")
    return "\n".join(lines)
