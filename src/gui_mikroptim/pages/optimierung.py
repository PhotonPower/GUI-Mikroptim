"""Seite „Optimierung“: Levenberg-Marquardt mit Live-Verlauf (G3)."""

from gui_mikroptim.views import common

common.settings_or_stop()
common.planned(
    "Optimierung",
    [
        ("G3-T1", "Variablen, Schranken und Optionen anzeigen und einstellen"),
        ("G3-T2", "Optimierung mit Live-Verlauf der Merit, Abbruch"),
        ("G3-T3", "Vorher/Nachher und Speichern des Ergebnisses im Arbeitsbereich"),
    ],
    "Hier wird mikroptim.optimize für ein System gestartet und verfolgt.",
)
