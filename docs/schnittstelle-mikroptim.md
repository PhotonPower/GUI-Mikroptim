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
| `trace(system, rings, spokes, gpu, device, precision)` → `Wavefront` | G2-T1 | RMS pro Feld und Wellenlänge, versagte Strahlen |
| `evaluate(system, grid, half, reference, gpu, …)` → `Evaluation` | G2-T2 | `stats`, `opd_map`, `spots`, `pupil_points` |
| `Evaluation.psf(f, l, padding, numerical_aperture, gpu)` → `Psf` | G2-T3 | PSF, MTF-Schnitte, Strehl |
| `optimize(system, …, jacobian, callback)` → `OptimizeResult` | G3 | Optimierung mit Live-Verlauf; `result.system.save(path)` |
| `run_cli(args)` / `python -m mikroptim` | G2-T3, G4 | Unterbefehle ohne Bindung (`synth`, `insert`, `snap`, `eval --vector`) |

Ausnahmen: `FormatError` (mit `json_path`, `message`, `file`), `GlassError`, `GpuUnavailableError`, `CudaError`, `FileNotFoundError`, `ValueError`. Ein nicht gefundener Glaskatalog ist ein `FormatError` mit `json_path` `glass_catalogs[i]`; Mikroptim sucht relative Katalogpfade ab dem Verzeichnis der Datei aufwärts (`resolve_glass_catalogs`).

## Kommandozeile (Referenz: Mikroptim `docs/cli.md`)

Jobs rufen die CLI auf, entweder das Programm `mikroptim` (`MKO_GUI_CLI`) oder `python -m mikroptim`. Das Programm ist für lange Läufe vorzuziehen: `python -m mikroptim` gibt die Ausgabe erst am Ende aus, das Programm schreibt fortlaufend.

| Unterbefehl | genutzt in | Ausgabe, die die GUI liest |
|---|---|---|
| `synth … --log <datei> [--dot <datei>]` | G4-T3 | `mikroptim.synth/1`, DOT |
| `optimize … --json -o <datei>` | G4 (als Job) | `mikroptim.optimize/1`, Systemdatei |
| `eval … --json --psf --vector` | G2-T3 | `mikroptim.eval/1` |
| `snap`, `insert` | G4 | `mikroptim.snap/1`, Systemdatei |

## Dateiformate

Gelesen werden die Formate aus `backend/protocols.py` (`KNOWN_FORMATS`), Hauptversion 1. Eine neue Hauptversion eines Formats wird abgelehnt, bis die GUI angepasst ist; neue Felder einer Nebenversion werden ignoriert.

## Wünsche an Mikroptim

Was die GUI braucht, aber nicht selbst rechnen darf. Jeder Punkt wird bei Bedarf eine Aufgabe im Mikroptim-Plan (Maintainer entscheidet).

| Nr. | Wunsch | Wofür | Stand |
|---|---|---|---|
| W1 | Strahlpfade: Schnittpunkte ausgewählter Strahlen (Randstrahlen, Hauptstrahl pro Feld) mit allen Flächen, z. B. `trace_rays(system, field, wavelength, pupil_coords)` → (Strahlen, Flächen, 3) und Status | Strahlen im Linsenschnitt (G1-T3) | offen; bis dahin Linsenschnitt nur mit Flächen |
| W2 | Fortlaufendes Protokoll von `synth` (z. B. eine JSON-Zeile pro Schritt mit `--log-jsonl`), oder `synth` in der Python-API mit Rückruf | Live-Fortschritt von Synthese-Jobs (G4) | offen; bis dahin Textausgabe des Programms mitlesen |
| W3 | Bindungen für `synth`, `insert`, `snap` und die vektorielle PSF | Aufrufe ohne CLI-Umweg | offen (in M9-T1 als Grenze genannt) |
| W4 | Nebenbedingungsberichte und Geisterdiagnose in `OptimizeResult` | Optimierungsseite (G3-T3) | offen (in M9-T1 als Grenze genannt); Umweg: `optimize --json` als Job |
| W5 | Abbruch einer laufenden `optimize`-Rechnung | Knopf „Abbrechen“ (G3-T2) | erfüllt: Ausnahme im `callback` bricht ab (M9-T1) |
| W6 | Linux-Wheels als manylinux bzw. veröffentlichte Wheels | Installation auf dem Server ohne Compiler | offen, nicht dringend |
