"""Contrato matemático y semántico del modelo matricial de 320 reglas."""

from __future__ import annotations

import copy
from dataclasses import replace
from datetime import timedelta
from itertools import product
import json
import math

import pytest

from casos.base import base, con, num, sin, txt
from poscosegran.dominio.hechos import Modalidad
from poscosegran.dominio.motor import evaluar
from poscosegran.inferencia import adquisicion, serializacion
from poscosegran.inferencia.base_conocimiento import BaseInvalida, cargar, desde_contenido
from poscosegran.inferencia.base_conocimiento import ruta_por_defecto
from poscosegran.sistema_difuso.defuzzificacion import centroide
from poscosegran.sistema_difuso.pertenencia import pertenencia

MODELO = cargar()
FIS = MODELO.contenido["operativa"]["difuso"]
ANCLAS = {
    "humedad_grano": dict(
        zip(FIS["entradas"]["humedad_grano"]["conjuntos"], [12, 12.75, 13.75, 15])
    ),
    "temperatura_grano": dict(
        zip(FIS["entradas"]["temperatura_grano"]["conjuntos"], [10, 20, 25, 35])
    ),
    "hr_almacen": dict(zip(FIS["entradas"]["hr_almacen"]["conjuntos"], [45, 55, 60, 75])),
}
TODAS = [(m, r) for m, d in FIS["matrices"].items() for r in d["reglas"]]


def test_ruta_del_conocimiento_respeta_el_contenedor(monkeypatch, tmp_path):
    monkeypatch.setenv("POSCOSEGRAN_KNOWLEDGE", str(tmp_path))
    assert ruta_por_defecto() == tmp_path


def test_jsonb_no_cambia_el_orden_semantico_de_la_matriz():
    reordenada = json.loads(json.dumps(MODELO.contenido, sort_keys=True))
    recuperada = desde_contenido(reordenada)
    assert recuperada.hash == MODELO.hash
    assert evaluar(instancia(), recuperada).decision_final == "AUTORIZAR_ALMACENAMIENTO"


@pytest.mark.parametrize("alteracion", ["decision", "orden", "vigencia", "control", "id", "tipo"])
def test_propuestas_no_pueden_cambiar_significado_del_protocolo(alteracion):
    contenido = copy.deepcopy(MODELO.contenido)
    m = contenido["operativa"]["difuso"]
    if alteracion == "decision":
        m["clasificacion"][-1]["decision"] = "AUTORIZAR_ALMACENAMIENTO"
    elif alteracion == "orden":
        m["clasificacion"].reverse()
    elif alteracion == "vigencia":
        m["politica"]["vigencia_medicion_horas"] = float("inf")
    elif alteracion == "control":
        m["clasificacion"][0]["control_dias"] = -1
    elif alteracion == "id":
        m["matrices"]["HERMETICO"]["reglas"][0]["id"] = "OTRA"
    else:
        m["entradas"]["estado_fisico_sanitario"]["tipo"] = "CONTINUA"
    with pytest.raises(BaseInvalida):
        desde_contenido(contenido)


def instancia(modalidad="NO_HERMETICO", **valores):
    b = base()
    b = replace(b, tipo_almacenamiento=Modalidad(modalidad))
    datos = {
        k: txt(k, v)
        if isinstance(v, str)
        else num(
            k,
            str(v),
            "PCT_BH" if k == "humedad_grano" else "PCT_HR" if k == "hr_almacen" else "CELSIUS",
        )
        for k, v in valores.items()
    }
    if modalidad == "HERMETICO":
        datos.update(
            estado_barrera=txt("estado_barrera", "INTEGRA"),
            procedimiento_interno=txt("procedimiento_interno", "SENSOR_INTERNO"),
        )
    return con(b, **datos)


