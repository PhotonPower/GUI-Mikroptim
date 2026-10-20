"""Startprogramm ``gui-mikroptim``: Streamlit nur auf 127.0.0.1 (ADR-0004).

Weitere Argumente werden an ``streamlit run`` durchgereicht, z. B. ``--server.port 8502``.
``--server.address`` ist nicht erlaubt.
"""

from __future__ import annotations

import sys
from pathlib import Path

APP = Path(__file__).resolve().parent / "app.py"


def build_argv(extra: list[str]) -> list[str]:
    """Argumente für ``streamlit run``; verweigert eine andere Bindung als 127.0.0.1."""
    for arg in extra:
        if arg.startswith("--server.address") or arg.startswith("--server.enableCORS"):
            raise SystemExit(
                "gui-mikroptim: --server.address/--server.enableCORS sind gesperrt "
                "(nur 127.0.0.1, Zugang per SSH-Tunnel, siehe docs/betrieb.md)"
            )
    return [
        "streamlit",
        "run",
        str(APP),
        "--server.address",
        "127.0.0.1",
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
        *extra,
    ]


def main(argv: list[str] | None = None) -> int:
    from streamlit.web import cli as stcli

    sys.argv = build_argv(sys.argv[1:] if argv is None else argv)
    return stcli.main()


if __name__ == "__main__":
    sys.exit(main())
