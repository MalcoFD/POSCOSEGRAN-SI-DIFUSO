"""El catálogo se rechaza si no está completo: nunca se completa por inferencia."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from poscosegran.conocimiento.esquema import Catalogo


def _regla(codigo: str) -> dict[str, object]:
    return {
        "id": codigo,
        "antecedente": "antecedente de ejemplo",
        "consecuente": "consecuente de ejemplo",
        "accion": "acción de ejemplo",
        "fundamento_markdown": "fundamento de ejemplo",
        "fundamento": "POLITICA_PROTOTIPO",
        "fuentes": [],
    }


def _reglas() -> list[dict[str, object]]:
    return [_regla(f"R{n:02d}") for n in range(1, 53)]


def _catalogo(**cambios: object) -> dict[str, object]:
    base: dict[str, object] = {
        "version_base": "5.1",
        "version_parametros": "1.0",
        "version_motor": "3.0.0-mamdani",
        "reglas": _reglas(),
        "fuentes": [{"id": f"S0{n}", "referencia_markdown": "referencia"} for n in range(1, 10)],
    }
    base.update(cambios)
    return base


def test_catalogo_completo_es_valido() -> None:
    catalogo = Catalogo.model_validate(_catalogo())
    assert len(catalogo.reglas) == 52


def test_faltan_reglas_invalida_el_catalogo() -> None:
    with pytest.raises(ValidationError):
        Catalogo.model_validate(_catalogo(reglas=_reglas()[:-1]))


def test_las_ramas_r30_ya_no_se_admiten() -> None:
    with pytest.raises(ValidationError):
        Catalogo.model_validate(_catalogo(ramas_r30=[_regla("R30.1")]))


def test_fuente_no_declarada_invalida_el_catalogo() -> None:
    reglas = _reglas()
    reglas[0]["fuentes"] = ["S42"]
    with pytest.raises(ValidationError):
        Catalogo.model_validate(_catalogo(reglas=reglas))


def test_fundamento_publicado_exige_fuente() -> None:
    reglas = _reglas()
    reglas[0]["fundamento"] = "PUBLICADO"
    with pytest.raises(ValidationError):
        Catalogo.model_validate(_catalogo(reglas=reglas))
