"""La evaluación nueva se obtiene del centroide, no del selector determinista."""
import copy
from dataclasses import replace

import pytest

from casos.base import bul, con, num, sin
from test_sistema_difuso import completa
from poscosegran.dominio.hechos import Fase, Plan
from poscosegran.dominio.motor import evaluar
from poscosegran.inferencia.base_conocimiento import cargar, ruta_por_defecto, desde_contenido, BaseInvalida
from poscosegran.inferencia.motor import Motor


def modelo():
    return cargar(ruta_por_defecto() / 'difuso')


def test_no_llama_a_r30_y_decision_coincide_con_centroide(monkeypatch):
    def prohibido(*args):
        raise AssertionError('Se invocó el selector histórico')
    monkeypatch.setattr(Motor, '_resolver', prohibido)
    base = modelo()
    ids_documentales = {regla['id'] for regla in base.contenido['documental']['reglas']}
    assert len(ids_documentales) == 52
    assert set(base.contenido['operativa']['difuso']['cobertura']) == ids_documentales
    r = evaluar(completa(), base)
    assert r.rama_r30 == 'MAMDANI_FINAL'
    assert r.version_motor == '3.0.0-mamdani'
    assert r.decision_final == 'AUTORIZAR_ALMACENAMIENTO'
    x = r.difuso['decision']
    assert len(x['reglas']) == 14
    assert r.decision_final == next(c['decision'] for c in x['clasificacion'] if x['centroide'] < c['hasta'])


@pytest.mark.parametrize('campo', ['moho_visible','heces_visibles','humedad_por_agua_en_unidad',
    'contacto_con_unidad_en_cuarentena','grano_derramado_reincorporado',
    'aplicacion_plaguicida_sin_registro_competente','exposicion_quimica_del_grano'])
def test_critico_impide_todas_las_conclusiones_permisivas(campo):
    r = evaluar(con(completa(), **{campo:bul(campo,True)}), modelo())
    assert r.decision_final == 'CUARENTENA'
    for regla in r.difuso['decision']['reglas']:
        if regla['entonces'] != 'CUARENTENA':
            assert regla['alfa'] == 0


def test_hallazgos_criticos_simultaneos_no_se_compensan():
    r = evaluar(con(completa(), moho_visible=bul('moho_visible',True),
                    exposicion_quimica_del_grano=bul('exposicion_quimica_del_grano',True)), modelo())
    assert r.decision_final == 'CUARENTENA'
    assert all(regla['alfa'] == 0 for regla in r.difuso['decision']['reglas'] if regla['entonces'] != 'CUARENTENA')


@pytest.mark.parametrize('fase,esperada', [(Fase.INGRESO,'BLOQUEAR_INGRESO'),(Fase.SEGUIMIENTO,'RETIRAR_LOTE'),(None,'SIN_CONCLUSION_AUTOMATICA')])
def test_suspension_con_fase_dentro_de_mamdani(fase,esperada):
    b = replace(con(completa(), humedad_grano=num('humedad_grano','15')),fase=fase)
    assert evaluar(b,modelo()).decision_final == esperada


def test_cambio_gradual_pesa_en_salida_final_y_plan():
    b = completa()
    b = replace(b,plan=Plan(registrado=True,vigente=True,intervalo_dias=5,fecha_salida_prevista=b.fecha_salida_prevista))
    rs = [evaluar(con(b,humedad_grano=num('humedad_grano',str(h)),temperatura_grano=num('temperatura_grano','24','CELSIUS')),modelo()) for h in (12.5,12.7,12.9)]
    zs = [r.difuso['decision']['centroide'] for r in rs]
    assert zs[0] < zs[1] < zs[2]
    assert rs[0].decision_final == 'AUTORIZAR_CON_MONITOREO'
    assert rs[-1].decision_final == 'CORREGIR_Y_REEVALUAR'



@pytest.mark.parametrize('t',[20,21,22,23,24,24.9])
def test_nunca_autoriza_seguimiento_sin_plan(t):
    r=evaluar(con(completa(),temperatura_grano=num('temperatura_grano',str(t),'CELSIUS')),modelo())
    assert r.decision_final != 'AUTORIZAR_CON_MONITOREO'


def test_desconocido_no_es_ausencia_de_riesgo():
    r=evaluar(sin(completa(),'moho_visible'),modelo())
    assert not r.decision_final.startswith('AUTORIZAR')


def test_adquisicion_rechaza_compensacion_de_cuarentena():
    contenido=copy.deepcopy(dict(modelo().contenido))
    m=contenido['operativa']['difuso']['decision']
    m['reglas'].append({'id':'INSEGURA','si':{'entrada':'cuarentena','conjunto':'presente'},'entonces':'AUTORIZAR_ALMACENAMIENTO'})
    with pytest.raises(BaseInvalida,match='compensa'):
        desde_contenido(contenido)


@pytest.mark.parametrize('antecedente,mensaje', [
    ({'todos':[{'entrada':'cuarentena','conjunto':'ausente'},{'entrada':'suspension','conjunto':'presente'}]}, 'suspensión'),
    ({'todos':[{'entrada':'cuarentena','conjunto':'ausente'},{'entrada':'suspension','conjunto':'ausente'},{'entrada':'correccion','conjunto':'presente'}]}, 'corrección'),
    ({'todos':[{'entrada':'cuarentena','conjunto':'ausente'},{'entrada':'suspension','conjunto':'ausente'},{'entrada':'correccion','conjunto':'ausente'},{'entrada':'evidencia','conjunto':'ausente'}]}, 'evidencia'),
])
def test_adquisicion_rechaza_otros_permisos_incompatibles(antecedente,mensaje):
    contenido=copy.deepcopy(dict(modelo().contenido))
    contenido['operativa']['difuso']['decision']['reglas'].append({'id':'INSEGURA','si':antecedente,'entonces':'AUTORIZAR_ALMACENAMIENTO'})
    with pytest.raises(BaseInvalida,match=mensaje):
        desde_contenido(contenido)


def test_historicos_no_cambian_de_algoritmo():
    for carpeta,version in [('historico_mamdani_3_1','1.0.0-mamdani'),('historico_mamdani_4_0','2.0.0-mamdani')]:
        r=evaluar(completa(),cargar(ruta_por_defecto()/carpeta))
        assert r.version_motor==version and 'decision' not in r.difuso
