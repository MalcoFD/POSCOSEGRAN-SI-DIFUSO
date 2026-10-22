"""Rechazo de modelos difusos incompletos antes de registrar o activar versiones."""
import math
from itertools import product
from collections.abc import Mapping
from typing import Any

from .pertenencia import pertenencia, puntos_validos
from .reglas import activacion, aplica, referencias


def validar(modelo: Any, reglas: set[str], campos: set[str]) -> list[str]:
    """Núcleo multivariable de conservación y decisión Mamdani final."""
    if not isinstance(modelo, Mapping) or modelo.get('tipo') != 'MAMDANI_TIPO_1':
        return ['difuso: tipo requerido MAMDANI_TIPO_1']
    if modelo.get('estructura') != 'MULTIVARIABLE':
        return ['difuso: estructura requerida MULTIVARIABLE']
    if 'decision' not in modelo:
        return ['difuso: falta la decisión Mamdani final']
    errores = _multivariable(modelo, reglas, campos)
    if not errores:
        from .validacion_decision import validar as validar_decision
        errores.extend(validar_decision(modelo['decision'], {m['id'] for m in modelo['modulos']}))
    return errores


def _curvas(modelo: Mapping[str, Any], reglas: set[str], campos: set[str]) -> list[str]:
    """Operadores, consecuentes, cobertura documental y curvas de cada entrada."""
    errores: list[str] = []
    try:
        if modelo.get('operadores') != {'AND': 'MIN', 'OR': 'MAX', 'implicacion': 'MIN', 'agregacion': 'MAX', 'defuzzificacion': 'CENTROIDE_EXACTO'}:
            errores.append('difuso: operadores no compatibles con esta versión del motor')
        limites = modelo['politica']
        if not 0 < limites['monitoreo_desde'] < limites['correccion_desde'] < 100:
            errores.append('difuso: cortes de monitoreo/corrección deben estar ordenados en (0,100)')
        salidas = modelo['salidas']
        if set(salidas) != {'bajo', 'medio', 'alto'} or any(not puntos_validos(p) for p in salidas.values()):
            errores.append('difuso: consecuentes bajo/medio/alto inválidos')
        if any(p[0] < 0 or p[-1] > 100 for p in salidas.values()):
            errores.append('difuso: las salidas deben pertenecer al universo [0,100]')
        if set(modelo['cobertura']) != reglas:
            errores.append('difuso: la cobertura debe incluir exactamente las reglas documentales')
        ids: set[str] = set()
        for modulo in modelo['modulos']:
            ident = str(modulo['id'])
            if ident in ids:
                errores.append(f'difuso: módulo duplicado {ident}')
            ids.add(ident)
            if modulo['origen'] not in reglas:
                errores.append(f'difuso.{ident}: regla de origen inexistente')
            if modulo['entrada'].get('campo') not in campos:
                errores.append(f'difuso.{ident}: campo inexistente')
            dominio = modulo['dominio']
            if len(dominio) != 2 or not all(math.isfinite(float(n)) for n in dominio) or dominio[0] >= dominio[1]:
                errores.append(f'difuso.{ident}: dominio inválido')
            conjuntos = modulo['conjuntos']
            if set(conjuntos) != set(salidas) or any(not puntos_validos(p) for p in conjuntos.values()):
                errores.append(f'difuso.{ident}: conjuntos inválidos')
                continue
            if any(p[0] < dominio[0] or p[-1] > dominio[1] for p in conjuntos.values()):
                errores.append(f'difuso.{ident}: conjunto fuera de su dominio')
            # Los mínimos de la suma de funciones lineales ocurren en vértices.
            puntos = {float(n) for p in conjuntos.values() for n in p} | set(dominio)
            if any(sum(pertenencia(x, p) for p in conjuntos.values()) <= 0 for x in puntos if dominio[0] <= x <= dominio[1]):
                errores.append(f'difuso.{ident}: región sin cobertura')
            if not modulo.get('fundamento_transicion'):
                errores.append(f'difuso.{ident}: falta justificar la transición')
        if not ids:
            errores.append('difuso: se necesita al menos un módulo')
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        errores.append(f'difuso: estructura inválida ({error})')
    return errores


