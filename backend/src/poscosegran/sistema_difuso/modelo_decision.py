"""Construcción declarativa de la semilla final; se publica en el YAML versionado."""
from typing import Any


def modelo_decision() -> dict[str, Any]:
    def t(entrada: str, conjunto: str = 'presente') -> dict[str, str]:
        return {'entrada': entrada, 'conjunto': conjunto}

    def todos(*nodos: Any) -> dict[str, Any]:
        return {'todos': list(nodos)}

    def alguno(*nodos: Any) -> dict[str, Any]:
        return {'alguno': list(nodos)}

    entradas: dict[str, Any] = {
        'cuarentena': {'nombre': 'Alerta sanitaria o cuarentena abierta', 'condicion': {'alguno': [{'solicitud': 'CUARENTENA'}, {'episodio': ['CUARENTENA']}] }},
        'suspension': {'nombre': 'Condición documental de suspensión', 'condicion': {'solicitud': 'SUSPENSION'}},
        'correccion': {'nombre': 'Hallazgo documental que requiere corrección', 'condicion': {'solicitud': 'CORRECCION'}},
        'pendientes': {'nombre': 'Evidencia aplicable pendiente', 'condicion': {'pendientes': True}},
        'evidencia': {'nombre': 'Evidencia suficiente para autorizar', 'condicion': {'es_verdadero': todos(
            {'definicion': 'condiciones_comunes_aptas'}, {'calculo': 'plazo_compatible'},
            alguno({'definicion': 'rama_condicional_admisible'}, todos({'hecho': 'HUMEDAD_APTA_BASE'}, {'definicion': 'proteccion_requerida'})))}},
        'plan': {'nombre': 'Plan de seguimiento registrado y vigente', 'condicion': {'es_verdadero': {'calculo': 'plan_vigente'}}},
        'monitoreo': {'nombre': 'Motivo documental de seguimiento', 'condicion': {'solicitud': 'MONITOREO'}},
        'condicional': {'nombre': 'Humedad en banda condicional', 'condicion': {'hecho': 'HUMEDAD_CONDICIONAL'}},
        'fase': {'nombre': 'Fase de almacenamiento', 'contexto': 'fase', 'conjuntos': ['INGRESO', 'SEGUIMIENTO', 'DESCONOCIDO']},
        'conservacion': {'nombre': 'Severidad conjunta de conservación', 'modulo': 'condiciones_almacenamiento',
                         'conjuntos': {'bajo': [0, 0, 20, 35], 'medio': [20, 45, 65], 'alto': [50, 65, 100, 100]}},
        'baja_completa': {'nombre': 'Conservación plenamente baja para autorizar sin plan', 'modulo': 'condiciones_almacenamiento', 'certeza_conjunto': 'bajo'},
    }
    reglas: list[dict[str, Any]] = []

    def agregar(ident: str, si: Any, salida: str) -> None:
        reglas.append({'id': ident, 'si': si, 'entonces': salida})

    sin_cuarentena = t('cuarentena', 'ausente')
    sin_suspension = todos(sin_cuarentena, t('suspension', 'ausente'))
    sin_correccion = todos(sin_suspension, t('correccion', 'ausente'))
    completo = todos(sin_correccion, t('pendientes', 'ausente'), t('evidencia'))
    motivo_seguimiento = alguno(t('monitoreo'), t('condicional'))
    sin_motivo = todos(t('monitoreo', 'ausente'), t('condicional', 'ausente'))
    agregar('MF01', t('cuarentena'), 'CUARENTENA')
    agregar('MF02', todos(sin_cuarentena, t('suspension'), t('fase', 'INGRESO')), 'BLOQUEAR_INGRESO')
    agregar('MF03', todos(sin_cuarentena, t('suspension'), t('fase', 'SEGUIMIENTO')), 'RETIRAR_LOTE')
    agregar('MF04', todos(sin_cuarentena, t('suspension'), t('fase', 'DESCONOCIDO')), 'SIN_CONCLUSION_AUTOMATICA')
    agregar('MF05', todos(sin_suspension, t('correccion')), 'CORREGIR_Y_REEVALUAR')
    agregar('MF06', todos(sin_correccion, t('pendientes')), 'SIN_CONCLUSION_AUTOMATICA')
    agregar('MF07', todos(sin_correccion, t('pendientes', 'ausente'), t('evidencia', 'ausente')), 'SIN_CONCLUSION_AUTOMATICA')
    agregar('MF08', todos(completo, t('plan'), t('conservacion', 'bajo'), sin_motivo), 'AUTORIZAR_ALMACENAMIENTO')
    agregar('MF09', todos(completo, t('plan'), t('conservacion', 'bajo'), motivo_seguimiento), 'AUTORIZAR_CON_MONITOREO')
    agregar('MF10', todos(completo, t('plan'), t('conservacion', 'medio')), 'AUTORIZAR_CON_MONITOREO')
    agregar('MF11', todos(completo, t('plan'), t('conservacion', 'alto')), 'CORREGIR_Y_REEVALUAR')
    agregar('MF12', todos(completo, t('plan', 'ausente'), t('baja_completa', 'ausente')), 'CORREGIR_Y_REEVALUAR')
    agregar('MF13', todos(completo, t('plan', 'ausente'), t('baja_completa'), motivo_seguimiento), 'CORREGIR_Y_REEVALUAR')
    agregar('MF14', todos(completo, t('plan', 'ausente'), t('baja_completa'), sin_motivo), 'AUTORIZAR_ALMACENAMIENTO')
    return {
        'entradas': entradas, 'reglas': reglas,
        'salidas': {
            'AUTORIZAR_ALMACENAMIENTO': [0, 0, 6, 12], 'AUTORIZAR_CON_MONITOREO': [20, 28, 36],
            'CORREGIR_Y_REEVALUAR': [44, 52, 60], 'SIN_CONCLUSION_AUTOMATICA': [66, 70, 74],
            'BLOQUEAR_INGRESO': [78, 81, 84], 'RETIRAR_LOTE': [86, 89, 92], 'CUARENTENA': [95, 98, 100],
        },
        'clasificacion': [
            {'hasta': 16, 'decision': 'AUTORIZAR_ALMACENAMIENTO'}, {'hasta': 40, 'decision': 'AUTORIZAR_CON_MONITOREO'},
            {'hasta': 63, 'decision': 'CORREGIR_Y_REEVALUAR'}, {'hasta': 76, 'decision': 'SIN_CONCLUSION_AUTOMATICA'},
            {'hasta': 85, 'decision': 'BLOQUEAR_INGRESO'}, {'hasta': 93.5, 'decision': 'RETIRAR_LOTE'},
            {'hasta': 101, 'decision': 'CUARENTENA'},
        ],
        'fundamento': 'POLITICA_PROTOTIPO: codificación de acciones, curvas y cortes internos; no es una escala física ni probabilidad. Las acciones críticas son mutuamente excluyentes por antecedentes. La ausencia de plan impide interpolar hacia una autorización con monitoreo.',
    }
