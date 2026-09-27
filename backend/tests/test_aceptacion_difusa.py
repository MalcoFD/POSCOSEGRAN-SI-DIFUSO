"""Aceptación del sistema de inferencia difusa (sección 13 de la base 3.1).

Cubre la extensión conservadora (con δ = 0 se reproduce la lógica nítida caso a
caso), los ejemplos resueltos del plan de migración, los criterios del Modus
Ponens Generalizado, la resolución por cortes-α y la garantía de que la base
difusa nunca es más permisiva que la nítida.
"""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from casos.base import base, bul, con, desconocido, num
from casos.nitida import base_con_anchos, base_nitida
from casos.test_aceptacion import dictamen_vigente, plan_reforzado
from poscosegran.dominio.hechos import Fase, Instantanea
from poscosegran.dominio.motor import evaluar
from poscosegran.dominio.valores import Conjunto
from poscosegran.sistema_experto import base_conocimiento, serializacion
from poscosegran.sistema_experto.explicacion import explicar
from poscosegran.sistema_experto.motor import Motor, Resultado

RAIZ = Path(__file__).resolve().parents[2]
SEVERIDAD = {
    "AUTORIZAR_ALMACENAMIENTO": 1, "AUTORIZAR_CON_MONITOREO": 2, "SIN_CONCLUSION_AUTOMATICA": 3,
    "CORREGIR_Y_REEVALUAR": 4, "BLOQUEAR_INGRESO": 5, "RETIRAR_LOTE": 5, "CUARENTENA": 6,
}
AUTORIZADAS = {"AUTORIZAR_ALMACENAMIENTO", "AUTORIZAR_CON_MONITOREO"}


def _humedad(valor: str, inst: Instantanea | None = None) -> Instantanea:
    return con(inst or base(), humedad_grano=num("humedad_grano", valor))


def _temperatura(valor: str, inst: Instantanea | None = None) -> Instantanea:
    return con(inst or base(), temperatura_grano=num("temperatura_grano", valor, "CELSIUS"))


def _alturas(resultado: Resultado) -> dict[str, float]:
    assert resultado.inferencia is not None
    return dict(resultado.inferencia.salida.alturas)


# --- Extensión conservadora --------------------------------------------------------


def _casos_nitidos() -> list[tuple[str, Instantanea, dict]]:
    contenido = json.loads((RAIZ / "knowledge" / "casos_referencia_nitida.json").read_text(encoding="utf-8"))
    return serializacion.cargar_casos(contenido)


def test_con_anchos_nulos_se_reproduce_la_base_nitida_caso_a_caso() -> None:
    """Decisión, rama, reglas, motivos y pendientes idénticos en los 242 casos de la base 2.0."""
    motor = Motor(base_nitida())
    distintos = []
    for ident, inst, esperado in _casos_nitidos():
        r = motor.evaluar(inst)
        obtenido = {
            "decision": r.decision_final,
            "rama": r.rama_r30,
            "reglas": sorted(r.reglas_activadas),
            "motivos": sorted(m.id for m in r.motivos),
            "pendientes": sorted({p.campo for p in r.datos_pendientes}),
        }
        if any(obtenido[k] != sorted(esperado[k]) if isinstance(obtenido[k], list) else obtenido[k] != esperado[k]
               for k in obtenido):
            distintos.append(ident)
    assert distintos == []


def test_con_anchos_nulos_todos_los_grados_son_nitidos() -> None:
    motor = Motor(base_nitida())
    for _, inst, _ in _casos_nitidos()[::10]:
        r = motor.evaluar(inst)
        assert {a.grado for a in r.traza} <= {1.0}
        assert r.inferencia is not None
        assert all(p.grado in (0.0, 1.0) for p in r.inferencia.pertenencias)
        assert r.origen_decision != "INDICE"