@pytest.mark.parametrize("modalidad,regla", TODAS, ids=[r["id"] for _, r in TODAS])
def test_cada_antecedente_de_la_matriz_activa_su_regla(modalidad, regla):
    valores = {
        h["entrada"]: h["conjunto"]
        if h["entrada"] == "estado_fisico_sanitario"
        else ANCLAS[h["entrada"]][h["conjunto"]]
        for h in regla["si"]["todos"]
    }
    r = evaluar(instancia(modalidad, **valores), MODELO)
    x = r.difuso["decision"]
    assert r.reglas_activadas == (regla["id"],)
    activa = next(z for z in x["reglas"] if z["alfa"] > 0)
    assert activa["alfa"] == 1
    assert activa["entonces"] == regla["entonces"]
    assert x["centroide"] == pytest.approx(centroide([(FIS["salidas"][regla["entonces"]], 1)])[0])


@pytest.mark.parametrize("x,esperado", [(0, 1), (12, 1), (12.25, 0.5), (12.5, 0), (100, 0)])
def test_pertenencia_hombro_y_transicion(x, esperado):
    assert pertenencia(x, [0, 0, 12, 12.5]) == esperado


def test_ocho_reglas_activas_y_minimo_de_antecedentes():
    r = evaluar(instancia(humedad_grano=12.25, temperatura_grano=17.5, hr_almacen=52.5), MODELO)
    activas = [x for x in r.difuso["decision"]["reglas"] if x["alfa"] > 0]
    assert len(activas) == 8
    assert all(x["alfa"] == 0.5 for x in activas)


def test_centroide_contrasta_con_integracion_numerica_independiente():
    pares = [([0, 0, 6, 12], 0.35), ([20, 28, 36], 0.7), ([44, 52, 60], 0.25)]
    exacto = centroide(pares)[0]
    # Regla del punto medio sobre una malla independiente de los vértices del motor.
    n = 50000
    area = momento = 0.0
    for i in range(n):
        x = (i + 0.5) * 100 / n
        valores = []
        for p, alfa in pares:
            a, b, c, d = p if len(p) == 4 else [p[0], p[1], p[1], p[2]]
            y = (
                0
                if x < a or x > d
                else 1
                if b <= x <= c
                else (x - a) / (b - a)
                if x < b
                else (d - x) / (d - c)
            )
            valores.append(min(alfa, y))
        mu = max(valores)
        area += mu
        momento += x * mu
    assert exacto == pytest.approx(momento / area, abs=1e-5)


def test_agregacion_no_duplica_area_ni_promedia_centroides():
    p = [20, 28, 36]
    a = centroide([(p, 0.3), (p, 0.8)])
    b = centroide([(p, 0.8)])
    assert a == b
    mezcla = centroide([([0, 0, 6, 12], 1), (p, 1)])[0]
    assert not math.isclose(mezcla, (4.6666666667 + 28) / 2, abs_tol=0.01)


@pytest.mark.parametrize(
    "campo", ["humedad_grano", "temperatura_grano", "hr_almacen", "estado_fisico_sanitario"]
)
def test_falta_de_entrada_no_es_favorable(campo):
    r = evaluar(sin(instancia(), campo), MODELO)
    assert r.decision_final == "SIN_CONCLUSION_AUTOMATICA"
    assert r.difuso["decision"]["centroide"] is None
    assert campo in {p.campo for p in r.datos_pendientes}


def test_hermetico_excluye_hr_sin_sustituirla_por_cero():
    r = evaluar(sin(instancia("HERMETICO"), "hr_almacen"), MODELO)
    assert r.decision_final == "AUTORIZAR_ALMACENAMIENTO"
    assert len(r.difuso["decision"]["reglas"]) == 64
    assert r.difuso["decision"]["entradas"]["hr_almacen"]["estado"] == "NO_APLICA"
    assert r.difuso["decision"]["entradas"]["hr_almacen"]["pertenencias"] == {}


@pytest.mark.parametrize("campo", ["estado_barrera", "procedimiento_interno"])
def test_hermetico_exige_contexto_observado(campo):
    r = evaluar(sin(instancia("HERMETICO"), campo), MODELO)
    assert r.decision_final == "SIN_CONCLUSION_AUTOMATICA"


