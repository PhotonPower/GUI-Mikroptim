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
| `views/compare_view.py` | G2-T4 | Reiter „Vergleich“: Wahl von B, Kennzahlen, Differenz-Heatmap (`wavefront_plots.rms_difference_heatmap`) oder Heatmaps nebeneinander, Paraxialdaten, Linsenschnitte |
| `views/jobs_view.py` | G4-T1 | Reiter „Jobs“: Liste, Details mit Selbstaktualisierung (`st.fragment(run_every=2 s)`) solange der Job läuft, Abbruch |
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
| `backend/compare.py` | G2-T4 | Vergleichbarkeit zweier Systeme (Feldwinkel, Wellenlängen, λ_ref), Differenz B − A der RMS-Wellenfront, Zeilen für RMS- und Paraxialvergleich |
| `backend/jobs.py` | G4-T1 | Jobs anlegen (`submit`), Warteschlange (`start_pending`), Status (`load`, `list_jobs`, `effective_status`), Abbruch (`cancel`), Ablage `gui-mikroptim.job/1`, Prozessprüfung für Linux und Windows |
| `backend/job_runner.py` | G4-T1 | Wrapper eines Jobs: Befehl starten, Ausgaben umleiten, Abbruch überwachen, Status schreiben, nächste Jobs starten |
| `backend/compute.py` | G1-T2 | dünne Hüllen um Mikroptim: `load_system`, `details` (Systembeschreibung, Paraxialdaten, Variablen mit Teilfehlern), `load_error` (Ausnahme → Art, Meldung, JSON-Pfad), `repair_catalogs` (über `System.from_json`/`save`); `TraceOptions` und `trace_wavefront` (G2-T1, Ergebnis als picklebare `WavefrontResult` mit NumPy-Arrays); `EvalOptions`, `evaluate` und `mm_to_waves` (G2-T2, Umrechnung genau wie `mikroptim eval`); `PsfOptions`, `VectorOptions`, `scalar_psf`, `vector_psf` (über `run_cli` mit temporären CSV-Dateien) und `window_warning` (Regel von `mikroptim eval`) mit Ergebnis `PsfResult` (G2-T3) |
| `backend/system_tables.py` | G1-T2, G2-T1 | Tabellenzeilen aus `System` und `system_to_dict` (Flächen, Spektrum, Felder, Paraxialdaten, Variablen) aus der Wellenfront (`wavefront_rows`, wie `trace --json`) und aus EVAL (`eval_rows`, wie `tuples` von `eval --json`), Zahlenformat mit ∞/NaN |

## Seiten

| Seite | Datei | Meilenstein | Rechnet im Streamlit-Prozess? |
|---|---|---|---|
| Start | `pages/start.py` | G0 | nein (nur Status) |
| System | `pages/system.py` | G1 | Laden und Paraxialdaten (Millisekunden) |
| Auswertung | `pages/auswertung.py` | G2 | Reiter „Wellenfront“ (`trace`), „OPD und Spots“ (`evaluate`), „PSF und MTF“ (`Evaluation.psf`, vektoriell über die CLI bis Raster 256) und „Vergleich“ (`trace` für zwei Systeme), Millisekunden bis Sekunden je nach Raster |
| Optimierung | `pages/optimierung.py` | G3 | `optimize` mit Rückruf (Sekunden bis Minuten, mit Abbruch) |
| Jobs und Synthese | `pages/synthese.py` | G4-T1, G4-T2 | nein: liest Protokolle, zeigt und steuert Jobs |

## Zustand und Cache

Streamlit führt das Seitenskript bei jeder Interaktion neu aus. Daraus folgen feste Regeln:

- **Einstellungen und Mikroptim-Status** sind `st.cache_resource` (einmal pro Serverprozess, Knopf „Neu prüfen“ leert den Status).
- **Geladene Systeme und Rechenergebnisse** sind `st.cache_data`. Der Schlüssel enthält den aufgelösten Pfad, die Änderungszeit und die Größe der Datei sowie alle Rechenoptionen (Ringe, Speichen, Raster, GPU, Genauigkeit). Eine geänderte Datei wird so nie mit altem Ergebnis gezeigt.
- Objekte aus Mikroptim (`System`, `Wavefront`, …) sind nanobind-Objekte. Gecacht werden die daraus gewonnenen NumPy-Arrays und Zahlen, nicht die Objekte selbst; nur `System` darf als Ressource gecacht werden, weil es unveränderlich ist.
- **Auswahl des Nutzers** (gewählte Datei, Feld, Wellenlänge) liegt in `st.session_state` unter Schlüsseln mit Seitenpräfix, z. B. `system.quelle`, `auswertung.feld`. Die gewählte Systemdatei ist seitenübergreifend `aktuell.datei` (`views/current.py`). Sie ist ein eigener Schlüssel und kein Widget-Zustand, weil Streamlit Widget-Zustände von nicht angezeigten Seiten verwirft.
- **Seitenleiste:** Die Zeile „Aktuelles System“ wird nach dem Lauf der Seite gefüllt (Platzhalter in `app.py`), damit eine neue Auswahl sofort erscheint.
- **Tests:** `AppTest.switch_page` führt nur das Seitenskript aus, nicht den Einstieg `app.py`; die Seitenleiste wird deshalb über einen normalen Lauf des Einstiegs getestet.
- Der Streamlit-Prozess wird von allen Browsersitzungen geteilt. GPU-Rechnungen im Prozess sind kurz zu halten; was länger dauert, wird ein Job.

