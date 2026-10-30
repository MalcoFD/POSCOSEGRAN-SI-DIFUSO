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
    from poscosegran.dominio.campos import CAMPOS
    now = datetime.now(UTC)-timedelta(seconds=1)
    valores = {'humedad_grano':12.0,'temperatura_grano':10.0,'hr_almacen':50.0,'estado_fisico_sanitario':'SIN_HALLAZGOS'}
    if unidad.get('tipo_almacenamiento') == 'HERMETICO':
        valores.pop('hr_almacen')
        valores.update(estado_barrera='INTEGRA',procedimiento_interno='SENSOR_INTERNO')
    if campos:
        valores.update(campos)
    if campos == {}:
        valores = {}
    observations = [{'campo':k,'captura':'APORTADO','valor':v,'unidad':CAMPOS[k].unidad,
        'valor_original':str(v),'fecha_observacion':now.isoformat(),
        'metodo':'INSTRUMENTAL' if isinstance(v,(float,int)) and not isinstance(v,bool) else 'INSPECCION',
        'evidencia':'Inspección de una muestra representativa; método y resultado documentados.', 'motivo_no_aplica':None} for k,v in valores.items()]
    return {'revision_unidad':unidad['revision'],'revision_almacen':unidad['revision_almacen'],
        'fase':'INGRESO','observaciones':observations,
        'historial':{'fecha_inicio_historial':None,'vida_previa_documentada':None,'evidencia_vida_previa':None,'intervalos_historial':[]},
        'dias_previstos_restantes':None,'fecha_salida_prevista':None}


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
    body = entrada(u, {"estado_fisico_sanitario": "HALLAZGO_CRITICO"})
    key = h()
    result = post(c, f'/unidades/{u["id"]}/evaluaciones', body, key)
    assert result['evaluacion']['decision_final'] == 'CUARENTENA'
    assert post(c, f'/unidades/{u["id"]}/evaluaciones', body, key) == result
    u = c.get('/api/v1/unidades/' + u['id']).json()
    second = post(c, f'/unidades/{u["id"]}/evaluaciones', entrada(u, {"estado_fisico_sanitario": "SIN_HALLAZGOS"}))
    assert second['evaluacion']['decision_final'] == 'AUTORIZAR_ALMACENAMIENTO'
    assert second['vigencia']['estado'] == 'INVALIDADA'
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
