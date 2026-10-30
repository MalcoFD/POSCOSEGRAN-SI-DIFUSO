"""Configuración de pruebas.

Las pruebas marcadas con @pytest.mark.bd exigen una base PostgreSQL migrada en
POSCOSEGRAN_BD_URL_PRUEBAS. Sin esa variable se omiten: no se simula PostgreSQL
con SQLite, porque los disparadores, los índices parciales y los arrays no se
comportan igual y una prueba que pasa en SQLite no demuestra nada aquí.

Omitirlas es aceptable en una máquina de desarrollo, pero no en integración
continua: ahí una suite que "pasa" porque no hay base es exactamente el fallo que
no debe poder ocultarse. Con POSCOSEGRAN_EXIGIR_BD=1 la ausencia de la variable
detiene la sesión en lugar de omitir.
"""

from __future__ import annotations

import os

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from poscosegran.db.modelos import Usuario, UsuarioRol

import pytest


@pytest.fixture(scope="session", autouse=True)
def registrar_cobertura_http():
    """Registra métodos, rutas y estados realmente ejercitados por la suite HTTP."""
    if os.environ.get("POSCOSEGRAN_REGISTRAR_COBERTURA") != "1":
        yield
        return
    import json
    import re
    from collections import Counter
    from urllib.parse import urlsplit

    raiz = Path(__file__).parents[2]
    contrato = json.loads((raiz / "docs/openapi.json").read_text(encoding="utf-8"))
    rutas = [(metodo.upper(), ruta, re.compile("^" + re.sub(r"\{[^}]+\}", "[^/]+", ruta) + "$"))
             for ruta, metodos in contrato["paths"].items()
             for metodo in metodos if metodo.lower() in {"get", "post", "put", "patch", "delete"}]
    if not any(ruta == "/auth/local/sesion" for _, ruta, _ in rutas):
        rutas.append(("POST", "/auth/local/sesion", re.compile("^/auth/local/sesion$")))
    llamadas = Counter()
    original = TestClient.request

    def observar(self, method, url, *args, **kwargs):
        respuesta = original(self, method, url, *args, **kwargs)
        path = urlsplit(str(respuesta.request.url)).path
        for verbo, ruta, patron in rutas:
            if verbo == method.upper() and patron.fullmatch(path):
                llamadas[(verbo, ruta, respuesta.status_code)] += 1
                break
        return respuesta

    TestClient.request = observar
    yield
    TestClient.request = original
    salida = []
    for verbo, ruta, _ in rutas:
        estados = {str(estado): cantidad for (v, p, estado), cantidad in llamadas.items() if v == verbo and p == ruta}
        salida.append({"metodo": verbo, "ruta": ruta, "estados": estados,
                       "exito_verificado": any(200 <= int(s) < 300 for s in estados)})
    destino = raiz / "test-results/cobertura-endpoints.json"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _exige_bd() -> bool:
    return os.environ.get("POSCOSEGRAN_EXIGIR_BD", "").strip().lower() in {"1", "true", "si", "yes"}


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """En CI, una prueba de integración omitida por falta de base es un fallo."""
    if not _exige_bd() or os.environ.get("POSCOSEGRAN_BD_URL_PRUEBAS"):
        return
    marcadas = [item.nodeid for item in items if item.get_closest_marker("bd")]
    if marcadas:
        raise pytest.UsageError(
            f"POSCOSEGRAN_EXIGIR_BD está activo y {len(marcadas)} pruebas marcadas 'bd' se "
            "omitirían: defina POSCOSEGRAN_BD_URL_PRUEBAS con una base PostgreSQL migrada."
        )


@pytest.fixture(scope="session")
def url_bd() -> str:
    url = os.environ.get("POSCOSEGRAN_BD_URL_PRUEBAS")
    if not url:
        if _exige_bd():
            pytest.fail("POSCOSEGRAN_BD_URL_PRUEBAS no está definida y POSCOSEGRAN_EXIGIR_BD lo exige")
        pytest.skip("POSCOSEGRAN_BD_URL_PRUEBAS no está definida")
    return url


