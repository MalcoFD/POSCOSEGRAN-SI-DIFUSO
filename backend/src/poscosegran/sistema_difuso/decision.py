"""Decisión final Mamdani: reglas MF01–MF14, agregación por máximo y centroide."""
from collections.abc import Mapping
from typing import Any

from ..dominio.valores import V, F
from ..inferencia.base_hechos import BaseHechos
from ..inferencia.lenguaje import Evaluador
from .defuzzificacion import centroide
from .pertenencia import pertenencia
from .reglas import activacion


def inferir(modelo: Mapping[str, Any], hechos: BaseHechos, evaluador: Evaluador) -> dict[str, Any]:
    """Fuzzificar hechos y salidas intermedias; agregar todas las reglas finales."""
    modulos = {m['id']: m for m in (hechos.difuso or {})['modulos']}
    grados: dict[str, dict[str, float]] = {}
    entradas: dict[str, Any] = {}
    for nombre, variable in modelo['entradas'].items():
        valor: Any = None
        estado = 'CONOCIDO'
        if 'condicion' in variable:
            juicio = evaluador.evaluar(variable['condicion']).valor
            valor = juicio.value
            estado = 'DESCONOCIDO' if juicio not in (V, F) else 'CONOCIDO'
            g = {'presente': float(juicio is V), 'ausente': float(juicio is F)}
        elif 'contexto' in variable:
            fase = hechos.instantanea.fase
            valor = fase.value if fase is not None else 'DESCONOCIDO'
            g = {c: float(c == valor) for c in variable['conjuntos']}
        else:
            modulo = modulos[variable['modulo']]
            valor = modulo['centroide']
            if valor is None:
                estado = 'DESCONOCIDO'
                g = {'presente': 0.0, 'ausente': 0.0} if 'certeza_conjunto' in variable else {c: 0.0 for c in variable['conjuntos']}
            elif 'certeza_conjunto' in variable:
                curvas = modelo['entradas']['conservacion']['conjuntos']
                completa = pertenencia(valor, curvas[variable['certeza_conjunto']]) == 1.0
                g = {'presente': float(completa), 'ausente': float(not completa)}
            else:
                g = {c: pertenencia(valor, puntos) for c, puntos in variable['conjuntos'].items()}
        grados[nombre] = g
        entradas[nombre] = {'nombre': variable['nombre'], 'valor': valor, 'estado': estado,
                            'pertenencias': g, 'definicion': variable}
    reglas = [dict(r, alfa=activacion(r['si'], grados), puntos_salida=modelo['salidas'][r['entonces']])
              for r in modelo['reglas']]
    resultado = centroide([(r['puntos_salida'], r['alfa']) for r in reglas])
    if resultado is None:
        # Un fallo de cobertura no se disfraza de autorización ni de resultado normal.
        raise ValueError('El modelo Mamdani final no tiene cobertura para estos hechos')
    indice, area, curva = resultado
    seleccion = next(c for c in modelo['clasificacion'] if indice < c['hasta'])
    return {'tipo': 'MAMDANI_DECISION_FINAL', 'entradas': entradas, 'reglas': reglas,
            'centroide': indice, 'area': area, 'curva': curva, 'clasificacion': modelo['clasificacion'],
            'decision': seleccion['decision'], 'fundamento': modelo['fundamento'],
            'operadores': {'AND': 'MIN', 'OR': 'MAX', 'implicacion': 'MIN', 'agregacion': 'MAX', 'defuzzificacion': 'CENTROIDE_EXACTO'}}
