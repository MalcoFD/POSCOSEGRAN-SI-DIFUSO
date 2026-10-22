"""Contrato matemático del motor Mamdani y efectos de las reglas ampliadas."""
import copy
from decimal import Decimal

import pytest

from casos.base import base, bul, con, sin
from poscosegran.dominio.motor import evaluar
from poscosegran.inferencia.base_conocimiento import BaseInvalida, cargar, desde_contenido
from poscosegran.sistema_difuso.defuzzificacion import centroide
from poscosegran.sistema_difuso.pertenencia import pertenencia


@pytest.mark.parametrize("x,esperado", [(0, 0), (2, .5), (4, 1), (6, .5), (8, 0)])
def test_triangulo(x, esperado):
    assert pertenencia(x, [0, 4, 8]) == pytest.approx(esperado)


def test_hombros_y_fuera_de_soporte():
    assert pertenencia(0, [0, 0, 2, 4]) == 1
    assert pertenencia(4, [0, 2, 4, 4]) == 1
    assert pertenencia(-1, [0, 0, 2, 4]) == 0


def test_centroide_conocido_y_area_nula():
    resultado = centroide([([0, 50, 100], 1.0)])
    assert resultado is not None
    assert resultado[0] == pytest.approx(50, abs=1e-9)
    assert resultado[1] == pytest.approx(50, abs=1e-9)
    assert centroide([([0, 50, 100], 0.0)]) is None


def test_centroide_de_triangulo_asimetrico():
    resultado = centroide([([0, 10, 50], 1.0)])
    assert resultado is not None
    assert resultado[0] == pytest.approx(20, abs=1e-9)


def test_agregacion_max_no_es_promedio_de_centroides():
    resultado = centroide([([0, 0, 20, 40], .6), ([40, 60, 100, 100], .9)])
    assert resultado is not None
    assert 50 < resultado[0] < 80


def test_configuracion_invalida_no_evaluada():
    with pytest.raises(ValueError):
        pertenencia(2, [0, 4, 2])


def test_transicion_tiene_mas_de_una_pertenencia():
    assert 0 < pertenencia(Decimal('24'), [20, 25, 30]) < 1
    assert 0 < pertenencia(24, [-30, -30, 20, 25]) < 1


def test_area_exacta_contra_integracion_independiente():
    conjuntos = [([0, 0, 10, 25], .25), ([20, 50, 80], .6), ([70, 85, 100, 100], .4)]
    resultado = centroide(conjuntos)
    xs = [(i + .5) * .01 for i in range(10000)]
    ys = [max(min(a, pertenencia(x, p)) for p, a in conjuntos) for x in xs]
    esperado = sum(x*y for x, y in zip(xs, ys)) / sum(ys)
    assert resultado[0] == pytest.approx(esperado, abs=1e-5)


def test_validacion_rechaza_regiones_sin_cobertura_y_referencias_rotas():
    contenido = copy.deepcopy(dict(cargar().contenido))
    entrada = contenido['operativa']['difuso']['modulos'][0]['entradas']['humedad_grano']
    entrada['entrada']['campo'] = 'campo_que_no_existe'
    entrada['conjuntos'] = {'bajo': [0, 1, 2], 'medio': [10, 11, 12], 'alto': [90, 95, 100]}
    with pytest.raises(BaseInvalida) as error:
        desde_contenido(contenido)
    assert 'campo inexistente' in str(error.value)
    assert 'sin cobertura' in str(error.value)


def test_datos_ampliados_exigibles_impiden_autorizar():
    r = evaluar(sin(base(), 'filtracion_agua_almacen'))
    assert evaluar(base()).decision_final == 'AUTORIZAR_ALMACENAMIENTO'
    assert r.decision_final == 'SIN_CONCLUSION_AUTOMATICA'
    assert 'filtracion_agua_almacen' in {p.campo for p in r.datos_pendientes}


def test_filtracion_acorta_control_y_r47_no_altera_aptitud():
    b = base()
    r = evaluar(con(b, filtracion_agua_almacen=bul('filtracion_agua_almacen', True)))
    assert r.decision_final == 'CORREGIR_Y_REEVALUAR'
    assert (r.fecha_proximo_control-b.fecha_evaluacion).days == 7
    logistica = evaluar(con(b, rotacion_no_justificada=bul('rotacion_no_justificada', True)))
    assert logistica.decision_final == 'AUTORIZAR_ALMACENAMIENTO'


@pytest.mark.parametrize('campo,decision', [
    ('filtracion_agua_almacen','CORREGIR_Y_REEVALUAR'), ('humedad_por_agua_en_unidad','CUARENTENA'),
    ('malla_ventana_danada','CORREGIR_Y_REEVALUAR'), ('contacto_con_unidad_en_cuarentena','CUARENTENA'),
    ('derrame_grano_en_piso','CORREGIR_Y_REEVALUAR'), ('grano_derramado_reincorporado','CUARENTENA'),
    ('aplicacion_plaguicida_sin_registro_competente','CUARENTENA'), ('exposicion_quimica_del_grano','CUARENTENA'),
])
def test_hallazgos_ampliados_determinan_la_accion(campo, decision):
    assert evaluar(con(base(), **{campo: bul(campo, True)})).decision_final == decision
