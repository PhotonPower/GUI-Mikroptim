# Schnittstelle zu Mikroptim

Die GUI nutzt Mikroptim nur über die öffentliche Python-API und die Kommandozeile (ADR-0002). Diese Seite listet, was genau genutzt wird. Wer eine neue Funktion von Mikroptim verwendet, trägt sie hier ein.

## Version

| | |
|---|---|
| Mindestversion | 0.1.0 (`MIN_MIKROPTIM_VERSION` in `backend/mko.py`) |
| Getestet gegen | Mikroptim `main` (CI-Job „Integration“, CPU-Wheel) |
| Prüfung | `backend.mko.status()`: Import, Version, alle Namen aus `REQUIRED_NAMES` |

Mikroptim hat noch keine Releases. Bis dahin gilt: Die CI baut bei jedem Lauf das Wheel aus Mikroptim `main`; bricht die Integration, ist entweder die GUI anzupassen oder in Mikroptim eine Änderung der API zu klären. Sobald Mikroptim Versionen markiert, wird hier eine getestete Version festgehalten und die CI zusätzlich gegen diese gebaut.

## Python-API (Referenz: Mikroptim `python/README.md`)

| Name | genutzt in | Zweck |
|---|---|---|
| `__version__`, `has_cuda`, `device_count()`, `devices()` | G0 Start | Status, Geräteliste (`index`, `name`, `total_bytes`, `free_bytes`) |
| `load_system(path)` → `System` | G1-T2 | Systemdatei samt Glaskatalogen laden |
| `System`-Eigenschaften `name`, `description`, `file`, `num_surfaces`, `num_ghost_plates`, `surface_types`, `curvatures`, `thicknesses`, `semi_diameters`, `materials`, `indices` (S, L), `wavelengths_nm`, `wavelength_weights`, `reference_nm`, `field_angles_deg`, `field_weights`, `source_type`, `target`, `warnings`, `catalog_files` | G1-T2 | Tabellen, Kennzahlen |
| `System.variables()` | G1-T2 | Variablentabelle; wirft `ValueError` bei Glasvariablen auf Katalog-Gläsern (die GUI zeigt dann den Abschnitt der Datei) |
| `System.from_json(text, base_dir)`, `System.save(path)` | G1-T2 | Glaskatalog-Pfade hochgeladener Dateien reparieren (`save` passt `glass_catalogs` an den neuen Ort an) |
| `system_to_dict` | G1-T2, G3 | Materialmodelle, Dezentrierung/Verkippung, Kommentare, `constraints`, `ghost_plates`, JSON-Ansicht |
| `paraxial(system)` → `Paraxial.to_dict()` | G1-T2 | Paraxialdaten; bei afokalen Systemen `afocal: true` und Brennweite/Schnittweiten `None` (wie die CLI) |
| `trace(system, rings, spokes, gpu, device, precision)` → `Wavefront` | G2-T1 | `rms_waves` (Wellen bei λ_ref), `rms_mm`, `piston_mm`, `rays`, `failed` [Feld, Wellenlänge]; `image_points`, `pupil_modes`, `wavelengths_nm`, `reference_nm`, `target_focal_length`, `backend`, `device_name`, `precision`, `rings`, `spokes`. Fehler: `ValueError` bei afokalen Systemen ohne `target.focal_length` und bei `precision="df64"` ohne GPU, `GpuUnavailableError` ohne CUDA/Gerät. Bitgleich zu `mikroptim trace --json` (Integrationstest, vier Systeme) |
| `evaluate(system, grid, half, reference, gpu, device)` → `Evaluation` | G2-T2 | `stats` (Arrays [Feld, Wellenlänge], OPD in mm, Verzeichnung in %), `opd_map(f, l, remove)` (mm, Zeile j = y, NaN außerhalb), `spots(f, l)` (`x`, `y` in mm relativ zum idealen Bildpunkt, `status`), `grid`, `grid_points`, `half_pupil`, `exit_pupil_position`, `failed_rays`, `reference_nm`, `backend`. Bitgleich zu `mikroptim eval --json` mit OPD in Wellen = mm / (λ_ref · 10⁻⁶) und zur CSV von `--map` (Integrationstests). Die Maréchal-Strehl-Zahl der CLI ist nicht in `stats` und wird in der GUI nicht nachgerechnet |
| `Evaluation.psf(f, l, padding, numerical_aperture, gpu, device)` → `Psf` | G2-T3 | `psf` [M, M] in Strehl-Einheiten (Zeile j = y, Bildpunkt bei M/2), `dx`, `dy`, `fft_size`, `frequencies()` (ν = f/f_c), `mtf_sagittal`, `mtf_tangential`, `cutoff_x`/`_y` (lp/mm), `na_x`/`_y`, `airy_radius`, `strehl`, `strehl_fft`, `strehl_origin`, `peak`, `peak_position`, `energy`. Bitgleich zu `eval --psf --json` (MTF bei f_c/2 = Stützstelle ν = 0,5) und zu `--psf-file`/`--mtf-file` (Integrationstests) |
| `optimize(system, …, jacobian, callback)` → `OptimizeResult` | G3 | Optimierung mit Live-Verlauf; `result.system.save(path)` |
| `run_cli(args)` / `python -m mikroptim` | G2-T3, G4 | Unterbefehle ohne Bindung (`synth`, `insert`, `snap`, `eval --vector`) |

