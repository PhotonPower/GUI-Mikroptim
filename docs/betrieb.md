# Betrieb auf dem Server

## Voraussetzungen

- Linux-Server mit dem Mikroptim-Build (für GPU: CUDA 12.x, siehe Mikroptim `docs/hardware.md`)
- Python ≥ 3.10, eine eigene virtuelle Umgebung für die GUI
- SSH-Zugang für alle Nutzer der GUI

## Installation

```bash
cd ~/src
git clone https://github.com/PhotonPower/GUI-Mikroptim.git
git clone https://github.com/PhotonPower/Mikroptim.git      # falls noch nicht vorhanden

python3 -m venv ~/venvs/gui-mikroptim
source ~/venvs/gui-mikroptim/bin/activate
python -m pip install -e ~/src/GUI-Mikroptim
```

### Mikroptim ins selbe venv

Nur CPU:

```bash
cd ~/src/Mikroptim
python -m pip wheel . -w dist --no-deps
python -m pip install --no-index --find-links dist mikroptim
```

### Mikroptim mit CUDA

```bash
cd ~/src/Mikroptim
MIKROPTIM_ENABLE_CUDA=ON python -m pip wheel . -w dist --no-deps -C build-dir=build/wheel-cuda
python -m pip install --force-reinstall --no-index --find-links dist mikroptim
```

Das CUDA-Wheel braucht zur Laufzeit cudart und cuFFT des Toolkits (Mikroptim `python/README.md`). Danach zeigt die Startseite die GPUs. Nach jedem Update von Mikroptim das Wheel neu bauen und die GUI neu starten (der Status wird pro Serverprozess gecacht).

Für Jobs ist zusätzlich das Programm `mikroptim` aus dem CMake-Build sinnvoll (fortlaufende Ausgabe, siehe docs/schnittstelle-mikroptim.md):

```bash
cmake --preset release-cuda && cmake --build --preset release-cuda
export MKO_GUI_CLI=~/src/Mikroptim/build/release-cuda/mikroptim
```

## Konfiguration

Alle Einstellungen über Umgebungsvariablen (`gui_mikroptim/config.py`):

| Variable | Standard | Bedeutung |
|---|---|---|
| `MKO_GUI_WORKSPACE` | `arbeitsbereich/` im Checkout | Einziges Verzeichnis, in das die GUI schreibt (`uploads/`, `ergebnisse/`, `jobs/`, `kataloge/` für hochgeladene Glaskataloge, ADR-0006). Auf dem Server außerhalb des Checkouts, z. B. `~/gui-mikroptim-daten`. |
| `MKO_GUI_MIKROPTIM_REPO` | – | Mikroptim-Checkout; liefert die Beispielsysteme (`data/systems`) und Glaskataloge. Wird nur gelesen. |
| `MKO_GUI_CLI` | – | Programm `mikroptim` für Jobs (Pfad oder Name im `PATH`); ohne: `python -m mikroptim` |
| `MKO_GUI_MAX_JOBS` | `1` | höchstens gleichzeitig laufende Jobs |

Streamlit-Einstellungen stehen in `.streamlit/config.toml` (Bindung, Upload-Grenze 20 MB, keine Telemetrie).

## Starten

```bash
source ~/venvs/gui-mikroptim/bin/activate
export MKO_GUI_WORKSPACE=~/gui-mikroptim-daten
export MKO_GUI_MIKROPTIM_REPO=~/src/Mikroptim
gui-mikroptim                       # 127.0.0.1:8501
gui-mikroptim --server.port 8502    # anderer Port, z. B. eine zweite Instanz
```

`gui-mikroptim` bindet immer an `127.0.0.1` und lehnt `--server.address` ab (ADR-0004).

## Zugriff per SSH-Tunnel

Auf dem eigenen Rechner:

```bash
ssh -N -L 8501:127.0.0.1:8501 benutzer@server
```

Dann im Browser `http://localhost:8501` öffnen. Unter Windows geht das mit dem eingebauten OpenSSH genauso (PowerShell), in PuTTY unter *Connection → SSH → Tunnels* (Source port 8501, Destination 127.0.0.1:8501). Dauerhaft in `~/.ssh/config`:

```
Host mikroptim-gui
    HostName server
    User benutzer
    LocalForward 8501 127.0.0.1:8501
```

## Als Dienst (systemd, Benutzerdienst)

Vorlage: [`deploy/gui-mikroptim.service`](../deploy/gui-mikroptim.service).

```bash
mkdir -p ~/.config/systemd/user ~/.config/gui-mikroptim
cp ~/src/GUI-Mikroptim/deploy/gui-mikroptim.service ~/.config/systemd/user/
cp ~/src/GUI-Mikroptim/deploy/gui-mikroptim.env ~/.config/gui-mikroptim/env   # Pfade anpassen
systemctl --user daemon-reload
systemctl --user enable --now gui-mikroptim
loginctl enable-linger "$USER"      # Dienst läuft auch ohne angemeldete Sitzung
journalctl --user -u gui-mikroptim -f
```

Jobs laufen in eigenen Sitzungen bzw. Prozessgruppen (docs/architektur.md, „Jobs“); zusammen mit `KillMode=process` beendet ein Neustart oder Stopp des Dienstes keinen laufenden Synthese-Lauf. Wartende Jobs startet der Wrapper eines endenden Jobs, auch wenn die GUI gerade nicht läuft. Ein Neustart des Rechners bricht laufende Jobs dagegen ab; sie erscheinen danach als „fehler“ mit Hinweis.

## Sicherheit

- Die GUI hat **keine Anmeldung**. Schutz entsteht ausschließlich dadurch, dass sie nur an `127.0.0.1` lauscht und der Zugang über SSH läuft (ADR-0004). Wer auf dem Server angemeldet ist, kann die GUI erreichen; auf Mehrbenutzerservern deshalb eigene Ports pro Nutzer und einen eigenen Arbeitsbereich.
- Nicht über einen Reverse-Proxy ins Netz stellen, ohne zuerst eine neue ADR mit Authentifizierung.
- Geheimnisse (Tokens) gehören nicht in Umgebungsdateien im Repository; `.streamlit/secrets.toml` ist ignoriert, wird aber derzeit nicht gebraucht.
- Die GUI schreibt nur in den Arbeitsbereich. Der Mikroptim-Checkout kann für den Dienstbenutzer schreibgeschützt sein.

## Fehlersuche

| Symptom | Ursache und Abhilfe |
|---|---|
| Startseite: „ModuleNotFoundError: No module named 'mikroptim'“ | Wheel nicht im selben venv installiert. `python -c "import mikroptim"` im venv prüfen. |
| Startseite: „ImportError … libcudart“ | CUDA-Wheel ohne Laufzeitbibliotheken; `LD_LIBRARY_PATH` auf `…/cuda-12.x/lib64` setzen (auch in der env-Datei des Dienstes). |
| „CUDA-Build, aber kein nutzbares Gerät“ | Treiber, `CUDA_VISIBLE_DEVICES`, Karte unter sm_60. `mikroptim --devices` prüfen. |
| GPU-Speicher knapp | Andere Prozesse (Agenten, Jobs) belegen die Karte; die Startseite zeigt den freien Speicher. |
| Job bleibt „läuft (startet)“ und wird nach 60 s „fehler“ | Der Wrapper konnte nicht starten; `.wrapper.txt` im Jobordner lesen (meist falsches venv oder fehlendes Paket). |
| Browser: Verbindung abgelehnt | Tunnel nicht offen oder anderer Port; `ss -ltnp | grep 8501` auf dem Server. |
