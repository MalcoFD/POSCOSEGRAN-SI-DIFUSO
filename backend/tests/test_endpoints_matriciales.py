"""Recorridos HTTP complementarios: consultas, metadatos y compatibilidad histórica."""
import copy
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from test_integracion_api import entrada, post, unidad
from test_flujo_completo import actual, rev
from test_inspecciones_almacen import inspeccion

pytestmark = pytest.mark.bd


def test_version_anterior_se_conserva_sin_ejecutar_otro_motor(api_real, url_bd):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from poscosegran.db.modelos import VersionConocimiento

    c,h,_ = api_real
    ident = uuid.uuid4()
    with Session(create_engine(url_bd)) as db, db.begin():
        db.add(VersionConocimiento(id=ident, version_base='historica-'+str(ident),
            version_parametros='1.0', version_motor='3.0.0-mamdani',
            hash_contenido=uuid.uuid4().hex*2, ruta_archivo='fixture histórica',
            estado='SUPERADA', activa=False, contenido={'operativa':{'difuso':{'estructura':'ANTERIOR'}}}))
    listado=c.get('/api/v1/adquisicion/versiones',headers=h('INGENIERO')).json()
    assert any(v['id']==str(ident) and not v['activa'] for v in listado)
    respuesta=c.get('/api/v1/adquisicion/versiones/'+str(ident),headers=h('INGENIERO'))
    assert respuesta.status_code == 409 and 'histórica' in respuesta.json()['mensaje']
    assert c.get('/api/v1/conocimiento').json()['version_base']=='6.0'


def test_consultas_paginadas_y_edicion_de_recursos(api_real):
    c, h, _ = api_real
    a, b = unidad(c), unidad(c)
    assert c.get('/api/v1/me').json()['roles'] == ['PRODUCTOR']
    assert c.get('/api/v1/inicio').json()['unidades_total'] == 2
    for recurso, ids in [('almacenes', [a['id_almacen'], b['id_almacen']]),
                         ('lotes', [a['id_lote'], b['id_lote']]),
                         ('unidades', [a['id'], b['id']])]:
        r = c.get('/api/v1/'+recurso, params={'limite': 1})
        assert r.status_code == 200, r.text
        p1 = r.json()
        assert len(p1['items']) == 1 and p1['siguiente_cursor']
        p2 = c.get('/api/v1/'+recurso, params={'limite': 1, 'cursor': p1['siguiente_cursor']}).json()
        assert {p1['items'][0]['id'], p2['items'][0]['id']} == set(ids)
        assert c.get('/api/v1/'+recurso, params={'cursor': 'invalido'}).status_code == 422
        for ident in ids:
            r = c.get(f'/api/v1/{recurso}/{ident}')
            assert r.status_code == 200 and r.json()['id'] == ident
            assert c.get(f'/api/v1/{recurso}/{ident}', headers=h('AJENO')).status_code == 404
    url = '/api/v1/almacenes/'+a['id_almacen']
    almacen = c.get(url).json()
    body = {k: almacen[k] for k in ['nombre', 'ubicacion', 'clima_calido', 'fundamento_clima']}
    body['ubicacion'] = 'Cusco, ubicación corregida'
    r = c.patch(url, json=body, headers={'If-Match': f'"{almacen["revision"]}"'})
    assert r.status_code == 200 and r.json()['revision'] == almacen['revision']+1
    assert c.patch(url, json=body, headers={'If-Match': f'"{almacen["revision"]}"'}).status_code == 409


