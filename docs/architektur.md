# Architektur

## Überblick

```mermaid
flowchart TB
    B[Browser des Nutzers] -- SSH-Tunnel, localhost:8501 --> S[Streamlit-Server<br/>127.0.0.1]
    subgraph GUI[GUI-Mikroptim, ein Prozess]
        P[pages/<br/>Seiten] --> V[views/<br/>Tabellen, Plotly-Figuren]
        P --> BK[backend/<br/>ohne Streamlit]
        V --> BK
    end
    S --> P
    BK -- import mikroptim --> M[Mikroptim-Python-API<br/>nanobind, CPU/CUDA]
    BK -- Unterprozess --> J[Jobs<br/>mikroptim synth …]
    J --> W[(Arbeitsbereich<br/>uploads/ ergebnisse/ jobs/)]
    BK --> W
    BK -. nur lesen .-> R[(Mikroptim-Checkout<br/>data/systems, Glaskataloge)]
```

Die GUI ist eine dünne Schicht über Mikroptim (ADR-0002). Sie lädt Dateien, ruft Mikroptim auf, stellt Ergebnisse dar und verwaltet lange Läufe als Jobs (ADR-0003). Es gibt keine eigene Optik, keine Datenbank und keine Benutzerverwaltung (ADR-0004).

## Schichten

| Schicht | Verzeichnis | Darf importieren | Aufgabe |
|---|---|---|---|
| Seiten | `src/gui_mikroptim/pages/` | `views`, `backend`, `streamlit` | Layout, Widgets, Ablauf einer Seite. Keine Logik, die man testen müsste, ohne die Seite zu rendern. |
| Views | `src/gui_mikroptim/views/` | `backend`, `streamlit`, `plotly`, `numpy` | Wiederverwendbare Darstellungen: Systemtabelle, OPD-Karte, Spotdiagramm, Verlaufskurve. Plotly-Figuren werden von reinen Funktionen erzeugt (testbar ohne Streamlit). |
| Backend | `src/gui_mikroptim/backend/` | `numpy`, Standardbibliothek, `mikroptim` (nur `mko.py`, `jobs.py`) | Dateien, Anbindung an Mikroptim, Protokolle, Jobs. **Kein** `streamlit`. |
| Konfiguration | `src/gui_mikroptim/config.py` | Standardbibliothek | Einstellungen aus Umgebungsvariablen |

### Views

| Modul | Stand | Inhalt |
|---|---|---|
| `views/common.py` | G0 | Einstellungen, Mikroptim-Status, Seitenleiste, Platzhalter |
| `views/file_picker.py` | G4-T2, G1-T1 | Quelle und Datei nach Format wählen, Upload, Vorauswahl der aktuellen Datei |
| `views/current.py` | G1-T1 | aktuelles System in `st.session_state["aktuell.datei"]` (absoluter Pfad, geprüft gegen die erlaubten Wurzeln) |
| `views/synth_plots.py` | G4-T2 | Verlaufsfigur eines Synthese-Protokolls (rein, ohne Streamlit) |
| `views/synth_view.py` | G4-T2 | Darstellung eines Synthese-Protokolls |
| `views/lens_plot.py` | G1-T3 | Geometrie des Linsenschnitts (`outline`: Profile mit exakter Pfeilhöhe, Glaskörper, Geisterplatten, Bildebene, Hinweise) und Plotly-Figur (`lens_figure`); rein, ohne Streamlit |
| `views/wavefront_plots.py` | G2-T1 | Heatmap Feld × Wellenlänge (rein) |
| `views/wavefront_view.py` | G2-T1 | Einstellungen (`gpu_inputs`: GPU nur mit Gerät), gecachte Rechnung (`st.cache_data` pro Pfad, Stand, Optionen), Darstellung |
| `views/eval_plots.py` | G2-T2 | OPD-Karte (divergierend, symmetrisch um 0, NaN leer) und Spotdiagramm in µm (ab 5000 Punkten WebGL); rein |
| `views/psf_plots.py` | G2-T3 | PSF (linear/log, Ausschnitt in mm, Achsen in µm) und MTF-Schnitte mit f_c; rein |
| `views/psf_view.py` | G2-T3 | PSF-Einstellungen, gecachte skalare und vektorielle PSF (`st.cache_data`), Kennzahlen, Hinweise, Figuren |
| `views/eval_view.py` | G2-T2 | EVAL-Einstellungen, `Evaluation` im Ressourcen-Cache (nanobind-Objekt, höchstens 8), Kennzahlen, Auswahl Feld/Wellenlänge/Abzug, Karten |
| `views/system_view.py` | G1-T2 | Laden mit Cache (`st.cache_resource` pro Pfad, Änderungszeit, Größe), Fehleranzeige, Katalogreparatur, Reiter der Seite „System“ |

