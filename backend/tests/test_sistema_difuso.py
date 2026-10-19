"""Contrato matemático y funcional del motor Mamdani, independiente del motor antiguo."""
from decimal import Decimal

import pytest

from casos.base import base, con, num
from poscosegran.sistema_difuso.pertenencia import pertenencia
from poscosegran.sistema_difuso.defuzzificacion import centroide


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


def test_motor_historico_se_conserva():
    from poscosegran.dominio.motor import evaluar
    r = evaluar(base())
    assert r.version_motor == '0.8.0'
    assert r.decision_final == 'AUTORIZAR_ALMACENAMIENTO'
    assert r.difuso is None


def test_modelo_difuso_valido_y_efectivo():
    from poscosegran.dominio.motor import evaluar
    from poscosegran.inferencia.base_conocimiento import cargar, ruta_por_defecto
    modelo = cargar(ruta_por_defecto() / 'historico_mamdani_3_1')
    normal = evaluar(base(), modelo)
    cercano = evaluar(con(base(), temperatura_almacen=num('temperatura_almacen', '24', 'CELSIUS')), modelo)
    assert normal.version_motor == '1.0.0-mamdani'
    assert cercano.difuso and cercano.difuso['tipo'] == 'MAMDANI_TIPO_1'
    assert cercano.decision_final != normal.decision_final or cercano.fecha_proximo_control != normal.fecha_proximo_control


def test_moho_no_se_compensa_por_condiciones_favorables():
    from casos.base import bul
    from poscosegran.dominio.motor import evaluar
    from poscosegran.inferencia.base_conocimiento import cargar, ruta_por_defecto
    r = evaluar(con(base(), moho_visible=bul('moho_visible', True)), cargar(ruta_por_defecto() / 'historico_mamdani_3_1'))
    assert r.decision_final == 'CUARENTENA'


def test_validacion_rechaza_regiones_sin_cobertura_y_referencias_rotas():
    import copy
    from poscosegran.inferencia.base_conocimiento import BaseInvalida, cargar, desde_contenido, ruta_por_defecto
    contenido = copy.deepcopy(dict(cargar(ruta_por_defecto() / 'historico_mamdani_3_1').contenido))
    m = contenido['operativa']['difuso']['modulos'][0]
    m['entrada']['campo'] = 'campo_que_no_existe'
    m['conjuntos'] = {'bajo': [0, 1, 2], 'medio': [10, 11, 12], 'alto': [90, 95, 100]}
    with pytest.raises(BaseInvalida) as error:
        desde_contenido(contenido)
    assert 'campo inexistente' in str(error.value)
    assert 'sin cobertura' in str(error.value)


def test_desconocido_no_es_pertenencia_media():
    from casos.base import sin
    from poscosegran.dominio.motor import evaluar
    from poscosegran.inferencia.base_conocimiento import cargar, ruta_por_defecto
    r = evaluar(sin(base(), 'temperatura_almacen'), cargar(ruta_por_defecto() / 'historico_mamdani_3_1'))
    m = next(m for m in r.difuso['modulos'] if m['id'] == 'temperatura_almacen')
    assert m['estado'] == 'DESCONOCIDO' and m['centroide'] is None
    assert not r.decision_final.startswith('AUTORIZAR')


def test_area_exacta_contra_integracion_independiente():
    conjuntos = [([0, 0, 10, 25], .25), ([20, 50, 80], .6), ([70, 85, 100, 100], .4)]
    resultado = centroide(conjuntos)
    xs = [(i + .5) * .01 for i in range(10000)]
    ys = [max(min(a, pertenencia(x, p)) for p, a in conjuntos) for x in xs]
    esperado = sum(x*y for x, y in zip(xs, ys)) / sum(ys)
    assert resultado[0] == pytest.approx(esperado, abs=1e-5)


def test_impacto_evalua_con_motor_difuso():
    from poscosegran.inferencia.adquisicion import medir_impacto
    from poscosegran.inferencia.base_conocimiento import cargar, ruta_por_defecto
    m = cargar(ruta_por_defecto() / 'historico_mamdani_3_1')
    casos = [('cercano', 'prueba', con(base(), temperatura_almacen=num('temperatura_almacen', '24', 'CELSIUS')))]
    assert medir_impacto(cargar(), m, casos).cambian == 1


def completa():
    from casos.base import bul
    from poscosegran.dominio.campos import CAMPOS
    datos = {k: bul(k, k in {'identificacion_unidad_legible', 'registro_trazabilidad_completo', 'programa_control_plagas_documentado'}) for k,v in CAMPOS.items() if v.paso >= 6 and v.tipo == 'B'}
    datos['distancia_entre_estantes'] = num('distancia_entre_estantes', '1.5', 'METROS')
    return con(base(), **datos)


def test_n13_exige_datos_ampliados_y_no_autoriza_ausencias():
    from poscosegran.dominio.motor import evaluar
    from poscosegran.inferencia.base_conocimiento import cargar, ruta_por_defecto
    m = cargar(ruta_por_defecto() / 'historico_mamdani_3_1')
    r = evaluar(base(), m)
    assert r.decision_final == 'SIN_CONCLUSION_AUTOMATICA'
    assert 'filtracion_agua_almacen' in {p.campo for p in r.datos_pendientes}
    assert evaluar(completa(), m).decision_final == 'AUTORIZAR_ALMACENAMIENTO'


def test_filtracion_acorta_control_y_r47_no_altera_aptitud():
    from casos.base import bul
    from poscosegran.dominio.motor import evaluar
    from poscosegran.inferencia.base_conocimiento import cargar, ruta_por_defecto
    m = cargar(ruta_por_defecto() / 'historico_mamdani_3_1')
    b = completa()
    r = evaluar(con(b, filtracion_agua_almacen=bul('filtracion_agua_almacen', True)), m)
    assert r.decision_final == 'CORREGIR_Y_REEVALUAR'
    assert (r.fecha_proximo_control-b.fecha_evaluacion).days == 7
    logistica = evaluar(con(b, rotacion_no_justificada=bul('rotacion_no_justificada', True)), m)
    assert logistica.decision_final == 'AUTORIZAR_ALMACENAMIENTO'


@pytest.mark.parametrize('campo,decision', [
    ('filtracion_agua_almacen','CORREGIR_Y_REEVALUAR'), ('humedad_por_agua_en_unidad','CUARENTENA'),
    ('malla_ventana_danada','CORREGIR_Y_REEVALUAR'), ('contacto_con_unidad_en_cuarentena','CUARENTENA'),
    ('derrame_grano_en_piso','CORREGIR_Y_REEVALUAR'), ('grano_derramado_reincorporado','CUARENTENA'),
    ('aplicacion_plaguicida_sin_registro_competente','CUARENTENA'), ('exposicion_quimica_del_grano','CUARENTENA'),
])
def test_prioridades_ampliadas_se_conservan(campo, decision):
    from casos.base import bul
    from poscosegran.dominio.motor import evaluar
    from poscosegran.inferencia.base_conocimiento import cargar, ruta_por_defecto
    r = evaluar(con(completa(), **{campo:bul(campo, True)}), cargar(ruta_por_defecto() / 'historico_mamdani_3_1'))
    assert r.decision_final == decision

