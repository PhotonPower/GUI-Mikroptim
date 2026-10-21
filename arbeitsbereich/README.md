# Arbeitsbereich

Standardverzeichnis für alles, was die GUI schreibt (`MKO_GUI_WORKSPACE`, siehe docs/betrieb.md):

| Unterverzeichnis | Inhalt |
|---|---|
| `uploads/` | hochgeladene Systemdateien und Protokolle |
| `ergebnisse/` | Ergebnisse von Optimierungen (neue Systemdateien, nie überschriebene Eingaben) |
| `kataloge/` | hochgeladene Glaskataloge (`mikroptim.glass/1`, ADR-0006) |
| `jobs/` | ein Verzeichnis pro Job mit `job.json`, Ausgaben und Protokollen (ab G4) |

Der Inhalt wird nicht versioniert (`.gitignore`). Auf dem Server liegt der Arbeitsbereich besser außerhalb des Checkouts.
