"""Validación estructural de las dos matrices completas de inferencia directa."""

from __future__ import annotations

from collections import Counter
from itertools import product
import math
from typing import Any

from .pertenencia import pertenencia, puntos_validos

OPERADORES = {
    "AND": "MIN",
    "implicacion": "MIN",
    "agregacion": "MAX",
    "defuzzificacion": "CENTROIDE_EXACTO",
}
ESTADOS = ("SIN_HALLAZGOS", "DANO_FISICO", "INDICIOS_BIOLOGICOS", "HALLAZGO_CRITICO")


def validar(modelo: Any) -> list[str]:
    errores: list[str] = []
    try:
        if modelo["tipo"] != "MAMDANI_TIPO_1" or modelo["estructura"] != "MATRICIAL_DIRECTA":
            return ["Se requiere Mamdani tipo 1 matricial directo."]
        if modelo["operadores"] != OPERADORES:
            errores.append("Operadores distintos del contrato Mamdani MIN/MIN/MAX/centroide.")
        entradas = modelo["entradas"]
        if set(entradas) != {
            "humedad_grano",
            "temperatura_grano",
            "hr_almacen",
            "estado_fisico_sanitario",
        }:
            return ["El modelo requiere las cuatro entradas declaradas."]
        for k, e in entradas.items():
            if (k == "estado_fisico_sanitario") != (e["tipo"] == "CATEGORICA"):
                errores.append(f"{k}: tipo de entrada incompatible con el protocolo.")
            if len(e["conjuntos"]) != 4:
                errores.append(f"{k}: se necesitan cuatro etiquetas.")
            if e["tipo"] == "CATEGORICA":
                if tuple(e["dominio"]) != ESTADOS or set(e["conjuntos"]) != set(ESTADOS):
                    errores.append("Protocolo sanitario incompleto.")
                continue
            a, b = e["dominio"]
            curvas = e["conjuntos"]
            if set(curvas) != {"bajo", "medio", "alto", "muy_alto"}:
                errores.append(f"{k}: etiquetas numéricas ajenas al modelo.")
            if not a < b or any(
                not puntos_validos(p) or p[0] < a or p[-1] > b for p in curvas.values()
            ):
                errores.append(f"{k}: dominio o curvas inválidos.")
                continue
            xs = sorted({a, b, *(x for p in curvas.values() for x in p)})
            xs += [(x + y) / 2 for x, y in zip(xs, xs[1:])]
            if any(max(pertenencia(x, p) for p in curvas.values()) <= 0 for x in xs):
                errores.append(f"{k}: región sin cobertura.")
        salidas = modelo["salidas"]
        if len(salidas) != 5 or any(
            not puntos_validos(p) or p[0] < 0 or p[-1] > 100 for p in salidas.values()
        ):
            errores.append("Se necesitan cinco curvas de salida válidas en [0,100].")
        clases = modelo["clasificacion"]
        decisiones = [
            "AUTORIZAR_ALMACENAMIENTO",
            "AUTORIZAR_CON_MONITOREO",
            "CORREGIR_Y_REEVALUAR",
            "SUSPENDER_ALMACENAMIENTO",
            "CUARENTENA",
        ]
        conjuntos = ["favorable", "vigilancia", "acondicionamiento", "suspension", "separacion"]
        if [c["decision"] for c in clases] != decisiones or [
            c["conjunto"] for c in clases
        ] != conjuntos:
            errores.append(
                "Las cinco recomendaciones deben conservar su orden y significado sanitario."
            )
        for c in clases:
            dias = c["control_dias"]
            if dias is not None and (
                not isinstance(dias, (int, float)) or not math.isfinite(dias) or dias <= 0
            ):
                errores.append("Intervalo de control inválido.")
        horas = modelo["politica"]["vigencia_medicion_horas"]
        if not isinstance(horas, (int, float)) or not math.isfinite(horas) or not 0 < horas <= 168:
            errores.append("La vigencia de observación debe estar entre cero y 168 horas.")
        limites = [c["hasta"] for c in clases]
        if (
            len(clases) != 5
            or limites[-1] <= 100
            or any(a >= b for a, b in zip(limites, limites[1:]))
        ):
            errores.append("Clasificación de salida incompleta o desordenada.")
        orden = {c["conjunto"]: i for i, c in enumerate(clases)}
        if set(orden) != set(salidas):
            errores.append("La clasificación no corresponde a las salidas.")
        if set(modelo["matrices"]) != {"HERMETICO", "NO_HERMETICO"}:
            return errores + ["Se necesitan ambas modalidades."]
        ids: list[str] = []
        for modalidad, matriz in modelo["matrices"].items():
            prefijo, cantidad = ("H", 64) if modalidad == "HERMETICO" else ("NH", 256)
            if {r["id"] for r in matriz["reglas"]} != {
                f"{prefijo}{i:03d}" for i in range(1, cantidad + 1)
            }:
                errores.append(f"{modalidad}: identificadores fuera de la matriz publicada.")
            campos = (
                ["humedad_grano", "temperatura_grano"]
                + (["hr_almacen"] if modalidad == "NO_HERMETICO" else [])
                + ["estado_fisico_sanitario"]
            )
            if matriz["entradas"] != campos:
                errores.append(f"{modalidad}: antecedentes no corresponden a la modalidad.")
            esperadas = set(product(*(entradas[k]["conjuntos"] for k in campos)))
            halladas: list[tuple[str, ...]] = []
            por_combinacion: dict[tuple[str, ...], int] = {}
            for r in matriz["reglas"]:
                ids.append(r["id"])
                hojas = r["si"]["todos"]
                if [h["entrada"] for h in hojas] != campos:
                    errores.append(
                        f'{r["id"]}: debe contener una vez cada antecedente, unido por AND.'
                    )
                    continue
                combinacion = tuple(h["conjunto"] for h in hojas)
                halladas.append(combinacion)
                if r["entonces"] not in orden:
                    errores.append(f'{r["id"]}: consecuente desconocido.')
                    continue
                por_combinacion[combinacion] = orden[r["entonces"]]
                if combinacion[-1] == "HALLAZGO_CRITICO" and r["entonces"] != "separacion":
                    errores.append(f'{r["id"]}: el hallazgo crítico no debe compensarse.')
                if combinacion[-1] != "HALLAZGO_CRITICO" and r["entonces"] == "separacion":
                    errores.append(f'{r["id"]}: separación sanitaria sin hallazgo crítico.')
            if set(halladas) != esperadas or len(halladas) != len(esperadas):
                errores.append(
                    f"{modalidad}: matriz incompleta o antecedentes duplicados; se requieren {len(esperadas)}."
                )
            # Monotonía en la retícula lingüística. La superficie continua se prueba aparte.
            # JSONB no conserva el orden de las claves. La gravedad es semántica.
            etiquetas = [list(ESTADOS) if k == "estado_fisico_sanitario" else ["bajo", "medio", "alto", "muy_alto"] for k in campos]
            for indices in product(range(4), repeat=len(campos)):
                c = tuple(etiquetas[i][v] for i, v in enumerate(indices))
                if c not in por_combinacion:
                    continue
                for eje in range(len(campos)):
                    if indices[eje] == 3:
                        continue
                    vecino = list(c)
                    vecino[eje] = etiquetas[eje][indices[eje] + 1]
                    if (
                        tuple(vecino) in por_combinacion
                        and por_combinacion[tuple(vecino)] < por_combinacion[c]
                    ):
                        errores.append(
                            f"{modalidad}: inversión lingüística entre {c} y {tuple(vecino)}."
                        )
        if len(ids) != 320 or any(n != 1 for n in Counter(ids).values()):
            errores.append("Deben existir exactamente 320 identificadores únicos.")
    except (KeyError, TypeError, ValueError, IndexError, AttributeError) as error:
        errores.append(f"Estructura matricial inválida: {error}")
    return list(dict.fromkeys(errores))
