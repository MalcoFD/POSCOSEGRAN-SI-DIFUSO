"""Núcleo reducido: interacciones reales, cobertura y restricciones conservadas."""
from dataclasses import replace
from itertools import product
import copy

import pytest

from casos.base import con, num, sin
from test_sistema_difuso import completa
from poscosegran.dominio.hechos import Modalidad
from poscosegran.dominio.motor import evaluar
from poscosegran.inferencia.base_conocimiento import cargar, ruta_por_defecto
from poscosegran.inferencia.base_conocimiento import BaseInvalida, desde_contenido


def modelo():
    return cargar(ruta_por_defecto() / 'historico_mamdani_4_0')


def test_nucleo_cuatro_entradas_nueve_reglas():
    m = modelo().contenido['operativa']['difuso']['modulos']
    assert modelo().version_base == '4.0'
    assert len(m) == 1 and len(m[0]['entradas']) == 4 and len(m[0]['reglas']) == 9
    r = evaluar(completa(), modelo())
    assert r.version_motor == '2.0.0-mamdani'
    assert r.decision_final == 'AUTORIZAR_ALMACENAMIENTO'


def test_interaccion_no_equivale_a_evaluar_variables_por_separado():
    b = completa()
    solo = evaluar(con(b, humedad_grano=num('humedad_grano', '13')), modelo())
    conjunto = evaluar(con(b, humedad_grano=num('humedad_grano', '13'),
                           temperatura_grano=num('temperatura_grano', '25', 'CELSIUS')), modelo())
    a, c = solo.difuso['modulos'][0], conjunto.difuso['modulos'][0]
    assert c['centroide'] > a['centroide']
    assert next(r for r in c['reglas'] if r['id'] == 'D07')['alfa'] == 1


@pytest.mark.parametrize('campo', ['humedad_grano', 'temperatura_grano', 'hr_almacen', 'granos_defectuosos'])
def test_falta_de_entrada_no_es_favorable(campo):
    r = evaluar(sin(completa(), campo), modelo())
    assert not r.decision_final.startswith('AUTORIZAR')
    assert r.difuso['modulos'][0]['centroide'] is None
    assert campo in {p.campo for p in r.datos_pendientes}


def test_hermetico_excluye_hr_sin_inventar_pertenencia():
    b = replace(sin(completa(), 'hr_almacen'), tipo_almacenamiento=Modalidad.HERMETICO)
    r = evaluar(b, modelo())
    m = r.difuso['modulos'][0]
    assert m['estado'] == 'CALCULADO'
    assert m['entradas']['hr_almacen']['estado'] == 'NO_APLICA'
    assert m['entradas']['hr_almacen']['pertenencias'] == {}
    assert next(r for r in m['reglas'] if r['id'] == 'D01')['estado'] == 'NO_APLICA'


def test_malla_numerica_sin_huecos_en_ambas_modalidades():
    for modalidad in (Modalidad.NO_HERMETICO, Modalidad.HERMETICO):
        for h, t, hr, d in product([12.5, 12.75, 13, 13.25, 13.5], [20, 22.5, 25, 27.5, 30],
                                    [50, 55, 60, 65, 70], [6, 6.5, 7, 7.5, 8]):
            b = replace(con(completa(), humedad_grano=num('humedad_grano', str(h)),
                            temperatura_grano=num('temperatura_grano', str(t), 'CELSIUS'),
                            hr_almacen=num('hr_almacen', str(hr), 'PCT_HR'),
                            granos_defectuosos=num('granos_defectuosos', str(d), 'PCT_MASA')),
                        tipo_almacenamiento=modalidad)
            m = evaluar(b, modelo()).difuso['modulos'][0]
            assert m['estado'] == 'CALCULADO', (modalidad, h, t, hr, d)
            assert 0 <= m['centroide'] <= 100


def test_reproduccion_mamdani_31():
    anterior = cargar(ruta_por_defecto() / 'historico_mamdani_3_1')
    r = evaluar(completa(), anterior)
    assert r.version_motor == '1.0.0-mamdani' and len(r.difuso['modulos']) == 20


@pytest.mark.parametrize('defecto', ['hueco', 'referencia', 'guarda', 'duplicado', 'conjunto'])
def test_no_se_activa_un_modelo_incompleto(defecto):
    contenido = copy.deepcopy(dict(modelo().contenido))
    m = contenido['operativa']['difuso']['modulos'][0]
    if defecto == 'hueco':
        m['reglas'] = [r for r in m['reglas'] if r['id'] != 'D01']
    elif defecto == 'referencia':
        m['reglas'][0]['si']['todos'][0]['entrada'] = 'inventada'
    elif defecto == 'guarda':
        m['reglas'][0].pop('aplica_si')
    elif defecto == 'duplicado':
        m['reglas'][1]['id'] = 'D01'
    else:
        m['entradas']['humedad_grano']['conjuntos']['alto'] = [15, 10, 5]
    with pytest.raises(BaseInvalida):
        desde_contenido(contenido)


def test_restricciones_no_se_compensan_por_el_centroide():
    from casos.base import bul
    for campo in ('moho_visible', 'exposicion_quimica_del_grano', 'heces_visibles'):
        r = evaluar(con(completa(), **{campo: bul(campo, True)}), modelo())
        assert r.difuso['modulos'][0]['centroide'] < 35
        assert r.decision_final == 'CUARENTENA'


def test_fuera_de_dominio_es_pendiente_y_no_cero():
    r = evaluar(con(completa(), temperatura_grano=num('temperatura_grano', '-31', 'CELSIUS')), modelo())
    assert r.difuso['modulos'][0]['entradas']['temperatura_grano']['estado'] == 'FUERA_DE_DOMINIO'
    assert r.difuso['modulos'][0]['centroide'] is None
    assert not r.decision_final.startswith('AUTORIZAR')