def _perturbar(inst: Instantanea, campo: str, valor: str) -> Instantanea | None:
    dato = inst.datos.datos.get(campo)
    if dato is None or not dato.utilizable:
        return None
    datos = dict(inst.datos.datos)
    datos[campo] = replace(dato, valor=Decimal(valor))
    return replace(inst, datos=Conjunto(datos))


MALLA = {
    "humedad_grano": ["12.4", "12.6", "12.75", "12.9", "13", "13.25", "13.5", "13.75", "13.9", "14", "14.1"],
    "temperatura_grano": ["13", "14", "15", "23", "24", "25", "35", "36", "37"],
    "hr_almacen": ["55", "57.5", "60"],
    "actividad_agua": ["0.65", "0.675", "0.7"],
}


@pytest.mark.parametrize("factor", [0.5, 1.0, 2.0])
def test_la_base_difusa_nunca_es_mas_permisiva_que_la_nitida(factor: float) -> None:
    """Propiedad de conservadurismo en una malla alrededor de cada umbral publicado."""
    nitido, difuso = Motor(base_nitida()), Motor(base_con_anchos(factor))
    permisivos = []
    for ident, inst, _ in _casos_nitidos()[::12]:
        for campo, valores in MALLA.items():
            for valor in valores:
                variante = _perturbar(inst, campo, valor)
                if variante is None:
                    continue
                a, b = nitido.evaluar(variante), difuso.evaluar(variante)
                if SEVERIDAD[b.decision_final] < SEVERIDAD[a.decision_final]:
                    permisivos.append((ident, campo, valor, a.decision_final, b.decision_final))
    assert permisivos == []


ESCENARIOS = {
    "sin_plan": lambda: base(),
    "con_plan": lambda: replace(base(), plan=plan_reforzado()),
    "dictamen_y_plan": lambda: replace(base(), dictamen=dictamen_vigente(), plan=plan_reforzado()),
}
BARRIDOS = {
    "humedad_grano": ("PCT_BH", 1200, 1501, 5),
    "temperatura_grano": ("CELSIUS", 1000, 4001, 25),
    "hr_almacen": ("PCT_HR", 5000, 6501, 50),
}


@pytest.mark.parametrize("escenario", sorted(ESCENARIOS))
@pytest.mark.parametrize("campo", sorted(BARRIDOS))
def test_la_severidad_es_monotona_en_cada_variable_adversa(escenario: str, campo: str) -> None:
    """Monotonía: una lectura más desfavorable nunca produce una decisión más favorable.

    Detectó que un dictamen para la banda [13, 14] dejaba "sin cubrir" a un lote
    más seco y parcialmente condicional (12,75 %).
    """
    unidad, desde, hasta, paso = BARRIDOS[campo]
    anterior = 0
    for centesimas in range(desde, hasta, paso):
        valor = str(Decimal(centesimas) / 100)
        r = evaluar(con(ESCENARIOS[escenario](), **{campo: num(campo, valor, unidad)}))
        actual = SEVERIDAD[r.decision_final]
        assert actual >= anterior, (campo, valor, r.decision_final)
        anterior = actual


# --- Umbrales efectivos (casos C02 y C04 con la base difusa) ---------------------------


def test_humedad_trece_ya_es_condicional() -> None:
    """C02 nítido: 13,0 % autoriza. Difuso: 13,0 es núcleo de CONDICIONAL; sin dictamen se corrige."""
    r = evaluar(_humedad("13"))
    assert r.decision_final == "CORREGIR_Y_REEVALUAR"
    assert "R02" in r.reglas_activadas and "R03" not in r.reglas_activadas


def test_humedad_catorce_es_no_apta() -> None:
    """C04 nítido: 14,0 % admite con dictamen. Difuso: el núcleo de NO_APTA empieza en 14 %."""
    inst = replace(base(), dictamen=dictamen_vigente(), plan=plan_reforzado())
    r = evaluar(_humedad("14", inst))
    assert r.decision_final == "BLOQUEAR_INGRESO"
    assert r.rama_r30 == "R30.2"


