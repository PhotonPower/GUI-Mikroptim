# ADR-0003: Lange Läufe als Jobs in eigenen Prozessen

- **Status:** angenommen
- **Datum:** 2026-10-20

## Kontext

Synthese-Läufe dauern Minuten bis Stunden (M6-T6: Hauptlauf 30 min, Erkundung rund 10 h). Streamlit führt Skripte bei jeder Interaktion neu aus und teilt einen Prozess zwischen allen Sitzungen; eine lange Rechnung im Skript blockiert, geht beim Neuladen verloren und hält GPU-Speicher fest. `synth` ist zudem nicht in der Python-API gebunden.

## Entscheidung

- Rechnungen, die länger als einige Sekunden ohne Rückmeldung laufen, starten als Job: eigener Prozess über die CLI (Programm `mikroptim` oder `python -m mikroptim`), eigener Ordner unter `arbeitsbereich/jobs/`, Beschreibung in `job.json` (Format `gui-mikroptim.job/1`, docs/architektur.md).
- Eingaben werden in den Jobordner kopiert; der vollständige Befehl steht in `job.json`, damit der Lauf ohne GUI wiederholbar ist.
- Die GUI liest den Fortschritt aus Dateien und Prozessstatus; sie wartet nie blockierend. Jobs überleben einen Neustart der GUI (eigene Prozessgruppe).
- Höchstens `MKO_GUI_MAX_JOBS` Jobs laufen gleichzeitig (Standard 1).
- Kurze Rechnungen (Laden, Paraxialdaten, `trace`, `evaluate`, `optimize` mit Rückruf und Abbruch) laufen direkt in der Seite.

## Konsequenzen

- Lange Läufe sind robust und reproduzierbar, Ergebnisse liegen als Dateien vor.
- Fortschritt der Synthese ist bis Mikroptim-Wunsch W2 nur so fein wie die Textausgabe des Programms.
- Ohne Warteschlangendienst gibt es keine Verteilung auf mehrere Rechner; das ist gewollt.

## Verworfene Alternativen

- **Threads im Streamlit-Prozess:** teilen GIL-freie, aber prozessweite Ressourcen (GPU-Kontext), gehen bei Neustart verloren.
- **Celery/Redis o. Ä.:** zu viel Infrastruktur für wenige Nutzer.