def _antecedente(nodo: Any, entradas: Mapping[str, Any], profundidad: int = 0) -> None:
    if profundidad > 8 or not isinstance(nodo, Mapping):
        raise ValueError('antecedente inválido o demasiado profundo')
    if set(nodo) == {'entrada', 'conjunto'}:
        if nodo['entrada'] not in entradas or nodo['conjunto'] not in {'bajo', 'medio', 'alto'}:
            raise ValueError('referencia lingüística inexistente')
        return
    if set(nodo) not in ({'todos'}, {'alguno'}):
        raise ValueError('antecedente admite todos, alguno o entrada/conjunto')
    hijos = next(iter(nodo.values()))
    if not isinstance(hijos, list) or not 1 <= len(hijos) <= 12:
        raise ValueError('antecedente vacío o excesivo')
    for hijo in hijos:
        _antecedente(hijo, entradas, profundidad + 1)


def _multivariable(modelo: Mapping[str, Any], reglas: set[str], campos: set[str]) -> list[str]:
    errores: list[str] = []
    try:
        modulos = modelo['modulos']
        if not isinstance(modulos, list) or len(modulos) != 1:
            return ['difuso: el núcleo multivariable requiere un único módulo']
        modulo = modulos[0]
        entradas = modulo['entradas']
        if not isinstance(entradas, Mapping) or not 2 <= len(entradas) <= 6:
            return ['difuso: el núcleo requiere de dos a seis entradas']
        errores.extend(_curvas({**modelo, 'modulos': list(entradas.values())}, reglas, campos))
        if modulo['origen'] not in reglas or not set(modulo['origenes']) <= reglas:
            errores.append('difuso: orígenes del núcleo inexistentes')
        if not modulo.get('fundamento_transicion'):
            errores.append('difuso: falta justificar las interacciones')
        if any(k != e['id'] or e['entrada']['tipo'] != 'dato' for k, e in entradas.items()):
            errores.append('difuso: identificación de entrada inválida; solo mediciones directas')
        producciones = modulo['reglas']
        if not isinstance(producciones, list) or not 1 <= len(producciones) <= 128:
            return errores + ['difuso: cantidad de reglas inválida']
        ids: set[str] = set()
        for objeto in [*entradas.values(), *producciones]:
            guarda = objeto.get('aplica_si')
            if guarda is not None and not any(aplica(guarda, m) for m in ('HERMETICO', 'NO_HERMETICO')):
                errores.append('difuso: guarda de modalidad inválida')
        for regla in producciones:
            if not isinstance(regla['id'], str) or not regla['id'] or regla['id'] in ids:
                errores.append('difuso: identificador de regla vacío o duplicado')
            ids.add(regla['id'])
            _antecedente(regla['si'], entradas)
            if regla['entonces'] not in modelo['salidas']:
                errores.append('difuso: consecuente inexistente')
        if errores:
            return errores
        for modalidad in ('HERMETICO', 'NO_HERMETICO'):
            activas = {k: e for k, e in entradas.items() if aplica(e.get('aplica_si'), modalidad)}
            habilitadas = [r for r in producciones if aplica(r.get('aplica_si'), modalidad)]
            usadas = set().union(*(referencias(r['si']) for r in habilitadas))
            if {k for k, _ in usadas} != set(activas):
                errores.append(f'difuso: entradas omitidas o inaplicables en reglas de {modalidad}')
                continue
            # Comprobar todas las combinaciones lingüísticas, no generar reglas.
            for terminos in product(('bajo', 'medio', 'alto'), repeat=len(activas)):
                grados = {k: {c: float(c == t) for c in ('bajo', 'medio', 'alto')}
                          for k, t in zip(activas, terminos)}
                if not any(activacion(r['si'], grados) > 0 for r in habilitadas):
                    errores.append(f'difuso: reglas sin cobertura en {modalidad}: {terminos}')
                    break
    except (KeyError, TypeError, ValueError, OverflowError, AttributeError) as error:
        errores.append(f'difuso: estructura multivariable inválida ({error})')
    return errores
