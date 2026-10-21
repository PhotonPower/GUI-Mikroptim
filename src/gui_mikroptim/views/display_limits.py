"""Begrenzung der Datenmenge für die Anzeige im Browser (G5-T2).

Nur die Darstellung wird reduziert, nie die Rechnung: Kennzahlen, Tabellen und Exporte nutzen die
vollen Daten von Mikroptim. Jede Reduktion wird im Diagramm angegeben.
"""

from __future__ import annotations

import math

import numpy as np

#: größte Kantenlänge einer gezeigten Karte (OPD, PSF) in Bildpunkten
MAX_SIDE = 512
#: größte Zahl gezeigter Punkte im Spotdiagramm
MAX_POINTS = 50_000


def block_factor(side: int, max_side: int = MAX_SIDE) -> int:
    return max(1, math.ceil(side / max_side))


def reduce_grid(
    z: np.ndarray, x: np.ndarray, y: np.ndarray, how: str, max_side: int = MAX_SIDE
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """Fasst je k × k Bildpunkte zusammen (``how``: ``"mean"`` ohne NaN oder ``"max"``).

    Blöcke ganz aus NaN bleiben NaN (z. B. außerhalb der Pupille). Ränder, die keinen vollen
    Block ergeben, werden mit NaN aufgefüllt. Rückgabe: Karte, Achsen (Blockmitten), Faktor k.
    """
    z = np.asarray(z, dtype=float)
    k = block_factor(max(z.shape), max_side)
    if k == 1:
        return z, np.asarray(x), np.asarray(y), 1
    ny, nx = z.shape
    py, px = (-ny) % k, (-nx) % k
    padded = np.pad(z, ((0, py), (0, px)), constant_values=np.nan)
    blocks = padded.reshape(padded.shape[0] // k, k, padded.shape[1] // k, k)
    finite = np.isfinite(blocks)
    count = finite.sum(axis=(1, 3))
    if how == "max":
        reduced = np.where(finite, blocks, -np.inf).max(axis=(1, 3))
    elif how == "mean":
        reduced = np.where(finite, blocks, 0.0).sum(axis=(1, 3)) / np.maximum(count, 1)
    else:
        raise ValueError(f"unbekannte Zusammenfassung {how!r}")
    reduced = np.where(count > 0, reduced, np.nan)

    def axis(values: np.ndarray, pad: int) -> np.ndarray:
        values = np.asarray(values, dtype=float)
        step = values[1] - values[0] if values.size > 1 else 0.0
        extended = np.concatenate([values, values[-1] + step * np.arange(1, pad + 1)])
        return extended.reshape(-1, k).mean(axis=1)

    return reduced, axis(x, px), axis(y, py), k


def thin_points(x: np.ndarray, y: np.ndarray, max_points: int = MAX_POINTS):
    """Jeden k-ten Punkt behalten, sodass höchstens ``max_points`` bleiben; Rückgabe x, y, k."""
    x, y = np.asarray(x), np.asarray(y)
    k = max(1, math.ceil(x.size / max_points))
    return x[::k], y[::k], k
