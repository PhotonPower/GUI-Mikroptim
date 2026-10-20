"""Darstellung eines geladenen Systems auf der Seite „System“ (G1-T2)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import streamlit as st

from gui_mikroptim.backend import compute, protocols, system_tables
from gui_mikroptim.backend.files import FileEntry
from gui_mikroptim.config import Settings
from gui_mikroptim.views import file_picker, lens_plot

PICKER_KEY = "system"


@st.cache_resource(show_spinner="System wird geladen …", max_entries=32)
def cached_system(path: str, mtime: float, size: int) -> Any:
    """``mikroptim.System`` pro Datei und Stand; ``System`` ist unveränderlich (architektur.md)."""
    del mtime, size  # nur Schlüssel
    return compute.load_system(Path(path))


def file_header(entry: FileEntry) -> dict[str, Any] | None:
    """Kopfdaten aus dem JSON, ohne Mikroptim (G1-T1)."""
    try:
        fmt, doc = protocols.load_document(entry.path)
    except protocols.ProtocolError as exc:
        st.error(str(exc))
        return None
    st.subheader(doc.get("name") or entry.path.stem)
    if doc.get("description"):
        st.write(doc["description"])
    spectrum = doc.get("spectrum") or {}
    source = doc.get("source") or {}
    c1, c2, c3 = st.columns(3)
    c1.metric("Flächen", len(doc.get("surfaces") or []))
    c2.metric("Wellenlängen", len(spectrum.get("wavelengths_nm") or []))
    c3.metric("Felder", len(source.get("field_angles_deg") or []))
    modified = dt.datetime.fromtimestamp(entry.mtime).strftime("%Y-%m-%d %H:%M")
    st.caption(
        f"{entry.path} · {fmt} · {entry.size / 1024:.1f} KiB · geändert {modified} · "
        f"Glaskataloge: {', '.join(doc.get('glass_catalogs') or []) or '–'}"
    )
    return doc


def load(entry: FileEntry) -> tuple[Any | None, compute.LoadError | None]:
    """System aus dem Cache laden; Ausnahmen von Mikroptim werden zu ``LoadError``."""
    try:
        return cached_system(str(entry.path), entry.mtime, entry.size), None
    except Exception as exc:  # FormatError, GlassError, ValueError, FileNotFoundError …
        return None, compute.load_error(exc)


def show_load_error(error: compute.LoadError) -> None:
    where = f" (JSON-Pfad `{error.json_path}`)" if error.json_path else ""
    st.error(f"{error.kind}{where}: {error.message}")


def load_or_report(cfg: Settings, entry: FileEntry) -> Any | None:
    """System laden; Fehler mit JSON-Pfad zeigen und bei Katalogfehlern Reparatur anbieten."""
    system, error = load(entry)
    if error is None:
        return system
    where = f" (JSON-Pfad `{error.json_path}`)" if error.json_path else ""
    st.error(f"{error.kind}{where}: {error.message}")
    if error.is_catalog_error:
        catalog_help(cfg, entry)
    return None


def catalog_help(cfg: Settings, entry: FileEntry) -> None:
    """Glaskataloge nicht gefunden: mit dem Mikroptim-Checkout als Basis neu speichern."""
    st.info(
        "Mikroptim sucht Glaskataloge vom Ordner der Systemdatei aus aufwärts. Dateien im "
        "Arbeitsbereich finden Kataloge wie `data/glass/basis.json` deshalb nicht."
    )
    if cfg.mikroptim_repo is None:
        st.caption("Zum Reparieren MKO_GUI_MIKROPTIM_REPO auf den Mikroptim-Checkout setzen.")
        return
    if st.button(
        "Mit Glaskatalogen aus dem Mikroptim-Checkout neu speichern",
        key="system.kataloge",
        help=(
            f"Mikroptim lädt die Datei mit Katalogsuche ab {cfg.mikroptim_repo} und speichert "
            "sie als neue Datei unter uploads/; die Katalogpfade passt Mikroptim selbst an. "
            "Die Eingabe bleibt unverändert."
        ),
    ):
        try:
            target = compute.repair_catalogs(entry.path, cfg.mikroptim_repo, cfg.workspace)
        except Exception as exc:
            error = compute.load_error(exc)
            st.error(f"Neu speichern fehlgeschlagen: {error.kind}: {error.message}")
            return
        file_picker.select_on_next_run(
            PICKER_KEY, target, remember=True, message=f"Neu gespeichert als {target.name}."
        )
        st.rerun()


def lens_section(data: dict[str, Any], key: str = "system.schnitt") -> None:
    """Linsenschnitt aus einer Systembeschreibung (G1-T3)."""
    try:
        geometry = lens_plot.outline(data)
    except (TypeError, ValueError) as exc:  # unvollständige Datei ohne Mikroptim-Prüfung
        st.warning(f"Linsenschnitt nicht möglich: {exc}")
        return
    if not geometry.surfaces:
        st.caption("Keine Flächen.")
        return
    long_image_space = lens_plot.image_space_is_long(geometry)
    full = st.toggle(
        "Bildraum vollständig zeigen",
        value=not long_image_space,
        key=f"{key}.bildraum",
        help="Aus: z-Achse endet kurz hinter der letzten Fläche, die Lage der Bildebene steht "
        "am rechten Rand.",
    )
    st.plotly_chart(
        lens_plot.lens_figure(geometry, full_image_space=full), width="stretch", key=key
    )
    for note in geometry.notes:
        st.info(note)
    caption = (
        "Schnitt in der y-z-Ebene, Maßstab 1:1. Blau: Glas, schwarz: Blende, violett "
        "gestrichelt: Geisterplatten, rot: Bildebene. Nur Flächen; Strahlen folgen, sobald "
        "Mikroptim Strahlpfade liefert."
    )
    if any(s.transformed for s in geometry.surfaces):
        caption += (
            " Dezentrierte/verkippte Flächen sind transformiert gezeichnet (Δx ist im Schnitt "
            "nicht sichtbar)."
        )
    st.caption(caption)


def _table(rows: list[dict[str, Any]], empty: str) -> None:
    if rows:
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.caption(empty)


def details(system: Any) -> None:
    """Kennzahlen und Reiter mit Tabellen eines geladenen Systems."""
    info = compute.details(system)
    data = info.data
    st.subheader(system.name or "System")
    if getattr(system, "description", ""):
        st.write(system.description)
    for warning in system.warnings:
        st.warning(warning)

    paraxial = info.paraxial or {}
    focal = paraxial.get("focal_length")
    focal_text = "afokal" if paraxial.get("afocal") else system_tables.fmt_number(focal, 7)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Flächen", system.num_surfaces)
    c2.metric("Geisterplatten", system.num_ghost_plates)
    c3.metric("Wellenlängen", len(system.wavelengths_nm))
    c4.metric("Felder", len(system.field_angles_deg))
    c5.metric("Brennweite f [mm]", focal_text)
    st.caption(
        f"{system.file} · λ_ref {system_tables.fmt_number(system.reference_nm)} nm · "
        f"Quelle {system.source_type} · Kataloge: "
        f"{', '.join(Path(p).name for p in system.catalog_files) or '–'}"
    )

    tabs = st.tabs(
        [
            "Linsenschnitt",
            "Flächen",
            "Spektrum und Felder",
            "Paraxialdaten",
            f"Variablen ({len(info.variables)})" if not info.variables_error else "Variablen",
            "Ziele und Nebenbedingungen",
            f"Geisterplatten ({system.num_ghost_plates})",
            "JSON",
        ]
    )
    with tabs[0]:
        lens_section(data)
    with tabs[1]:
        _table(system_tables.surface_rows(system, data), "Keine Flächen.")
        st.caption(
            "Material und Brechzahlen gelten für das Medium nach der Fläche; Radius nur zur "
            "Anzeige (1/Krümmung)."
        )
    with tabs[2]:
        left, right = st.columns(2)
        with left:
            st.markdown("**Spektrum**")
            _table(system_tables.spectrum_rows(system), "Keine Wellenlängen.")
        with right:
            st.markdown("**Felder**")
            _table(system_tables.field_rows(system), "Keine Feldwinkel (Punktquelle).")
    with tabs[3]:
        if info.paraxial is None:
            st.error(f"Paraxialdaten nicht verfügbar: {info.paraxial_error}")
        else:
            st.caption(
                f"Bei λ_ref = {system_tables.fmt_number(system.reference_nm)} nm, berechnet von "
                "mikroptim.paraxial (wie Feld `paraxial` von `mikroptim trace --json`)."
            )
            _table(system_tables.paraxial_rows(info.paraxial), "Keine Paraxialdaten.")
            with st.expander("Paraxialdaten als JSON"):
                st.json(info.paraxial)
    with tabs[4]:
        if info.variables_error:
            st.warning(
                f"Mikroptim kann die Variablen nicht auflösen: {info.variables_error}. "
                "Angezeigt wird der Abschnitt `variables` der Datei."
            )
            st.json(data.get("variables") or {})
        else:
            _table(system_tables.variable_rows(info.variables), "Keine Variablen.")
    with tabs[5]:
        st.markdown("**Ziele** (`target`)")
        st.json(system.target or {}, expanded=True)
        st.markdown("**Nebenbedingungen** (`constraints`)")
        if data.get("constraints"):
            st.json(data["constraints"], expanded=False)
        else:
            st.caption("Keine Nebenbedingungen.")
    with tabs[6]:
        if data.get("ghost_plates"):
            st.json(data["ghost_plates"], expanded=False)
        else:
            st.caption("Keine Geisterplatten.")
    with tabs[7]:
        st.json(data, expanded=False)
