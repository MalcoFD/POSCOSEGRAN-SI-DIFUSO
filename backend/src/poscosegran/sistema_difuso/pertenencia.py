"""Funciones lineales por tramos, incluidos hombros triangulares/trapezoidales."""

import math
from collections.abc import Sequence
from decimal import Decimal


def puntos_validos(puntos: Sequence[float]) -> bool:
    return (
        len(puntos) in (3, 4)
        and all(math.isfinite(float(p)) for p in puntos)
        and list(puntos) == sorted(puntos)
        and puntos[0] < puntos[-1]
    )


def pertenencia(valor: float | Decimal, puntos: Sequence[float]) -> float:
    if not puntos_validos(puntos):
        raise ValueError(
            "La función necesita 3 o 4 vértices finitos, ordenados y con soporte no vacío"
        )
    x = float(valor)
    if not math.isfinite(x):
        raise ValueError("La observación debe ser finita")
    a, b, c, d = (
        [float(p) for p in puntos] if len(puntos) == 4 else [float(puntos[i]) for i in (0, 1, 1, 2)]
    )
    if x < a or x > d:
        return 0.0
    if b <= x <= c:
        return 1.0
    if a <= x < b:
        return (x - a) / (b - a)
    return (d - x) / (d - c) if d > c else 0.0
