"""Antecedentes lingüísticos multivariables; AND mínimo y OR máximo."""

from collections.abc import Mapping
from typing import Any


def activacion(nodo: Mapping[str, Any], grados: Mapping[str, Mapping[str, float]]) -> float:
    if "todos" in nodo:
        return min(activacion(hijo, grados) for hijo in nodo["todos"])
    if "alguno" in nodo:
        return max(activacion(hijo, grados) for hijo in nodo["alguno"])
    return grados[nodo["entrada"]][nodo["conjunto"]]


def referencias(nodo: Mapping[str, Any]) -> set[tuple[str, str]]:
    if "entrada" in nodo:
        return {(nodo["entrada"], nodo["conjunto"])}
    operador = "todos" if "todos" in nodo else "alguno"
    return set().union(*(referencias(hijo) for hijo in nodo[operador]))


def aplica(guarda: Mapping[str, Any] | None, modalidad: str) -> bool:
    """Guardas declarativas acotadas a modalidad, también usadas al probar cobertura."""
    return guarda is None or guarda == {"contexto": "tipo_almacenamiento", "igual": modalidad}