### Backend-Module

| Modul | Stand | Inhalt |
|---|---|---|
| `backend/files.py` | G0 | Pfade unter einer Wurzel auflösen (Schutz vor `..` und Symlinks), Dateilisten, sichere Dateinamen, neue Dateien ohne Überschreiben |
| `backend/mko.py` | G0 | Status von Mikroptim (Version, CUDA, Geräte), `require()`; einziger `import mikroptim` |
| `backend/protocols.py` | G0 | JSON-Formate von Mikroptim erkennen, `mikroptim.synth/1` in Tabellenzeilen und Stammbaum (DOT) umordnen |
| `backend/protocols.py` (Erweiterung) | G4-T2 | Format aus dem Dateianfang (`peek_format`), Dateilisten nach Format (`list_documents`), Kandidaten- und Zieltabellen, Schrittfilter |
| `backend/uploads.py` | G1-T1 | Upload prüfen (Endung, Größe, UTF-8, Format) und unter `uploads/` ablegen, BOM entfernen |
| `backend/jobs.py` | G4-T1 | Jobs als Unterprozesse, Ablage `gui-mikroptim.job/1` |
| `backend/compute.py` | G1-T2 | dünne Hüllen um Mikroptim: `load_system`, `details` (Systembeschreibung, Paraxialdaten, Variablen mit Teilfehlern), `load_error` (Ausnahme → Art, Meldung, JSON-Pfad), `repair_catalogs` (über `System.from_json`/`save`); `TraceOptions` und `trace_wavefront` (G2-T1, Ergebnis als picklebare `WavefrontResult` mit NumPy-Arrays); `EvalOptions`, `evaluate` und `mm_to_waves` (G2-T2, Umrechnung genau wie `mikroptim eval`); `PsfOptions`, `VectorOptions`, `scalar_psf`, `vector_psf` (über `run_cli` mit temporären CSV-Dateien) und `window_warning` (Regel von `mikroptim eval`) mit Ergebnis `PsfResult` (G2-T3) |
| `backend/system_tables.py` | G1-T2, G2-T1 | Tabellenzeilen aus `System` und `system_to_dict` (Flächen, Spektrum, Felder, Paraxialdaten, Variablen) aus der Wellenfront (`wavefront_rows`, wie `trace --json`) und aus EVAL (`eval_rows`, wie `tuples` von `eval --json`), Zahlenformat mit ∞/NaN |

## Seiten

| Seite | Datei | Meilenstein | Rechnet im Streamlit-Prozess? |
|---|---|---|---|
| Start | `pages/start.py` | G0 | nein (nur Status) |
| System | `pages/system.py` | G1 | Laden und Paraxialdaten (Millisekunden) |
| Auswertung | `pages/auswertung.py` | G2-T1 bis G2-T3 | Reiter „Wellenfront“ (`trace`), „OPD und Spots“ (`evaluate`) und „PSF und MTF“ (`Evaluation.psf`, vektoriell über die CLI bis Raster 256), Millisekunden bis Sekunden je nach Raster |
| Optimierung | `pages/optimierung.py` | G3 | `optimize` mit Rückruf (Sekunden bis Minuten, mit Abbruch) |
| Jobs und Synthese | `pages/synthese.py` | G4 | nein: startet Jobs und liest deren Dateien |

## Zustand und Cache

Streamlit führt das Seitenskript bei jeder Interaktion neu aus. Daraus folgen feste Regeln:

