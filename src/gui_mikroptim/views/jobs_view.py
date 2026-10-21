"""Reiter „Jobs“: Liste, Status, Ausgabe und Abbruch (G4-T1, ADR-0003)."""

from __future__ import annotations

import datetime as dt

import streamlit as st

from gui_mikroptim.backend import jobs, synth_job
from gui_mikroptim.config import Settings
from gui_mikroptim.views import current, file_picker, synth_view

KEY = "jobs"
REFRESH_SECONDS = 2.0
STATUS_ICONS = {
    jobs.WAITING: "⏳",
    jobs.RUNNING: "▶️",
    jobs.DONE: "✅",
    jobs.FAILED: "❌",
    jobs.CANCELLED: "⏹️",
}


def _local(iso: str | None) -> str:
    if not iso:
        return "–"
    return dt.datetime.fromisoformat(iso).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _duration(seconds: float | None) -> str:
    if seconds is None:
        return "–"
    if seconds < 120:
        return f"{seconds:.0f} s"
    if seconds < 7200:
        return f"{seconds / 60:.1f} min"
    return f"{seconds / 3600:.1f} h"


def status_text(job: jobs.Job) -> str:
    text = f"{STATUS_ICONS.get(job.status, '')} {job.status}"
    return f"{text} ({job.note})" if job.note else text


def job_rows(job_list: list[jobs.Job]) -> list[dict]:
    return [
        {
            "Job": j.id,
            "Art": j.data.get("kind"),
            "Status": status_text(j),
            "angelegt": _local(j.data.get("created")),
            "Dauer": _duration(j.duration_seconds()),
            "Exit-Code": j.data.get("exit_code"),
        }
        for j in job_list
    ]


def _details(cfg: Settings, job_id: str) -> None:
    try:
        job = jobs.load(jobs.jobs_root(cfg.workspace) / job_id)
    except jobs.JobError as exc:
        st.error(str(exc))
        return
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Status", status_text(job))
    c2.metric("Dauer", _duration(job.duration_seconds()))
    c3.metric("Exit-Code", "–" if job.data.get("exit_code") is None else job.data["exit_code"])
    c4.metric("Mikroptim", job.data.get("mikroptim_version") or "–")
    st.caption(
        f"angelegt {_local(job.data.get('created'))} · gestartet "
        f"{_local(job.data.get('started'))} · beendet {_local(job.data.get('finished'))} · "
        f"Ordner `{job.path}`"
    )
    if job.data.get("error"):
        st.error(job.data["error"])

    if not job.final and st.button("Abbrechen", key=f"{KEY}.abbrechen.{job.id}", type="primary"):
        jobs.cancel(cfg.workspace, job.id)
        st.rerun()

    st.markdown("**Befehl** (im Jobordner ausführen, um den Lauf von Hand zu wiederholen)")
    st.code(f"cd {job.path}\n{job.command_line()}", language="bash")
    if job.data.get("inputs"):
        st.caption(
            "Eingaben: "
            + ", ".join(
                f"`{rel}` (aus {src})"
                for rel, src in zip(job.data["inputs"], job.data.get("sources", []), strict=False)
            )
        )
    out, err = st.columns(2)
    with out:
        st.markdown(f"**Ausgabe** (`{jobs.STDOUT_FILE}`, letzte 200 Zeilen)")
        st.code(job.tail(jobs.STDOUT_FILE) or "–", language="text")
    with err:
        st.markdown(f"**Fehlerausgabe** (`{jobs.STDERR_FILE}`)")
        st.code(job.tail(jobs.STDERR_FILE) or "–", language="text")
    if job.data.get("options"):
        with st.expander("Optionen"):
            st.json(job.data["options"])
    if job.final:
        from gui_mikroptim.views.files_view import zip_button

        files = sorted(
            p.relative_to(job.path).as_posix()
            for p in job.path.rglob("*")
            if p.is_file() and not p.name.startswith(".")
        )
        zip_button(job.path, files, job.id, f"{KEY}.zip.{job.id}", "Jobordner als ZIP")
    if job.data.get("kind") == "synth":
        _synth_results(job)


def _synth_results(job: jobs.Job) -> None:
    """Ergebnisse eines Synthese-Jobs: Protokoll direkt, Übernahme des Ergebnisses (G4-T3)."""
    found = synth_job.outputs(job)
    if not job.final:
        last = job.tail(jobs.STDOUT_FILE, lines=1)
        if last:
            st.caption(f"Letzte Zeile der Ausgabe: `{last}`")
        return
    c1, c2 = st.columns(2)
    if "ergebnis" in found and c1.button(
        "Ergebnis als aktuelles System übernehmen", key=f"{KEY}.uebernehmen.{job.id}"
    ):
        current.set_path(found["ergebnis"])
        st.toast(f"Aktuelles System: {found['ergebnis'].name} aus {job.id}")
    if "protokoll" in found:
        if c2.button("Im Reiter „Protokolle“ öffnen", key=f"{KEY}.protokoll.{job.id}"):
            file_picker.select_on_next_run("synthese.protokoll", found["protokoll"], False)
            st.rerun()
        with st.expander("Protokoll der Synthese", expanded=True):
            synth_view.render(found["protokoll"], key=f"{KEY}.synth.{job.id}")
    elif job.status == jobs.DONE:
        st.warning("Job fertig, aber kein protokoll.json gefunden.")


def render(cfg: Settings) -> None:
    try:
        started = jobs.start_pending(cfg.workspace, cfg.max_jobs, cfg.sessions_root)
        job_list = jobs.list_jobs(cfg.workspace)
    except jobs.JobError as exc:
        st.error(str(exc))
        return
    if started:
        st.toast(f"Gestartet: {', '.join(started)}")

    running = jobs.running_count(cfg.workspace, cfg.sessions_root)
    waiting = sum(1 for j in job_list if j.status == jobs.WAITING)
    c1, c2, c3 = st.columns([1, 1, 2])
    c1.metric(
        "laufend",
        f"{running} / {cfg.max_jobs}",
        help="Höchstzahl MKO_GUI_MAX_JOBS; mit Sitzungen gezählt über alle Sitzungen, weil sie "
        "sich die GPU teilen",
    )
    c2.metric("wartend", waiting)
    if c3.button("Aktualisieren", key=f"{KEY}.neu"):
        st.rerun()

    if not job_list:
        st.info(
            "Noch keine Jobs. Eine Synthese startet im Reiter „Neue Synthese“; Jobs liegen "
            f"unter {jobs.jobs_root(cfg.workspace)}."
        )
        return
    st.dataframe(job_rows(job_list), hide_index=True, width="stretch")

    ids = [j.id for j in job_list]
    pending = st.session_state.pop("jobs.auswahl_neu", None)
    if pending in ids:
        st.session_state[f"{KEY}.auswahl"] = pending  # vor dem Widget: erlaubt
    job_id = st.selectbox("Job", ids, key=f"{KEY}.auswahl")
    selected = next(j for j in job_list if j.id == job_id)
    live = selected.status in (jobs.WAITING, jobs.RUNNING)

    @st.fragment(run_every=REFRESH_SECONDS if live else None)
    def details() -> None:
        _details(cfg, job_id)

    details()
