# ADR-0006: Glaskataloge im Arbeitsbereich

- **Status:** angenommen
- **Datum:** 2026-10-21

## Kontext

Nutzer der GUI haben keinen Zugang zum Server. Eigene Glaskataloge – vor allem Herstellerdaten, die nach Mikroptims AGENTS.md nicht ins Repository dürfen und dort unter `data/glass/private/` liegen sollen – konnten sie bisher nicht bereitstellen. Die GUI schreibt nie in den Mikroptim-Checkout (AGENTS.md, Abschnitt 6.3).

Mikroptim sucht die Einträge von `glass_catalogs` nur vom Ordner der Systemdatei aus aufwärts. Seit G1-T2 lädt die GUI eine Datei mit fehlenden Katalogen mit *einer* Basis (Mikroptim-Checkout) neu. Eine Datei, die Kataloge aus dem Checkout *und* eigene Kataloge nennt, ließ sich damit nicht laden (Anlass: Patentsystem DE 103 16 415 mit Schott-Gläsern, 2026-10-21).

## Entscheidung

- Hochgeladene Glaskataloge liegen unter `<Arbeitsbereich>/kataloge/` (Format `mikroptim.glass/1`). Beim Hochladen prüft die GUI den Aufbau und lässt Mikroptim den Katalog mit einem Prüfsystem laden (jedes Glas als Medium); abgelehnte Kataloge werden nicht gespeichert. Der Dateiname bleibt erhalten, ein vorhandener Katalog gleichen Namens wird nicht überschrieben (Löschen mit Bestätigung).
- Einträge von `glass_catalogs`, die Mikroptim nicht findet, ordnet die GUI zu (`backend.catalogs.resolve_entries`): zuerst wie Mikroptim vom Ordner der Systemdatei aufwärts, dann `<Mikroptim-Checkout>/<Eintrag>`, dann `kataloge/<Dateiname des Eintrags>`. Mit diesen Pfaden lädt Mikroptim die Datei (`System.from_json`) und schreibt sie neu (`System.save`, Pfade relativ zur neuen Datei).
- Das ersetzt die Aussage aus G1-T2, die GUI brauche dafür keine eigene Pfadlogik: Sie ordnet jetzt Dateien zu, rechnet aber weiter keine Optik (ADR-0002 bleibt unberührt).

## Konsequenzen

- Nutzer ohne Serverzugang können Systeme mit eigenen Gläsern rechnen; Herstellerdaten bleiben im Arbeitsbereich und kommen in kein Repository.
- Die Zuordnung nach Dateiname ist bewusst einfach: Zwei verschiedene Kataloge gleichen Namens sind im Arbeitsbereich nicht möglich.
- Gläser, die zugleich in einem Katalog von Mikroptim stehen (z. B. N-BK7), meldet die GUI beim Hochladen; ein System, das beide Kataloge nennt, lehnt Mikroptim ab.
- Bietet Mikroptim einmal einen Suchpfad für Kataloge (Wunsch W9), kann die Zuordnung entfallen.

## Verworfene Alternativen

- **In `data/glass/private/` des Checkouts schreiben:** verstößt gegen „nie in den Checkout schreiben“ und würde Daten eines Nutzers für alle sichtbar machen.
- **Arbeitsbereich nach dem Vorbild `data/glass/private/` gliedern**, damit Mikroptims Aufwärtssuche greift: deckt nur Dateien im Arbeitsbereich ab und nicht die Kataloge des Checkouts.
