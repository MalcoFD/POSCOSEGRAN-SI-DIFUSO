"""Inspecciones reales: alcance, aislamiento, precedencia y administración por rol."""
from datetime import UTC, datetime, timedelta
from pathlib import Path
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from test_integracion_api import unidad, entrada, post
from test_regresiones_diagnostico import observacion
from poscosegran.conocimiento.cargar import cargar
from poscosegran.db.modelos import Almacen, Evento
from poscosegran.servicios.inspecciones import vigente

pytestmark = pytest.mark.bd


def inspeccion(c,u,campos=None):
    return post(c,f'/almacenes/{u["id_almacen"]}/inspecciones',{
        'revision_almacen':u['revision_almacen'],'fecha':datetime.now(UTC).isoformat(),
        'vigente_hasta':(datetime.now(UTC)+timedelta(days=1)).isoformat(),'evidencia':'Acta de inspección de infraestructura',
        'observaciones':campos or [observacion('filtracion_agua_almacen',False)]})


def test_reutiliza_en_dos_unidades_y_no_en_otro_almacen(api_real):
    c,_,_=api_real
    u=unidad(c)
    i=inspeccion(c,u)
    otra=post(c,'/unidades',{'id_lote':u['id_lote'],'id_almacen':u['id_almacen'],
                            'nombre_recipiente':'Segunda unidad','tipo_almacenamiento':'NO_HERMETICO'})
    ajena=unidad(c)
    cargar(Path(__file__).parents[2]/'knowledge',activar=True,notas='Prueba Mamdani con inspección')
    for x in (u,otra,ajena):
        actual=c.get('/api/v1/unidades/'+x['id']).json()
        r=post(c,f'/unidades/{x["id"]}/evaluaciones',entrada(actual))['evaluacion']
        obs=[o for o in r['observaciones_aplicadas'] if o['entrada']['campo']=='filtracion_agua_almacen']
        assert bool(obs)==(x['id']!=ajena['id'])
        if obs:
            assert obs[0]['entrada']['valor'] is False and obs[0]['procedencia']=='HISTORICA'
        assert not r['decision_final'].startswith('AUTORIZAR')  # la inspección parcial no inventa el resto
    assert i['id_almacen']==u['id_almacen']


def test_declaracion_actual_desconocida_no_se_reemplaza_por_inspeccion(api_real):
    c,_,_=api_real
    u=unidad(c)
    inspeccion(c,u)
    u=c.get('/api/v1/unidades/'+u['id']).json()
    body=entrada(u)
    o=observacion('filtracion_agua_almacen',False)
    o.update(captura='DESCONOCIDO',valor=None,fecha_observacion=None,metodo=None)
    body['observaciones'].append(o)
    e=post(c,f'/unidades/{u["id"]}/evaluaciones',body)['evaluacion']
    obs=next(o for o in e['observaciones_aplicadas'] if o['entrada']['campo']=='filtracion_agua_almacen')
    assert obs['estado_dato']=='DESCONOCIDO' and obs['procedencia']=='ACTUAL'


def test_inspeccion_vencida_o_almacen_modificado_no_reutiliza(api_real,url_bd):
    c,_,_=api_real
    u=unidad(c)
    i=inspeccion(c,u)
    with Session(create_engine(url_bd)) as s:
        a=s.get(Almacen,u['id_almacen'])
        assert vigente(s,a,datetime.now(UTC)) is not None
        assert vigente(s,a,datetime.fromisoformat(i['vigente_hasta'])+timedelta(seconds=1)) is None
        a.revision+=1
        assert vigente(s,a,datetime.now(UTC)) is None


def test_exposicion_agua_invalida_solo_la_unidad_afectada(api_real,url_bd):
    c,_,usuarios=api_real
    u=unidad(c)
    inspeccion(c,u)
    otra=post(c,'/unidades',{'id_lote':u['id_lote'],'id_almacen':u['id_almacen'],
                            'nombre_recipiente':'Unidad no expuesta','tipo_almacenamiento':'NO_HERMETICO'})
    with Session(create_engine(url_bd)) as s:
        a=s.get(Almacen,uuid.UUID(u['id_almacen']))
        assert a is not None
        assert vigente(s,a,datetime.now(UTC),uuid.UUID(u['id'])) is not None
        s.add(Evento(id_unidad=uuid.UUID(u['id']),tipo='EXPOSICION_AGUA',fecha=datetime.now(UTC),
                     evidencia='Incidente de agua verificado',id_responsable=usuarios['PRODUCTOR']))
        s.flush()
        assert vigente(s,a,datetime.now(UTC),uuid.UUID(u['id'])) is None
        assert vigente(s,a,datetime.now(UTC),uuid.UUID(otra['id'])) is not None


def test_no_permite_compartir_datos_del_grano_ni_acceso_ajeno(api_real):
    c,h,_=api_real
    u=unidad(c)
    ruta=f'/api/v1/almacenes/{u["id_almacen"]}/inspecciones'
    b={'revision_almacen':u['revision_almacen'],'fecha':datetime.now(UTC).isoformat(),
       'vigente_hasta':(datetime.now(UTC)+timedelta(days=1)).isoformat(),'evidencia':'Acta',
       'observaciones':[observacion('moho_visible',False)]}
    assert c.post(ruta,json=b,headers=h()).status_code==422
    for rol in ('AJENO','ADMINISTRADOR','INGENIERO'):
        assert c.get(ruta.rsplit('/',1)[0]+'/inspeccion',headers=h(rol)).status_code==404


def test_administrador_asigna_y_revoca_tecnico_sin_acceder_a_evaluaciones(api_real):
    c,h,usuarios=api_real
    u=unidad(c)
    for rol in ('PRODUCTOR','TECNICO','INGENIERO'):
        assert c.get('/api/v1/administracion/asignaciones',headers=h(rol)).status_code==403
    assert c.get('/api/v1/administracion/asignaciones',headers=h('ADMINISTRADOR')).status_code==200
    assert c.get('/api/v1/unidades/'+u['id'],headers=h('TECNICO')).status_code==404
    body={'id_tecnico':str(usuarios['TECNICO']),'id_recurso':u['id_almacen'],'tipo':'ALMACEN','vigente':True}
    post(c,'/administracion/asignaciones',body,h('ADMINISTRADOR'))
    assert c.get('/api/v1/unidades/'+u['id'],headers=h('TECNICO')).status_code==200
    assert c.get('/api/v1/unidades/'+u['id'],headers=h('ADMINISTRADOR')).status_code==404
    body['vigente']=False
    post(c,'/administracion/asignaciones',body,h('ADMINISTRADOR'))
    assert c.get('/api/v1/unidades/'+u['id'],headers=h('TECNICO')).status_code==404