## Jobs (G4-T1)

Lange Läufe laufen als eigene Prozesse (ADR-0003), umgesetzt in `backend/jobs.py` und dem Wrapper `backend/job_runner.py`.

```mermaid
sequenceDiagram
    participant S as Seite (Streamlit)
    participant J as backend/jobs.py
    participant W as Wrapper (job_runner)
    participant B as Befehl (z. B. mikroptim synth)
    S->>J: submit(kind, argv, inputs)
    J->>J: Jobordner, eingabe/ kopieren, job.json (wartend)
    J->>J: start_pending: Sperre, freie Plätze zählen, .gestartet anlegen
    J->>W: Popen, eigene Sitzung/Prozessgruppe
    W->>W: job.json: läuft, pid, started
    W->>B: Popen im Jobordner, stdout/stderr → ausgabe.txt/fehler.txt
    loop alle 0,2 s
        W->>W: .abbrechen vorhanden? → Prozessbaum beenden
    end
    W->>W: job.json: fertig/fehler/abgebrochen, exit_code, finished
    W->>J: start_pending (nächster wartender Job)
    S->>J: list_jobs / load (Status, Ausgabe), cancel → .abbrechen
```

**Ablage** pro Job `jobs/<JJJJMMTT-hhmmss>-<art>[-n]/`:

| Datei | geschrieben von | Inhalt |
|---|---|---|
| `job.json` | Anlage, danach nur der Wrapper | Beschreibung `gui-mikroptim.job/1` (unten) |
| `eingabe/` | Anlage | Kopien der Eingaben; Systemdateien über eine Kopierfunktion (z. B. Mikroptim `System.save`), damit Glaskataloge vom Jobordner aus gefunden werden |
| `ausgabe.txt`, `fehler.txt` | Wrapper | stdout und stderr des Befehls |
| `.gestartet` | Starter (mit `O_EXCL`) | verhindert doppelten Start; „wartend“ mit dieser Datei wird als „läuft (startet)“ angezeigt |
| `.abbrechen` | Oberfläche | Abbruchwunsch; der Wrapper beendet den Befehl samt Kindprozessen (POSIX: eigene Prozessgruppe, SIGTERM, nach 5 s SIGKILL; Windows: `taskkill /T /F`) |
| `.wrapper.txt` | Wrapper | Ausgaben des Wrappers selbst (Fehlersuche) |

Die Sperre `jobs/.sperre` (mit `O_EXCL` angelegt, nach 30 s verwaist) schützt Zählen und Starten, sodass nie mehr als `MKO_GUI_MAX_JOBS` Jobs laufen. Wartende Jobs starten in der Reihenfolge der Anlage (`created_ns`), entweder vom Wrapper eines endenden Jobs (die Warteschlange läuft also ohne offene Oberfläche weiter) oder beim Anzeigen der Jobliste.

**Unabhängig von der Oberfläche:** Der Wrapper läuft in einer eigenen Sitzung (POSIX `start_new_session`) bzw. Prozessgruppe ohne Konsole (Windows `CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS`); ein Neustart von Streamlit oder des systemd-Dienstes (`KillMode=process`) beendet laufende Jobs nicht.

**Status**, wie die Oberfläche ihn zeigt (`jobs.effective_status`): `status` aus `job.json`; „läuft“ mit nicht mehr vorhandenem Wrapper-Prozess wird zu „fehler“ (z. B. nach einem Neustart des Rechners), „wartend“ mit `.gestartet` zu „läuft (startet)“ und nach 60 s ohne Meldung des Wrappers zu „fehler“.

Format `gui-mikroptim.job/1` (`job.json`):

| Feld | Bedeutung |
|---|---|
| `format` | `"gui-mikroptim.job/1"` |
| `id` | Name des Jobordners |
| `kind` | Art: `synth`, `eval`, `optimize`, …; kleingeschrieben, Teil des Ordnernamens |
| `argv` | vollständige Argumentliste, wie gestartet (im Jobordner von Hand wiederholbar) |
| `inputs`, `sources` | kopierte Eingaben (relativ zum Jobordner) und ihre Herkunft |
| `options` | Optionen und Seed des Laufs, zur Anzeige und Nachvollziehbarkeit |
| `mikroptim_version` | Version beim Anlegen |
| `created`, `created_ns`, `started`, `finished` | Zeitpunkte (ISO 8601, UTC; `created_ns` für die Reihenfolge) |
| `pid` | Prozess-ID des Wrappers |
| `exit_code` | Exit-Code des Befehls (`null` solange laufend, negativ bei Signal) |
| `status` | `wartend`, `läuft`, `fertig`, `fehler`, `abgebrochen` |
| `error` | nur wenn der Befehl nicht starten konnte |

Mikroptim-Befehle baut `jobs.mikroptim_argv`: das Programm `mikroptim` (`MKO_GUI_CLI`, fortlaufende Ausgabe) oder `python -m mikroptim`.

## Fehlerbehandlung

- Ausnahmen von Mikroptim (`FormatError` mit `json_path`, `GlassError`, `GpuUnavailableError`, `CudaError`) werden auf der Seite mit `st.error` gezeigt, mit JSON-Pfad, wenn vorhanden. Die App stürzt nicht ab.
- Ohne Mikroptim laufen alle Seiten und zeigen einen Hinweis; das prüfen die App-Tests (`tests/test_app.py`).
