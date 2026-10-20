# Bedienung

Die GUI hat eine Navigation am linken Rand. In der Seitenleiste stehen die Versionen von Mikroptim und der GUI und ob GPUs verfügbar sind.

## Start (G0)

Zeigt, ob Mikroptim geladen werden kann (Version, CPU- oder CUDA-Build, GPUs mit freiem Speicher), und die Verzeichnisse: Arbeitsbereich, Mikroptim-Checkout, Beispielsysteme, CLI für Jobs. Fehlt Mikroptim, steht hier die Fehlermeldung des Imports und der Befehl zum Installieren. „Neu prüfen“ fragt Mikroptim und die GPUs erneut ab, z. B. nach einer Installation oder wenn ein anderer Prozess GPU-Speicher freigegeben hat.

## System (G1, geplant)

Datei wählen aus den Beispielsystemen von Mikroptim, den Uploads oder den Ergebnissen, oder eine Datei hochladen. Danach Flächentabelle (Typ, Krümmung und Radius, Dicke, Material, Halbdurchmesser, Dezentrierung/Verkippung), Spektrum, Felder, Variablen und Nebenbedingungen, Paraxialdaten bei λ_ref und der Linsenschnitt. Die gewählte Datei gilt auch auf den anderen Seiten.

## Auswertung (G2, geplant)

Für das gewählte System: RMS-Wellenfront in Wellen pro Feld und Wellenlänge als Tabelle und Heatmap, OPD-Karten, Spotdiagramme, PSF, MTF und Strehl. Einstellungen (Ringe, Speichen, Raster, Referenz, GPU, df64) stehen über den Ergebnissen und werden mit angezeigt. Ein zweites System kann zum Vergleich gewählt werden.

## Optimierung (G3, geplant)

Variablen mit Schranken und die Optionen von `mikroptim.optimize` einstellen, starten, Merit-Verlauf live verfolgen, abbrechen. Das Ergebnis wird als neue Datei unter `ergebnisse/` gespeichert, die Eingabe nie überschrieben. Vorher/Nachher als Tabelle und Wellenfront.

## Jobs und Synthese (G4, geplant)

Lange Läufe (Synthese, Multistart, große Auswertungen) als Jobs starten und verfolgen. Protokolle `mikroptim.synth/1` öffnen: Kopfzeile mit Ergebnis, Schritttabelle, Verlauf von NA, Feld und RMS über den Schritten, Einfügungen markiert, Stammbaum der Kandidaten. Jeder Job zeigt den vollständigen Befehl, mit dem er sich auf der Kommandozeile wiederholen lässt.
