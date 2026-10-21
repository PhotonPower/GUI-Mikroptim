"""Reiter „Neue Synthese“: Formular für ``mikroptim synth`` als Job (G4-T3)."""

from __future__ import annotations

import streamlit as st

from gui_mikroptim.backend import jobs, mko, synth_job
from gui_mikroptim.config import Settings
from gui_mikroptim.views import common, file_picker

KEY = "synthese.neu"
#: Sitzungsschlüssel: diesen Job beim nächsten Lauf im Reiter „Jobs“ auswählen
SELECT_JOB = "jobs.auswahl_neu"


def _form(status: mko.MikroptimStatus) -> synth_job.SynthOptions | None:
    d = synth_job.SynthOptions()
    with st.form(f"{KEY}.formular"):
        st.markdown("**Ziel**")
        c1, c2, c3, c4, c5 = st.columns(5)
        target_na = c1.number_input(
            "Ziel-NA", 0.0, 1.5, 0.0, 0.05, format="%.4f", help="0: NA des Starts"
        )
        start_field = c2.number_input("Feldanteil Start", 0.0001, 10.0, d.start_field, 0.1)
        target_field = c3.number_input(
            "Feldanteil Ziel", 0.0, 10.0, 0.0, 0.1, help="0: wie am Start"
        )
        rms_target = c4.number_input(
            "RMS-Ziel [Wellen]", 0.0001, 10.0, d.rms_target, 0.01, format="%.5f"
        )
        merit_factor = c5.number_input("Merit-Faktor K", 0.0001, 100.0, d.merit_factor, 0.1)

        with st.expander("Homotopie und LM"):
            c1, c2, c3, c4 = st.columns(4)
            d0 = c1.number_input("Δ₀", 1e-6, 1.0, d.step[0], 0.005, format="%.4f")
            dmin = c2.number_input("Δ_min", 1e-6, 1.0, d.step[1], 0.001, format="%.4f")
            dmax = c3.number_input("Δ_max", 1e-6, 1.0, d.step[2], 0.01, format="%.4f")
            saddle = c4.number_input(
                "Sattel-Δ [1/mm]", 0.0, 1.0, d.saddle_delta, 0.001, format="%.4f"
            )
            c1, c2, c3, c4, c5 = st.columns(5)
            max_steps = c1.number_input("max. Optimierungen", 1, 100000, d.max_steps)
            max_iterations = c2.number_input("LM-Zyklen pro Schritt", 1, 100000, d.max_iterations)
            rings = c3.number_input("Ringe", 1, 256, d.rings)
            spokes = c4.number_input("Speichen", 1, 256, d.spokes)
            bound = c5.number_input(
                "Krümmungsschranke [1/mm]", 0.0, 100.0, 0.0, 0.1, help="0: offen"
            )

        with st.expander("Einfügen (Operator A)"):
            c1, c2, c3, c4, c5 = st.columns(5)
            max_elements = c1.number_input("max. Glaselemente", 1, 100, d.max_elements)
            thickness = c2.number_input("Mittendicke [mm]", 1e-4, 100.0, d.element_thickness)
            max_thickness = c3.number_input("max. Dicke [mm]", 0.0, 100.0, d.element_max_thickness)
            stages = c4.number_input("Dickenstufen", 1, 100, d.element_stages)
            air_gap = c5.number_input("min. Luftspalt [mm]", 0.0, 100.0, d.min_air_gap)

        with st.expander("Strahlsuche (--beam)"):
            c1, c2, c3, c4 = st.columns(4)
            beam = c1.number_input("Breite (0: aus)", 0, 64, d.beam)
            alternatives = c2.number_input("Alternativen", 1, 64, d.alternatives)
            starts = c3.number_input("gestörte Starts", 0, 1000, d.starts)
            perturbation = c4.number_input(
                "Störung [1/mm]", 0.0, 10.0, d.start_perturbation, 0.001, format="%.4f"
            )
            c1, c2, c3 = st.columns(3)
            seed = c1.number_input("Seed", 0, 2**31 - 1, d.seed)
            dedup = c2.number_input(
                "Duplikat-Schwelle", -1.0, 1.0, d.dedup, format="%.2e", help="negativ: aus"
            )
            prefilter = c3.checkbox("FP32-Vorfilter", value=d.prefilter)

        c1, c2, c3 = st.columns(3)
        jacobian = c1.radio("Jacobi-Matrix", list(synth_job.JACOBIANS), horizontal=True)
        gpu, device = False, 0
        if status.has_cuda and status.devices:
            gpu = c2.toggle("GPU", value=False)
            device = c3.number_input("Gerät", 0, max(0, len(status.devices) - 1), 0)
        submitted = st.form_submit_button("Synthese starten", type="primary")

    if not submitted:
        return None
    return synth_job.SynthOptions(
        target_na=float(target_na) or None,
        start_field=float(start_field),
        target_field=float(target_field) or None,
        rms_target=float(rms_target),
        merit_factor=float(merit_factor),
        step=(float(d0), float(dmin), float(dmax)),
        max_elements=int(max_elements),
        max_steps=int(max_steps),
        max_iterations=int(max_iterations),
        rings=int(rings),
        spokes=int(spokes),
        element_thickness=float(thickness),
        element_max_thickness=float(max_thickness),
        element_stages=int(stages),
        min_air_gap=float(air_gap),
        saddle_delta=float(saddle),
        curvature_bound=float(bound) or None,
        gpu=bool(gpu),
        device=int(device),
        jacobian=str(jacobian),
        beam=int(beam),
        alternatives=int(alternatives),
        starts=int(starts),
        start_perturbation=float(perturbation),
        seed=int(seed),
        prefilter=bool(prefilter),
        dedup=float(dedup),
    )


def render(cfg: Settings) -> None:
    status = common.mikroptim_status()
    if not status.available:
        st.warning("Für Synthese-Jobs wird Mikroptim benötigt (Details auf der Startseite).")
        return
    message = st.session_state.pop(f"{KEY}.meldung", None)
    if message:
        st.success(message)
    entry = file_picker.pick_document(
        cfg,
        ("mikroptim.system",),
        key=f"{KEY}.start",
        empty_hint="Startsystem auf der Seite „System“ wählen oder hochladen.",
        source_list=file_picker.system_sources(cfg),
        remember=True,
    )
    if entry is None:
        return
    st.caption(
        "Das Startsystem wird in den Jobordner kopiert (Glaskataloge über Mikroptim neu "
        "verknüpft); Ergebnis `ergebnis.json`, Protokoll `protokoll.json`, bei Strahlsuche "
        "Stammbaum `stammbaum.dot`. Optionen wie `mikroptim synth` (Mikroptim docs/cli.md)."
    )
    options = _form(status)
    if options is None:
        return
    try:
        job = synth_job.submit_synth(
            cfg.workspace,
            entry.path,
            options,
            cfg.max_jobs,
            cfg.read_roots,
            cfg.cli,
            cfg.sessions_root,
        )
    except (ValueError, jobs.JobError) as exc:
        st.error(f"Synthese nicht angelegt: {exc}")
        return
    except Exception as exc:  # Laden/Speichern des Startsystems in Mikroptim
        st.error(f"Startsystem nicht kopierbar: {type(exc).__name__}: {exc}")
        return
    st.session_state[SELECT_JOB] = job.id
    st.session_state[f"{KEY}.meldung"] = (
        f"Job {job.id} angelegt ({job.status}); Fortschritt im Reiter „Jobs“."
    )
    st.rerun()