def test_humedad_holgada_sigue_autorizando() -> None:
    r = evaluar(_humedad("12.5"))
    assert r.decision_final == "AUTORIZAR_ALMACENAMIENTO"
    assert r.origen_decision == "NITIDO"


# --- Ejemplos resueltos del plan (sección 8.5) -----------------------------------------------


def test_ejemplo_a_enmascaramiento_la_cuarentena_no_sale_del_indice() -> None:
    r = evaluar(con(base(), moho_visible=bul("moho_visible", True)))
    assert _alturas(r) == {"BAJA": 1.0, "CRITICA": 1.0}
    assert r.inferencia is not None and r.inferencia.salida.indice == pytest.approx(50.0, abs=0.01)
    assert r.decision_final == "CUARENTENA" and r.rama_r30 == "R30.1"


def test_ejemplo_b_temperatura_en_transicion() -> None:
    r = evaluar(_temperatura("23.5", replace(base(), plan=plan_reforzado())))
    assert _alturas(r) == {"BAJA": 1.0, "MODERADA": 1.0, "ALTA": 0.25}
    assert r.inferencia is not None and r.inferencia.salida.indice == pytest.approx(30.72, abs=0.01)
    assert r.decision_final == "AUTORIZAR_CON_MONITOREO" and r.rama_r30 == "R30.7"
    motivo = next(m for m in r.motivos if m.regla == "R08")
    assert motivo.grado == 0.25 and "0.25" in motivo.mensaje


def test_ejemplo_c_humedad_13_8_se_degrada_a_correccion() -> None:
    r = evaluar(_humedad("13.8"))
    grados = dict(r.grados_hechos)
    assert grados["HUMEDAD_NO_APTA"] == 0.6 and grados["HUMEDAD_CONDICIONAL"] == 0.4
    assert dict(r.grados_solicitudes)["SUSPENSION_SOLICITADA"] == 0.6
    assert dict(r.grados_solicitudes)["CORRECCION_SOLICITADA"] == 0.6  # degradación con su grado
    assert r.decision_final == "CORREGIR_Y_REEVALUAR" and r.rama_r30 == "R30.4"
    assert r.origen_decision == "CORTE_ALFA"


def test_ejemplo_c_con_dictamen_la_difusa_corrige() -> None:
    inst = replace(base(), dictamen=dictamen_vigente(), plan=plan_reforzado())
    assert Motor(base_nitida()).evaluar(_humedad("13.8", inst)).decision_final == "AUTORIZAR_CON_MONITOREO"
    assert evaluar(_humedad("13.8", inst)).decision_final == "CORREGIR_Y_REEVALUAR"


def test_la_suspension_solo_decide_en_su_nucleo() -> None:
    parcial, plena = evaluar(_humedad("13.9")), evaluar(_humedad("14.2"))
    assert parcial.decision_final == "CORREGIR_Y_REEVALUAR"
    assert plena.decision_final == "BLOQUEAR_INGRESO"
    seguimiento = evaluar(_humedad("14.2", replace(base(), fase=Fase.SEGUIMIENTO)))
    assert seguimiento.decision_final == "RETIRAR_LOTE"


# --- Etiquetas compuestas ------------------------------------------------------------


def test_etiqueta_compuesta_sin_valle_en_la_frontera_interna() -> None:
    """A 24 °C "TEMPLADA o CALIDA" vale 1, como la condición nítida 15 <= t <= 35."""
    r = evaluar(_temperatura("24", replace(base(), plan=plan_reforzado())))
    assert dict(r.grados_hechos)["AMBIENTE_FAVORABLE_A_INSECTOS"] == 1.0
    assert dict(r.grados_hechos)["RIESGO_TERMICO"] == 0.5


