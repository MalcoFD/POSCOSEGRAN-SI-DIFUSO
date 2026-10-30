"""Construye las matrices Mamdani explícitas y su catálogo desde criterios declarados.

Este programa se ejecuta al editar el conocimiento, nunca durante una evaluación.
Las matrices publicadas se validan antes de cargarse en PostgreSQL.
"""

from __future__ import annotations

from itertools import product
from pathlib import Path
import json
import yaml

RAIZ = Path(__file__).resolve().parents[2]
NIVELES = ("bajo", "medio", "alto", "muy_alto")
ESTADOS = ("SIN_HALLAZGOS", "DANO_FISICO", "INDICIOS_BIOLOGICOS", "HALLAZGO_CRITICO")
SALIDAS = ("favorable", "vigilancia", "acondicionamiento", "suspension", "separacion")


def nivel(h: int, t: int, hr: int, sanitario: int) -> int:
    """Criterio editorial de la FAM; no es un segundo motor en ejecución."""
    if sanitario == 3:
        return 4
    ambiente = max(h, t, hr)
    if sum(v >= 2 for v in (h, t, hr)) >= 2:
        ambiente = min(3, ambiente + 1)
    elif sum(v >= 1 for v in (h, t, hr)) >= 2:
        ambiente = max(2, ambiente)
    return max(ambiente, (0, 2, 3)[sanitario])