Ausnahmen: `FormatError` (mit `json_path`, `message`, `file`), `GlassError`, `GpuUnavailableError`, `CudaError`, `FileNotFoundError`, `ValueError`. Ein nicht gefundener Glaskatalog ist ein `FormatError` mit `json_path` `glass_catalogs[i]`; Mikroptim sucht relative Katalogpfade ab dem Verzeichnis der Datei aufwärts (`resolve_glass_catalogs`).

## Kommandozeile (Referenz: Mikroptim `docs/cli.md`)

Jobs rufen die CLI auf, entweder das Programm `mikroptim` (`MKO_GUI_CLI`) oder `python -m mikroptim`. Das Programm ist für lange Läufe vorzuziehen: `python -m mikroptim` gibt die Ausgabe erst am Ende aus, das Programm schreibt fortlaufend.

| Unterbefehl | genutzt in | Ausgabe, die die GUI liest |
|---|---|---|
| `synth <start> [Optionen] -o ergebnis.json --log protokoll.json [--dot stammbaum.dot]` | G4-T3 | Systemdatei, `mikroptim.synth/1`, DOT; Optionen und Standardwerte aus `docs/cli.md` in `synth_job.SynthOptions`. Integrationstest: Job und Lauf von Hand mit dem gespeicherten Befehl ergeben dasselbe Protokoll (ohne `seconds`) |
| `System.save(path)` | G4-T3 | Startsystem in den Jobordner kopieren, Glaskatalog-Pfade relativ zur Kopie |
| `optimize … --json -o <datei>` | G4 (als Job) | `mikroptim.optimize/1`, Systemdatei |
| `eval … --json --psf --vector --polarization P --defocus Z --psf-tuple F,L --psf-file … --mtf-file … --component-files …` | G2-T3 | `mikroptim.eval/1` (Feld `vector`), PSF-, MTF- und Komponenten-CSV (erste Zeile = größtes y) |
| `snap`, `insert` | G4 | `mikroptim.snap/1`, Systemdatei |

## Dateiformate

Gelesen werden die Formate aus `backend/protocols.py` (`KNOWN_FORMATS`), Hauptversion 1. Eine neue Hauptversion eines Formats wird abgelehnt, bis die GUI angepasst ist; neue Felder einer Nebenversion werden ignoriert.

## Wünsche an Mikroptim

Was die GUI braucht, aber nicht selbst rechnen darf. Jeder Punkt wird bei Bedarf eine Aufgabe im Mikroptim-Plan (Maintainer entscheidet).

| Nr. | Wunsch | Wofür | Stand |
|---|---|---|---|
| W1 | Strahlpfade: Schnittpunkte ausgewählter Strahlen (Randstrahlen, Hauptstrahl pro Feld) mit allen Flächen, z. B. `trace_rays(system, field, wavelength, pupil_coords)` → (Strahlen, Flächen, 3) und Status | Strahlen im Linsenschnitt (G1-T3) | offen; bis dahin Linsenschnitt nur mit Flächen |
| W2 | Fortlaufendes Protokoll von `synth` (z. B. eine JSON-Zeile pro Schritt mit `--log-jsonl`), oder `synth` in der Python-API mit Rückruf | Live-Fortschritt von Synthese-Jobs (G4) | offen; bis dahin Textausgabe des Programms mitlesen |
| W3 | Bindungen für `synth`, `insert`, `snap` und die vektorielle PSF | Aufrufe ohne CLI-Umweg | offen (in M9-T1 als Grenze genannt); die vektorielle PSF läuft bis dahin über `run_cli` mit temporären CSV-Dateien (G2-T3) |
| W4 | Nebenbedingungsberichte und Geisterdiagnose in `OptimizeResult` | Optimierungsseite (G3-T3) | offen (in M9-T1 als Grenze genannt); Umweg: `optimize --json` als Job |
| W5 | Abbruch einer laufenden `optimize`-Rechnung | Knopf „Abbrechen“ (G3-T2) | erfüllt: Ausnahme im `callback` bricht ab (M9-T1) |
| W6 | Linux-Wheels als manylinux bzw. veröffentlichte Wheels | Installation auf dem Server ohne Compiler | offen, nicht dringend |
| W7 | Warnungen der Auswertung in der Python-API (`Evaluation.warnings` bzw. pro `Psf`), insbesondere „Bildfenster zu klein“ | PSF-Reiter (G2-T3) | offen; bis dahin bildet `compute.window_warning` die Regel von `psf_window_warnings` nach (Integrationstest: gleiche Tupel, gleiche Zahlen wie die CLI) |
| W8 | `strehl_marechal` in `Evaluation.stats` wie in `eval --json` | Kennzahlentabelle (G2-T2) | offen; die GUI zeigt den Wert bis dahin nicht |
