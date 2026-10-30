"""Estructura de una activación Mamdani para la explicación persistida."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Activacion:
    orden: int
    etapa: str
    pasada: int
    produccion: str
    regla: str
    hallazgo: str | None
    soportes: tuple[str, ...]
    solicitudes: tuple[str, ...]
