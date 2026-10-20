# Mitarbeit

Diese Regeln gelten für Menschen und Programmieragenten. Agenten lesen zusätzlich [AGENTS.md](AGENTS.md).

## Ablauf

1. Aufgabe aus [docs/plan/meilensteine.md](docs/plan/meilensteine.md) wählen, deren Abhängigkeiten erledigt sind.
2. Branch anlegen: `g<Meilenstein>/t<Nr>-<kurzname>`, z. B. `g1/t2-systemtabelle`. Das Präfix `g` unterscheidet die Aufgaben der GUI von denen in Mikroptim (`m…`).
3. Implementieren, Tests schreiben, Doku und `CHANGELOG.md` aktualisieren.
4. Pull Request mit der Vorlage öffnen. Ein PR pro Aufgabe.
5. Merge erst nach grüner CI und Review durch den Maintainer.

## Commits

Kurze Betreffzeile im Imperativ mit Aufgaben-ID, z. B. `G1-T2: Systemtabelle und Paraxialdaten`.

## Sprache

- Dokumentation, Commit-Nachrichten, PR-Texte und alle Texte der Oberfläche: Deutsch.
- Bezeichner im Code: Englisch. Kommentare und Docstrings: Deutsch.

## Entscheidungen

Grundsätzliche Entscheidungen (Framework, Abhängigkeiten, Anbindung an Mikroptim, Sicherheit, Jobmodell) werden als ADR in [docs/adr/](docs/adr/) festgehalten. Eine bestehende ADR wird nicht still umgangen, sondern durch eine neue ersetzt.

## Änderungen an Mikroptim

Braucht die GUI etwas, das Mikroptim nicht anbietet (z. B. Strahlpfade für den Linsenschnitt), wird das **nicht** in der GUI nachgebaut. Es kommt als Wunsch in [docs/schnittstelle-mikroptim.md](docs/schnittstelle-mikroptim.md#wünsche-an-mikroptim) und als Aufgabe in den Meilensteinplan von Mikroptim.
