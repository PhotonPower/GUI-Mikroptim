"""Gemeinsame Bausteine aller Seiten: Einstellungen, Mikroptim-Status, Seitenleiste."""

from __future__ import annotations

import streamlit as st

from gui_mikroptim.backend import export, mko
from gui_mikroptim.config import ConfigError, Settings, load_settings
from gui_mikroptim.views import current


@st.cache_resource(show_spinner=False)
def settings() -> Settings:
    """Einstellungen einmal pro Serverprozess laden; legt den Arbeitsbereich an."""
    cfg = load_settings()
    cfg.ensure_workspace()
    return cfg


@st.cache_resource(show_spinner=False)
def mikroptim_status() -> mko.MikroptimStatus:
    """Status von Mikroptim; der Knopf „Neu prüfen“ auf der Startseite leert den Cache."""
    return mko.status()


def settings_or_stop() -> Settings:
    """Einstellungen oder eine Fehlermeldung mit ``st.stop()``."""
    try:
        return settings()
    except ConfigError as exc:
        st.error(f"Konfiguration ungültig: {exc}")
        st.caption("Umgebungsvariablen siehe docs/betrieb.md, Abschnitt „Konfiguration“.")
        st.stop()
        raise  # für Typprüfer; st.stop() kehrt nicht zurück


def require_mikroptim() -> mko.MikroptimStatus:
    """Für Seiten, die rechnen: ohne nutzbares Mikroptim Hinweis und ``st.stop()``."""
    status = mikroptim_status()
    if not status.available:
        st.warning(
            "Mikroptim ist nicht nutzbar. Details und Installationshinweise auf der Startseite."
        )
        st.stop()
    return status


def sidebar(version: str):
    """Seitenleiste: Version der GUI und Kurzstatus von Mikroptim.

    Gibt einen Platzhalter für das aktuelle System zurück; :func:`sidebar_current` füllt ihn
    nach dem Lauf der Seite, damit eine Auswahl auf der Seite sofort erscheint.
    """
    with st.sidebar:
        status = mikroptim_status()
        if status.available:
            gpu = f", {status.gpu_count} GPU" if status.has_cuda else ", nur CPU"
            st.caption(f"Mikroptim {status.version}{gpu}")
        else:
            st.caption("Mikroptim: nicht verfügbar")
        placeholder = st.empty()
        st.caption(f"GUI-Mikroptim {version}")
    return placeholder


def sidebar_current(placeholder) -> None:
    """Zeile „Aktuelles System“ in der Seitenleiste."""
    try:
        path = current.get_path(settings())
    except ConfigError:
        path = None
    placeholder.caption(f"Aktuelles System: {path.name if path else '–'}")


def planned(title: str, tasks: list[tuple[str, str]], intro: str) -> None:
    """Platzhalter für eine Seite, deren Aufgaben noch offen sind."""
    st.title(title)
    st.info(intro)
    st.markdown("**Geplante Aufgaben** (docs/plan/meilensteine.md):")
    st.markdown("\n".join(f"- `{task_id}` {text}" for task_id, text in tasks))


def chart(fig, key: str, container=None, filename: str | None = None) -> None:
    """``plotly_chart`` mit voller Breite und Bildexport (SVG, Dateiname aus dem Schlüssel)."""
    target = st if container is None else container
    target.plotly_chart(fig, width="stretch", key=key, config=export.plotly_config(filename or key))


def download_csv(rows: list[dict], filename: str, key: str, label: str = "CSV") -> None:
    """Download-Knopf für Tabellenzeilen als CSV (im Speicher erzeugt)."""
    st.download_button(
        label,
        export.rows_to_csv(rows).encode("utf-8"),
        file_name=f"{export.safe_stem(filename)}.csv",
        mime="text/csv",
        key=key,
    )


# --- Einstellungen über Seitenwechsel behalten (G5-T4) -----------------------------------------
#
# Streamlit verwirft die Zustände von Widgets, deren Seite gerade nicht angezeigt wird. Die
# Hüllen unten merken jeden Wert unter „_behalten.<Schlüssel>“ (wird nie verworfen) und geben ihn
# beim nächsten Anlegen als Standardwert mit. Der Wert wird nicht in den Widget-Schlüssel
# geschrieben; so entsteht keine Warnung „default value … set via the Session State API“.

KEEP_PREFIX = "_behalten."


def kept(key: str, default):
    return st.session_state.get(KEEP_PREFIX + key, default)


def keep(key: str, value):
    st.session_state[KEEP_PREFIX + key] = value
    return value


def number(container, label, min_value, max_value, value, *args, key: str, **kwargs):
    """``number_input`` mit gemerktem Wert (gemerkt nur innerhalb der Grenzen)."""
    start = kept(key, value)
    if not (min_value <= start <= max_value):
        start = value
    return keep(
        key, container.number_input(label, min_value, max_value, start, *args, key=key, **kwargs)
    )


def toggle(container, label, value: bool = False, *, key: str, **kwargs) -> bool:
    return keep(key, container.toggle(label, value=bool(kept(key, value)), key=key, **kwargs))


def _index(key: str, options: list, index: int) -> int:
    remembered = kept(key, None)
    return options.index(remembered) if remembered in options else index


def select(container, label, options, *, key: str, index: int = 0, **kwargs):
    options = list(options)
    return keep(
        key,
        container.selectbox(label, options, index=_index(key, options, index), key=key, **kwargs),
    )


def radio(container, label, options, *, key: str, index: int = 0, **kwargs):
    options = list(options)
    return keep(
        key, container.radio(label, options, index=_index(key, options, index), key=key, **kwargs)
    )
