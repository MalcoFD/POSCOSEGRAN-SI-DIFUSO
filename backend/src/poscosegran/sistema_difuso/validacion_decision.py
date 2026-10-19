"""Cobertura y no compensación de la decisión final, antes de activar la base."""
from itertools import product
from functools import lru_cache
import json
from typing import Any

from .defuzzificacion import centroide
from .pertenencia import pertenencia, puntos_validos
from .reglas import activacion, referencias

DECISIONES = {'CUARENTENA', 'BLOQUEAR_INGRESO', 'RETIRAR_LOTE', 'CORREGIR_Y_REEVALUAR',
              'SIN_CONCLUSION_AUTOMATICA', 'AUTORIZAR_CON_MONITOREO', 'AUTORIZAR_ALMACENAMIENTO'}


def validar(modelo: Any, modulos: set[str]) -> list[str]:
    # La adquisición simula cientos de casos con el mismo modelo inmutable.
    # Se comprueba exhaustivamente una vez por contenido y dependencias.
    clave = json.dumps(modelo, sort_keys=True, ensure_ascii=True, default=str)
    return list(_validar_cache(clave, tuple(sorted(modulos))))


@lru_cache(maxsize=64)
def _validar_cache(clave: str, modulos: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(_validar(json.loads(clave), set(modulos)))


def _validar(modelo: Any, modulos: set[str]) -> list[str]:
    errores: list[str] = []
    try:
        entradas, reglas = modelo['entradas'], modelo['reglas']
        if not 1 <= len(reglas) <= 80 or len({r['id'] for r in reglas}) != len(reglas):
            return ['decisión Mamdani: reglas vacías, excesivas o duplicadas']
        if set(modelo['salidas']) != DECISIONES or {c['decision'] for c in modelo['clasificacion']} != DECISIONES:
            return ['decisión Mamdani: requiere las siete decisiones y su clasificación']
        cortes = [c['hasta'] for c in modelo['clasificacion']]
        if len(cortes) != 7 or any(a >= b for a, b in zip(cortes, cortes[1:])) or cortes[-1] <= 100:
            return ['decisión Mamdani: clasificación no ordenada o incompleta']
        for decision, puntos in modelo['salidas'].items():
            if not puntos_validos(puntos) or puntos[0] < 0 or puntos[-1] > 100:
                return ['decisión Mamdani: curva de salida inválida']
            for alfa in (.01, .1, .5, 1):
                calculo = centroide([(puntos, alfa)])
                if calculo is None or next(c['decision'] for c in modelo['clasificacion'] if calculo[0] < c['hasta']) != decision:
                    return ['decisión Mamdani: una salida aislada clasifica en otra acción']
        conjuntos: dict[str, set[str]] = {}
        for nombre, e in entradas.items():
            if 'modulo' in e and e['modulo'] not in modulos:
                errores.append('decisión Mamdani: dependencia inexistente o cíclica')
            if 'condicion' in e or 'certeza_conjunto' in e:
                conjuntos[nombre] = {'presente', 'ausente'}
            elif isinstance(e['conjuntos'], list):
                if e.get('contexto') != 'fase' or set(e['conjuntos']) != {'INGRESO', 'SEGUIMIENTO', 'DESCONOCIDO'}:
                    errores.append('decisión Mamdani: contexto inválido')
                conjuntos[nombre] = set(e['conjuntos'])
            else:
                curvas = e['conjuntos']
                if set(curvas) != {'bajo', 'medio', 'alto'} or any(not puntos_validos(p) for p in curvas.values()):
                    errores.append('decisión Mamdani: conjuntos de entrada inválidos')
                conjuntos[nombre] = set(curvas)
                xs = {0, 100, *(v for p in curvas.values() for v in p)}
                if any(not max(pertenencia(x, p) for p in curvas.values()) for x in xs if 0 <= x <= 100):
                    errores.append('decisión Mamdani: conservación sin cobertura')
        for r in reglas:
            if r['entonces'] not in DECISIONES or any(k not in conjuntos or c not in conjuntos[k] for k, c in referencias(r['si'])):
                errores.append('decisión Mamdani: referencia rota')
        necesarios = {'cuarentena', 'suspension', 'correccion', 'pendientes', 'evidencia', 'plan', 'monitoreo', 'condicional', 'fase', 'conservacion', 'baja_completa'}
        if set(entradas) != necesarios:
            errores.append('decisión Mamdani: contrato de antecedentes incompleto')
        if errores:
            return errores
        binarios = sorted(necesarios - {'fase', 'conservacion', 'baja_completa'})
        for valores in product((0, 1), repeat=len(binarios)):
            banderas = dict(zip(binarios, valores))
            for fase, z in product(('INGRESO', 'SEGUIMIENTO', 'DESCONOCIDO'), (0, 20, 27.5, 35, 45, 50, 57.5, 65, 100)):
                grados = {k: {'presente': float(v), 'ausente': float(1-v)} for k, v in banderas.items()}
                grados['fase'] = {f: float(f == fase) for f in conjuntos['fase']}
                grados['conservacion'] = {c: pertenencia(z, p) for c, p in entradas['conservacion']['conjuntos'].items()}
                plena = grados['conservacion']['bajo'] == 1
                grados['baja_completa'] = {'presente': float(plena), 'ausente': float(not plena)}
                activas = {r['entonces'] for r in reglas if activacion(r['si'], grados) > 0}
                if not activas:
                    return ['decisión Mamdani: reglas sin cobertura']
                if banderas['cuarentena'] and activas != {'CUARENTENA'}:
                    return ['decisión Mamdani: una condición crítica se compensa']
                if not banderas['cuarentena'] and banderas['suspension']:
                    esperadas = {
                        'INGRESO': {'BLOQUEAR_INGRESO'},
                        'SEGUIMIENTO': {'RETIRAR_LOTE'},
                        'DESCONOCIDO': {'SIN_CONCLUSION_AUTOMATICA'},
                    }
                    if activas != esperadas[fase]:
                        return ['decisión Mamdani: la suspensión se compensa o cambia de fase']
                if not banderas['cuarentena'] and not banderas['suspension'] and banderas['correccion'] and activas != {'CORREGIR_Y_REEVALUAR'}:
                    return ['decisión Mamdani: una corrección exigida se compensa']
                if not any(banderas[k] for k in ('cuarentena', 'suspension', 'correccion')) and (banderas['pendientes'] or not banderas['evidencia']) and activas != {'SIN_CONCLUSION_AUTOMATICA'}:
                    return ['decisión Mamdani: autoriza sin evidencia suficiente']
                if not banderas['plan'] and 'AUTORIZAR_CON_MONITOREO' in activas:
                    return ['decisión Mamdani: permite monitoreo sin plan']
        if not modelo.get('fundamento'):
            errores.append('decisión Mamdani: fundamento ausente')
    except (KeyError, TypeError, ValueError, StopIteration, RecursionError) as error:
        errores.append(f'decisión Mamdani: estructura inválida ({error})')
    return errores