@pytest.fixture(scope="session")
def motor(url_bd: str):  # type: ignore[no-untyped-def]
    from sqlalchemy import create_engine

    motor = create_engine(url_bd, future=True)
    yield motor
    motor.dispose()


@pytest.fixture
def configuracion_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSCOSEGRAN_ENTORNO", "pruebas")
    monkeypatch.setenv("POSCOSEGRAN_BD_URL_APP", "postgresql+psycopg://x:y@localhost/z")
    monkeypatch.setenv("POSCOSEGRAN_JWT_MODO", "SECRETO_COMPARTIDO")
    monkeypatch.setenv("POSCOSEGRAN_JWT_ALGORITMOS", "HS256")
    monkeypatch.setenv("POSCOSEGRAN_JWT_SECRETO", "s" * 48)
    monkeypatch.setenv("POSCOSEGRAN_JWT_EMISOR", "https://emisor.ejemplo/auth/v1")
    monkeypatch.setenv("POSCOSEGRAN_JWT_AUDIENCIA", "authenticated")


@pytest.fixture
def api_real(url_bd, monkeypatch):
    from poscosegran.config import obtener_configuracion
    from poscosegran.db import sesion as db
    from poscosegran.seguridad import dependencias as seguridad
    monkeypatch.setenv("POSCOSEGRAN_AUTH_LOCAL_HABILITADA", "false")
    monkeypatch.setenv("POSCOSEGRAN_ENTORNO", "pruebas")
    monkeypatch.setenv("POSCOSEGRAN_BD_URL_APP", url_bd)
    monkeypatch.setenv("POSCOSEGRAN_JWT_MODO", "SECRETO_COMPARTIDO")
    monkeypatch.setenv("POSCOSEGRAN_JWT_ALGORITMOS", "HS256")
    monkeypatch.setenv("POSCOSEGRAN_JWT_SECRETO", "pruebas-locales-" * 4)
    monkeypatch.setenv("POSCOSEGRAN_JWT_EMISOR", "http://localhost/auth/v1")
    monkeypatch.setenv("POSCOSEGRAN_LIMITE_PETICIONES_POR_MINUTO", "10000")
    monkeypatch.setenv("POSCOSEGRAN_LIMITE_PETICIONES_ESCRITURA_POR_MINUTO", "10000")
    obtener_configuracion.cache_clear()
    if db._motor:
        db._motor.dispose()
    db._motor = db._fabrica = None
    seguridad._verificador = seguridad._limitador_lectura = seguridad._limitador_escritura = None
    from poscosegran.api.app import crear_app
    from poscosegran.conocimiento.cargar import cargar
    cargar(Path(__file__).parents[2] / "knowledge", activar=True, notas=None)
    users = {}
    # Dos ingenieros del conocimiento: la separación de funciones en adquisición exige
    # que quien propone una versión y quien la activa sean identidades distintas.
    cuentas = {
        "PRODUCTOR": "PRODUCTOR",
        "TECNICO": "TECNICO",
        "ADMINISTRADOR": "ADMINISTRADOR",
        "AJENO": "PRODUCTOR",
        "INGENIERO": "INGENIERO_CONOCIMIENTO",
        "REVISOR": "INGENIERO_CONOCIMIENTO",
    }
    with Session(create_engine(url_bd)) as session, session.begin():
        for cuenta, rol in cuentas.items():
            usuario = Usuario(id=uuid.uuid4(), nombre=cuenta)
            session.add(usuario)
            session.flush()
            session.add(UsuarioRol(id_usuario=usuario.id, rol=rol, otorgado_por="pytest"))
            users[cuenta] = usuario.id
    client = TestClient(crear_app(), raise_server_exceptions=False)

    def headers(rol="PRODUCTOR", key=None):
        now = datetime.now(UTC)
        token = jwt.encode({"sub": str(users[rol]), "iss": "http://localhost/auth/v1",
                            "aud": "authenticated", "iat": now, "exp": now + timedelta(hours=1)},
                           "pruebas-locales-" * 4, algorithm="HS256")
        return {"Authorization": f"Bearer {token}", "Idempotency-Key": key or str(uuid.uuid4())}
    client.headers.update(headers())
    yield client, headers, users
    client.close()

