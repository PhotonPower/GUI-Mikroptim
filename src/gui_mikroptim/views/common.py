"""Gemeinsame Bausteine aller Seiten: Einstellungen, Mikroptim-Status, Seitenleiste."""

from __future__ import annotations

import streamlit as st

from gui_mikroptim.backend import mko
from gui_mikroptim.config import ConfigError, Settings, load_settings


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


def sidebar(version: str) -> None:
    """Seitenleiste: Version der GUI und Kurzstatus von Mikroptim."""
    with st.sidebar:
        status = mikroptim_status()
        if status.available:
            gpu = f", {status.gpu_count} GPU" if status.has_cuda else ", nur CPU"
            st.caption(f"Mikroptim {status.version}{gpu}")
        else:
            st.caption("Mikroptim: nicht verfügbar")
        st.caption(f"GUI-Mikroptim {version}")


def planned(title: str, tasks: list[tuple[str, str]], intro: str) -> None:
    """Platzhalter für eine Seite, deren Aufgaben noch offen sind."""
    st.title(title)
    st.info(intro)
    st.markdown("**Geplante Aufgaben** (docs/plan/meilensteine.md):")
    st.markdown("\n".join(f"- `{task_id}` {text}" for task_id, text in tasks))
