"""JSON-Dateien von Mikroptim erkennen und für die Darstellung aufbereiten.

Formate und Felder stehen in Mikroptim, ``docs/cli.md`` und ``docs/dateiformat.md``. Hier wird nur
gelesen und umgeordnet (Tabellenzeilen, Stammbaum als DOT), nichts nachgerechnet (ADR-0002).
Unbekannte Felder werden ignoriert; neuere Nebenversionen eines Formats bleiben lesbar.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gui_mikroptim.backend.files import FileEntry, list_files

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


#: Ergebnisstatus von ``mikroptim synth`` (Mikroptim, docs/cli.md) mit deutscher Bezeichnung
SYNTH_STATUS_LABELS: dict[str, str] = {
    "goal_reached": "Ziel erreicht",
    "goal_not_reached": "Ziel nicht erreicht",
    "step_too_small": "Schrittweite zu klein",
    "max_elements": "Höchstzahl der Elemente erreicht",
    "max_steps": "Höchstzahl der Schritte erreicht",
    "start_rejected": "Startsystem abgelehnt",
}

_FORMAT_PEEK = re.compile(rb'"format"\s*:\s*"([^"]{1,100})"')


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


def peek_format(path: Path, limit: int = 4096) -> FormatId | None:
    """Format aus den ersten ``limit`` Bytes, ohne die ganze Datei zu parsen.

    Mikroptim schreibt ``format`` als erstes Feld; für Auswahllisten reicht das. Verbindlich
    prüft erst :func:`load_document`.
    """
    try:
        with path.open("rb") as handle:
            head = handle.read(limit)
    except OSError:
        return None
    match = _FORMAT_PEEK.search(head)
    return parse_format(match.group(1).decode("utf-8", "replace")) if match else None


def list_documents(root: Path, names: tuple[str, ...]) -> list[FileEntry]:
    """Dateien unter ``root``, deren Format (laut :func:`peek_format`) in ``names`` liegt."""
    result = []
    for entry in list_files(root):
        fmt = peek_format(entry.path)
        if fmt is not None and fmt.name in names:
            result.append(entry)
    return result


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
        point = res.get("point") or {}
        return {
            "status": res.get("status"),
            "status_text": SYNTH_STATUS_LABELS.get(str(res.get("status")), res.get("status")),
            "meldung": res.get("message"),
            "elemente_start": res.get("start_elements"),
            "elemente": res.get("elements"),
            "einfuegungen": res.get("insertions"),
            "optimierungen": res.get("solves"),
            "ziel_erreicht": goal.get("reached"),
            "max_rms_wellen": goal.get("max_rms_waves"),
            "sekunden": res.get("seconds"),
            "na_ende": point.get("aperture"),
            "feld_ende": point.get("field"),
            "spektrum_ende": point.get("spectrum"),
            "na_ziel": (res.get("target") or {}).get("aperture")
            if isinstance(res.get("target"), dict)
            else None,
        }

    @property
    def best_candidate_id(self) -> Any:
        """ID des besten Kandidaten; Mikroptim schreibt eine Zahl oder ein Objekt mit ``id``."""
        best = (self.result.get("beam_search") or {}).get("best")
        return best.get("id") if isinstance(best, dict) else best

    def candidate_rows(self) -> list[dict[str, Any]]:
        """Kandidaten der Strahlsuche als Tabellenzeilen."""
        rows = []
        for cand in self.candidates:
            point = cand.get("point") or {}
            rows.append(
                {
                    "id": cand.get("id"),
                    "eltern": cand.get("parent"),
                    "operation": cand.get("operation"),
                    "zweig": cand.get("branch"),
                    "elemente": cand.get("elements"),
                    "na": point.get("aperture"),
                    "feld": point.get("field"),
                    "merit": cand.get("merit"),
                    "bewertung": cand.get("evaluation"),
                    "rms_wellen": cand.get("rms_waves"),
                    "versagte_strahlen": cand.get("failed_rays"),
                    "annehmbar": cand.get("acceptable"),
                    "status": cand.get("status"),
                    "grund": cand.get("reason"),
                    "bester": cand.get("id") == self.best_candidate_id,
                }
            )
        return rows

    def goal_rows(self) -> list[dict[str, Any]]:
        """Ziel-Tupel (Feld × Wellenlänge) aus ``result.goal.tuples``."""
        tuples = (self.result.get("goal") or {}).get("tuples") or []
        return [dict(t) for t in tuples if isinstance(t, dict)]


def _step_row(step: dict[str, Any]) -> dict[str, Any]:
    point = step.get("point") or {}
    lm = step.get("lm") or {}
    return {
        "schritt": step.get("index"),
        "art": step.get("kind"),
        "kandidat": step.get("candidate"),
        "gruppe": step.get("group"),
        "na": point.get("aperture"),
        "feld": point.get("field"),
        "spektrum": point.get("spectrum"),
        "strafe_faktor": point.get("penalty_scale"),
        "delta": step.get("delta"),
        "naechstes_delta": step.get("next_delta"),
        "angenommen": step.get("accepted"),
        "aktion": step.get("action"),
        "empfehlung": step.get("recommendation"),
        "elemente": step.get("elements"),
        "merit_start": lm.get("start_merit"),
        "merit": lm.get("merit"),
        "wellenfront": lm.get("wavefront"),
        "geister_strafe": lm.get("ghost_penalty"),
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
    best_id = protocol.best_candidate_id
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


def filter_steps(
    steps: list[dict[str, Any]],
    kinds: list[str] | None = None,
    actions: list[str] | None = None,
    accepted: bool | None = None,
    candidate: Any = None,
) -> list[dict[str, Any]]:
    """Schrittzeilen filtern; ``None`` bzw. leere Liste heißt „alle“."""
    result = []
    for row in steps:
        if kinds and row.get("art") not in kinds:
            continue
        if actions and row.get("aktion") not in actions:
            continue
        if accepted is not None and row.get("angenommen") is not accepted:
            continue
        if candidate is not None and row.get("kandidat") != candidate:
            continue
        result.append(row)
    return result


def distinct(steps: list[dict[str, Any]], key: str) -> list[Any]:
    """Verschiedene Werte einer Spalte in Reihenfolge des ersten Auftretens (ohne ``None``)."""
    seen: list[Any] = []
    for row in steps:
        value = row.get(key)
        if value is not None and value not in seen:
            seen.append(value)
    return seen
