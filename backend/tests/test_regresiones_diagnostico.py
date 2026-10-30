"""Regresiones de captura, trazabilidad y conocimiento matricial por HTTP."""

from datetime import UTC, datetime, timedelta
import copy
import pytest
from test_integracion_api import entrada, unidad, post


def observacion(campo, valor):
    return {
        "campo": campo,
        "captura": "APORTADO",
        "valor": valor,
        "unidad": "BOOLEANO",
        "valor_original": str(valor),
        "fecha_observacion": (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
        "metodo": "INSPECCION",
        "evidencia": "Inspección documentada de campo",
        "motivo_no_aplica": None,
    }


@pytest.mark.bd
def test_api_mamdani_guarda_traza_y_reproduce_historial(api_real):
    c, _, _ = api_real
    u = unidad(c)
    e = post(c, f'/unidades/{u["id"]}/evaluaciones', entrada(u))["evaluacion"]
    assert e["version_motor"] == "4.0.0-matricial"
    assert len(e["difuso"]["decision"]["reglas"]) == 256
    assert "modulos" not in e["difuso"]
    x = c.get(f'/api/v1/evaluaciones/{e["id"]}/explicacion')
    assert x.status_code == 200, x.text
    assert x.json()["difuso"] == e["difuso"]
    assert all(not r.startswith(("R", "MF")) for r in e["reglas_activadas"])


@pytest.mark.bd
def test_dato_actual_desconocido_no_resucita_valor_favorable(api_real):
    c, _, _ = api_real
    u = unidad(c)
    post(c, f'/unidades/{u["id"]}/evaluaciones', entrada(u))
    u = c.get("/api/v1/unidades/" + u["id"]).json()
    b = entrada(u, {})
    b["observaciones"] = [
        {
            "campo": "estado_fisico_sanitario",
            "captura": "DESCONOCIDO",
            "valor": None,
            "unidad": "TEXTO",
            "valor_original": None,
            "fecha_observacion": None,
            "metodo": None,
            "evidencia": None,
            "motivo_no_aplica": None,
        }
    ]
    e = post(c, f'/unidades/{u["id"]}/evaluaciones', b)["evaluacion"]
    assert e["decision_final"] == "SIN_CONCLUSION_AUTOMATICA"
    assert e["difuso"]["decision"]["centroide"] is None


@pytest.mark.bd
def test_hermetico_aplica_solo_64_reglas_y_documenta_integridad(api_real):
    c, _, _ = api_real
    u = unidad(c)
    r = c.patch(
        "/api/v1/unidades/" + u["id"],
        headers={"If-Match": f'"{u["revision"]}"'},
        json={
            "id_lote": u["id_lote"],
            "id_almacen": u["id_almacen"],
            "nombre_recipiente": "Hermético",
            "tipo_almacenamiento": "HERMETICO",
        },
    )
    assert r.status_code == 200, r.text
    u = r.json()
    e = post(c, f'/unidades/{u["id"]}/evaluaciones', entrada(u))["evaluacion"]
    assert e["decision_final"] == "AUTORIZAR_ALMACENAMIENTO"
    assert len(e["difuso"]["decision"]["reglas"]) == 64
    assert e["difuso"]["decision"]["entradas"]["hr_almacen"]["estado"] == "NO_APLICA"
    u = c.get("/api/v1/unidades/" + u["id"]).json()
    e = post(c, f'/unidades/{u["id"]}/evaluaciones', entrada(u, {"estado_barrera": "NO_INTEGRA"}))[
        "evaluacion"
    ]
    assert e["decision_final"] == "SIN_CONCLUSION_AUTOMATICA"


@pytest.mark.bd
def test_inspeccion_sin_evidencia_no_produce_indice(api_real):
    c, _, _ = api_real
    u = unidad(c)
    b = entrada(u)
    next(o for o in b["observaciones"] if o["campo"] == "estado_fisico_sanitario")["evidencia"] = (
        None
    )
    e = post(c, f'/unidades/{u["id"]}/evaluaciones', b)["evaluacion"]
    assert e["decision_final"] == "SIN_CONCLUSION_AUTOMATICA"


@pytest.mark.bd
def test_propuesta_de_curvas_y_rechazo_de_matriz_incompleta(api_real):
    c, h, _ = api_real
    m = copy.deepcopy(c.get("/api/v1/conocimiento").json()["modelo_difuso"])
    m["entradas"]["temperatura_grano"]["conjuntos"]["bajo"][-2] = 14
    b = {
        "motivo": "Revisión documentada de transición térmica",
        "version_base": "6.1-regresion",
        "difuso": m,
        "guardar": False,
    }
    r = c.post("/api/v1/adquisicion/propuestas", json=b, headers=h("INGENIERO"))
    assert r.status_code == 200 and r.json()["valida"], r.text
    assert r.json()["impacto"]["evaluados"] >= 320
    m["matrices"]["HERMETICO"]["reglas"].pop()
    r = c.post("/api/v1/adquisicion/propuestas", json=b, headers=h("INGENIERO"))
    assert r.status_code == 200 and not r.json()["valida"], r.text


@pytest.mark.bd
def test_control_completo_critico_abre_incidencia_sin_duplicarla(api_real):
    c, _, _ = api_real
    u = unidad(c)
    b = entrada(u, {"estado_fisico_sanitario": "HALLAZGO_CRITICO"})
    control = post(
        c,
        f'/unidades/{u["id"]}/controles',
        {
            "revision_unidad": u["revision"],
            "revision_almacen": u["revision_almacen"],
            "tipo": "GRANO",
            "fecha": b["observaciones"][0]["fecha_observacion"],
            "observaciones": b["observaciones"],
            "evidencia": "Moho observado en muestra representativa",
        },
    )
    assert control["completo"]
    items = c.get(f'/api/v1/unidades/{u["id"]}/incidencias').json()["items"]
    assert len(items) == 1 and items[0]["tipo"] == "CUARENTENA"


@pytest.mark.bd
def test_vigencia_no_supera_antiguedad_de_mediciones(api_real):
    c, _, _ = api_real
    u = unidad(c)
    b = entrada(u)
    fecha = (datetime.now(UTC) - timedelta(days=6)).isoformat()
    for o in b["observaciones"]:
        o["fecha_observacion"] = fecha
    r = post(c, f'/unidades/{u["id"]}/evaluaciones', b)
    assert r["vigencia"]["estado"] == "VIGENTE"
    limite = datetime.fromisoformat(fecha) + timedelta(days=7)
    assert (
        datetime.fromisoformat(
            r["evaluacion"]["fecha_vencimiento_autorizacion"].replace("Z", "+00:00")
        )
        <= limite
    )
