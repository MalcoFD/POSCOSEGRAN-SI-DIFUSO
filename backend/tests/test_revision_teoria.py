"""Regresiones de la revisión contra las diapositivas de conjuntos y Mamdani."""

import copy
from dataclasses import replace
from datetime import timedelta

import pytest

from casos.base import AHORA, base, bul, con, fec, num
from poscosegran.dominio.hechos import Episodio
from poscosegran.sistema_experto.base_hechos import BaseHechos
from poscosegran.sistema_experto.lenguaje import Evaluador
from poscosegran.sistema_experto.motor import Motor

from poscosegran.sistema_experto import base_conocimiento
from poscosegran.sistema_experto.base_conocimiento import BaseInvalida, desde_contenido


def test_union_zadeh_no_confunde_fusion_de_intervalos() -> None:
    modelo = base_conocimiento.cargar().modelo_difuso
    assert modelo is not None
    variable = modelo.variables["temperatura_grano_aplicable"]
    assert variable.grado_union(["TEMPLADA", "CALIDA"], 24) == 0.5
    assert variable.grado_compuesto(["TEMPLADA", "CALIDA"], 24) == 1.0


def test_disyuncion_de_reglas_usa_max_y_no_fusion() -> None:
    inst = con(base(), temperatura_almacen=num("temperatura_almacen", "24", "CELSIUS"))
    evaluador = Evaluador(base_conocimiento.cargar(), BaseHechos.desde(inst), None)
    disyuncion = {"alguno": [
        {"difuso": "temperatura_almacen", "es": "TEMPLADA"},
        {"difuso": "temperatura_almacen", "es": "CALIDA"},
    ]}
    fusion = {"difuso": "temperatura_almacen", "es": ["TEMPLADA", "CALIDA"]}
    assert evaluador.grado(disyuncion).cierto == 0.5
    assert evaluador.grado(fusion).cierto == 1.0


@pytest.mark.parametrize("valor", [float("nan"), float("inf"), float("-inf")])
def test_rechaza_puntos_no_finitos_de_pertenencia(valor: float) -> None:
    contenido = copy.deepcopy(base_conocimiento.leer_archivos())
    salida = contenido["operativa"]["inferencia_difusa"]["variable_salida"]
    salida["terminos"]["ALTA"] = {"gaussiana": {"m": valor, "k": 0.5}}
    with pytest.raises(BaseInvalida):
        desde_contenido(contenido)


def test_normalizacion_se_comprueba_dentro_del_universo() -> None:
    contenido = copy.deepcopy(base_conocimiento.leer_archivos())
    salida = contenido["operativa"]["inferencia_difusa"]["variable_salida"]
    salida["terminos"]["ALTA"] = {"triangular": [110, 120, 130]}
    with pytest.raises(BaseInvalida, match="normalizado"):
        desde_contenido(contenido)


@pytest.mark.parametrize("universo", [[100, 0], [0, 0], [0], [0, float("inf")]])
def test_rechaza_universo_salida_invalido(universo: list[float]) -> None:
    contenido = copy.deepcopy(base_conocimiento.leer_archivos())
    contenido["operativa"]["inferencia_difusa"]["variable_salida"]["universo"] = universo
    with pytest.raises(BaseInvalida, match="universo"):
        desde_contenido(contenido)


@pytest.mark.parametrize("puntos", [True, 100.5, "muchos", 100001])
def test_rechaza_resolucion_invalida_o_excesiva(puntos: object) -> None:
    contenido = copy.deepcopy(base_conocimiento.leer_archivos())
    contenido["operativa"]["inferencia_difusa"]["puntos"] = puntos
    with pytest.raises(BaseInvalida, match="puntos"):
        desde_contenido(contenido)


@pytest.mark.parametrize("valor", ["NaN", "Infinity", "-Infinity"])
def test_parametro_no_finito_es_error_de_base(valor: str) -> None:
    contenido = copy.deepcopy(base_conocimiento.leer_archivos())
    contenido["operativa"]["parametros"]["transicion_hr"]["valor"] = valor
    with pytest.raises(BaseInvalida):
        desde_contenido(contenido)


