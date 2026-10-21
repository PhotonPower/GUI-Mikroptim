# Bedienung

Die GUI hat eine Navigation am linken Rand. In der Seitenleiste stehen die Versionen von Mikroptim und der GUI und ob GPUs verfügbar sind.

## Einstellungen bleiben erhalten (G5-T4)

Die Einstellungen auf „Auswertung“ (Ringe, Speichen, Raster, Pupille, Referenz, Feld, Wellenlänge, Abzug, PSF-Optionen, GPU) und „Optimierung“ (alle Optionen und die Zeitgrenze) bleiben beim Wechsel auf eine andere Seite und zurück erhalten, solange der Browser-Tab offen ist. Gibt es einen gemerkten Wert beim neuen System nicht (z. B. Feld 2 bei einem System mit einem Feld), gilt wieder der Standard.

## Große Raster (G5-T2)

Damit der Browser bei großen Rastern flüssig bleibt, zeigt die GUI höchstens 512 × 512 Bildpunkte pro Karte und höchstens 50.000 Punkte pro Spotdiagramm. Größere OPD-Karten werden blockweise gemittelt, größere PSF-Ausschnitte blockweise über das Maximum zusammengefasst (die Spitze bleibt sichtbar), Spotdiagramme auf jeden k-ten Punkt ausgedünnt; der Titel des Diagramms nennt das dann („Anzeige: Mittel über 2 × 2 Rasterpunkte“). Nur die Anzeige ist reduziert – Kennzahlen, Tabellen, Farbskalen und CSV-Exporte nutzen die vollen Daten von Mikroptim.

## Exporte (G5-T3)

Alles wird im Browser heruntergeladen; die GUI schreibt dafür nichts in den Arbeitsbereich.

- **Diagramme:** Die Kamera-Schaltfläche oben rechts in jedem Diagramm speichert es als **SVG** (verlustfrei, für Berichte und Präsentationen) mit einem sprechenden Dateinamen, z. B. `auswertung_eval_opd.svg`.
- **Tabellen:** Knöpfe „CSV“ unter den wichtigsten Tabellen (Flächen, Paraxialdaten, Wellenfront, EVAL-Kennzahlen, Vergleich, Synthese-Schritte, Optimierungsverlauf). Zahlen stehen in voller Genauigkeit (wie in den JSON-Dateien von Mikroptim), Komma als Trenner, Punkt als Dezimalzeichen, UTF-8. Jede Tabelle lässt sich außerdem über ihr eigenes Menü (oben rechts beim Überfahren) herunterladen.
- **Systembericht:** „Bericht (Markdown)“ auf der Seite „System“ – Flächen, Spektrum, Felder, Paraxialdaten, Variablen und die RMS-Wellenfront (10 × 8, CPU) als Markdown-Datei mit Tabellen.

## Start (G0)

Zeigt, ob Mikroptim geladen werden kann (Version, CPU- oder CUDA-Build, GPUs mit freiem Speicher), und die Verzeichnisse: Arbeitsbereich, Mikroptim-Checkout, Beispielsysteme, CLI für Jobs. Fehlt Mikroptim, steht hier die Fehlermeldung des Imports und der Befehl zum Installieren. „Neu prüfen“ fragt Mikroptim und die GPUs erneut ab, z. B. nach einer Installation oder wenn ein anderer Prozess GPU-Speicher freigegeben hat.

## System

### Datei wählen und hochladen (G1-T1)

