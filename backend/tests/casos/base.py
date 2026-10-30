"""Datos mínimos y utilidades para probar las cuatro entradas matriciales."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from poscosegran.dominio.hechos import Fase, Instantanea, Modalidad
from poscosegran.dominio.valores import Conjunto, Dato, EstadoDato

AHORA = datetime(2026, 9, 13, 9, 0, tzinfo=UTC)


def num(campo: str, valor: str, unidad: str = "PCT_BH", **extra: Any) -> Dato:
    return Dato(
        campo=campo,
        estado=EstadoDato.VALIDO,
        valor=Decimal(valor),
        unidad=unidad,
        fecha_observacion=AHORA,
        metodo="INSTRUMENTAL",
        **extra,
    )


def txt(campo: str, valor: str) -> Dato:
    return Dato(
        campo=campo,
        estado=EstadoDato.VALIDO,
        valor=valor,
        evidencia="Registro de inspección representativa de la muestra.",
        unidad="TEXTO",
        fecha_observacion=AHORA,
        metodo="REGISTRO",
    )


def desconocido(campo: str) -> Dato:
    return Dato(campo=campo, estado=EstadoDato.DESCONOCIDO)


def datos_base() -> dict[str, Dato]:
    return {
        "humedad_grano": num("humedad_grano", "12"),
        "temperatura_grano": num("temperatura_grano", "10", "CELSIUS"),
        "hr_almacen": num("hr_almacen", "50", "PCT_HR"),
        "estado_fisico_sanitario": txt("estado_fisico_sanitario", "SIN_HALLAZGOS"),
    }


def base(**cambios: Any) -> Instantanea:
    datos = cambios.pop("datos", None)
    inst = Instantanea(
        fecha_evaluacion=AHORA,
        fase=Fase.INGRESO,
        tipo_almacenamiento=Modalidad.NO_HERMETICO,
        datos=Conjunto(datos if datos is not None else datos_base()),
    )
    return replace(inst, **cambios) if cambios else inst


def con(inst: Instantanea, **datos: Dato) -> Instantanea:
    """Devuelve la instantánea con los datos indicados sustituidos."""
    mezcla = dict(inst.datos.datos)
    mezcla.update(datos)
    return replace(inst, datos=Conjunto(mezcla))


def sin(inst: Instantanea, *campos: str) -> Instantanea:
    mezcla = dict(inst.datos.datos)
    for campo in campos:
        mezcla[campo] = desconocido(campo)
    return replace(inst, datos=Conjunto(mezcla))