- **Einstellungen und Mikroptim-Status** sind `st.cache_resource` (einmal pro Serverprozess, Knopf „Neu prüfen“ leert den Status).
- **Geladene Systeme und Rechenergebnisse** sind `st.cache_data`. Der Schlüssel enthält den aufgelösten Pfad, die Änderungszeit und die Größe der Datei sowie alle Rechenoptionen (Ringe, Speichen, Raster, GPU, Genauigkeit). Eine geänderte Datei wird so nie mit altem Ergebnis gezeigt.
- Objekte aus Mikroptim (`System`, `Wavefront`, …) sind nanobind-Objekte. Gecacht werden die daraus gewonnenen NumPy-Arrays und Zahlen, nicht die Objekte selbst; nur `System` darf als Ressource gecacht werden, weil es unveränderlich ist.
- **Auswahl des Nutzers** (gewählte Datei, Feld, Wellenlänge) liegt in `st.session_state` unter Schlüsseln mit Seitenpräfix, z. B. `system.quelle`, `auswertung.feld`. Die gewählte Systemdatei ist seitenübergreifend `aktuell.datei` (`views/current.py`). Sie ist ein eigener Schlüssel und kein Widget-Zustand, weil Streamlit Widget-Zustände von nicht angezeigten Seiten verwirft.
- **Seitenleiste:** Die Zeile „Aktuelles System“ wird nach dem Lauf der Seite gefüllt (Platzhalter in `app.py`), damit eine neue Auswahl sofort erscheint.
- **Tests:** `AppTest.switch_page` führt nur das Seitenskript aus, nicht den Einstieg `app.py`; die Seitenleiste wird deshalb über einen normalen Lauf des Einstiegs getestet.
- Der Streamlit-Prozess wird von allen Browsersitzungen geteilt. GPU-Rechnungen im Prozess sind kurz zu halten; was länger dauert, wird ein Job.

## Jobs (ab G4-T1)

Lange Läufe laufen als eigener Prozess (ADR-0003):

1. Die Seite erzeugt eine Jobbeschreibung (Befehl als Argumentliste, Eingabedateien, Optionen, Seed).
2. `backend/jobs.py` legt `jobs/<JJJJMMTT-hhmmss>-<kurz>/` an, kopiert die Eingaben dorthin, schreibt `job.json` und startet den Prozess mit Arbeitsverzeichnis im Jobordner. `stdout`/`stderr` gehen nach `ausgabe.txt`/`fehler.txt`.
3. Der Status ergibt sich aus der Prozess-ID, dem Exit-Code (`exit_code` in `job.json`, geschrieben von einem kleinen Wrapper) und den Dateien. Die GUI kann neu starten, ohne laufende Jobs zu verlieren.
4. Die Seite liest Ausgaben und Protokolle zyklisch (`st.fragment(run_every=…)`), nicht durch Blockieren.

Format `gui-mikroptim.job/1` (`job.json`):

| Feld | Bedeutung |
|---|---|
| `format` | `"gui-mikroptim.job/1"` |
| `id` | Name des Jobordners |
| `kind` | `synth`, `optimize`, `eval`, … |
| `argv` | vollständige Argumentliste, so wie gestartet (reproduzierbar per Hand) |
| `inputs` | kopierte Eingabedateien (relativ zum Jobordner) |
| `mikroptim_version` | Version beim Start |
| `created`, `started`, `finished` | Zeitpunkte (ISO 8601, UTC) |
| `pid`, `exit_code` | Prozess-ID, Exit-Code (`null` solange laufend) |
| `status` | `wartend`, `läuft`, `fertig`, `fehler`, `abgebrochen` |

Gleichzeitig laufende Jobs sind auf `MKO_GUI_MAX_JOBS` begrenzt (Standard 1, weil die GPU geteilt wird).

## Fehlerbehandlung

- Ausnahmen von Mikroptim (`FormatError` mit `json_path`, `GlassError`, `GpuUnavailableError`, `CudaError`) werden auf der Seite mit `st.error` gezeigt, mit JSON-Pfad, wenn vorhanden. Die App stürzt nicht ab.
- Ohne Mikroptim laufen alle Seiten und zeigen einen Hinweis; das prüfen die App-Tests (`tests/test_app.py`).