1. **Quelle:** „Beispielsysteme (Mikroptim)“ (`data/systems` im Checkout, nur mit `MKO_GUI_MIKROPTIM_REPO`), „Uploads“, „Ergebnisse“ oder „Jobergebnisse“ (Jobordner, z. B. `ergebnis.json` einer Synthese) im Arbeitsbereich sowie „Mikroptim: docs/ergebnisse“ (Ergebnisse dokumentierter Läufe, z. B. M6-T6). Angeboten werden nur Systemdateien (`mikroptim.system/1`); Glaskataloge und andere Formate im selben Ordner erscheinen nicht.
2. **Datei:** Die Auswahl gilt als **aktuelles System** für alle Seiten und steht in der Seitenleiste. Beim nächsten Besuch der Seite ist sie wieder ausgewählt.
3. **Hochladen:** unter „Datei hochladen“ eine `.json`-Datei wählen. Sie wird geprüft (JSON, Feld `format`, Systembeschreibung in Hauptversion 1, höchstens 20 MB, UTF-8) und unter `uploads/` gespeichert. Ein vorhandener Name wird nie überschrieben: Die zweite `linse.json` heißt `linse-2.json`. Nach dem Speichern ist die neue Datei sofort ausgewählt. Abgelehnte Dateien werden nicht gespeichert; die Meldung nennt den Grund.

Darunter stehen Name, Beschreibung, Zahl der Flächen, Wellenlängen und Felder, Pfad, Größe, Änderungszeit und die Glaskataloge der Datei, so wie sie in der Datei stehen.

### System ansehen (G1-T2)

Ist Mikroptim installiert, lädt die Seite die gewählte Datei mit `mikroptim.load_system` und zeigt:

- **Kennzahlen:** Flächen, Geisterplatten, Wellenlängen, Felder, Brennweite (bei afokalen Systemen „afokal“), darunter Pfad, λ_ref, Art der Quelle und die tatsächlich geladenen Glaskataloge. Warnungen von Mikroptim stehen gelb darüber.
- **Flächen:** Typ, Krümmung, Radius (nur Anzeige, ∞ bei Planflächen), Dicke, Material nach der Fläche (Katalogname, „konstant n = …“ oder Buchdahl-Koeffizienten), Halbdurchmesser, Brechzahl je Wellenlänge, Dezentrierung, Verkippung, Kommentar.
- **Spektrum und Felder** mit Gewichten; die Referenzwellenlänge ist markiert.
- **Paraxialdaten** bei λ_ref aus `mikroptim.paraxial` (identisch zum Feld `paraxial` von `mikroptim trace --json`): Brennweite, Schnittweiten, Hauptebenen, Defokus der Bildebene, Petzvalsumme, -krümmung und -radius, Austrittspupille, ABCD-Matrix. Leere Werte („–“) liefert Mikroptim z. B. bei afokalen Systemen. Aufklappbar als JSON.
- **Variablen** mit Wert und Schranken. Kann Mikroptim sie nicht auflösen (z. B. Glasvariablen auf Katalog-Gläsern, die erst `optimize` umwandelt), steht dort die Meldung und der Abschnitt `variables` der Datei.
- **Ziele und Nebenbedingungen**, **Geisterplatten** und die ganze Datei als **JSON**, so wie Mikroptim sie liest (`system_to_dict`).

Fehler beim Laden erscheinen rot mit dem JSON-Pfad, an dem Mikroptim den Fehler gefunden hat, z. B. ``FormatError (JSON-Pfad `surfaces[1].curvature`)``. Ohne Mikroptim zeigt die Seite nur die Kopfdaten aus der Datei.

### Glaskataloge hochladen (G1-T4)

Eigene Glaskataloge – z. B. Herstellerdaten, die nicht ins Mikroptim-Repository dürfen – lädt man im aufklappbaren Bereich **„Glaskataloge“** auf der Seite „System“ hoch (Format `mikroptim.glass/1`, Mikroptim docs/dateiformat.md, „Glasdaten“). Die GUI prüft den Aufbau und lässt Mikroptim den Katalog laden; abgelehnte Kataloge werden nicht gespeichert, die Meldung nennt den Grund. Gespeichert wird unter `kataloge/` im Arbeitsbereich mit unverändertem Dateinamen, denn Systemdateien finden Kataloge über ihn (`data/glass/private/schott.json` → `kataloge/schott.json`). Ein vorhandener Katalog gleichen Namens wird nicht überschrieben; „Katalog löschen“ (mit Bestätigung) macht den Namen frei. Steht ein Glas auch in einem Katalog von Mikroptim (z. B. N-BK7), weist die GUI darauf hin: Ein System, das beide Kataloge nennt, lädt Mikroptim nicht.

