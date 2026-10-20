"""Seite „Auswertung“: Wellenfront, OPD-Karten, Spots, PSF/MTF, Strehl (G2)."""

from gui_mikroptim.views import common

common.settings_or_stop()
common.planned(
    "Auswertung",
    [
        ("G2-T1", "RMS-Wellenfront pro Feld und Wellenlänge (mikroptim.trace)"),
        ("G2-T2", "EVAL: OPD-Karten, Spotdiagramme, Kennzahlen"),
        ("G2-T3", "PSF, MTF und Strehl (skalar, vektoriell)"),
        ("G2-T4", "Vergleich zweier Systeme"),
    ],
    "Hier wird ein System mit Mikroptim ausgewertet, auf CPU oder GPU.",
)
