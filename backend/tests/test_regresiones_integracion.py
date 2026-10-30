
from test_integracion_api import entrada, unidad
import pytest
from concurrent.futures import ThreadPoolExecutor


@pytest.mark.bd
@pytest.mark.parametrize('misma_clave', [True, False])
def test_evaluaciones_concurrentes_no_duplican_efectos(api_real, misma_clave):
    c, h, _ = api_real
    u = unidad(c)
    body = entrada(u, {'estado_fisico_sanitario': 'HALLAZGO_CRITICO'})
    primero = h()
    headers = [primero, primero if misma_clave else h()]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda cabeceras: c.post(
            f'/api/v1/unidades/{u["id"]}/evaluaciones', json=body, headers=cabeceras
        ), headers))
    assert sorted(r.status_code for r in responses) == ([201, 201] if misma_clave else [201, 409])
    if misma_clave:
        assert responses[0].json() == responses[1].json()
    historial = c.get(f'/api/v1/unidades/{u["id"]}/historial').json()['items']
    incidencias = c.get(f'/api/v1/unidades/{u["id"]}/incidencias').json()['items']
    assert len(historial) == 1
    assert len([i for i in incidencias if i['tipo'] == 'CUARENTENA']) == 1
