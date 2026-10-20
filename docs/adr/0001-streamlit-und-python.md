# ADR-0001: Streamlit und Python als Grundlage

- **Status:** angenommen
- **Datum:** 2026-10-20

## Kontext

Mikroptim soll auf dem Rechenserver leichter testbar werden, ohne jeden Lauf über die Kommandozeile und JSON-Dateien auszuwerten. Seit Mikroptim M9-T1 gibt es Python-Bindings, die Ergebnisse als NumPy-Arrays liefern. Nutzer sind wenige Fachleute, nicht die Öffentlichkeit; Entwicklungszeit ist knapper als Feinschliff der Oberfläche.

## Entscheidung

- Die GUI ist eine Streamlit-App in Python (≥ 3.10, wie die Mikroptim-Bindings), eigenes Repository, Paket `gui_mikroptim` im src-Layout.
- Laufzeitabhängigkeiten: `streamlit` (≥ 1.40, < 2, für `st.navigation`, `st.fragment`, `AppTest`), `numpy`, `plotly` (ADR-0005) und ein separat installiertes `mikroptim`. Entwicklung: `pytest`, `ruff`.
- Mehrseiten-App über `st.navigation` mit Seiten unter `pages/`.
- Tests mit pytest und `streamlit.testing.v1.AppTest`.

## Konsequenzen

- Schnell entwickelbar, gut testbar, gleiche Sprache wie die Bindings.
- Streamlit führt das Skript bei jeder Interaktion neu aus: Rechenergebnisse müssen gecacht werden, lange Rechnungen gehören nicht in das Skript (ADR-0003).
- Ein Serverprozess für alle Sitzungen: GPU und Speicher werden geteilt; Grenzen über Jobs und `MKO_GUI_MAX_JOBS`.
- Gestaltungsspielraum ist begrenzt; für ein späteres echtes Entwurfsprogramm wäre eine andere Technik zu prüfen.

## Verworfene Alternativen

- **Jupyter-Notebooks:** gut für Einzelanalysen, aber keine feste Oberfläche für wiederkehrende Tests und schwer automatisiert testbar.
- **Dash/Panel:** mehr Kontrolle über Rückrufe, aber mehr Code für denselben Umfang.
- **Web-Frontend (React) mit eigenem Backend:** für den Zweck zu aufwendig.
- **Desktop-GUI (Qt):** braucht X-Weiterleitung oder lokale Installation; der Server hat die GPUs.