### Glaskataloge hochgeladener Dateien

Mikroptim sucht die Pfade unter `glass_catalogs` vom Verzeichnis der Systemdatei aus aufwärts. Eine hochgeladene Kopie eines Beispielsystems mit `data/glass/basis.json` findet ihren Katalog im Arbeitsbereich deshalb nicht; die Seite meldet den Fehler mit JSON-Pfad `glass_catalogs[…]`.

Dann zeigt die Seite für jeden Eintrag, wo die GUI ihn gefunden hat: „Datei“ (wie Mikroptim), „Mikroptim“ (im Checkout, `MKO_GUI_MIKROPTIM_REPO`), „Arbeitsbereich“ (hochgeladener Katalog gleichen Dateinamens) oder „fehlt“ – dann nennt ein Hinweis die Datei, die unter „Glaskataloge“ hochzuladen ist. Sind alle gefunden, erscheint **„Glaskataloge zuordnen und neu speichern“**: Mikroptim lädt die Datei mit diesen Katalogen (`System.from_json`) und speichert sie als `uploads/<name>-kataloge.json` (`System.save`). Dabei passt Mikroptim nur die Einträge unter `glass_catalogs` an den neuen Ort an, alles andere bleibt gleich; die neue Datei ist sofort ausgewählt, die ursprüngliche bleibt unverändert. Die neuen Pfade sind relativ zur neuen Datei (z. B. `../../src/Mikroptim/data/glass/basis.json`): Verschiebt man Arbeitsbereich oder Checkout, muss man neu speichern.

### Linsenschnitt (G1-T3)

Erster Reiter der Seite: Schnitt des Systems in der y-z-Ebene im Maßstab 1:1, gezeichnet aus Krümmung, Dicke, Halbdurchmesser, Material, Dezentrierung und Verkippung der Systembeschreibung.

- **Blau gefüllt:** Glas, also jeder Raum zwischen zwei Flächen, nach denen das Medium nicht `AIR` ist; Kittglieder erscheinen als zwei angrenzende Körper. **Schwarz:** Blende (Fläche 0) mit Pupillenradius. **Violett gestrichelt:** Geisterplatten mit ihrem Normierungsradius. **Rot:** Bildebene. Grau strichpunktiert: optische Achse. Über jeder Fläche steht ihre Nummer, mit der Maus Typ, Scheitellage und ob die Fläche dezentriert oder verkippt ist.
- **Bildraum:** Ist er länger als das System selbst (z. B. Einzellinse mit 100 mm Schnittweite), endet die z-Achse kurz hinter der letzten Fläche, und die Lage der Bildebene steht am rechten Rand. Der Schalter „Bildraum vollständig zeigen“ zeigt alles.
- **Hinweise** erscheinen unter dem Schnitt, z. B. wenn ein Halbdurchmesser größer als der Flächenradius ist (Profil dann bis zur Halbkugel gezeichnet, gepunktet) oder wenn nach der letzten Fläche kein Luft folgt.
- **Dezentrierung und Verkippung** nach Mikroptim ADR-0011: Sie betreffen nur die Fläche, Drehpunkt ist ihr Scheitel. Gezeichnet wird das transformierte Meridianprofil; eine Dezentrierung in x ist im y-z-Schnitt nicht sichtbar. Toleranzwerte sind klein und deshalb meist nicht zu erkennen.
- **Ohne Mikroptim** wird der Schnitt direkt aus der Datei gezeichnet, ungeprüft.

Strahlen folgen, sobald Mikroptim Strahlpfade liefert (Wunsch W1 in docs/schnittstelle-mikroptim.md).

## Auswertung

