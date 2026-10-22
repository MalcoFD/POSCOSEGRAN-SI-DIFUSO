"""Regresiones de la ampliación R31–R52 sobre PostgreSQL real."""
from datetime import UTC, datetime, timedelta

import pytest

from test_integracion_api import agregar, entrada, post, unidad


def observacion(campo, valor):
    return {'campo': campo, 'captura': 'APORTADO', 'valor': valor, 'unidad': 'BOOLEANO',
            'valor_original': str(valor), 'fecha_observacion': (datetime.now(UTC)-timedelta(seconds=1)).isoformat(),
            'metodo': 'Inspección documentada', 'evidencia': 'Acta de revisión', 'motivo_no_aplica': None}


@pytest.mark.bd
@pytest.mark.parametrize('campos', [
    ['humedad_por_agua_en_unidad'], ['contacto_con_unidad_en_cuarentena'],
    ['grano_derramado_reincorporado'],
    ['aplicacion_plaguicida_sin_registro_competente', 'exposicion_quimica_del_grano'],
])
def test_cuarentena_nueva_persiste_y_no_la_cierra_una_medicion(api_real, campos):
    c, _, _ = api_real
    u = unidad(c)
    body = entrada(u)
    agregar(body, *[observacion(k, True) for k in campos])
    r = post(c, f'/unidades/{u["id"]}/evaluaciones', body)
    assert r['evaluacion']['decision_final'] == 'CUARENTENA'
    episodios = c.get(f'/api/v1/unidades/{u["id"]}/incidencias').json()['items']
    assert len(episodios) == 1 and episodios[0]['tipo'] == 'CUARENTENA'
    if len(campos) == 2:
        assert set(episodios[0]['causas']) == {'R50', 'R51'}
    u = c.get('/api/v1/unidades/' + u['id']).json()
    body = entrada(u)
    agregar(body, *[observacion(k, False) for k in campos])
    r = post(c, f'/unidades/{u["id"]}/evaluaciones', body)
    assert r['evaluacion']['decision_final'] == 'CUARENTENA'
    assert r['vigencia']['estado'] != 'VIGENTE'


def test_no_aplica_vencimiento_con_contexto():
    from poscosegran.dominio.valores import Dato, EstadoDato
    from poscosegran.servicios.aplicabilidad import comprobar
    n = Dato('fecha_vencimiento_producto', no_aplica=True, motivo_no_aplica='Sin vencimiento comercial aplicable')
    falso = Dato('vencimiento_aplicable', estado=EstadoDato.VALIDO, valor=False)
    r = comprobar({'fecha_vencimiento_producto': n, 'vencimiento_aplicable': falso}, 'NO_HERMETICO', 'INGRESO')
    assert r['fecha_vencimiento_producto'].no_aplica


@pytest.mark.bd
def test_api_mamdani_guarda_traza_y_reproduce_historial(api_real):
    c, _, _ = api_real
    u = unidad(c)
    e = post(c, f'/unidades/{u["id"]}/evaluaciones', entrada(u))['evaluacion']
    assert e['difuso']['tipo'] == 'MAMDANI_TIPO_1'
    assert e['version_motor'] == '3.0.0-mamdani'
    detalle = c.get(f'/api/v1/evaluaciones/{e["id"]}/explicacion')
    assert detalle.status_code == 200, detalle.text
    assert detalle.json()['difuso']['modulos']
    assert detalle.json()['difuso']['decision']['decision'] == e['decision_final']


@pytest.mark.bd
def test_adquisicion_valida_y_simula_curvas_mamdani(api_real):
    import copy
    from pathlib import Path
    from poscosegran.conocimiento.cargar import cargar
    c, h, _ = api_real
    cargar(Path(__file__).resolve().parents[2] / 'knowledge', activar=True, notas='Prueba de adquisición difusa')
    modelo = c.get('/api/v1/conocimiento').json()['modelo_difuso']
    propuesta = copy.deepcopy(modelo)
    propuesta['politica']['monitoreo_desde'] = 30
    body = {'motivo': 'Revisión de la política preventiva Mamdani', 'version_base': '3.2-prueba', 'difuso': propuesta, 'guardar': False}
    r = c.post('/api/v1/adquisicion/propuestas', json=body, headers=h('INGENIERO'))
    assert r.status_code == 200 and r.json()['valida'], r.text
    assert r.json()['impacto']['evaluados'] >= 242
    body['difuso']['modulos'][0]['entradas']['humedad_grano']['conjuntos']['alto'] = [15, 10, 5]
    r = c.post('/api/v1/adquisicion/propuestas', json=body, headers=h('INGENIERO'))
    assert r.status_code == 200 and not r.json()['valida'], r.text


@pytest.mark.bd
def test_autorizacion_difusa_ordinaria_y_seguimiento_real(api_real):
    from pathlib import Path
    from casos.base import base as completa
    from poscosegran.conocimiento.cargar import cargar
    from poscosegran.dominio.campos import CAMPOS
    c, _, _ = api_real
    cargar(Path(__file__).resolve().parents[2] / 'knowledge', activar=True, notas='Verificación de autorización difusa')
    u = unidad(c)

    def completa_entrada(u, temperatura):
        body = entrada(u)
        for o in body['observaciones']:
            if o['campo'] == 'temperatura_grano':
                o['valor'] = temperatura
        for k, d in completa().datos.datos.items():
            if CAMPOS[k].paso < 6:
                continue
            o = observacion(k, d.valor if isinstance(d.valor, bool) else float(d.valor))
            o['unidad'] = CAMPOS[k].unidad
            agregar(body, o)
        return body

    r = post(c, f'/unidades/{u["id"]}/evaluaciones', completa_entrada(u, 10))
    assert r['evaluacion']['decision_final'] == 'AUTORIZAR_ALMACENAMIENTO', r
    u = c.get('/api/v1/unidades/' + u['id']).json()
    r = post(c, f'/unidades/{u["id"]}/evaluaciones', completa_entrada(u, 24))
    assert r['evaluacion']['decision_final'] == 'CORREGIR_Y_REEVALUAR'
    u = c.get('/api/v1/unidades/' + u['id']).json()
    post(c, f'/unidades/{u["id"]}/planes', {
        'revision_unidad': u['revision'], 'revision_almacen': u['revision_almacen'],
        'fecha_proximo_control': (datetime.now(UTC)+timedelta(days=5)).isoformat(),
        'fecha_salida_prevista': (datetime.now(UTC)+timedelta(days=20)).isoformat(),
        'intervalo_dias': 5, 'actividades': 'Control por proximidad térmica según Mamdani',
    })
    u = c.get('/api/v1/unidades/' + u['id']).json()
    r = post(c, f'/unidades/{u["id"]}/evaluaciones', completa_entrada(u, 24))
    assert r['evaluacion']['decision_final'] == 'AUTORIZAR_CON_MONITOREO', r
