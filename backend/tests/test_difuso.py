"""Componentes difusos: formas, particiones ancladas, agregación y centroide.

Las formas siguen la nomenclatura del material del curso (Γ lineal, L lineal,
triangular, trapezoidal, S, Z y gaussiana). Los centroides de referencia son los
del plan de migración (N = 1001).
"""

from __future__ import annotations

import copy

import pytest

from casos.nitida import contenido_con_anchos
from poscosegran.sistema_experto import base_conocimiento
from poscosegran.sistema_experto.base_conocimiento import BaseInvalida, desde_contenido
from poscosegran.sistema_experto.difuso import (
    Corte,
    FuncionS,
    Gaussiana,
    Singleton,
    TerminoParticion,
    Trapezoidal,
    borrosidad,
    distancia_tchebychev,
    gamma_lineal,
    l_lineal,
    triangular,
)


@pytest.fixture(scope="module")
def modelo():
    base = base_conocimiento.cargar()
    assert base.modelo_difuso is not None
    return base.modelo_difuso


def _malla(inicio: float, fin: float, puntos: int = 2001) -> list[float]:
    paso = (fin - inicio) / (puntos - 1)
    return [inicio + i * paso for i in range(puntos)]


# --- Formas -------------------------------------------------------------------


def test_triangular_y_trapezoidal() -> None:
    t = triangular(15, 35, 55)
    assert (t.grado(15), t.grado(25), t.grado(35), t.grado(45), t.grado(55)) == (0, 0.5, 1, 0.5, 0)
    z = Trapezoidal(12.5, 13, 13.5, 14)
    assert (z.grado(12.5), z.grado(12.75), z.grado(13.2), z.grado(13.75), z.grado(14)) == (0, 0.5, 1, 0.5, 0)


def test_gamma_y_l_lineales_son_hombros_abiertos() -> None:
    g, lin = gamma_lineal(75, 90), l_lineal(10, 25)
    assert (g.grado(70), g.grado(82.5), g.grado(90), g.grado(1e6)) == (0, 0.5, 1, 1)
    assert (lin.grado(-1e6), lin.grado(10), lin.grado(17.5), lin.grado(25)) == (1, 1, 0.5, 0)


def test_funciones_s_z_gaussiana_y_singleton() -> None:
    s, z = FuncionS(0, 5, 10), FuncionS(0, 5, 10, decreciente=True)
    assert (s.grado(0), s.grado(5), s.grado(10)) == (0, 0.5, 1)
    assert s.grado(2.5) == pytest.approx(0.125)
    for x in _malla(-2, 12, 141):
        assert s.grado(x) + z.grado(x) == pytest.approx(1.0)
    g = Gaussiana(20, 0.5)
    assert g.grado(20) == 1.0 and g.grado(21) == pytest.approx(0.606531, abs=1e-6)
    assert Singleton(3).grado(3) == 1.0 and Singleton(3).grado(3.01) == 0.0


# --- Particiones ancladas -----------------------------------------------------


def test_corte_con_ancho_nulo_reproduce_el_operador_nitido() -> None:
    menor_igual = Corte(13, 0, "INFERIOR", "INFERIOR")  # 13 pertenece al término inferior (<= 13)
    mayor_igual = Corte(25, 0, "INFERIOR", "SUPERIOR")  # 25 pertenece al término superior (>= 25)
    assert (menor_igual.subida(12.99), menor_igual.subida(13), menor_igual.subida(13.01)) == (0, 0, 1)
    assert (mayor_igual.subida(24.99), mayor_igual.subida(25), mayor_igual.subida(25.01)) == (0, 1, 1)


def test_rampa_del_lado_seguro() -> None:
    inferior = Corte(14, 0.5, "INFERIOR", "INFERIOR")
    superior = Corte(35, 2, "SUPERIOR", "INFERIOR")
    assert (inferior.subida(13.5), inferior.subida(13.75), inferior.subida(14)) == (0, 0.5, 1)
    assert (superior.subida(35), superior.subida(36), superior.subida(37)) == (0, 0.5, 1)