Braucht Mikroptim. Oben steht dieselbe Dateiauswahl wie auf der Seite „System“; vorausgewählt ist das aktuelle System, und eine Auswahl hier wird ebenso zum aktuellen System. Ladefehler erscheinen mit JSON-Pfad; die Reparatur von Glaskatalog-Pfaden gibt es auf der Seite „System“.

### RMS-Wellenfront (G2-T1)

Rechnet `mikroptim.trace` für das gewählte System, sobald sich Datei oder Einstellungen ändern. Ergebnisse werden pro Datei, Dateistand und Einstellungen zwischengespeichert, ein Zurückschalten rechnet also nicht neu.

- **Einstellungen:** Ringe und Speichen der Pupillenquadratur (Standard 10 × 8 wie in Mikroptim). Nur mit CUDA-Build und nutzbarem Gerät: Schalter „GPU“, bei mehreren Karten die Gerätewahl, und die Genauigkeit `fp64` oder `df64`. Die CPU rechnet immer in FP64.
- **Kopfzeile:** RMS in Wellen bei λ_ref, Quadratur, Backend (mit Gerätename) und Genauigkeit, Sollbrennweite der Bildpunkte. Darunter größter und kleinster RMS-Wert, Zahl der Strahlen und der versagten Strahlen; gibt es versagte Strahlen, erscheint ein Hinweis.
- **Heatmap** Feld × Wellenlänge: Zeilen sind die Felder mit Feldwinkel, Spalten die Wellenlängen (λ_ref markiert); jede Zelle trägt den RMS-Wert, Zellen mit versagten Strahlen „⚠ n versagt“, Zellen ohne gültigen Strahl „–“.
- **Tabelle** (aufklappbar): pro Feld und Wellenlänge Pupillenmodus, Strahlen, versagte Strahlen, RMS in Wellen und mm, Kolben, Bildpunkt; Reihenfolge und Werte wie das Feld `wavefront` von `mikroptim trace --json`.
- **Nachrechnen:** Die letzte Zeile nennt den passenden Befehl `mikroptim trace … --json` mit denselben Optionen.

Fehler von Mikroptim erscheinen als Meldung, z. B. bei afokalen Systemen ohne `target.focal_length` (`ValueError: Wellenfront: Sollbrennweite ist nicht endlich …`) oder wenn die GPU nicht verfügbar ist (`GpuUnavailableError`).

Die RMS-Wellenfront steht im Reiter **„Wellenfront (trace)“**.

### OPD und Spots (G2-T2)

Reiter **„OPD und Spots (eval)“**: rechnet `mikroptim.evaluate` auf dem dichten Pupillenraster (wie `mikroptim eval`); Ergebnisse werden pro Datei, Dateistand und Einstellungen zwischengespeichert.

- **Einstellungen:** Raster N (N × N über das Quadrat der normierten Pupille, Standard 64), „halbe Pupille“ (nur x ≥ 0, Symmetrie x → −x), Referenzsphäre durch die Austrittspupille (Standard) oder durch den Scheitel der letzten Fläche (wie trace), GPU und Gerät nur mit CUDA-Build und Gerät. Ab N = 512 steht die Zahl der Strahlen pro Tupel dabei; große Raster rechnen spürbar länger.
- **Kopfzeile:** Raster und Punkte in der Pupille, Referenzsphäre mit Lage der Austrittspupille, Backend; ein Hinweis, wenn Strahlen versagen.
- **Kennzahlentabelle** pro Feld und Wellenlänge, wie `tuples` von `mikroptim eval --json`: Bildhöhe, Strahlen, versagt, RMS- und PV-OPD sowie RMS nach Abzug der Kippung bzw. des Defokus (Wellen bei λ_ref), RMS-Spotradius, Schwerpunkt und Hauptstrahl relativ zum idealen Bildpunkt, Verzeichnung von Hauptstrahl (HS) und Schwerpunkt (SP) in %, Brennlinien z_t und z_s relativ zur Bildebene, Astigmatismus und Defokus-Koeffizient (mm). Nicht endliche Werte (z. B. Verzeichnung auf der Achse) stehen leer. Die Strehl-Zahl nach Maréchal aus der Textausgabe von `mikroptim eval` fehlt hier; die Strehl-Zahl über die FFT kommt mit G2-T3.
- **OPD-Karte** für das gewählte Feld und die gewählte Wellenlänge, nach Abzug von Kolben, Kolben und Kippung oder Kolben, Kippung und Defokus: in Wellen bei λ_ref über der normierten Pupille (x nach rechts, y nach oben), Farbskala blau–weiß–rot symmetrisch um 0; außerhalb der Pupille und bei versagten Strahlen leer. Bei halber Pupille ist die Karte gespiegelt (wie in Mikroptim).
- **Spotdiagramm** desselben Tupels: Durchstoßpunkte in der Bildebene relativ zum idealen Bildpunkt in µm, Schwerpunkt als rotes ×, idealer Bildpunkt als Kreuz; versagte Strahlen fehlen. Bei halber Pupille nur die gerechnete Hälfte.
- **Nachrechnen:** Die letzte Zeile nennt `mikroptim eval … --json` mit denselben Optionen und die Optionen für dieselbe OPD-Karte als CSV (`--map F,L --map-file … --remove …`).

