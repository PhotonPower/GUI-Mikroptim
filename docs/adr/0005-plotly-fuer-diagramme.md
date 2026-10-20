# ADR-0005: Plotly für Diagramme

- **Status:** angenommen
- **Datum:** 2026-10-20

## Kontext

Die GUI zeigt OPD-Karten (2D mit NaN außerhalb der Pupille), PSF (logarithmisch), MTF-Kurven, Spotdiagramme, Verläufe über Optimierungsschritte und Linsenschnitte. Nutzer wollen zoomen und Werte ablesen.

## Entscheidung

- Diagramme mit Plotly (`plotly.graph_objects`), in Streamlit mit `st.plotly_chart`.
- Figuren werden in `views/` von reinen Funktionen erzeugt (Eingabe NumPy, Ausgabe `go.Figure`) und sind ohne Streamlit testbar.
- Einheitliche Regeln: Achsen mit Einheit, OPD in Wellen bei λ_ref mit divergierender, um 0 symmetrischer Farbskala, Seitenverhältnis 1 bei Pupillen- und Bildebenen-Darstellungen.
- Stammbäume als Graphviz-DOT über `st.graphviz_chart` (keine zusätzliche Abhängigkeit).

## Konsequenzen

- Interaktive Diagramme ohne eigenen JavaScript-Code.
- Sehr große Punktwolken (Spots bei großen Rastern) müssen ggf. ausgedünnt oder mit `Scattergl` gezeichnet werden.

## Verworfene Alternativen

- **Matplotlib:** statisch, schlechter zum Ablesen; bleibt für Exporte denkbar.
- **Altair/Vega:** schwächer bei 2D-Feldern mit NaN und gleichem Seitenverhältnis.
