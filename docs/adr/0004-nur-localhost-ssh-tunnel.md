# ADR-0004: Nur localhost, Zugang per SSH-Tunnel, keine Benutzerverwaltung

- **Status:** angenommen
- **Datum:** 2026-10-20

## Kontext

Streamlit hat keine eingebaute Anmeldung. Die GUI kann Rechnungen auf der GPU starten und Dateien schreiben; sie soll nur für wenige Personen mit Serverzugang erreichbar sein.

## Entscheidung

- Die GUI bindet ausschließlich an `127.0.0.1` (`.streamlit/config.toml` und Startprogramm `gui-mikroptim`, das `--server.address` ablehnt).
- Zugang nur über einen SSH-Tunnel; Authentifizierung ist die SSH-Anmeldung.
- Keine eigene Benutzerverwaltung, keine Freigabe ins Netz, keine Telemetrie.
- Dateizugriff nur unter erlaubten Wurzeln, geschrieben wird nur im Arbeitsbereich (`backend/files.py`).

## Konsequenzen

- Einfach und sicher, solange alle Nutzer SSH-Zugang haben.
- Alle, die auf dem Server angemeldet sind, erreichen den Port; auf Mehrbenutzerservern eigene Instanzen und Arbeitsbereiche.
- Zugriff für Personen ohne SSH-Zugang erfordert eine neue ADR (z. B. Reverse-Proxy mit Anmeldung).

## Verworfene Alternativen

- **Passwort in Streamlit-Secrets:** selbstgebaute Anmeldung, leicht falsch zu machen.
- **Reverse-Proxy mit OAuth:** möglich, aber für den jetzigen Nutzerkreis unnötig.