@pytest.mark.parametrize(
    "nombre",
    [
        "humedad_grano", "temperatura_almacen", "temperatura_grano_aplicable", "hr_almacen",
        "hr_aire_exterior", "actividad_agua", "vida_consumida", "aumento_termico",
        "humedad_frente_equilibrio", "aire_frente_grano",
    ],
)
def test_particiones_de_ruspini_y_normalizadas(modelo, nombre: str) -> None:
    variable = modelo.variables[nombre]
    inicio, fin = variable.universo
    for x in _malla(inicio, fin):
        grados = variable.fuzzificar(x)
        assert sum(grados.values()) == pytest.approx(1.0, abs=1e-6), (nombre, x, grados)
    for termino, funcion in variable.terminos.items():
        assert isinstance(funcion, TerminoParticion)
        puntos = _malla(inicio, fin) + [c.umbral for c in funcion.cortes]
        assert max(funcion.grado(x) for x in puntos) == 1.0, termino


def test_humedad_anclada_en_los_umbrales_publicados(modelo) -> None:
    humedad = modelo.variables["humedad_grano"]
    assert humedad.fuzzificar(12.5) == {"APTA_BASE": 1.0, "CONDICIONAL": 0.0, "NO_APTA": 0.0}
    assert humedad.fuzzificar(13.0) == {"APTA_BASE": 0.0, "CONDICIONAL": 1.0, "NO_APTA": 0.0}
    assert humedad.fuzzificar(13.8) == {"APTA_BASE": 0.0, "CONDICIONAL": 0.4, "NO_APTA": 0.6}
    assert humedad.fuzzificar(14.0)["NO_APTA"] == 1.0
    assert humedad.terminos["CONDICIONAL"].describir() == "trap(12.5; 13; 13.5; 14)"


def test_temperatura_tiene_cuatro_terminos(modelo) -> None:
    temperatura = modelo.variables["temperatura_grano_aplicable"]
    assert temperatura.fuzzificar(23.5) == {"FRIA": 0.0, "TEMPLADA": 0.75, "CALIDA": 0.25, "MUY_CALIDA": 0.0}
    assert temperatura.fuzzificar(14.0)["TEMPLADA"] == 0.5
    assert temperatura.fuzzificar(36.0) == {"FRIA": 0.0, "TEMPLADA": 0.0, "CALIDA": 0.5, "MUY_CALIDA": 0.5}


# --- Salida, agregación y centroide ---------------------------------------------


@pytest.mark.parametrize(
    ("alturas", "esperado"),
    [
        ({"BAJA": 1.0}, 9.259),
        ({"MODERADA": 1.0}, 35.0),
        ({"ALTA": 1.0}, 65.0),
        ({"CRITICA": 1.0}, 90.741),
        ({"BAJA": 1.0, "MODERADA": 1.0}, 23.077),
        ({"BAJA": 1.0, "CRITICA": 1.0}, 50.0),
        ({"BAJA": 1.0, "MODERADA": 1.0, "ALTA": 0.25}, 30.72),
        ({"BAJA": 1.0, "ALTA": 0.4, "CRITICA": 0.6}, 48.13),
    ],
)
def test_centroides_de_referencia(modelo, alturas: dict[str, float], esperado: float) -> None:
    assert modelo.salida.centroide(alturas) == pytest.approx(esperado, abs=0.01)


def test_implicacion_de_mamdani_recorta_y_une_por_maximo(modelo) -> None:
    agregado = modelo.salida.agregar({"MODERADA": 0.5, "ALTA": 0.25})
    salida = modelo.salida
    for y, mu in zip(salida.abscisas, agregado):
        esperado = max(min(0.5, salida.terminos["MODERADA"].grado(y)), min(0.25, salida.terminos["ALTA"].grado(y)))
        assert mu == pytest.approx(esperado)
    assert max(agregado) == 0.5


