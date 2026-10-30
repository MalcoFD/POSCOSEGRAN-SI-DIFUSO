"""Estructura de persistencia de cálculos opcionales.

El modelo matricial no estima vida útil a partir de una tabla externa.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from ..dominio.hechos import Estimacion


@dataclass(frozen=True, slots=True)
class CalculosTiempo:
    vida_consumida: Decimal | None = None
    vida_minima_documentada: Decimal | None = None
    vida_proyectada: Decimal | None = None
    tiempo_referencia_actual: int | None = None
    celda: Any = None
    motivos_no_disponible: tuple[str, ...] = ()
    estimaciones: tuple[Estimacion, ...] = ()
