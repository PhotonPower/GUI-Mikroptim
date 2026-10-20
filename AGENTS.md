# AGENTS.md – Arbeitsanweisung für Programmieragenten

Diese Datei ist verbindlich für alle Agenten, die an GUI-Mikroptim arbeiten. Bei Widerspruch zwischen dieser Datei und anderen Dokumenten gilt: ADRs in `docs/adr/` > AGENTS.md > übrige Doku. Unklarheiten, die eine der Entscheidungen unter „Nicht selbst entscheiden“ berühren, werden als Frage an den Maintainer im PR formuliert, nicht still aufgelöst.

## 1. Worum es geht

GUI-Mikroptim ist eine Streamlit-Oberfläche, mit der man [Mikroptim](https://github.com/PhotonPower/Mikroptim) auf dem Rechenserver bequem testet: Systeme ansehen, auswerten, optimieren, Synthese-Läufe starten und ihre Protokolle verstehen. Nutzer sind der Maintainer und wenige Mitarbeiter, Zugang nur über SSH-Tunnel.

Die GUI ist eine **dünne Schicht**. Jede Zahl, die sie anzeigt, kommt aus Mikroptim. Die GUI rechnet keine Optik (kein Raytracing, keine Paraxialformeln, keine OPD, keine Merit), sondern stellt dar, startet und verwaltet (ADR-0002).

## 2. Lesereihenfolge vor jeder Aufgabe

1. `README.md`
2. diese Datei
3. `docs/plan/meilensteine.md` – deine Aufgabe, ihre Abhängigkeiten und Abnahmekriterien
4. `docs/architektur.md` und `docs/schnittstelle-mikroptim.md`
5. alle ADRs in `docs/adr/` (kurz, bitte vollständig lesen)
6. Für fachliche Begriffe: `python/README.md`, `docs/cli.md` und `docs/glossar.md` im Mikroptim-Repository. Einheiten und Konventionen von dort übernehmen, nicht neu erfinden.

## 3. Arbeitsweise

- **Eine Aufgabe = ein Branch = ein PR.** Branchname `g<M>/t<N>-<kurzname>`. Aufgaben nur beginnen, wenn ihre Abhängigkeiten gemergt sind.
- **Tests zuerst denken.** Jedes Abnahmekriterium wird durch einen automatisierten Test belegt (pytest, Streamlit `AppTest`) oder, wo nur ein Mensch urteilen kann (Optik einer Darstellung), durch Screenshots im PR.
- **Klein bleiben.** Keine Arbeit an Folgeaufgaben „nebenbei“. Gefundene Probleme außerhalb der Aufgabe als Notiz im PR auflisten.
- **Doku mitziehen.** Neue Seiten in `docs/bedienung.md`, neue Mikroptim-Aufrufe in `docs/schnittstelle-mikroptim.md`, neue Einstellungen in `docs/betrieb.md`. `CHANGELOG.md` unter „Unreleased“ ergänzen.
- **PR-Vorlage vollständig ausfüllen**, jedes Abnahmekriterium mit Ergebnis (Testname, Screenshot) auflisten.

## 4. Bauen und Testen

```bash
python -m pip install -e ".[dev]"
ruff check . && ruff format --check .
python -m pytest                     # Einheiten- und App-Tests, ohne Mikroptim lauffähig
python -m pytest -m integration      # braucht ein installiertes Mikroptim-Wheel und MKO_GUI_MIKROPTIM_REPO
```

Die CI hat keine GPU. GPU-Pfade (Schalter „GPU“ auf den Seiten) werden lokal auf dem Server geprüft; Tests, die eine GPU brauchen, prüfen `mikroptim.device_count()` und überspringen sich sonst (`pytest.skip`).

## 5. Code-Konventionen

- Python ≥ 3.10, Paket `gui_mikroptim` im src-Layout. Formatierung und Lint mit `ruff` (Konfiguration in `pyproject.toml`), Typannotationen für alle öffentlichen Funktionen.
- **Schichten** (docs/architektur.md): `pages/` (nur Streamlit, keine Logik) → `views/` (wiederverwendbare Darstellungen: Tabellen, Plotly-Figuren) → `backend/` (ohne Streamlit-Import, voll testbar) → Mikroptim. `backend/` darf `streamlit` **nicht** importieren.
- Mikroptim wird nur in `backend/mko.py` und `backend/jobs.py` importiert bzw. aufgerufen, und nur über die öffentliche API (`import mikroptim`, Namen ohne Unterstrich) oder die CLI. Keine privaten Symbole (`mikroptim._mikroptim`), keine Kopien von Mikroptim-Code.
- Mikroptim ist **optional** für den Import der GUI: `import gui_mikroptim` und der Start der App funktionieren ohne Mikroptim; Seiten zeigen dann einen klaren Hinweis.
- Dateizugriff nur über `backend/files.py` (Arbeitsbereich, Schutz gegen `..` und Symlinks nach außen). Niemals Pfade aus der Oberfläche ungeprüft öffnen.
- Lange Rechnungen (Synthese, große Batches, alles über einige Sekunden ohne Rückmeldung) laufen als Job in einem eigenen Prozess (ADR-0003), nicht im Streamlit-Skript.
- Teure Ergebnisse mit `st.cache_data`/`st.cache_resource` zwischenspeichern; Schlüssel enthalten Dateipfad **und** Änderungszeit bzw. Hash der Datei.
- Texte der Oberfläche auf Deutsch, Zahlen mit Einheit (mm, nm, Wellen bei λ_ref), Einheiten wie in Mikroptim.
- Plots mit Plotly (ADR-0005). Farbskalen für OPD divergierend und symmetrisch um 0.

## 6. Nicht verhandelbar ohne ADR

1. **Keine Optik in der GUI.** Was Mikroptim nicht liefert, wird als Wunsch an Mikroptim dokumentiert (`docs/schnittstelle-mikroptim.md`), nicht nachgebaut. Erlaubt ist reine Darstellung (z. B. Linsenschnitt aus Krümmung, Dicke und Halbdurchmesser zeichnen, Einheiten umrechnen, Tabellen sortieren).
2. **Nur lokale Bindung.** Die GUI bindet an `127.0.0.1`. Keine Freigabe auf `0.0.0.0`, keine eigene Benutzerverwaltung (ADR-0004).
3. **Keine Schreibzugriffe außerhalb des Arbeitsbereichs**, insbesondere nie in den Mikroptim-Checkout. Eingabedateien werden nie überschrieben.
4. **Determinismus erhalten:** Startwerte (Seeds) und alle Optionen eines Laufs werden in der Oberfläche angezeigt und im Job gespeichert, damit jeder Lauf mit der CLI reproduzierbar ist.

## 7. Daten und Sicherheit

- **Niemals** Tokens, Passwörter oder andere Geheimnisse in Code, Konfiguration, CI oder Commit-Nachrichten.
- Keine Linsendaten realer Objektive und keine lizenzpflichtigen Glaskataloge committen. Testdaten sind frei erfunden oder stammen aus `data/` von Mikroptim (über `MKO_GUI_MIKROPTIM_REPO`, nicht kopiert).
- Hochgeladene Dateien landen im Arbeitsbereich unter `uploads/`, Größe begrenzt (`.streamlit/config.toml`).

## 8. Nicht selbst entscheiden – Maintainer fragen

- Neue Laufzeitabhängigkeiten über `streamlit`, `numpy`, `plotly` und `mikroptim` hinaus (Entwicklungswerkzeuge: `pytest`, `ruff`)
- Änderungen an Bindung, Authentifizierung oder Netzwerkzugang
- Änderungen am Jobmodell oder am Ablageformat der Jobs (`gui-mikroptim.job/1`)
- Anforderungen an eine neue Mikroptim-Version (Mindestversion in `docs/schnittstelle-mikroptim.md`)
- Änderungen an Mikroptim selbst (eigenes Repository, eigener Plan)

## 9. Definition of Done

Eine Aufgabe ist fertig, wenn

- alle Abnahmekriterien belegt sind,
- CI grün ist (Lint, Tests auf Linux und Windows, Integration gegen Mikroptim `main`),
- neue Seiten in einem `AppTest` ohne Ausnahme laufen, mit und ohne Mikroptim,
- Doku und `CHANGELOG.md` aktualisiert sind, Screenshots neuer Seiten im PR liegen.