### PSF und MTF (G2-T3)

Reiter **„PSF und MTF“**: Beugungs-PSF eines Feldes und einer Wellenlänge aus der EVAL-Rechnung. Raster, Referenzsphäre und GPU kommen aus dem Reiter „OPD und Spots“; ein größeres Raster dort vergrößert das Bildfenster der PSF.

- **Einstellungen:** Zero-Padding Q (≥ 2, Standard 4), NA vorgeben (0: aus den Feldstrahlen, wie in Mikroptim; nötig z. B. bei afokalen Systemen), Modell skalar oder vektoriell (Richards-Wolf), beim vektoriellen Modell Polarisation (linear x/y, zirkular, unpolarisiert) und Defokus der Auswerteebene. Feld, Wellenlänge, lineare oder logarithmische Darstellung und der Ausschnitt in Airy-Radien (0: ganzes Bildfenster).
- **Kennzahlen:** Strehl (nach Abzug der Kippung), Strehl im idealen Bildpunkt, Maximum der abgetasteten PSF, Airy-Radius, MTF bei f_c/2 sagittal und tangential; darunter NA, FFT-Größe und Pixel, Lage des Maximums, transmittierter Anteil und Grenzfrequenz f_c. Beim vektoriellen Modell zusätzlich FWHM und die Energieanteile von E_x, E_y, E_z.
- **Hinweise:** NA über 0,6 beim skalaren Modell (die skalare Näherung ist dann ungenau, vektoriell verwenden). Bildfenster zu klein: Reicht der geometrische Spot (Schwerpunkt ± 3 RMS-Radien) über das halbe Bildfenster, faltet die FFT die PSF zurück – dieselbe Warnung wie `mikroptim eval`; Abhilfe ist ein größeres Raster.
- **PSF** in Strehl-Einheiten über der Bildebene in µm relativ zum idealen Bildpunkt; **MTF** sagittal und tangential über der Ortsfrequenz in lp/mm mit f_c und f_c/2. Beim vektoriellen Modell aufklappbar die Feldkomponenten |E_x|², |E_y|², |E_z|² (logarithmisch).
- Die vektorielle PSF rechnet Mikroptim über die Kommandozeile (`mikroptim eval --vector`), solange sie nicht in der Python-API steht; direkt in der Seite nur bis Raster 256, größere Läufe gehören in einen Job (ab G4-T1).
- **Nachrechnen:** `mikroptim eval … --json --psf …` mit denselben Optionen, PSF und MTF des Tupels als CSV.

### Vergleich zweier Systeme (G2-T4)

