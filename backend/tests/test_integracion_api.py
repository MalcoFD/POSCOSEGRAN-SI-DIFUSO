"""Recorridos reales HTTP → servicios → PostgreSQL → motor, sin sustituir dependencias."""
import uuid
from datetime import UTC, datetime, timedelta

import pytest


pytestmark = pytest.mark.bd




def post(client, url, body, headers=None):
    response = client.post("/api/v1" + url, json=body,
                           headers=headers or {"Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 201, response.text
    return response.json()


def unidad(client):
    almacen = post(client, "/almacenes", {"nombre": "Almacén", "ubicacion": "Cusco",
                        "clima_calido": False, "fundamento_clima": "Clasificación documentada"})
    lote = post(client, "/lotes", {"codigo": str(uuid.uuid4()), "variedad": "MAIZ_CHULPI", "uso_final": "ALIMENTACION"})
    return post(client, "/unidades", {"id_lote": lote["id"], "id_almacen": almacen["id"],
                         "nombre_recipiente": "Costal 1", "tipo_almacenamiento": "NO_HERMETICO"})


def entrada(unidad, campos=None, ampliadas=True):
    from casos.base import datos_base
    from poscosegran.dominio.campos import CAMPOS
    now = datetime.now(UTC) - timedelta(seconds=1)
    observations = []
    for campo, dato in datos_base().items():
        # Sin `ampliadas`, solo la captura básica (pasos 1–5): las observaciones
        # R31–R52 quedan pendientes o llegan de una inspección de almacén.
        if campo not in CAMPOS or (not ampliadas and CAMPOS[campo].paso >= 6):
            continue
        valor = dato.valor
        if isinstance(valor, datetime):
            valor = now.isoformat()
        elif not isinstance(valor, (bool, str)):
            valor = float(valor)
        observations.append({"campo": campo, "captura": "APORTADO", "valor": valor,
                             "unidad": CAMPOS[campo].unidad, "valor_original": str(valor),
                             "fecha_observacion": now.isoformat(), "metodo": "Inspección documentada",
                             "evidencia": "Registro de campo", "motivo_no_aplica": None})
    observations += [{"campo": "ingreso_inspeccionado", "captura": "APORTADO", "valor": True,
                      "unidad": "BOOLEANO", "valor_original": None, "fecha_observacion": now.isoformat(),
                      "metodo": "Inspección", "evidencia": "Acta", "motivo_no_aplica": None}]
    for field in ("fecha_control_almacen", "fecha_inspeccion_grano"):
        observations.append({"campo": field, "captura": "APORTADO", "valor": now.isoformat(),
                             "unidad": "TEXTO", "valor_original": None, "fecha_observacion": now.isoformat(),
                             "metodo": "Acta", "evidencia": "Inspecci?n completa", "motivo_no_aplica": None})
    if campos is not None:
        observations = [o for o in observations if o["campo"] in campos]
        for obs in observations:
            obs["valor"] = campos[obs["campo"]]
    return {"revision_unidad": unidad["revision"], "revision_almacen": unidad["revision_almacen"],
            "fase": "INGRESO", "observaciones": observations,
            "historial": {"fecha_inicio_historial": now.isoformat(), "vida_previa_documentada": 0.1,
                          "evidencia_vida_previa": "Registro anterior", "intervalos_historial": []},
            "dias_previstos_restantes": 20, "fecha_salida_prevista": (now + timedelta(days=20)).isoformat()}


def agregar(body, *observaciones):
    """Añade observaciones al cuerpo sustituyendo la del mismo campo: la API rechaza duplicados."""
    nuevos = {o["campo"] for o in observaciones}
    body["observaciones"] = [o for o in body["observaciones"] if o["campo"] not in nuevos] + list(observaciones)
    return body


def test_errores_y_permiso(api_real):
    c, h, _ = api_real
    u = unidad(c)
    r = c.get('/api/v1/unidades/' + u['id'], headers=h("AJENO"))
    assert r.status_code == 404, r.text
    assert set(r.json()) == {"codigo", "mensaje", "campos", "id_solicitud"}
    assert c.get('/api/v1/me', headers={"Authorization": "Bearer invalido"}).status_code == 401
    assert c.post('/api/v1/lotes', headers=h("ADMINISTRADOR"), json={"codigo":"X", "variedad":"MAIZ_CHULPI", "uso_final":"ALIMENTACION"}).status_code == 403


def test_editar_lote(api_real):
    c, h, _ = api_real
    base = {"variedad": "MAIZ_CHULPI", "uso_final": "ALIMENTACION"}
    a = post(c, "/lotes", {"codigo": str(uuid.uuid4()), **base})
    b = post(c, "/lotes", {"codigo": str(uuid.uuid4()), **base})
    nuevo = "CH-" + str(uuid.uuid4())[:8]
    r = c.patch(f"/api/v1/lotes/{a['id']}", headers={"If-Match": f'"{a["revision"]}"'}, json={"codigo": nuevo, **base})
    assert r.status_code == 200, r.text
    assert r.json()["codigo"] == nuevo and r.json()["revision"] == a["revision"] + 1
    # Revisión obsoleta y código ajeno repetido no alteran el lote.
    assert c.patch(f"/api/v1/lotes/{a['id']}", headers={"If-Match": f'"{a["revision"]}"'}, json={"codigo": "otro", **base}).status_code == 409
    r = c.patch(f"/api/v1/lotes/{b['id']}", headers={"If-Match": f'"{b["revision"]}"'}, json={"codigo": nuevo, **base})
    assert r.status_code == 409 and r.json()["mensaje"] == "Ya existe otro lote con ese código."
    r = c.post("/api/v1/lotes", headers={"Idempotency-Key": str(uuid.uuid4())}, json={"codigo": nuevo, **base})
    assert r.status_code == 409
    assert c.patch(f"/api/v1/lotes/{a['id']}", headers={**h("AJENO"), "If-Match": '"2"'}, json={"codigo": "x", **base}).status_code == 404


def test_evaluar_reintentar_historial_cuarentena(api_real):
    c, h, _ = api_real
    u = unidad(c)
    body = entrada(u, {"moho_visible": True})
    key = h()
    result = post(c, f'/unidades/{u["id"]}/evaluaciones', body, key)
    assert result['evaluacion']['decision_final'] == 'CUARENTENA'
    assert post(c, f'/unidades/{u["id"]}/evaluaciones', body, key) == result
    u = c.get('/api/v1/unidades/' + u['id']).json()
    second = post(c, f'/unidades/{u["id"]}/evaluaciones', entrada(u, {"moho_visible": False}))
    assert second['evaluacion']['decision_final'] == 'CUARENTENA'
    assert c.get(f'/api/v1/unidades/{u["id"]}/historial').status_code == 200
    assert c.post(f'/api/v1/unidades/{u["id"]}/admisiones', headers=h(), json={
        'revision_unidad': u['revision'], 'revision_almacen': u['revision_almacen'],
        'id_evaluacion': second['evaluacion']['id'], 'tipo': 'INGRESO'}).status_code == 409


def test_caso_base_y_reutilizacion(api_real):
    c, _, _ = api_real
    u = unidad(c)
    result = post(c, f'/unidades/{u["id"]}/evaluaciones', entrada(u))
    assert result['evaluacion']['decision_final'] == 'AUTORIZAR_ALMACENAMIENTO', result
    assert result['vigencia']['estado'] == 'VIGENTE'
    u = c.get('/api/v1/unidades/' + u['id']).json()
    second = post(c, f'/unidades/{u["id"]}/evaluaciones', entrada(u, {}))
    assert second['evaluacion']['decision_final'] == 'AUTORIZAR_ALMACENAMIENTO', second
