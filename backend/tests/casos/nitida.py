"""La base de conocimiento difusa en modo nítido: todos los anchos de transición a 0.

Los casos de aceptación C01–C40 (sección 9) especifican la lógica nítida del
documento. La base difusa con δ = 0 debe cumplirlos sin cambiar una sola
expectativa: es la prueba de que la lógica clásica es un caso particular del
modelo. El comportamiento con los anchos aprobados se verifica en
tests/test_aceptacion_difusa.py.
"""

from __future__ import annotations

import copy
from functools import cache

from poscosegran.dominio.hechos import Instantanea
from poscosegran.sistema_experto import base_conocimiento
from poscosegran.sistema_experto.base_conocimiento import BaseConocimiento
from poscosegran.sistema_experto.motor import Motor, Resultado


def contenido_con_anchos(factor: float) -> dict:
    """Contenido de la base del repositorio con los anchos de transición escalados."""
    contenido = copy.deepcopy(base_conocimiento.leer_archivos())
    for nombre, parametro in contenido["operativa"]["parametros"].items():
        if nombre.startswith("transicion_"):
            parametro["valor"] = parametro["valor"] * factor
    return contenido


@cache
def base_con_anchos(factor: float) -> BaseConocimiento:
    return base_conocimiento.desde_contenido(contenido_con_anchos(factor))


def base_nitida() -> BaseConocimiento:
    return base_con_anchos(0.0)


def evaluar(instantanea: Instantanea) -> Resultado:
    return Motor(base_nitida()).evaluar(instantanea)
