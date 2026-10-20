"""Seite „Optimierung“: Variablen und Optionen (G3-T1); Lauf und Ergebnis folgen (G3-T2, T3)."""

from __future__ import annotations

from typing import Any

import streamlit as st

from gui_mikroptim.backend import compute, mko, system_tables
from gui_mikroptim.backend.files import FileEntry
from gui_mikroptim.backend.optimize_options import JACOBIANS, OptimizeOptions
from gui_mikroptim.views.wavefront_view import gpu_inputs

KEY = "optimierung"


def variables_section(system: Any) -> None:
    info = compute.details(system)
    st.markdown("**Variablen**")
    if info.variables_error:
        st.warning(
            f"Mikroptim kann die Variablen nicht auflösen: {info.variables_error}. "
            "`mikroptim optimize` wandelt Glasvariablen erst beim Start um; angezeigt wird der "
            "Abschnitt `variables` der Datei."
        )
        st.json(info.data.get("variables") or {})
    elif not info.variables:
        st.info("Das System hat keine Variablen; eine Optimierung ändert nichts.")
    else:
        st.dataframe(system_tables.variable_rows(info.variables), hide_index=True, width="stretch")
    constraints = info.data.get("constraints")
    if constraints:
        with st.expander("Nebenbedingungen"):
            st.json(constraints)


def options_form(status: mko.MikroptimStatus) -> OptimizeOptions:
    """Einstellungen mit den Standardwerten von Mikroptim; ungültige Kombinationen sind gesperrt."""
    d = OptimizeOptions()
    c1, c2, c3, c4 = st.columns(4)
    max_iterations = c1.number_input(
        "Zyklen pro Lauf", 0, 100000, d.max_iterations, key=f"{KEY}.zyklen",
        help="0: nur den Startpunkt auswerten",
    )  # fmt: skip
    rings = c2.number_input("Ringe", 1, 256, d.rings, key=f"{KEY}.ringe")
    spokes = c3.number_input("Speichen", 1, 256, d.spokes, key=f"{KEY}.speichen")
    jacobian = c4.radio("Jacobi-Matrix", list(JACOBIANS), horizontal=True, key=f"{KEY}.jacobi")

    c1, c2, c3 = st.columns(3)
    runs = c1.number_input("Läufe (Multistart)", 1, 1000, d.runs, key=f"{KEY}.laeufe")
    multistart = runs >= 2
    perturbation = c2.number_input(
        "relative Störung", 0.0, 10.0, d.perturbation, 0.01, key=f"{KEY}.stoerung",
        disabled=not multistart, help="nur mit mindestens 2 Läufen",
    )  # fmt: skip
    seed = c3.number_input(
        "Seed", 0, 2**31 - 1, d.seed, key=f"{KEY}.seed", disabled=not multistart,
        help="nur mit mindestens 2 Läufen; gleicher Seed ergibt dasselbe Ergebnis",
    )  # fmt: skip

    c1, c2, c3, c4 = st.columns(4)
    hard = c1.toggle("hartes Strahlversagen", value=False, key=f"{KEY}.hart")
    own_weight = c2.toggle(
        "eigenes Strafgewicht", value=False, key=f"{KEY}.eigenes_gewicht", disabled=hard,
        help="nur beim weichen Strahlversagen",
    )  # fmt: skip
    weight = c3.number_input(
        "w_fail [Wellen²]", 1e-9, 1e9, 1.0, format="%.4g", key=f"{KEY}.gewicht",
        disabled=hard or not own_weight,
    )  # fmt: skip
    gpu, device, _ = gpu_inputs(status, c4, c4, KEY, with_precision=False)
    return OptimizeOptions(
        max_iterations=int(max_iterations),
        rings=int(rings),
        spokes=int(spokes),
        runs=int(runs),
        perturbation=float(perturbation),
        seed=int(seed),
        fail_weight=float(weight) if own_weight and not hard else None,
        hard_failure=bool(hard),
        gpu=gpu,
        device=device,
        jacobian=str(jacobian),
    )


def command_caption(entry: FileEntry, options: OptimizeOptions) -> None:
    args = " ".join(options.cli_args())
    st.caption(
        f"Entspricht: `mikroptim optimize {entry.path.name} --json {args}`".replace("  ", " ")
    )
