"""Contrato del resultado de una inferencia Mamdani directa."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from ..dominio.hechos import Accion, Estimacion, Motivo, Pendiente
from ..dominio.valores import Tri
from .base_hechos import Activacion
from .calculos import CalculosTiempo


@dataclass(frozen=True, slots=True)
class Resultado:
    decision_final: str
    motivos: tuple[Motivo, ...]
    acciones_requeridas: tuple[Accion, ...]
    datos_pendientes: tuple[Pendiente, ...]
    estimaciones: tuple[Estimacion, ...]
    reglas_activadas: tuple[str, ...]
    calculos: CalculosTiempo
    fecha_proximo_control: datetime | None
    fecha_vencimiento_autorizacion: datetime | None
    solicitudes: dict[str, tuple[str, ...]]
    riesgo_activo: Tri
    version_base: str
    version_parametros: str
    version_motor: str
    hash_base: str
    traza: tuple[Activacion, ...]
    hechos_inferidos: tuple[str, ...]
    hechos_iniciales: tuple[tuple[str, object, str], ...]
    no_aplicables: tuple[str, ...]
    difuso: dict[str, Any] | None = None