def construir() -> tuple[dict, dict]:
    anterior = yaml.safe_load((RAIZ / "knowledge/catalogo.yaml").read_text(encoding="utf-8"))
    fuentes = anterior["fuentes"]
    entradas = {
        "humedad_grano": {
            "nombre": "Humedad del grano",
            "unidad": "% b.h.",
            "unidad_dato": "PCT_BH",
            "tipo": "CONTINUA",
            "dominio": [0, 100],
            "fuentes": ["S01", "S03", "S04"],
            "conjuntos": dict(
                zip(
                    NIVELES,
                    (
                        [0, 0, 12, 12.5],
                        [12, 12.5, 13, 13.5],
                        [13, 13.5, 14, 14.5],
                        [14, 14.5, 100, 100],
                    ),
                )
            ),
            "fundamento": "Referencias 12–13 % de secado y 14 % de calidad transferidas de maíz amarillo duro. Vértices y etiquetas: diseño del prototipo.",
        },
        "temperatura_grano": {
            "nombre": "Temperatura del grano",
            "unidad": "°C",
            "unidad_dato": "CELSIUS",
            "tipo": "CONTINUA",
            "dominio": [-30, 90],
            "fuentes": ["S01", "S03", "S04"],
            "conjuntos": dict(
                zip(
                    NIVELES,
                    ([-30, -30, 15, 20], [15, 20, 20, 25], [20, 25, 25, 30], [25, 30, 90, 90]),
                )
            ),
            "fundamento": "La referencia ambiental menor de 25 °C se adapta al grano. Transiciones 15–30 °C: diseño preventivo, no límite universal para chulpi.",
        },
        "hr_almacen": {
            "nombre": "Humedad relativa del almacén",
            "unidad": "% HR",
            "unidad_dato": "PCT_HR",
            "tipo": "CONTINUA",
            "dominio": [0, 100],
            "fuentes": ["S01", "S03"],
            "conjuntos": dict(
                zip(
                    NIVELES,
                    ([0, 0, 50, 55], [50, 55, 55, 60], [55, 60, 60, 70], [60, 70, 100, 100]),
                )
            ),
            "fundamento": "Referencia ambiental menor de 60 % HR. Curvas 50–70 %: diseño. Excluida del modelo hermético.",
        },
        "estado_fisico_sanitario": {
            "nombre": "Estado físico y sanitario del grano",
            "unidad": "categoría",
            "unidad_dato": "TEXTO",
            "tipo": "CATEGORICA",
            "dominio": list(ESTADOS),
            "conjuntos": {e: {"valor": e} for e in ESTADOS},
            "fuentes": ["S02", "S04", "S06", "S09"],
            "protocolo": {
                "SIN_HALLAZGOS": "Inspección documentada sin daño físico relevante, indicios de plagas, moho visible ni insectos vivos. Ausencia de inspección no pertenece a este estado.",
                "DANO_FISICO": "Daño físico observado que requiere limpieza o clasificación, sin indicios biológicos ni hallazgo crítico. Describir muestra, tipo de defecto y proporción cuando se mida.",
                "INDICIOS_BIOLOGICOS": "Perforaciones anormales, polvillo o restos compatibles con plagas, sin insectos vivos ni moho observado. Es una sospecha, no un diagnóstico de infestación.",
                "HALLAZGO_CRITICO": "Moho visible o insectos vivos observados en el grano. Documentar el hallazgo; requiere separación y evaluación técnica. No cuantifica micotoxinas.",
            },
            "fundamento": "Cuatro categorías operativas del prototipo, ingresadas directamente por el inspector. Funciones características 0/1; no son cuatro grados continuos de contaminación.",
        },
    }
    salidas = {
        "favorable": [0, 0, 6, 12],
        "vigilancia": [20, 28, 36],
        "acondicionamiento": [44, 52, 60],
        "suspension": [73, 81, 89],
        "separacion": [95, 98, 100],
    }
    clasificacion = [
        {
            "hasta": 16,
            "conjunto": "favorable",
            "decision": "AUTORIZAR_ALMACENAMIENTO",
            "recomendacion": "Condiciones favorables para conservar con controles ordinarios",
            "control_dias": 14,
        },
        {
            "hasta": 40,
            "conjunto": "vigilancia",
            "decision": "AUTORIZAR_CON_MONITOREO",
            "recomendacion": "Conservar con vigilancia reforzada y registrar un plan de seguimiento",
            "control_dias": 7,
        },
        {
            "hasta": 66,
            "conjunto": "acondicionamiento",
            "decision": "CORREGIR_Y_REEVALUAR",
            "recomendacion": "Acondicionar el grano o corregir el ambiente y volver a evaluar",
            "control_dias": 3,
        },
        {
            "hasta": 93,
            "conjunto": "suspension",
            "decision": "SUSPENDER_ALMACENAMIENTO",
            "recomendacion": "Suspender el almacenamiento normal y solicitar revisión técnica",
            "control_dias": 1,
        },
        {
            "hasta": 101,
            "conjunto": "separacion",
            "decision": "CUARENTENA",
            "recomendacion": "Separar el lote y solicitar evaluación técnica por hallazgo sanitario",
            "control_dias": None,
        },
    ]
    matrices = {}
    documental = []
    for modalidad, prefijo in [("NO_HERMETICO", "NH"), ("HERMETICO", "H")]:
        ids = (
            ["humedad_grano", "temperatura_grano"]
            + (["hr_almacen"] if modalidad == "NO_HERMETICO" else [])
            + ["estado_fisico_sanitario"]
        )
        reglas = []
        for i, indices in enumerate(product(range(4), repeat=len(ids)), 1):
            h, t = indices[:2]
            hr = indices[2] if modalidad == "NO_HERMETICO" else 0
            sanitario = indices[-1]
            etiquetas = [
                ESTADOS[v] if k == "estado_fisico_sanitario" else NIVELES[v]
                for k, v in zip(ids, indices)
            ]
            ident = f"{prefijo}{i:03d}"
            consecuente = SALIDAS[nivel(h, t, hr, sanitario)]
            si = {"todos": [{"entrada": k, "conjunto": e} for k, e in zip(ids, etiquetas)]}
            reglas.append({"id": ident, "si": si, "entonces": consecuente})
            antecedente = " Y ".join(
                f'{entradas[k]["nombre"]} ES {e}' for k, e in zip(ids, etiquetas)
            )
            documental.append(
                {
                    "id": ident,
                    "antecedente": antecedente,
                    "consecuente": consecuente,
                    "accion": next(
                        c["recomendacion"] for c in clasificacion if c["conjunto"] == consecuente
                    ),
                    "fundamento_markdown": "POLITICA_PROTOTIPO: matriz diseñada por el equipo a partir de referencias poscosecha. Las fuentes no publican esta regla ni sus curvas.",
                    "fundamento": "MIXTO",
                    "fuentes": ["S01", "S03", "S04"]
                    + (["S06"] if modalidad == "HERMETICO" else []),
                }
            )
        matrices[modalidad] = {
            "id": prefijo,
            "nombre": "Almacenamiento "
            + ("hermético" if modalidad == "HERMETICO" else "no hermético"),
            "entradas": ids,
            "reglas": reglas,
        }
    modelo = {
        "tipo": "MAMDANI_TIPO_1",
        "estructura": "MATRICIAL_DIRECTA",
        "operadores": {
            "AND": "MIN",
            "implicacion": "MIN",
            "agregacion": "MAX",
            "defuzzificacion": "CENTROIDE_EXACTO",
        },
        "entradas": entradas,
        "matrices": matrices,
        "salidas": salidas,
        "clasificacion": clasificacion,
        "politica": {
            "vigencia_medicion_horas": 168,
            "fundamento": "Ventana de siete días y controles por recomendación: política del prototipo. La inspección interna debe seguir siendo representativa y no estar invalidada por eventos.",
        },
        "fundamento": "Una inferencia Mamdani directa por modalidad; 256 + 64 reglas explícitas. No hay agenda de producciones ni segunda etapa de decisión. Índice de intervención, no probabilidad ni certificación de inocuidad.",
    }
    operativa = {
        "version_base": "6.0",
        "version_parametros": "2.0",
        "parametros": {},
        "difuso": modelo,
    }
    catalogo = {
        "version_base": "6.0",
        "version_parametros": "2.0",
        "version_motor": "4.0.0-matricial",
        "fuentes": fuentes,
        "reglas": documental,
    }
    return operativa, catalogo


if __name__ == "__main__":
    operativa, catalogo = construir()
    for nombre, contenido in [("base_conocimiento", operativa), ("catalogo", catalogo)]:
        (RAIZ / "knowledge" / f"{nombre}.yaml").write_text(
            yaml.safe_dump(contenido, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
    (RAIZ / "knowledge/matriz_320.json").write_text(
        json.dumps(operativa["difuso"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("Modelo 6.0 generado: 256 reglas no herméticas y 64 herméticas.")