def test_la_frontera_de_insectos_esta_del_lado_seguro() -> None:
    fria = evaluar(_temperatura("14", replace(base(), plan=plan_reforzado())))
    assert dict(fria.grados_hechos)["AMBIENTE_FAVORABLE_A_INSECTOS"] == 0.5
    assert fria.decision_final == "AUTORIZAR_CON_MONITOREO"
    assert evaluar(_temperatura("13", replace(base(), plan=plan_reforzado()))).decision_final == "AUTORIZAR_ALMACENAMIENTO"


# --- Criterios del Modus Ponens Generalizado ----------------------------------------------


def test_criterio_1_antecedente_pleno_concluye_el_consecuente() -> None:
    """A′ = A (lectura en el núcleo) ⇒ B′ = B: la regla se activa con α = 1."""
    r = evaluar(_humedad("15"))
    activacion = next(a for a in r.traza if a.produccion == "R01")
    assert activacion.grado == 1.0 and activacion.terminos_salida == ("CRITICA",)
    assert _alturas(r)["CRITICA"] == 1.0


def test_criterio_4_antecedente_negado_no_concluye() -> None:
    """A′ = no A ⇒ con la implicación de Mamdani B′ = ∅: la regla no se dispara."""
    r = evaluar(_humedad("12"))
    assert "R01" not in {a.produccion for a in r.traza}
    assert "CRITICA" not in _alturas(r)


def test_dato_desconocido_no_se_convierte_en_favorable() -> None:
    """La ignorancia es el intervalo [0, 1]: no dispara reglas y deja el dato pendiente."""
    r = evaluar(con(base(), humedad_grano=desconocido("humedad_grano")))
    assert not {"R01", "R02", "R03"} & set(r.reglas_activadas)
    assert r.decision_final == "SIN_CONCLUSION_AUTOMATICA"
    assert r.origen_decision == "PENDIENTES"


def test_grado_de_activacion_es_el_minimo_del_antecedente() -> None:
    r = evaluar(_humedad("13.75"))
    activaciones = {a.produccion: a.grado for a in r.traza}
    assert activaciones["R01"] == 0.5 and activaciones["R02"] == 0.5


# --- Resolución por cortes-α e índice ------------------------------------------------------


def test_monitoreo_parcial_sin_plan_exige_correccion() -> None:
    r = evaluar(_temperatura("14"))
    assert r.decision_final == "CORREGIR_Y_REEVALUAR"
    assert dict(r.grados_solicitudes)["CORRECCION_SOLICITADA"] == 0.5


def test_el_indice_solo_endurece() -> None:
    for inst in (base(), _humedad("13.8"), con(base(), moho_visible=bul("moho_visible", True))):
        r = evaluar(inst)
        estructural = Motor(base_nitida()).evaluar(inst)
        assert r.inferencia is not None
        if r.origen_decision == "INDICE":
            assert SEVERIDAD[r.decision_final] > SEVERIDAD[estructural.decision_final]


def test_el_indice_puede_endurecer_una_autorizacion() -> None:
    """Una autorización cuyo índice cae en la banda de corrección se corrige."""
    contenido = copy.deepcopy(base_conocimiento.leer_archivos())
    bandas = contenido["operativa"]["inferencia_difusa"]["bandas"]
    bandas[0]["hasta"] = 5  # cualquier índice >= 5 ya no autoriza sin seguimiento
    bandas[1]["hasta"] = 8
    motor = Motor(base_conocimiento.desde_contenido(contenido))
    r = motor.evaluar(base())
    assert r.decision_final == "CORREGIR_Y_REEVALUAR"
    assert r.origen_decision == "INDICE"
    assert any(m.id == "R30.4:INDICE_SEVERIDAD" for m in r.motivos)
    e = explicar(r, motor.base)
    assert "índice de severidad" in e.resumen


