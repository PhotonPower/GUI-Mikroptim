"""Hochgeladene Dateien prüfen und im Arbeitsbereich unter ``uploads/`` ablegen (G1-T1).

Gespeichert wird nur, was ein Mikroptim-Dokument eines erlaubten Formats ist; sonst bleibt
der Arbeitsbereich unverändert. Bestehende Dateien werden nie überschrieben.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gui_mikroptim.backend import files, protocols

UPLOAD_SUBDIR = "uploads"

#: Obergrenze für hochgeladene Dateien (wie ``server.maxUploadSize`` in .streamlit/config.toml)
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


class UploadError(ValueError):
    """Upload abgelehnt; die Meldung ist für die Oberfläche gedacht."""


@dataclass(frozen=True)
class UploadResult:
    path: Path
    format: protocols.FormatId
    name: str | None


def check_upload(filename: str, data: bytes, allowed: tuple[str, ...]) -> protocols.FormatId:
    """Prüft Name, Größe, Kodierung und Format; gibt das Format zurück.

    Raises:
        UploadError: mit einer Meldung, die den Grund nennt.
    """
    try:
        safe = files.safe_filename(filename)
    except files.PathError as exc:
        raise UploadError(str(exc)) from exc
    if not safe.lower().endswith(".json"):
        raise UploadError(f"{filename}: nur JSON-Dateien (.json) werden angenommen")
    if len(data) > MAX_UPLOAD_BYTES:
        raise UploadError(
            f"{filename}: zu groß ({len(data) / 1e6:.1f} MB, höchstens "
            f"{MAX_UPLOAD_BYTES / 1e6:.0f} MB)"
        )
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UploadError(f"{filename}: keine UTF-8-Datei") from exc
    try:
        fmt, _ = protocols.parse_document_text(text, filename)
    except protocols.ProtocolError as exc:
        raise UploadError(str(exc)) from exc
    if fmt.name not in allowed:
        wanted = ", ".join(protocols.KNOWN_FORMATS.get(n, n) for n in allowed)
        raise UploadError(f"{filename}: {fmt.label} ({fmt}) passt hier nicht; erwartet: {wanted}")
    return fmt


def save_upload(
    workspace: Path, filename: str, data: bytes, allowed: tuple[str, ...]
) -> UploadResult:
    """Prüft ``data`` und speichert sie als neue Datei unter ``workspace/uploads``."""
    fmt = check_upload(filename, data, allowed)
    # UTF-8-BOM entfernen: Mikroptim und load_document erwarten reines UTF-8
    data = data.removeprefix(b"\xef\xbb\xbf")
    path = files.write_new_file(workspace, UPLOAD_SUBDIR, filename, data)
    name = None
    try:
        _, doc = protocols.load_document(path)
        name = doc.get("name") if isinstance(doc.get("name"), str) else None
    except protocols.ProtocolError:
        pass
    return UploadResult(path=path, format=fmt, name=name)
