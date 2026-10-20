# ADR-0002: Mikroptim nur über die öffentliche API, keine Optik in der GUI

- **Status:** angenommen
- **Datum:** 2026-10-20

## Kontext

Mikroptim legt großen Wert auf Genauigkeit und Reproduzierbarkeit (FP64, deterministische Reduktionen, Abnahme gegen analytische Orakel). Eine GUI, die selbst Strahlen rechnet, Formeln nachbaut oder interne Strukturen liest, würde Zahlen zeigen, die nicht durch diese Tests abgesichert sind, und bei jeder Änderung in Mikroptim brechen. Die API von Mikroptim ist noch in Bewegung (Controller-Umbau nach M6-T6).

## Entscheidung

1. Die GUI rechnet keine Optik. Jede angezeigte Zahl stammt aus Mikroptim. Erlaubt ist Darstellung: Einheiten umrechnen (z. B. Radius aus Krümmung zur Anzeige), sortieren, Flächenformen aus Krümmung, Dicke und Halbdurchmesser zeichnen.
2. Mikroptim wird nur über öffentliche Namen von `import mikroptim` und über die CLI genutzt, nicht über `mikroptim._mikroptim` oder kopierten Code.
3. Der Import steht an einer Stelle (`backend/mko.py`, für Jobs `backend/jobs.py`). Mikroptim ist keine Paketabhängigkeit der GUI, sondern wird als eigenes Wheel (CPU oder CUDA) installiert; die GUI startet auch ohne.
4. Fehlende Funktionen werden als Wunsch in `docs/schnittstelle-mikroptim.md` geführt und in Mikroptim umgesetzt.

## Konsequenzen

- Was in der GUI steht, ist durch die Tests von Mikroptim gedeckt.
- Manche Darstellungen warten auf Mikroptim, z. B. Strahlen im Linsenschnitt (Wunsch W1).
- API-Änderungen in Mikroptim fallen in der CI der GUI auf (Integrationsjob gegen Mikroptim `main`).

## Verworfene Alternativen

- **Eigener kleiner Tracer für die Darstellung:** schnell gemacht, aber eine zweite Wahrheit mit eigenen Konventionen (Vorzeichen, Dezentrierung nach ADR-0011 von Mikroptim).
- **Mikroptim als Abhängigkeit in `pyproject.toml`:** es gibt kein veröffentlichtes Wheel, und CPU- und CUDA-Build müssen wählbar bleiben.
