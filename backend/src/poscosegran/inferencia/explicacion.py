"""Módulo de explicación.

    ¿Cómo?              La cadena de reglas documentales que se dispararon y el
                        centroide Mamdani que clasificó la decisión final.
    ¿Por qué se pide?   Qué reglas usan un dato antes de que el usuario lo aporte.

Trabaja solo con la traza que deja el motor y con la base de conocimiento; no
vuelve a razonar sobre el caso, de modo que explica exactamente lo que ocurrió.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .base_conocimiento import BaseConocimiento
from .base_hechos import Activacion
from .motor import Resultado

ETIQUETA_DECISION = {
    "SUSPENDER_ALMACENAMIENTO": "Suspender almacenamiento en las condiciones actuales",
    "CUARENTENA": "Separar y solicitar evaluación técnica",
    "BLOQUEAR_INGRESO": "Ingreso no autorizado",
    "RETIRAR_LOTE": "Suspender almacenamiento en las condiciones actuales",
    "CORREGIR_Y_REEVALUAR": "Corregir y volver a evaluar",
    "SIN_CONCLUSION_AUTOMATICA": "Faltan datos o revisión",
    "AUTORIZAR_CON_MONITOREO": "Almacenamiento autorizado con seguimiento reforzado",
    "AUTORIZAR_ALMACENAMIENTO": "Almacenamiento autorizado con controles ordinarios",
}


@dataclass(frozen=True, slots=True)
class Paso:
    orden: int
    regla: str
    etapa: str
    pasada: int
    conclusion: str | None
    solicitudes: tuple[str, ...]
    porque: tuple[str, ...]
    antecedente: str | None


@dataclass(frozen=True, slots=True)
class Explicacion:
    decision: str
    etiqueta: str
    resumen: str
    cadena: tuple[Paso, ...]
    hechos_iniciales: tuple[tuple[str, object, str], ...]
    hechos_inferidos: tuple[str, ...]
    no_aplicables: tuple[str, ...]


def _antecedentes(base: BaseConocimiento) -> dict[str, str]:
    return {r["id"]: r.get("antecedente", "") for r in base.documental.get("reglas", [])}


def _paso(activacion: Activacion, antecedentes: Mapping[str, str]) -> Paso:
    return Paso(
        orden=activacion.orden,
        regla=activacion.regla,
        etapa=activacion.etapa,
        pasada=activacion.pasada,
        conclusion=activacion.hallazgo,
        solicitudes=activacion.solicitudes,
        porque=activacion.soportes,
        antecedente=antecedentes.get(activacion.regla),
    )


def explicar(resultado: Resultado, base: BaseConocimiento) -> Explicacion:
    informe = (resultado.difuso or {})["decision"]
    etiqueta = ETIQUETA_DECISION[resultado.decision_final]
    indice = informe["centroide"]
    resumen = (
        (
            f"La matriz {informe['matriz']} evaluó {len(informe['reglas'])} reglas; "
            f"{len(resultado.reglas_activadas)} tuvieron activación positiva. "
            f"El centroide {indice:.3f} corresponde a: {etiqueta}."
        )
        if indice is not None
        else (
            "No se calculó un índice: completar o corregir las entradas indicadas. No se sustituyen datos desconocidos por condiciones favorables."
        )
    )
    antecedentes = _antecedentes(base)
    return Explicacion(
        decision=resultado.decision_final,
        etiqueta=etiqueta,
        resumen=resumen,
        cadena=tuple(_paso(a, antecedentes) for a in resultado.traza),
        hechos_iniciales=resultado.hechos_iniciales,
        hechos_inferidos=resultado.hechos_inferidos,
        no_aplicables=resultado.no_aplicables,
    )


@dataclass(frozen=True, slots=True)
class PorQueSePide:
    campo: str
    reglas: tuple[str, ...]
    texto: str


def por_que_se_pide(campo: str, base: BaseConocimiento) -> PorQueSePide:
    reglas = base.uso_de_campos.get(campo, ())
    if not reglas:
        texto = "Ninguna regla usa este dato para decidir; se registra como contexto del caso."
    else:
        antecedentes = _antecedentes(base)
        primeras = "; ".join(f"{r}: {antecedentes.get(r, '')}".strip(": ") for r in reglas[:3])
        extra = f" y {len(reglas) - 3} más" if len(reglas) > 3 else ""
        texto = f"Lo usan {', '.join(reglas)}. Por ejemplo, {primeras}{extra}."
    return PorQueSePide(campo=campo, reglas=reglas, texto=texto)