def test_consultas_de_seguimiento_conservan_traza_y_actuaciones(api_real):
    c, h, usuarios = api_real
    u = unidad(c)
    post(c, '/administracion/asignaciones', {'id_tecnico':str(usuarios['TECNICO']),
        'id_recurso':u['id_lote'], 'tipo':'LOTE', 'vigente':True}, h('ADMINISTRADOR'))
    e = post(c, f'/unidades/{u["id"]}/evaluaciones', entrada(u))['evaluacion']
    captura = c.get(f'/api/v1/unidades/{u["id"]}/captura-anterior')
    assert captura.status_code == 200 and len(captura.json()['contenido']['observaciones']) == 4
    u = actual(c,u)
    dictamen = {**rev(u), 'humedad_min':10, 'humedad_max':13, 'plazo_maximo_dias':3,
        'vence_en':(datetime.now(UTC)+timedelta(days=1)).isoformat(),
        'condiciones':'Registro técnico histórico, no altera la matriz', 'evidencia':'Acta de revisión de prueba'}
    assert c.post(f'/api/v1/unidades/{u["id"]}/dictamenes', json=dictamen, headers=h()).status_code == 403
    di = post(c, f'/unidades/{u["id"]}/dictamenes', dictamen, h('TECNICO'))
    assert di['vigente']
    assert c.get(f'/api/v1/unidades/{u["id"]}/dictamenes').json()['items'][0]['id'] == di['id']
    u = actual(c,u)
    obs = entrada(u)['observaciones']
    co = post(c, f'/unidades/{u["id"]}/controles', {**rev(u), 'tipo':'GRANO',
        'fecha':datetime.now(UTC).isoformat(), 'evidencia':'Control de prueba', 'observaciones':obs})
    u = actual(c,u)
    pl = post(c, f'/unidades/{u["id"]}/planes', {**rev(u),
        'fecha_proximo_control':(datetime.now(UTC)+timedelta(days=3)).isoformat(),
        'fecha_salida_prevista':(datetime.now(UTC)+timedelta(days=6)).isoformat(),
        'intervalo_dias':3, 'actividades':'Control de condiciones del grano'})
    u = actual(c,u)
    ev = post(c, f'/unidades/{u["id"]}/eventos', {**rev(u), 'tipo':'LIMPIEZA_GENERAL',
        'fecha':datetime.now(UTC).isoformat(), 'evidencia':'Limpieza documentada'})
    for tipo, ident in [('controles',co['id']), ('planes',pl['id']), ('eventos',ev['id'])]:
        r = c.get(f'/api/v1/unidades/{u["id"]}/{tipo}')
        assert r.status_code == 200 and r.json()['items'][0]['id'] == ident
    assert c.get('/api/v1/evaluaciones/'+e['id']).json()['evaluacion']['difuso'] == e['difuso']
    u = actual(c,u)
    ins = inspeccion(c,u)
    r = c.get('/api/v1/almacenes/'+u['id_almacen']+'/inspeccion')
    assert r.status_code == 200 and r.json()['id'] == ins['id']
    u = actual(c,u)
    post(c, f'/unidades/{u["id"]}/evaluaciones', entrada(u,{'estado_fisico_sanitario':'HALLAZGO_CRITICO'}))
    inc = c.get(f'/api/v1/unidades/{u["id"]}/incidencias').json()['items'][0]
    u = actual(c,u)
    re = post(c, f'/incidencias/{inc["id"]}/revisiones', {**rev(u),'revision_incidencia':inc['revision'],
        'resultado':'CONFIRMADA','evidencia':'Hallazgo verificado por técnico'},h('TECNICO'))
    assert c.get(f'/api/v1/incidencias/{inc["id"]}/revisiones').json()['items'][0]['id'] == re['id']
    inc = c.get('/api/v1/incidencias/'+inc['id']).json()
    u = actual(c,u)
    re = post(c, f'/incidencias/{inc["id"]}/resoluciones', {**rev(u),'revision_incidencia':inc['revision'],
        'disposicion':'Disposición registrada, requiere nueva evaluación', 'evidencia':'Acta de cierre del escenario'},h('TECNICO'))
    assert c.get(f'/api/v1/incidencias/{inc["id"]}/resoluciones').json()['items'][0]['id'] == re['id']


def test_detalle_version_y_validador_de_regla(api_real):
    c,h,_ = api_real
    versions = c.get('/api/v1/adquisicion/versiones',headers=h('INGENIERO')).json()
    v = next(v for v in versions if v['activa'])
    r = c.get('/api/v1/adquisicion/versiones/'+v['id'],headers=h('INGENIERO'))
    assert r.status_code == 200 and len(r.json()['reglas']) == 320
    regla = copy.deepcopy(r.json()['reglas'][0])
    url = '/api/v1/adquisicion/validar-regla'
    assert c.post(url,json={'definicion':regla},headers=h('INGENIERO')).json()['valida']
    regla['si']['todos'][-1]['conjunto'] = 'INEXISTENTE'
    assert not c.post(url,json={'definicion':regla},headers=h('INGENIERO')).json()['valida']
    assert c.post(url,json={'definicion':regla},headers=h()).status_code == 403
    assert c.get('/api/v1/adquisicion/versiones/'+str(uuid.uuid4()),headers=h('INGENIERO')).status_code == 404


def test_salud_y_autenticacion_local_real(api_real, monkeypatch):
    c,_,usuarios = api_real
    assert c.get('/salud').json()['estado'] == 'activo'
    assert c.get('/salud/bd').json()['estado'] == 'conectado'
    from poscosegran.api import local
    from poscosegran.api.app import crear_app
    from poscosegran.config import obtener_configuracion
    monkeypatch.setenv('POSCOSEGRAN_AUTH_LOCAL_HABILITADA','true')
    monkeypatch.setenv('POSCOSEGRAN_AUTH_LOCAL_PASSWORD','testeo')
    monkeypatch.setitem(local.USUARIOS,'prueba_http',usuarios['PRODUCTOR'])
    obtener_configuracion.cache_clear()
    with TestClient(crear_app()) as client:
        assert client.post('/auth/local/sesion',json={'usuario':'prueba_http','password':'erronea'}).status_code == 401
        r=client.post('/auth/local/sesion',json={'usuario':'prueba_http','password':'testeo'})
        assert r.status_code == 200
        token=r.json()['access_token']
        assert client.get('/api/v1/me',headers={'Authorization':'Bearer '+token}).status_code == 200
        assert client.get('/openapi.json').status_code == 200
        assert client.get('/documentacion').status_code == 200
    obtener_configuracion.cache_clear()