Reiter **„Vergleich“**: A ist das aktuelle System (oben gewählt), B wird im Reiter selbst gewählt (gleiche Quellen wie auf „System“); die Wahl von B ändert das aktuelle System nicht. Beide werden mit den Einstellungen des Reiters „Wellenfront“ gerechnet. Typischer Fall: das Ergebnis einer Synthesestufe gegen die vorige.

- **Kennzahlen:** größter RMS-Wert von A und B (bei B mit Δ, grün wenn kleiner), versagte Strahlen und Flächenzahl beider Systeme.
- **Gleiche Feldwinkel, Wellenlängen und Referenzwellenlänge:** Heatmap der Differenz B − A in Wellen (rot: B schlechter, blau: B besser, symmetrisch um 0) und aufklappbar die Tabelle mit RMS A, RMS B, Δ und versagten Strahlen.
- **Sonst:** ein Hinweis mit den Unterschieden und beide RMS-Heatmaps nebeneinander. Die Referenzwellenlänge gehört dazu, weil RMS-Werte in Wellen bei λ_ref des jeweiligen Systems stehen.
- **Paraxialdaten** nebeneinander mit Δ B − A (nur bei zwei endlichen Zahlen) und aufklappbar beide **Linsenschnitte**.
- Ist B dieselbe Datei wie A, steht nur ein Hinweis; Fehler eines der beiden Systeme (z. B. afokal) erscheinen mit A oder B gekennzeichnet.

## Optimierung

Braucht Mikroptim. Dateiauswahl wie auf „System“, vorausgewählt das aktuelle System.

### Variablen und Optionen (G3-T1)

Hat ein System keinen Abschnitt `variables`, kann Mikroptim es nicht optimieren; die Seite sagt das, nennt Beispielsysteme mit Variablen und zeigt keine Optionen.

- **Variablen** aus `System.variables()`: Name, Typ, Fläche bzw. Geisterplatte, Ordnung, Wert, untere und obere Schranke, typische Größe. Kann Mikroptim sie nicht auflösen (Glasvariablen auf Katalog-Gläsern werden erst beim Start der Optimierung umgewandelt), stehen dort ein Hinweis und der Abschnitt `variables` der Datei. Nebenbedingungen aufklappbar.
- **Optionen** wie `mikroptim optimize`, mit denselben Standardwerten: Zyklen pro Lauf (100; 0 wertet nur den Startpunkt aus), Ringe und Speichen (10 × 8), Jacobi-Matrix `fd` oder `adjoint`, Läufe für den Multistart (1), relative Störung (0,05) und Seed (0) – beide nur mit mindestens 2 Läufen einstellbar –, hartes Strahlversagen, eigenes Strafgewicht w_fail (nur beim weichen Strahlversagen), GPU und Gerät nur mit CUDA-Build und Gerät.
- Darunter steht der entsprechende Befehl `mikroptim optimize … --json` mit genau diesen Optionen (nur Abweichungen vom Standard).

### Lauf (G3-T2)

- **Zeitgrenze** (Standard 60 s) und **„Optimierung starten“**: `mikroptim.optimize` läuft direkt in der Seite. Währenddessen stehen Lauf, Zyklus, aktuelle und beste Merit darüber, und der Merit-Verlauf wird laufend gezeichnet (logarithmisch, eine Kurve pro Lauf des Multistarts, abgelehnte Versuchsschritte als Kreuze).
- **„Abbrechen“** unterbricht den Lauf; die bis dahin gerechneten Zyklen bleiben als Verlauf stehen, das System ist unverändert. Jede andere Eingabe auf der Seite während des Laufs unterbricht ihn ebenso (Streamlit führt die Seite dann neu aus); das wird als „unterbrochen“ gemeldet.
- **Zeitgrenze erreicht:** Hinweis und Knopf „Als Job rechnen“ – dieselbe Optimierung läuft dann als Job (`mikroptim optimize … --json -o ergebnis.json`) und ist auf der Seite „Jobs und Synthese“ zu verfolgen.
- **Ergebnis:** Status von Mikroptim, Zyklen und Laufzeit, Merit am Start und am Ende, Zahl der Läufe und bester Lauf, Tabelle der Variablen (Start, Ende, Änderung), Warnungen und der Verlauf. Das Ergebnis bleibt in der Sitzung, solange Datei und Optionen gleich bleiben; nach einer Änderung steht ein Hinweis.

