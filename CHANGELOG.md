# Changelog

Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionierung nach [SemVer](https://semver.org/lang/de/).

## [Unreleased]

### Hinzugefügt
- G0: Projektgerüst. Paket `gui_mikroptim` (src-Layout, `pyproject.toml`, Python ≥ 3.10), Startprogramm `gui-mikroptim` (bindet an 127.0.0.1), Konfiguration über Umgebungsvariablen (`gui_mikroptim.config`), sicherer Dateizugriff im Arbeitsbereich (`backend.files`), Erkennen und Lesen der JSON-Formate von Mikroptim (`backend.protocols`, u. a. `mikroptim.synth/1` mit Schritten und Kandidaten-Stammbaum), Statusabfrage von Mikroptim ohne harte Abhängigkeit (`backend.mko`), Streamlit-App mit Navigation, Startseite (Status von Mikroptim, GPUs, Arbeitsbereich) und Platzhalterseiten für G1–G4; Tests (pytest, Streamlit `AppTest`), Integrationstests gegen ein installiertes Mikroptim (Marker `integration`); CI (ruff, pytest auf Linux und Windows, Integration mit dem CPU-Wheel aus Mikroptim `main`); Dokumentation, ADR-0001 bis ADR-0005, Meilensteinplan, Vorlagen für PRs und Issues, systemd-Vorlage.