def test_conjunto_agregado_vacio_no_tiene_centroide(modelo) -> None:
    assert modelo.salida.centroide({}) is None
    assert modelo.salida.centroide({"BAJA": 0.0}) is None


def test_bandas_del_indice(modelo) -> None:
    assert modelo.banda(9.26).decision == "AUTORIZAR_ALMACENAMIENTO"
    assert modelo.banda(25.0).decision == "AUTORIZAR_CON_MONITOREO"
    assert modelo.banda(49.99).decision == "AUTORIZAR_CON_MONITOREO"
    assert modelo.banda(50.0).decision == "CORREGIR_Y_REEVALUAR"
    assert modelo.banda(100.0).decision == "CORREGIR_Y_REEVALUAR"


# --- Medidas -----------------------------------------------------------------------


def test_borrosidad_normalizada() -> None:
    assert borrosidad([0.0, 1.0, 1.0]) == 0.0
    assert borrosidad([0.5, 0.5]) == 1.0
    assert borrosidad([0.25, 0.75]) == 0.5
    assert borrosidad([]) is None


def test_distancia_de_tchebychev() -> None:
    assert distancia_tchebychev(triangular(0, 5, 10), triangular(0, 5, 10), (0, 10)) == 0.0
    assert distancia_tchebychev(triangular(0, 5, 10), triangular(1, 6, 11), (0, 12)) == pytest.approx(0.2)


# --- Validación de la sección inferencia_difusa ------------------------------------


def _base_con(modificar) -> None:
    contenido = copy.deepcopy(base_conocimiento.leer_archivos())
    modificar(contenido["operativa"])
    desde_contenido(contenido)


def test_rampas_solapadas_invalidan_la_base() -> None:
    def ensanchar(operativa):
        operativa["parametros"]["transicion_humedad"]["valor"] = 2

    with pytest.raises(BaseInvalida) as error:
        _base_con(ensanchar)
    assert any("se solapan" in e or "transicion_humedad" in e for e in error.value.errores)


def test_termino_desconocido_invalida_la_base() -> None:
    def romper(operativa):
        regla = next(r for r in operativa["reglas"] if r["id"] == "R07")
        regla["si"] = {"difuso": "hr_almacen", "es": "MUY_HUMEDA"}

    with pytest.raises(BaseInvalida) as error:
        _base_con(romper)
    assert any("no tiene el término 'MUY_HUMEDA'" in e for e in error.value.errores)


def test_teoria_no_implementada_invalida_la_base() -> None:
    def cambiar(operativa):
        operativa["inferencia_difusa"]["teoria"]["t_norma"] = "PRODUCTO"

    with pytest.raises(BaseInvalida) as error:
        _base_con(cambiar)
    assert any("t_norma" in e for e in error.value.errores)


def test_forma_mal_parametrizada_invalida_la_base() -> None:
    def cambiar(operativa):
        operativa["inferencia_difusa"]["variable_salida"]["terminos"]["ALTA"] = {"triangular": [65, 45, 85]}

    with pytest.raises(BaseInvalida) as error:
        _base_con(cambiar)
    assert any("a < m < b" in e for e in error.value.errores)


def test_corte_alfa_fuera_de_rango_invalida_la_base() -> None:
    def cambiar(operativa):
        operativa["parametros"]["corte_correccion"]["valor"] = 1.5

    with pytest.raises(BaseInvalida):
        _base_con(cambiar)


def test_anchos_nulos_son_una_base_valida() -> None:
    base = desde_contenido(contenido_con_anchos(0.0))
    assert base.es_difusa
    assert base.modelo_difuso is not None
    assert base.modelo_difuso.variables["humedad_grano"].fuzzificar(13.0)["APTA_BASE"] == 1.0