# Expectativas de dominio independientes del YAML: no se debe perder ningún
# veto de las reglas adicionales al migrar las variables numéricas a difusas.
ADICIONALES = [
    ("R31", "filtracion_agua_almacen", True, "CORREGIR_Y_REEVALUAR"),
    ("R32", "drenaje_obstruido", True, "CORREGIR_Y_REEVALUAR"),
    ("R33", "malla_ventana_danada", True, "CORREGIR_Y_REEVALUAR"),
    ("R34", "agua_estancada_entorno", True, "CORREGIR_Y_REEVALUAR"),
    ("R35", "residuos_de_proceso_sin_retirar", True, "CORREGIR_Y_REEVALUAR"),
    ("R36", "humedad_por_agua_en_unidad", True, "CUARENTENA"),
    ("R37", "paleta_danada_o_con_salientes", True, "CORREGIR_Y_REEVALUAR"),
    ("R38", "estiba_inestable", True, "CORREGIR_Y_REEVALUAR"),
    ("R39", "pasillo_inspeccion_obstruido", True, "CORREGIR_Y_REEVALUAR"),
    ("R40", "identificacion_unidad_legible", False, "CORREGIR_Y_REEVALUAR"),
    ("R41", "registro_trazabilidad_completo", False, "CORREGIR_Y_REEVALUAR"),
    ("R42", "movimiento_sin_registro", True, "CORREGIR_Y_REEVALUAR"),
    ("R43", "contacto_con_unidad_en_cuarentena", True, "CUARENTENA"),
    ("R44", "separacion_cuarentena_verificada", False, "CUARENTENA"),
    ("R45", "derrame_grano_en_piso", True, "CORREGIR_Y_REEVALUAR"),
    ("R46", "grano_derramado_reincorporado", True, "CUARENTENA"),
    ("R47", "rotacion_no_justificada", True, "AUTORIZAR_ALMACENAMIENTO"),
    ("R48", "alimentos_olor_incompatible_en_contacto", True, "CORREGIR_Y_REEVALUAR"),
    ("R49", "programa_control_plagas_documentado", False, "CORREGIR_Y_REEVALUAR"),
    ("R50", "aplicacion_plaguicida_sin_registro_competente", True, "CUARENTENA"),
    ("R51", "exposicion_quimica_del_grano", True, "CUARENTENA"),
]


@pytest.mark.parametrize("regla,campo,adverso,decision", ADICIONALES)
def test_reglas_adicionales_conservan_su_proposito(regla, campo, adverso, decision):
    motor = Motor(base_conocimiento.cargar())
    inst = base()
    if regla == "R44":
        inst = replace(inst, episodios=(Episodio("revision", "CUARENTENA"),))
    resultado = motor.evaluar(con(inst, **{campo: bul(campo, adverso)}))
    assert regla in resultado.reglas_activadas
    assert next(a.grado for a in resultado.traza if a.regla == regla) == 1.0
    assert resultado.decision_final == decision
    favorable = motor.evaluar(con(inst, **{campo: bul(campo, not adverso)}))
    assert regla not in favorable.reglas_activadas


def test_r52_no_confunde_fecha_comercial_con_vida_estimada():
    motor = Motor(base_conocimiento.cargar())
    inst = con(base(), vencimiento_aplicable=bul("vencimiento_aplicable", True))
    vencida = con(inst, fecha_vencimiento_producto=fec("fecha_vencimiento_producto", AHORA - timedelta(days=1)))
    vigente = con(inst, fecha_vencimiento_producto=fec("fecha_vencimiento_producto", AHORA + timedelta(days=1)))
    assert motor.evaluar(vencida).decision_final == "BLOQUEAR_INGRESO"
    assert "R52" in motor.evaluar(vencida).reglas_activadas
    assert "R52" not in motor.evaluar(vigente).reglas_activadas