def test_invariante_ninguna_solicitud_adversa_sobre_su_corte_termina_en_autorizacion() -> None:
    cortes = {"CUARENTENA_SOLICITADA": 1.0, "SUSPENSION_SOLICITADA": 1.0, "CORRECCION_SOLICITADA": 0.5}
    for _, inst, _ in _casos_nitidos()[::7]:
        r = evaluar(inst)
        grados = dict(r.grados_solicitudes)
        if any(grados.get(s, 0.0) >= c for s, c in cortes.items()):
            assert r.decision_final not in AUTORIZADAS


@pytest.mark.parametrize("escenario", sorted(ESCENARIOS))
def test_invariante_monitoreo_exige_plan_vigente(escenario: str) -> None:
    """Autorizar con monitoreo sin plan registrado y vigente sería una orden inejecutable.

    Detectó que, con antecedente parcial, la implicación de rama_condicional_admisible
    dejaba elegible R30.6 a 12,55 % sin dictamen ni plan.
    """
    variantes = [
        con(ESCENARIOS[escenario](), **{campo: num(campo, str(Decimal(c) / 100), unidad)})
        for campo, (unidad, desde, hasta, paso) in BARRIDOS.items()
        for c in range(desde, hasta, paso * 4)
    ]
    for inst in variantes + [inst for _, inst, _ in _casos_nitidos()[::5]]:
        r = evaluar(inst)
        if r.decision_final == "AUTORIZAR_CON_MONITOREO":
            assert inst.plan.registrado and inst.plan.vigente


# --- Explicación y evidencias ------------------------------------------------------------------


def test_explicacion_con_grados_cortes_e_indice() -> None:
    r = evaluar(_temperatura("23.5", replace(base(), plan=plan_reforzado())))
    e = explicar(r, base_conocimiento.cargar())
    elegida = next(x for x in e.ramas if x.aplicada)
    assert elegida.rama == "R30.7" and elegida.grado == 0.75 and elegida.corte == 0.5  # temperatura_bajo_alerta = 0,75
    r304 = next(x for x in e.ramas if x.rama == "R30.4")
    assert r304.grado == 0.25 and not r304.aplicada
    assert "Índice de severidad difuso: 30.7" in e.resumen
    assert e.inferencia is not None and e.origen_decision == r.origen_decision
    assert {p.grado for p in e.cadena} >= {1.0}


def test_evidencia_de_pertenencia() -> None:
    r = evaluar(_humedad("13.8"))
    motivo = next(m for m in r.motivos if m.regla == "R01")
    evidencia = motivo.evidencias[0]
    assert (evidencia.operador, evidencia.termino, evidencia.grado) == ("PERTENENCIA", "NO_APTA", 0.6)
    assert evidencia.umbral is None


def test_fuzzificacion_registrada_y_borrosidad() -> None:
    r = evaluar(_humedad("13.8"))
    assert r.inferencia is not None
    humedad = {p.termino: p.grado for p in r.inferencia.pertenencias if p.variable == "humedad_grano"}
    assert humedad == {"APTA_BASE": 0.0, "CONDICIONAL": 0.4, "NO_APTA": 0.6}
    assert r.inferencia.borrosidad is not None and 0 < r.inferencia.borrosidad < 1
    nitida = evaluar(base())
    assert nitida.inferencia is not None and nitida.inferencia.borrosidad == 0.0


def test_la_refraccion_termina_y_no_duplica_motivos() -> None:
    r = evaluar(_humedad("13.8"))
    ids = [m.id for m in r.motivos]
    assert len(ids) == len(set(ids))


def test_el_operador_difuso_exige_declarar_el_modelo() -> None:
    contenido = copy.deepcopy(base_conocimiento.leer_archivos())
    contenido["operativa"].pop("inferencia_difusa")
    with pytest.raises(base_conocimiento.BaseInvalida) as error:
        base_conocimiento.desde_contenido(contenido)
    assert any("inferencia_difusa" in e for e in error.value.errores)
