"""Seite „System“: Systemdatei wählen, Tabelle, Paraxialdaten, Linsenschnitt (G1)."""

from gui_mikroptim.views import common

common.settings_or_stop()
common.planned(
    "System",
    [
        ("G1-T1", "Dateiauswahl (Beispiele, Uploads, Ergebnisse) und Upload"),
        ("G1-T2", "Flächentabelle, Spektrum, Felder, Variablen, Nebenbedingungen, Paraxialdaten"),
        ("G1-T3", "Linsenschnitt in der y-z-Ebene"),
    ],
    "Hier wird eine Systemdatei (mikroptim.system/1) geladen und dargestellt.",
)
