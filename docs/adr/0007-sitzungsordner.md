# ADR-0007: Sitzungsordner

- **Status:** angenommen
- **Datum:** 2026-10-21

## Kontext

Bisher teilten sich alle Nutzer einer Instanz einen Arbeitsbereich: Jeder sah die Uploads, Ergebnisse, Jobs und Glaskataloge der anderen und konnte sie löschen oder abbrechen. Der Maintainer hat festgelegt: Jede Sitzung bekommt einen eigenen Ordner; dessen Wurzel steht in einer Umgebungsvariablen; Ergebnisse sichert der Nutzer durch Herunterladen.

## Entscheidung

- `MKO_GUI_SESSIONS` nennt die Wurzel der Sitzungsordner. Jede Sitzung arbeitet in `<MKO_GUI_SESSIONS>/<kennung>/` mit `uploads/`, `ergebnisse/`, `jobs/` und `kataloge/`; dieser Ordner ersetzt für die Sitzung den Arbeitsbereich (`Settings.for_session`). Ohne `MKO_GUI_SESSIONS` bleibt der gemeinsame Arbeitsbereich `MKO_GUI_WORKSPACE`.
- Die Kennung ist zufällig (`secrets.token_urlsafe(16)`, nicht erratbar) und steht in der Adresse (`?sitzung=…`). Neuladen behält den Ordner, ein Lesezeichen führt zurück; eine ungültige Kennung in der Adresse ergibt eine neue Sitzung. Wer die Adresse kennt, hat Zugriff – sie ist wie ein Schlüssel zu behandeln.
- Die Warteschlange der Jobs gilt für alle Sitzungen zusammen (Sperre und Zählung auf der Ebene von `MKO_GUI_SESSIONS`, älteste wartende Jobs zuerst), weil sich die Sitzungen die GPU teilen. Jede Sitzung sieht und steuert nur ihre eigenen Jobs.
- Sitzungsordner ohne Zugriff seit `MKO_GUI_SESSION_DAYS` Tagen (Standard 14) und ohne wartende oder laufende Jobs werden gelöscht; aufgeräumt wird beim Anlegen einer neuen Sitzung, höchstens stündlich.
- Ergebnisse sichert der Nutzer über die Seite „Dateien“ (Auswahl als ZIP, einzelne Dateien) und Knöpfe an Ort und Stelle (optimiertes System, Jobordner); heruntergeladene Systemdateien tragen übertragbare Katalogpfade (`data/glass/…`), die ADR-0006 beim erneuten Hochladen zuordnet.

## Konsequenzen

- Nutzer sehen und ändern nur ihre eigenen Daten; Mikroptims Beispielsysteme und `docs/ergebnisse` bleiben für alle lesbar.
- Daten sind nicht dauerhaft: Nach der Frist ist ein unbenutzter Sitzungsordner weg. Wer Ergebnisse braucht, lädt sie herunter oder bewahrt die Adresse auf und nutzt sie innerhalb der Frist.
- Keine Anmeldung (ADR-0004 bleibt): Die Trennung schützt vor Versehen, nicht vor jemandem, der eine fremde Adresse kennt.

## Verworfene Alternativen

- **Kennung nur aus Streamlits Sitzung:** wechselt bei jedem Neuladen; Ergebnisse und laufende Jobs wären nach F5 unerreichbar.
- **Ordner pro Linux-Benutzer:** setzt eigene Instanzen pro Benutzer voraus, die der Maintainer nicht will.
