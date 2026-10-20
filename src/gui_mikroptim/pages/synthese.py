"""Seite „Jobs und Synthese“: lange Läufe als Jobs, Protokolle von synth (G4)."""

from gui_mikroptim.views import common

common.settings_or_stop()
common.planned(
    "Jobs und Synthese",
    [
        ("G4-T1", "Jobverwaltung: starten, Status, Ausgabe, abbrechen (eigene Prozesse)"),
        ("G4-T2", "Protokollbrowser mikroptim.synth/1: Schritte, Verlauf, Stammbaum"),
        ("G4-T3", "Synthese-Job mit Formular für mikroptim synth"),
        ("G4-T4", "Ergebnisordner von Läufen (z. B. docs/ergebnisse/ in Mikroptim) durchsehen"),
    ],
    "Hier laufen Synthese und andere lange Rechnungen als eigene Prozesse (ADR-0003).",
)
