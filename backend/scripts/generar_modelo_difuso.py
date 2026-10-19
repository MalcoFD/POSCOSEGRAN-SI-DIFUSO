"""Genera la base Mamdani 5.0 desde la base documental; conserva el historial."""
from pathlib import Path
from typing import Any

import yaml


def generar(carpeta: Path) -> None:
    base = yaml.safe_load((carpeta / 'base_conocimiento.yaml').read_text(encoding='utf-8'))
    catalogo = yaml.safe_load((carpeta / 'catalogo.yaml').read_text(encoding='utf-8'))
    base['version_base'] = catalogo['version_base'] = '5.0'
    catalogo['version_motor'] = '3.0.0-mamdani'
    no_hermetico = {'contexto': 'tipo_almacenamiento', 'igual': 'NO_HERMETICO'}
    hermetico = {'contexto': 'tipo_almacenamiento', 'igual': 'HERMETICO'}
    entradas: dict[str, Any] = {}
    for campo, regla, r, w, dominio, unidad, nombre in [
        ('humedad_grano', 'R02', 13, .5, [0, 100], '% b.h.', 'Humedad del grano'),
        ('temperatura_grano', 'R08', 25, 5, [-30, 90], '°C', 'Temperatura del grano'),
        ('hr_almacen', 'R07', 60, 10, [0, 100], '% HR', 'Humedad relativa del almacén'),
        ('granos_defectuosos', 'R21', 7, 1, [0, 100], '% masa', 'Granos defectuosos'),
    ]:
        entradas[campo] = {
            'id': campo, 'nombre': nombre, 'origen': regla, 'unidad': unidad,
            'entrada': {'tipo': 'dato', 'campo': campo}, 'dominio': dominio,
            'conjuntos': {'bajo': [dominio[0], dominio[0], r-w, r], 'medio': [r-w, r, r+w], 'alto': [r, r+w, dominio[1], dominio[1]]},
            'referencia': r,
            'fundamento_transicion': f'POLITICA_PROTOTIPO: transición ±{w:g} {unidad} alrededor de {r:g}; pendiente de calibración agronómica.',
        }
    entradas['humedad_grano']['valido_si'] = {'definicion': 'medicion_confirmada'}
    entradas['hr_almacen']['aplica_si'] = no_hermetico
    comunes = ['humedad_grano', 'temperatura_grano', 'granos_defectuosos']

    def termino(campo: str, conjunto: str) -> dict[str, str]:
        return {'entrada': campo, 'conjunto': conjunto}

    reglas: list[dict[str, Any]] = [
        {'id': 'D01', 'si': {'todos': [termino(c, 'bajo') for c in entradas]}, 'entonces': 'bajo', 'aplica_si': no_hermetico},
        {'id': 'D02', 'si': {'todos': [termino(c, 'bajo') for c in comunes]}, 'entonces': 'bajo', 'aplica_si': hermetico},
        {'id': 'D03', 'si': {'alguno': [termino(c, 'medio') for c in comunes]}, 'entonces': 'medio'},
        {'id': 'D04', 'si': termino('hr_almacen', 'medio'), 'entonces': 'medio', 'aplica_si': no_hermetico},
        {'id': 'D05', 'si': {'alguno': [termino(c, 'alto') for c in comunes]}, 'entonces': 'alto'},
        {'id': 'D06', 'si': termino('hr_almacen', 'alto'), 'entonces': 'alto', 'aplica_si': no_hermetico},
    ]
    for ident, a, b in [('D07', 'humedad_grano', 'temperatura_grano'), ('D08', 'humedad_grano', 'hr_almacen'), ('D09', 'temperatura_grano', 'hr_almacen')]:
        regla: dict[str, Any] = {'id': ident, 'si': {'todos': [termino(a, 'medio'), termino(b, 'medio')]}, 'entonces': 'alto'}
        if b == 'hr_almacen':
            regla['aplica_si'] = no_hermetico
        reglas.append(regla)
    origenes = {e['origen'] for e in entradas.values()}
    # La ampliación de 28 campos no puede quedar fuera de los requisitos de
    # autorización. Los condicionales y la logística se tratan por separado.
    from poscosegran.dominio.campos import CAMPOS
    condicionales = {'separacion_cuarentena_verificada', 'fecha_vencimiento_producto', 'rotacion_no_justificada'}
    nuevos = [k for k, v in CAMPOS.items() if v.paso >= 6 and k not in condicionales]
    base['datos_exigibles'].append({'cuando': {'siempre': True}, 'campos': nuevos, 'motivo': 'Comprobación necesaria de la ampliación R31–R52; registrar observación o NO_APLICA permitido.'})
    base['datos_exigibles'].append({'cuando': {'dato': 'vencimiento_aplicable'}, 'campos': ['fecha_vencimiento_producto'], 'motivo': 'El vencimiento comercial aplicable requiere fecha documentada.'})
    base['datos_exigibles'].append({'cuando': {'episodio': ['CUARENTENA']}, 'campos': ['separacion_cuarentena_verificada'], 'motivo': 'Documentar el aislamiento de la unidad en cuarentena.'})
    riesgos = base['definiciones']['riesgo_activo']['alguno']
    riesgos.append({'algun_hecho': [r['entonces']['hallazgo'] for r in base['reglas'] if r['id'] in {f'R{n}' for n in range(31, 53)} - {'R44', 'R47'}]})
    riesgos.append({'es_desconocido': {'conocidos': nuevos}})
    base['difuso'] = {
        'tipo': 'MAMDANI_TIPO_1', 'estructura': 'MULTIVARIABLE',
        'operadores': {'AND': 'MIN', 'OR': 'MAX', 'implicacion': 'MIN', 'agregacion': 'MAX', 'defuzzificacion': 'CENTROIDE_EXACTO'},
        'politica': {'monitoreo_desde': 35, 'correccion_desde': 65, 'fundamento': 'POLITICA_PROTOTIPO: cortes de severidad, no probabilidades ni límites publicados.'},
        'salidas': {'bajo': [0, 0, 10, 25], 'medio': [20, 50, 80], 'alto': [70, 85, 100, 100]},
        'modulos': [{
            'id': 'condiciones_almacenamiento', 'nombre': 'Condiciones conjuntas de almacenamiento',
            'origen': 'R02', 'origenes': sorted(origenes), 'entradas': entradas, 'reglas': reglas,
            'fundamento_transicion': 'POLITICA_PROTOTIPO: severidad conjunta; las interacciones medias D07–D09 refuerzan la prevención. Las fuentes respaldan variables y referencias, no estas nueve reglas ni sus curvas.',
        }],
        'cobertura': {r['id']: ('MAMDANI_Y_RESTRICCION' if r['id'] in origenes else 'RESTRICCION_O_CONTEXTO') for r in catalogo['reglas']},
    }
    from poscosegran.sistema_difuso.modelo_decision import modelo_decision
    base['difuso']['decision'] = modelo_decision()
    base['difuso']['cobertura'] = {r['id']: ('RECOMENDACION' if r['id'] in {'R10', 'R11', 'R47'} else 'ANTECEDENTE_O_REGLA_MAMDANI') for r in catalogo['reglas']}
    for r in catalogo['reglas']:
        if r['id'] in origenes:
            r['fundamento_markdown'] += '\n\nBase 5.0: esta variable participa en el núcleo Mamdani conjunto. Curvas, interacciones y cortes son POLITICA_PROTOTIPO; se conservan los límites exactos documentados.'
    destino = carpeta / 'difuso'
    destino.mkdir(exist_ok=True)
    for nombre, contenido in [('base_conocimiento.yaml', base), ('catalogo.yaml', catalogo)]:
        (destino / nombre).write_text(yaml.safe_dump(contenido, allow_unicode=True, sort_keys=False), encoding='utf-8')


if __name__ == '__main__':
    generar(Path(__file__).resolve().parents[2] / 'knowledge')
