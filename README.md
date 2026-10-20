# GUI-Mikroptim

Streamlit-Oberfläche für [Mikroptim](https://github.com/PhotonPower/Mikroptim), den GPU-beschleunigten Raytracer und Systemsynthese-Optimierer für hochaperturige Mikroskopobjektive.

Die GUI ist ein **Test- und Auswertecockpit** für den Server, auf dem Mikroptim läuft: Systemdateien ansehen, Wellenfront, OPD-Karten, Spots, PSF/MTF und Strehl auswerten, Optimierungen starten und verfolgen, Synthese-Läufe als Jobs starten und ihre Protokolle durchsehen. Sie ist **kein** Linsen-Entwurfsprogramm und enthält keine eigene Optik: Gerechnet wird ausschließlich in Mikroptim, über dessen Python-API (`import mikroptim`) und Kommandozeile ([ADR-0002](docs/adr/0002-nur-oeffentliche-api.md)).

## Status

G0 (Gerüst), G4-T2 (Protokollbrowser für Synthese-Läufe) und G1-T1 (Dateiauswahl mit Upload, aktuelles System) G1-T2 (Systemtabellen und Paraxialdaten, Reparatur der Glaskatalog-Pfade) und G1-T3 (Linsenschnitt) abgeschlossen, damit ist G1 fertig; dazu G2 (Seite „Auswertung“: RMS-Wellenfront, OPD-Karten, Spotdiagramme, PSF, MTF, Strehl und Vergleich zweier Systeme) G4-T1 (Jobverwaltung für lange Läufe), G4-T3 (Synthese als Job mit Formular) G3 (Seite „Optimierung“: Variablen, Optionen, Lauf mit Live-Verlauf, Vorher/Nachher und Speichern). G0: Paketstruktur, Konfiguration, sicherer Dateizugriff im Arbeitsbereich, Lesen der Mikroptim-Protokolle, Startseite mit Status von Mikroptim und GPUs, Platzhalterseiten, Tests, CI, Dokumentation. Die Funktionsseiten folgen nach dem [Meilensteinplan](docs/plan/meilensteine.md): G1 System, G2 Auswertung, G3 Optimierung, G4 Jobs und Synthese, G5 Betrieb.

## Schnellstart

Voraussetzungen: Python ≥ 3.10 und ein installiertes Mikroptim-Wheel (Bau siehe [Mikroptim, python/README.md](https://github.com/PhotonPower/Mikroptim/blob/main/python/README.md)). Ohne Mikroptim startet die GUI trotzdem und zeigt auf der Startseite, was fehlt.

```bash
git clone https://github.com/PhotonPower/GUI-Mikroptim.git
cd GUI-Mikroptim
python -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"

# Mikroptim-Wheel aus dem Mikroptim-Checkout bauen und installieren (CPU; CUDA siehe docs/betrieb.md)
(cd ../Mikroptim && python -m pip wheel . -w dist --no-deps)
python -m pip install --no-index --find-links ../Mikroptim/dist mikroptim

# Starten (bindet nur an 127.0.0.1:8501)
export MKO_GUI_MIKROPTIM_REPO=../Mikroptim     # optional: Beispielsysteme und Glaskataloge
gui-mikroptim
```

Auf dem Server wird die GUI nur lokal gebunden und per SSH-Tunnel geöffnet:

```bash
ssh -L 8501:127.0.0.1:8501 benutzer@server
# danach im Browser: http://localhost:8501
```

Konfiguration, CUDA-Wheel, systemd-Dienst und Sicherheit: [docs/betrieb.md](docs/betrieb.md).

## Dokumentation

| Dokument | Inhalt |
|---|---|
| [docs/architektur.md](docs/architektur.md) | Schichten, Seiten, Datenfluss, Zustand, Jobs |
| [docs/schnittstelle-mikroptim.md](docs/schnittstelle-mikroptim.md) | Genutzte Mikroptim-Funktionen, Versionen, Wünsche an Mikroptim |
| [docs/bedienung.md](docs/bedienung.md) | Bedienung der Seiten |
| [docs/betrieb.md](docs/betrieb.md) | Installation auf dem Server, Konfiguration, SSH-Tunnel, systemd |
| [docs/plan/meilensteine.md](docs/plan/meilensteine.md) | Aufgaben mit Abhängigkeiten und Abnahmekriterien |
| [docs/adr/](docs/adr/) | Architekturentscheidungen |
| [AGENTS.md](AGENTS.md) | Verbindliche Regeln für Programmieragenten |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Ablauf für Mitarbeit |

## Entwicklung

```bash
python -m pip install -e ".[dev]"
ruff check . && ruff format --check .
python -m pytest                      # ohne Mikroptim werden die Integrationstests übersprungen
python -m pytest -m integration       # nur Integrationstests (Mikroptim installiert)
streamlit run src/gui_mikroptim/app.py --server.address 127.0.0.1
```

## Lizenz

MIT, siehe [LICENSE](LICENSE).