Das Ergebnis ist gleich dem von `mikroptim optimize` mit denselben Optionen (Merit bitgleich).

### Vorher/Nachher und Speichern (G3-T3)

- **RMS-Wellenfront vorher → nachher** mit derselben Quadratur wie die Optimierung: größter RMS-Wert vorher und nachher (Δ grün, wenn kleiner), Heatmap der Differenz nachher − vorher (blau: besser) und aufklappbar die Tabelle.
- **Ergebnis speichern:** Dateiname (Vorschlag `<name>-optimiert.json`) und „Speichern“ schreibt das optimierte System über Mikroptim (`System.save`) als neue Datei nach `ergebnisse/`. Ein vorhandener Name wird nie überschrieben (`…-2.json`), Sonderzeichen werden ersetzt, die Eingabedatei bleibt unverändert. Mit „als aktuelles System übernehmen“ (Standard) ist die neue Datei danach ausgewählt – auf dieser und allen anderen Seiten – und kann gleich weiter ausgewertet oder optimiert werden.

Die gespeicherte Datei reproduziert die Endmerit der Optimierung bitgleich.

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

### Reiter „Ergebnisordner“ (G4-T4)

Zeigt einen ganzen Lauf mit allen Stufen, z. B. `docs/ergebnisse/m6-t6/` in Mikroptim.

- **Ordner:** Unterordner von `docs/ergebnisse` im Mikroptim-Checkout, die Mikroptim-Dateien enthalten, die Jobordner und `ergebnisse/` im Arbeitsbereich. „Neu einlesen“ liest den Ordner erneut (sonst 30 s zwischengespeichert).
- **Überblick:** Zahl der Systeme, Synthese-Protokolle, Auswertungen (`mikroptim eval --json`), Textausgaben und JSON-Dateien ohne Mikroptim-Format (z. B. eigene Laufdateien eines Skripts). Liegt im Ordner ein `README.md`/`bericht.md` oder daneben eine Markdown-Datei, die mit dem Ordnernamen beginnt (`m6-t6-zielspezifikation.md`), ist sie aufklappbar als **Bericht** dabei.
- **Stufen:** Die Dateien werden nach dem Kürzel am Anfang des Namens gegliedert (`p1`, `p2`, …, `a3`, `z2`; natürlich sortiert), mit der Zahl der Dateien je Art.
- **Systeme:** Tabelle (Name, Flächen, Felder, Wellenlängen, Geisterplatten) und für das gewählte System: „Als aktuelles System“, „Auf ‚System‘ ansehen“, „Auswerten“ und „Mit aktuellem System vergleichen“ (öffnet „Auswertung“ mit dem gewählten System als B im Reiter „Vergleich“).
- **Synthese-Protokolle:** Tabelle (Status, NA und Feld am Ende, Elemente, Einfügungen, Optimierungen, Laufzeit) und das gewählte Protokoll aufklappbar wie im Reiter „Protokolle“.
- **Auswertungen:** Tabelle mit Raster, Referenzsphäre, PSF-Modell, Zahl der Tupel, größtem und kleinstem RMS-OPD, kleinstem und größtem Strehl und versagten Strahlen – Werte aus den Dateien.
- **Weitere Dateien:** Textausgaben, JSON ohne Format und Stammbäume (DOT) zum Ansehen.

### Reiter „Neue Synthese“ (G4-T3)

Startet `mikroptim synth` als Job.

