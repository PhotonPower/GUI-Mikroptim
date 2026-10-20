# Bedienung

Die GUI hat eine Navigation am linken Rand. In der Seitenleiste stehen die Versionen von Mikroptim und der GUI und ob GPUs verfügbar sind.

## Start (G0)

Zeigt, ob Mikroptim geladen werden kann (Version, CPU- oder CUDA-Build, GPUs mit freiem Speicher), und die Verzeichnisse: Arbeitsbereich, Mikroptim-Checkout, Beispielsysteme, CLI für Jobs. Fehlt Mikroptim, steht hier die Fehlermeldung des Imports und der Befehl zum Installieren. „Neu prüfen“ fragt Mikroptim und die GPUs erneut ab, z. B. nach einer Installation oder wenn ein anderer Prozess GPU-Speicher freigegeben hat.

## System

### Datei wählen und hochladen (G1-T1)

1. **Quelle:** „Beispielsysteme (Mikroptim)“ (`data/systems` im Checkout, nur mit `MKO_GUI_MIKROPTIM_REPO`), „Uploads“ oder „Ergebnisse“ im Arbeitsbereich. Angeboten werden nur Systemdateien (`mikroptim.system/1`); Glaskataloge und andere Formate im selben Ordner erscheinen nicht.
2. **Datei:** Die Auswahl gilt als **aktuelles System** für alle Seiten und steht in der Seitenleiste. Beim nächsten Besuch der Seite ist sie wieder ausgewählt.
3. **Hochladen:** unter „Datei hochladen“ eine `.json`-Datei wählen. Sie wird geprüft (JSON, Feld `format`, Systembeschreibung in Hauptversion 1, höchstens 20 MB, UTF-8) und unter `uploads/` gespeichert. Ein vorhandener Name wird nie überschrieben: Die zweite `linse.json` heißt `linse-2.json`. Nach dem Speichern ist die neue Datei sofort ausgewählt. Abgelehnte Dateien werden nicht gespeichert; die Meldung nennt den Grund.

Darunter stehen Name, Beschreibung, Zahl der Flächen, Wellenlängen und Felder, Pfad, Größe, Änderungszeit und die Glaskataloge der Datei, so wie sie in der Datei stehen.

**Hinweis zu Glaskatalogen:** Mikroptim sucht die Pfade unter `glass_catalogs` vom Verzeichnis der Systemdatei aus aufwärts. Eine hochgeladene Datei mit `data/glass/basis.json` findet ihren Katalog im Arbeitsbereich deshalb nicht. Das löst G1-T2 (siehe Plan); bis dahin absolute Pfade verwenden oder Beispielsysteme direkt aus dem Mikroptim-Checkout wählen.

### Tabellen, Paraxialdaten, Linsenschnitt (G1-T2, G1-T3, geplant)

Flächentabelle (Typ, Krümmung und Radius, Dicke, Material, Halbdurchmesser, Dezentrierung/Verkippung), Spektrum, Felder, Variablen und Nebenbedingungen, Paraxialdaten bei λ_ref und der Linsenschnitt.

## Auswertung (G2, geplant)

Für das gewählte System: RMS-Wellenfront in Wellen pro Feld und Wellenlänge als Tabelle und Heatmap, OPD-Karten, Spotdiagramme, PSF, MTF und Strehl. Einstellungen (Ringe, Speichen, Raster, Referenz, GPU, df64) stehen über den Ergebnissen und werden mit angezeigt. Ein zweites System kann zum Vergleich gewählt werden.

## Optimierung (G3, geplant)

Variablen mit Schranken und die Optionen von `mikroptim.optimize` einstellen, starten, Merit-Verlauf live verfolgen, abbrechen. Das Ergebnis wird als neue Datei unter `ergebnisse/` gespeichert, die Eingabe nie überschrieben. Vorher/Nachher als Tabelle und Wellenfront.

## Jobs und Synthese

### Reiter „Protokolle“ (G4-T2)

Zeigt Protokolle von `mikroptim synth … --log datei.json` (Format `mikroptim.synth/1`).

1. **Quelle wählen:** Arbeitsbereich (z. B. `uploads/`, später Jobordner) oder, wenn `MKO_GUI_MIKROPTIM_REPO` gesetzt ist, `docs/ergebnisse` bzw. `data` im Mikroptim-Checkout. Angeboten werden nur Dateien, deren Feld `format` ein Synthese-Protokoll ist. „Liste neu laden“ sucht erneut (sonst wird die Liste 30 s gecacht). Protokolle von anderen Rechnern lassen sich unter „Datei hochladen“ nach `uploads/` laden (gleiche Regeln wie auf der Seite „System“, nur Format `mikroptim.synth/1`).
2. **Kopfzeile:** Ergebnisstatus mit Meldung von Mikroptim (grün: Ziel erreicht, gelb: Ziel nicht erreicht oder Schrittweite zu klein, rot: Start abgelehnt), NA am Ende und Ziel-NA, Feldanteil, Elemente vorher → nachher, Einfügungen und Optimierungen, Laufzeit. Darüber Datei, Eingabesystem, Backend und Mikroptim-Version.
3. **Verlauf:** oben NA und Feldanteil der angenommenen Schritte, in der Mitte die RMS-Wellenfront in Wellen (logarithmisch; angenommene Schritte als Linie, abgelehnte als rote Kreuze), unten die Zahl der Glaselemente. Senkrechte gestrichelte Linien markieren Einfügungen. Mit der Maus über einem Punkt stehen Art, Kandidat, Aktion, LM-Status und die Operation.
4. **Schritte:** Tabelle aller Schritte, filterbar nach Art (`aperture`, `field`, `spectrum`, `penalty`, …), Aktion (`advance`, `shrink`, `insert`, `stop`, …), angenommen ja/nein und, bei Strahlsuche, Kandidat. Darunter die Einfügungen mit Empfehlung der Diagnose und Beschreibung der Operation.
5. **Strahlsuche** (nur bei `synth --beam`): Stammbaum der Kandidaten (grün beendet, blau behalten, grau expandiert, rosa verworfen; der beste Kandidat mit dickem Rahmen) und Kandidatentabelle. Liegt neben dem Protokoll eine gleichnamige `.dot`-Datei, wird diese gezeigt.
6. **Ziel-Tupel** (wenn vorhanden) und, aufklappbar, die Optionen des Laufs und das Ergebnis als JSON.

Die GUI rechnet dabei nichts nach: Alle Werte stehen so im Protokoll. `null` im Protokoll (nicht endliche Zahl) erscheint als Lücke bzw. „–“.

### Reiter „Jobs“ (G4-T1, G4-T3, geplant)

Lange Läufe (Synthese, Multistart, große Auswertungen) als Jobs starten und verfolgen. Jeder Job zeigt den vollständigen Befehl, mit dem er sich auf der Kommandozeile wiederholen lässt.
