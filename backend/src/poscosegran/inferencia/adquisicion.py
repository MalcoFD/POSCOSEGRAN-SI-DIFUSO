"""Módulo de adquisición del conocimiento.

Es la vía por la que el ingeniero del conocimiento modifica la base sin tocar el
motor. Un cambio sigue siempre el mismo ciclo:

    proponer   partir de la versión activa y cambiar parámetros o reglas, con motivo;
    validar    la base resultante debe pasar el mismo cargador que la versión activa:
               sintaxis, referencias, ciclos, coherencia con el documento y
               restricciones de integridad;
    medir      evaluar los casos de referencia —y las evaluaciones históricas que se
               aporten— con la versión activa y con la propuesta, y listar qué
               decisiones cambiarían;
    activar    solo una propuesta válida y revisada; la activación la registra la
               capa de servicios, y las evaluaciones ya emitidas no se recalculan.

Nada de esto escribe en disco ni en base de datos: devuelve la propuesta y su
impacto, y la capa de servicios decide qué persistir.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from ..dominio.hechos import Instantanea
from . import serializacion
from .base_conocimiento import BaseConocimiento, BaseInvalida, desde_contenido, ruta_por_defecto

LONGITUD_MINIMA_MOTIVO = 15


@dataclass(frozen=True, slots=True)
class CambioParametro:
    nombre: str
    anterior: Decimal
    nuevo: Decimal
    unidad: str


@dataclass(frozen=True, slots=True)
class CambioRegla:
    produccion: str
    regla: str
    tipo: str  # MODIFICADA | NUEVA | RETIRADA


@dataclass(frozen=True, slots=True)
class CasoAfectado:
    id: str
    origen: str
    decision_antes: str
    decision_despues: str
    reglas_nuevas: tuple[str, ...]
    reglas_retiradas: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Impacto:
    evaluados: int
    cambian: int
    transiciones: dict[str, int]
    casos: tuple[CasoAfectado, ...]
    nuevas_autorizaciones: int


@dataclass(frozen=True)
class Propuesta:
    valida: bool
    errores: tuple[str, ...]
    advertencias: tuple[str, ...]
    version_base: str
    version_parametros: str
    motivo: str
    cambios_parametros: tuple[CambioParametro, ...]
    cambios_reglas: tuple[CambioRegla, ...]
    impacto: Impacto | None
    contenido: Mapping[str, Any] | None = field(repr=False, default=None)
    base: BaseConocimiento | None = field(repr=False, default=None)


# --- Casos de referencia -------------------------------------------------------------


def cargar_casos_referencia(ruta: Path | None = None) -> list[tuple[str, str, Instantanea]]:
    ruta = ruta or (ruta_por_defecto() / "casos_referencia.json")
    if not ruta.exists():
        return []
    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    return [
        (ident, ident.split(":", 1)[0], inst)
        for ident, inst, _ in serializacion.cargar_casos(contenido)
    ]


# --- Propuesta --------------------------------------------------------------------------


def proponer(
    activa: BaseConocimiento,
    *,
    motivo: str,
    version_parametros: str | None = None,
    version_base: str | None = None,
    parametros: Mapping[str, Any] | None = None,
    reglas: Mapping[str, Mapping[str, Any] | None] | None = None,
    casos: Iterable[tuple[str, str, Instantanea]] | None = None,
    difuso: Mapping[str, Any] | None = None,
) -> Propuesta:
    """Valida matrices completas y mide el efecto de una nueva versión."""
    errores: list[str] = []
    avisos: list[str] = []
    contenido = copy.deepcopy(dict(activa.contenido))
    op = contenido["operativa"]
    if len(motivo.strip()) < LONGITUD_MINIMA_MOTIVO:
        errores.append("El motivo técnico necesita al menos quince caracteres.")
    if parametros:
        errores.append("Los vértices y la política se editan dentro del modelo matricial completo.")
    cambios: list[CambioRegla] = []
    modelo = copy.deepcopy(dict(difuso)) if difuso is not None else op["difuso"]
    for ident, definicion in (reglas or {}).items():
        encontrado = False
        for matriz in modelo.get("matrices", {}).values():
            for i, regla in enumerate(matriz["reglas"]):
                if regla["id"] == ident:
                    encontrado = True
                    if definicion is None:
                        matriz["reglas"].pop(i)
                    else:
                        matriz["reglas"][i] = {**dict(definicion), "id": ident}
                    cambios.append(
                        CambioRegla(
                            ident, ident, "RETIRADA" if definicion is None else "MODIFICADA"
                        )
                    )
                    break
        if not encontrado:
            errores.append(
                f"Regla inexistente: {ident}. Las matrices conservan sus antecedentes completos."
            )
    if modelo == op["difuso"]:
        errores.append("La propuesta no cambia el modelo activo.")
    nueva_base, nuevos_parametros = (
        version_base or activa.version_base,
        version_parametros or activa.version_parametros,
    )
    if nueva_base == activa.version_base:
        errores.append("Un cambio del modelo requiere una nueva versión de base.")
    op["difuso"] = modelo
    op["version_base"], op["version_parametros"] = nueva_base, nuevos_parametros
    doc = contenido["documental"]
    doc["version_base"], doc["version_parametros"] = nueva_base, nuevos_parametros
    # La descripción publicada se deriva de las mismas reglas propuestas.
    anteriores = {r["id"]: r for r in doc["reglas"]}
    nuevas = []
    try:
        for matriz in modelo["matrices"].values():
            for r in matriz["reglas"]:
                anterior = anteriores.get(r["id"])
                if anterior is None:
                    errores.append("Identificador no publicado en las matrices activas.")
                    continue
                ficha = copy.deepcopy(anterior)
                ficha["antecedente"] = " Y ".join(
                    f"{modelo['entradas'][h['entrada']]['nombre']} ES {h['conjunto']}"
                    for h in r["si"]["todos"]
                )
                ficha["consecuente"] = r["entonces"]
                ficha["accion"] = next(
                    c["recomendacion"]
                    for c in modelo["clasificacion"]
                    if c["conjunto"] == r["entonces"]
                )
                nuevas.append(ficha)
        doc["reglas"] = nuevas
    except (KeyError, TypeError, StopIteration) as error:
        errores.append(f"Propuesta matricial inválida: {error}")
    base = None
    try:
        base = desde_contenido(contenido)
    except BaseInvalida as error:
        errores.extend(error.errores)
    impacto = None
    if base is not None and not errores:
        impacto = medir_impacto(
            activa, base, casos if casos is not None else cargar_casos_referencia()
        )
        avisos.append("Revisar cobertura, superficie continua y fuentes antes de activar.")
        if impacto.nuevas_autorizaciones:
            avisos.append(
                f"{impacto.nuevas_autorizaciones} casos pasarían a una recomendación favorable: requieren revisión."
            )
    return Propuesta(
        valida=not errores,
        errores=tuple(errores),
        advertencias=tuple(avisos),
        version_base=nueva_base,
        version_parametros=nuevos_parametros,
        motivo=motivo.strip(),
        cambios_parametros=(),
        cambios_reglas=tuple(cambios),
        impacto=impacto,
        contenido=contenido if not errores else None,
        base=base if not errores else None,
    )


def medir_impacto(
    activa: BaseConocimiento,
    propuesta: BaseConocimiento,
    casos: Iterable[tuple[str, str, Instantanea]],
) -> Impacto:
    """Evalúa cada caso con ambas versiones y recoge los que cambian de decisión."""
    from ..dominio.motor import evaluar

    autorizadas = activa.decisiones_autorizadas
    afectados: list[CasoAfectado] = []
    transiciones: dict[str, int] = {}
    evaluados = 0
    nuevas_autorizaciones = 0
    for ident, origen, inst in casos:
        evaluados += 1
        antes, despues = evaluar(inst, activa), evaluar(inst, propuesta)
        reglas_antes, reglas_despues = set(antes.reglas_activadas), set(despues.reglas_activadas)
        if antes.decision_final == despues.decision_final and reglas_antes == reglas_despues:
            continue
        if antes.decision_final != despues.decision_final:
            clave = f"{antes.decision_final} → {despues.decision_final}"
            transiciones[clave] = transiciones.get(clave, 0) + 1
            if despues.decision_final in autorizadas and antes.decision_final not in autorizadas:
                nuevas_autorizaciones += 1
        afectados.append(
            CasoAfectado(
                id=ident,
                origen=origen,
                decision_antes=antes.decision_final,
                decision_despues=despues.decision_final,
                reglas_nuevas=tuple(sorted(reglas_despues - reglas_antes)),
                reglas_retiradas=tuple(sorted(reglas_antes - reglas_despues)),
            )
        )
    cambian = sum(1 for c in afectados if c.decision_antes != c.decision_despues)
    return Impacto(
        evaluados=evaluados,
        cambian=cambian,
        transiciones=dict(sorted(transiciones.items(), key=lambda kv: -kv[1])),
        casos=tuple(afectados),
        nuevas_autorizaciones=nuevas_autorizaciones,
    )
