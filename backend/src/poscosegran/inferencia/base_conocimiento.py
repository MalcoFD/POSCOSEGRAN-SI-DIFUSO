"""Conocimiento Mamdani versionado: carga, consulta y huella del modelo matricial."""

from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from functools import cached_property
from pathlib import Path
from typing import Any
import hashlib
import json
import os
import yaml
from ..sistema_difuso.matricial import validar

DECISIONES = frozenset(
    {
        "AUTORIZAR_ALMACENAMIENTO",
        "AUTORIZAR_CON_MONITOREO",
        "CORREGIR_Y_REEVALUAR",
        "SUSPENDER_ALMACENAMIENTO",
        "CUARENTENA",
        "SIN_CONCLUSION_AUTOMATICA",
    }
)


class BaseInvalida(ValueError):
    def __init__(self, errores: list[str]):
        self.errores = errores
        super().__init__("; ".join(errores))


@dataclass(frozen=True)
class Parametro:
    nombre: str
    valor: Decimal
    unidad: str = ""
    fundamento: str = "POLITICA_PROTOTIPO"
    fuentes: tuple[str, ...] = ()
    descripcion: str = ""


@dataclass(frozen=True)
class Regla:
    id: str
    regla: str
    si: Mapping[str, Any]
    entonces: str


@dataclass(frozen=True)
class BaseConocimiento:
    version_base: str
    version_parametros: str
    parametros: Mapping[str, Parametro]
    documental: Mapping[str, Any]
    contenido: Mapping[str, Any] = field(repr=False)

    @cached_property
    def hash(self) -> str:
        return hashlib.sha256(
            json.dumps(self.contenido, sort_keys=True, ensure_ascii=False, default=str).encode()
        ).hexdigest()

    @property
    def reglas(self) -> tuple[Regla, ...]:
        return tuple(
            Regla(r["id"], r["id"], r["si"], r["entonces"])
            for m in self.contenido["operativa"]["difuso"]["matrices"].values()
            for r in m["reglas"]
        )

    @property
    def decisiones_autorizadas(self) -> frozenset[str]:
        return frozenset({"AUTORIZAR_ALMACENAMIENTO", "AUTORIZAR_CON_MONITOREO"})

    def parametro(self, nombre: str) -> Decimal:
        return self.parametros[nombre].valor

    def fuentes_de(self, regla: str) -> tuple[tuple[str, str | None], ...]:
        r = next((r for r in self.documental["reglas"] if r["id"] == regla), None)
        return tuple((s, None) for s in r["fuentes"]) if r else ()

    def fundamento_de(self, regla: str) -> str:
        return next(
            (r["fundamento"] for r in self.documental["reglas"] if r["id"] == regla),
            "POLITICA_PROTOTIPO",
        )

    @cached_property
    def uso_de_campos(self) -> dict[str, tuple[str, ...]]:
        modelo = self.contenido["operativa"]["difuso"]
        return {
            campo: tuple(
                r["id"]
                for m in modelo["matrices"].values()
                if campo in m["entradas"]
                for r in m["reglas"]
            )
            for campo in modelo["entradas"]
        }


def desde_contenido(contenido: Mapping[str, Any]) -> BaseConocimiento:
    try:
        op, doc = contenido["operativa"], contenido["documental"]
        errores = validar(op["difuso"])
        if str(op["version_base"]) != str(doc["version_base"]) or str(
            op["version_parametros"]
        ) != str(doc["version_parametros"]):
            errores.append("Versiones operativa y catálogo distintas.")
        ids = {r["id"] for m in op["difuso"]["matrices"].values() for r in m["reglas"]}
        if ids != {r["id"] for r in doc["reglas"]} or len(doc["reglas"]) != 320:
            errores.append("El catálogo debe describir las mismas 320 reglas ejecutables.")
        fuentes = {s["id"] for s in doc["fuentes"]}
        if any(set(r["fuentes"]) - fuentes for r in doc["reglas"]):
            errores.append("Una regla cita una fuente inexistente.")
        if errores:
            raise BaseInvalida(errores)
        parametros = {
            k: Parametro(
                k,
                Decimal(str(p["valor"])),
                p.get("unidad", ""),
                p.get("fundamento", "POLITICA_PROTOTIPO"),
                tuple(p.get("fuentes", [])),
                p.get("descripcion", ""),
            )
            for k, p in op.get("parametros", {}).items()
        }
        return BaseConocimiento(
            str(op["version_base"]), str(op["version_parametros"]), parametros, doc, contenido
        )
    except (KeyError, TypeError, ValueError, ArithmeticError) as error:
        if isinstance(error, BaseInvalida):
            raise
        raise BaseInvalida([f"Conocimiento inválido: {error}"]) from error


def construir(operativa: Mapping[str, Any], documental: Mapping[str, Any]) -> BaseConocimiento:
    return desde_contenido({"operativa": operativa, "documental": documental})


def ruta_por_defecto() -> Path:
    configurada = os.environ.get("POSCOSEGRAN_KNOWLEDGE")
    return Path(configurada) if configurada else Path(__file__).resolve().parents[4] / "knowledge"


def leer_archivos(carpeta: Path) -> dict[str, Any]:
    return {
        k: yaml.safe_load((carpeta / n).read_text(encoding="utf-8"))
        for k, n in [("operativa", "base_conocimiento.yaml"), ("documental", "catalogo.yaml")]
    }


def cargar(carpeta: Path | None = None) -> BaseConocimiento:
    return desde_contenido(leer_archivos(carpeta or ruta_por_defecto()))


def validar_sintaxis_regla(regla: Mapping[str, Any], base: BaseConocimiento) -> list[str]:
    try:
        modelo = base.contenido["operativa"]["difuso"]
        if regla["entonces"] not in modelo["salidas"]:
            return ["Consecuente desconocido."]
        hojas = regla["si"]["todos"]
        if len(hojas) not in (3, 4) or len({h["entrada"] for h in hojas}) != len(hojas):
            return ["Cada antecedente debe aparecer una vez."]
        if any(
            h["entrada"] not in modelo["entradas"]
            or h["conjunto"] not in modelo["entradas"][h["entrada"]]["conjuntos"]
            for h in hojas
        ):
            return ["Antecedente o etiqueta desconocida."]
        return []
    except (KeyError, TypeError):
        return ["Regla Mamdani inválida: requiere id, si.todos y entonces."]
