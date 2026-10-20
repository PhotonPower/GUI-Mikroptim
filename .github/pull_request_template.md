## Aufgabe

Meilenstein und Aufgaben-ID (z. B. `G1-T2`), Link zum Abschnitt in `docs/plan/meilensteine.md`:

## Was wurde gemacht

## Abnahmekriterien

- [ ] Alle Abnahmekriterien der Aufgabe sind erfüllt (bitte einzeln mit Ergebnis auflisten: Testname, Screenshot)

## Screenshots

## Checkliste

- [ ] `ruff check .` und `ruff format --check .` sauber, `python -m pytest` grün
- [ ] Neue oder geänderte Seiten: `AppTest` mit und ohne Mikroptim, Integrationstest mit Mikroptim
- [ ] Keine Optik in der GUI (ADR-0002); neue Mikroptim-Aufrufe in `docs/schnittstelle-mikroptim.md` eingetragen
- [ ] Dateizugriff nur über `backend/files.py`, nichts außerhalb des Arbeitsbereichs geschrieben
- [ ] Bei GPU-Pfaden: lokal auf dem Server geprüft
- [ ] Doku aktualisiert (`docs/…`), `CHANGELOG.md` ergänzt
- [ ] Abweichung von Konventionen oder Plan? Dann ADR in `docs/adr/` angelegt
- [ ] Keine Geheimnisse, Tokens, realen Linsendaten oder lizenzpflichtigen Glaskataloge im Commit
