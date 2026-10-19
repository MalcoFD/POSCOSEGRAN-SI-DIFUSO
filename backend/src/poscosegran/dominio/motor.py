"""Punto de entrada del motor para el resto del backend.

El motor de inferencia vive en poscosegran.inferencia y es genérico: todo el
conocimiento del dominio —reglas, umbrales, tablas y prioridades— se lee de la
base de conocimiento. Este módulo solo decide qué base usar cuando el llamador no
indica una: la de los archivos del repositorio, que es la semilla de la versión
activa.

En producción el servicio de evaluaciones pasa siempre la versión activa de la
base de datos, de modo que el conocimiento adquirido gobierna las decisiones.
"""

from __future__ import annotations

from ..inferencia import base_conocimiento
from ..inferencia.base_conocimiento import BaseConocimiento
from ..inferencia.calculos import CalculosTiempo
from ..inferencia.motor import VERSION_MOTOR, Resultado
from ..sistema_experto.motor import Motor
from .hechos import Instantanea

__all__ = ["CalculosTiempo", "Resultado", "VERSION_MOTOR", "evaluar"]


def evaluar(instantanea: Instantanea, base: BaseConocimiento | None = None) -> Resultado:
    elegida = base or base_conocimiento.cargar()
    if 'difuso' in elegida.contenido['operativa']:
        from ..sistema_difuso.motor import MotorDifuso
        return MotorDifuso(elegida).evaluar(instantanea)
    return Motor(elegida).evaluar(instantanea)