1. **Startsystem** wählen (vorausgewählt das aktuelle System; Quellen wie auf „System“, dazu „Jobergebnisse“, also Ergebnisse früherer Läufe). Es wird in den Jobordner kopiert; Mikroptim schreibt die Kopie neu, damit die Glaskataloge von dort gefunden werden.
2. **Optionen** wie in Mikroptim (`docs/cli.md`, „mikroptim synth“), mit denselben Standardwerten:
   - **Ziel:** Ziel-NA (0: NA des Starts), Feldanteil am Start und am Ende (0: wie am Start), RMS-Ziel in Wellen (Standard 1/14), Merit-Faktor K.
   - **Homotopie und LM:** Schrittweite Δ₀, Δ_min, Δ_max, Sattel-Δ, höchstens so viele Optimierungen, LM-Zyklen pro Schritt, Ringe und Speichen, Krümmungsschranke (0: offen).
   - **Einfügen (Operator A):** höchstens so viele Glaselemente, Mittendicke, maximale Dicke, Dickenstufen, kleinster Luftspalt.
   - **Strahlsuche:** Breite (0: aus), Alternativen, gestörte Starts, Störung, Seed, Duplikat-Schwelle, FP32-Vorfilter.
   - **Rechnen:** Jacobi-Matrix `fd` oder `adjoint`; GPU und Gerät nur mit CUDA-Build und Gerät.
3. **„Synthese starten“** legt den Job an; er startet, sobald ein Platz frei ist, und ist danach im Reiter „Jobs“ vorausgewählt.

Im Befehl stehen nur Optionen, die vom Standard abweichen, dazu `-o ergebnis.json --log protokoll.json` und bei Strahlsuche `--dot stammbaum.dot`; alle Werte stehen zusätzlich in `job.json`. Gleiche Eingabe und gleiche Optionen (einschließlich Seed) ergeben dasselbe Protokoll.

### Reiter „Jobs“ (G4-T1)

Lange Läufe (Synthese, Multistart, große Auswertungen) laufen als Jobs in eigenen Prozessen; sie laufen weiter, wenn der Browser geschlossen oder die GUI neu gestartet wird. Jobs entstehen aus Formularen der GUI (Synthese ab G4-T3).

- **Oben:** laufende Jobs gegen die Höchstzahl (`MKO_GUI_MAX_JOBS`, Standard 1, weil die GPU geteilt wird) und wartende Jobs; „Aktualisieren“ liest alles neu.
- **Liste:** alle Jobs, neueste zuerst, mit Art, Status (⏳ wartend, ▶️ läuft, ✅ fertig, ❌ fehler, ⏹️ abgebrochen), Anlagezeit, Dauer und Exit-Code. Wartende Jobs starten automatisch in der Reihenfolge der Anlage, sobald ein Platz frei wird.
- **Details** des gewählten Jobs: Status, Dauer, Exit-Code, Mikroptim-Version, Zeiten und Ordner; der **Befehl** zum Wiederholen von Hand (im Jobordner auszuführen); Eingaben; die letzten 200 Zeilen von Ausgabe und Fehlerausgabe; Optionen. Solange der Job läuft, aktualisiert sich die Ansicht alle 2 Sekunden selbst.
- **Abbrechen:** beendet den Befehl samt aller Kindprozesse, der Status wird „abgebrochen“; ein wartender Job wird gar nicht erst gestartet.
- „fehler“ mit dem Hinweis „Wrapper-Prozess nicht mehr vorhanden“ heißt: Der Job lief, als der Rechner neu gestartet oder der Prozess von außen beendet wurde.

Bei **Synthese-Jobs** stehen nach dem Ende zusätzlich das Protokoll (wie im Reiter „Protokolle“) und zwei Knöpfe in den Details: „Ergebnis als aktuelles System übernehmen“ (dann auf „System“ oder „Auswertung“ ansehen) und „Im Reiter Protokolle öffnen“. Während des Laufs steht die letzte Zeile der Ausgabe darunter.

Die Dateien eines Jobs liegen unter `jobs/` im Arbeitsbereich (Aufbau: docs/architektur.md, „Jobs“); Synthese-Protokolle aus Jobs erscheinen im Reiter „Protokolle“ unter der Quelle „Arbeitsbereich“.
