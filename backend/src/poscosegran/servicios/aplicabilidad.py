"""Comprueba NO_APLICA con hechos de contexto; el motivo por sí solo no basta."""
from dataclasses import replace

from ..dominio.valores import Dato, EstadoDato, F, V


def comprobar(datos: dict[str, Dato], modalidad: str | None, fase: str | None) -> dict[str, Dato]:
    salida = dict(datos)
    hermetico = modalidad == "HERMETICO"
    no_hermetico = modalidad == "NO_HERMETICO"
    def booleano(campo: str):  # type: ignore[no-untyped-def]
        return datos.get(campo, Dato(campo)).booleano
    for campo, dato in datos.items():
        if not dato.no_aplica:
            continue
        permitido = False
        if campo == "temperatura_muestra":
            permitido = datos.get("metodo_humedad", Dato("")).texto == "LABORATORIO"
        elif campo == "actividad_agua":
            permitido = booleano("aw_medida") is F
        elif campo in {"temperatura_grano_previa", "punto_medicion_previo", "metodo_termico_previo"}:
            permitido = not datos.get("temperatura_grano_previa", Dato("")).utilizable
        elif campo in {"temperatura_aire_exterior", "hr_aire_exterior", "lluvia_o_niebla",
                       "humedad_equilibrio_maiz", "tabla_equilibrio_id"}:
            permitido = hermetico
        elif campo in {"sello_integro", "perforacion_barrera", "bolsa_abierta_sin_resellar",
                       "condensacion_interna", "sensor_interno_hermetico", "fecha_inspeccion_exterior"}:
            permitido = no_hermetico
        elif campo == "temperatura_ambiente_maxima_intervalo":
            permitido = no_hermetico or booleano("sensor_interno_hermetico") is V
        elif campo == "fecha_inspeccion_grano":
            permitido = hermetico and fase == "SEGUIMIENTO"
        elif campo in {"ingreso_inspeccionado", "limpieza_previa_nuevo_lote"}:
            permitido = fase == "SEGUIMIENTO"
        elif campo == "limpieza_tras_operaciones":
            # La matriz permite ausencia documentada de operaciones.
            permitido = bool((dato.motivo_no_aplica or "").strip())
        elif campo == 'fecha_vencimiento_producto':
            aplicable = datos.get('vencimiento_aplicable', Dato('vencimiento_aplicable'))
            permitido = aplicable.booleano is F or aplicable.no_aplica
        elif campo in {'distancia_entre_estantes', 'vencimiento_aplicable'}:
            # El catálogo actual no dispone de otro indicador de estantes o
            # vencimiento comercial. La exclusión requiere constancia explícita.
            permitido = bool((dato.motivo_no_aplica or '').strip())
        if not permitido:
            salida[campo] = replace(dato, no_aplica=False, estado=EstadoDato.INVALIDO)
    return salida