@pytest.mark.parametrize("valor", [-31, 91, float("inf"), float("nan")])
def test_fuera_de_dominio_o_no_finito_no_autoriza(valor):
    r = evaluar(instancia(temperatura_grano=valor), MODELO)
    assert r.difuso["decision"]["centroide"] is None


@pytest.mark.parametrize(
    "cambio", ["futuro", "vencido", "sin_metodo", "sin_evidencia", "estado_desconocido"]
)
def test_calidad_y_fecha_de_las_observaciones(cambio):
    b = instancia()
    d = b.datos["estado_fisico_sanitario"]
    if cambio == "futuro":
        d = replace(d, fecha_observacion=b.fecha_evaluacion + timedelta(minutes=1))
    elif cambio == "vencido":
        d = replace(d, fecha_observacion=b.fecha_evaluacion - timedelta(days=8))
    elif cambio == "sin_metodo":
        d = replace(d, metodo=None)
    elif cambio == "sin_evidencia":
        d = replace(d, evidencia=None)
    else:
        d = replace(d, valor="NO_INSPECCIONADO")
    r = evaluar(con(b, estado_fisico_sanitario=d), MODELO)
    assert r.decision_final == "SIN_CONCLUSION_AUTOMATICA"


def test_critico_nunca_se_compensa_en_transiciones_continuas():
    for h, t, hr in product(
        [12, 12.25, 13.25, 14.25], [10, 17.5, 22.5, 27.5], [45, 52.5, 57.5, 65]
    ):
        r = evaluar(
            instancia(
                humedad_grano=h,
                temperatura_grano=t,
                hr_almacen=hr,
                estado_fisico_sanitario="HALLAZGO_CRITICO",
            ),
            MODELO,
        )
        assert r.decision_final == "CUARENTENA"
        assert {x["entonces"] for x in r.difuso["decision"]["reglas"] if x["alfa"] > 0} == {
            "separacion"
        }


@pytest.mark.parametrize(
    "defecto", ["falta", "duplicada", "curva", "critico", "inversion", "fuente", "catalogo"]
)
def test_modelo_inconsistente_no_se_carga(defecto):
    c = copy.deepcopy(dict(MODELO.contenido))
    m = c["operativa"]["difuso"]
    rs = m["matrices"]["NO_HERMETICO"]["reglas"]
    if defecto == "falta":
        rs.pop()
    elif defecto == "duplicada":
        rs[-1] = copy.deepcopy(rs[0])
    elif defecto == "curva":
        m["entradas"]["humedad_grano"]["conjuntos"]["alto"] = [15, 10, 5]
    elif defecto == "critico":
        rs[3]["entonces"] = "favorable"
    elif defecto == "inversion":
        rs[0]["entonces"] = "suspension"
    elif defecto == "fuente":
        c["documental"]["reglas"][0]["fuentes"] = ["S99"]
    else:
        c["documental"]["reglas"].pop()
    with pytest.raises(BaseInvalida):
        desde_contenido(c)


def test_reproduccion_serializada_y_huella():
    b = instancia("HERMETICO")
    a = evaluar(b, MODELO)
    reconstruida = serializacion.desde_json(json.loads(json.dumps(serializacion.a_json(b))))
    r = evaluar(reconstruida, MODELO)
    assert r.difuso == a.difuso
    assert r.hash_base == MODELO.hash


def test_propuesta_de_matriz_se_valida_y_compara():
    modelo = copy.deepcopy(FIS)
    modelo["entradas"]["temperatura_grano"]["conjuntos"]["bajo"][-2] = 14
    r = adquisicion.proponer(
        MODELO,
        motivo="Revisión técnica de la transición térmica",
        version_base="6.1-prueba",
        difuso=modelo,
        casos=[("caso", "prueba", instancia())],
    )
    assert r.valida and r.impacto.evaluados == 1
    assert r.contenido["documental"]["version_base"] == "6.1-prueba"
    modelo["matrices"]["HERMETICO"]["reglas"].pop()
    assert not adquisicion.proponer(
        MODELO,
        motivo="Ensayo de matriz incompleta",
        version_base="6.2-prueba",
        difuso=modelo,
        casos=[],
    ).valida
