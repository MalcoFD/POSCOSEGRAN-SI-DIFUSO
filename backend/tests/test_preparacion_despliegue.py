"""La preparación migra con DDL y conserva el conocimiento ya activado."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.mark.parametrize("activa", [None, "version-vigente"])
def test_preparador_separa_credenciales_y_no_reactiva_semilla(monkeypatch, activa) -> None:
    ruta = Path(__file__).parents[1] / "scripts" / "render_prepare.py"
    spec = importlib.util.spec_from_file_location("preparador", ruta)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    url_app = "postgresql+psycopg://aplicacion:prueba@localhost/db"
    url_admin = "postgresql+psycopg://migraciones:prueba@localhost/db"
    monkeypatch.setenv("POSCOSEGRAN_BD_URL_MIGRACIONES", url_admin)
    monkeypatch.setenv("POSCOSEGRAN_BD_URL_APP", url_app)
    monkeypatch.setattr(modulo, "obtener_configuracion", lambda: SimpleNamespace(bd_url_app=url_app))
    ejecutar = MagicMock()
    crear = MagicMock()
    crear.return_value.connect.return_value.__enter__.return_value.scalar.return_value = activa
    monkeypatch.setattr(modulo.subprocess, "run", ejecutar)
    monkeypatch.setattr(modulo.sa, "create_engine", crear)
    assert modulo.main() == 0
    assert crear.call_args.args[0] == url_admin
    assert ejecutar.call_args_list[0].kwargs["env"]["POSCOSEGRAN_BD_URL_MIGRACIONES"] == url_admin
    assert ejecutar.call_count == (2 if activa is None else 1)
    if activa is None:
        assert ejecutar.call_args_list[1].kwargs["env"]["POSCOSEGRAN_BD_URL_APP"] == url_admin
    assert modulo.os.environ["POSCOSEGRAN_BD_URL_APP"] == url_app
