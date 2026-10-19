"""Alcance y reutilización: nunca se heredan mediciones ni hallazgos de otro lote."""
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Session

from ..db.modelos import Almacen, InspeccionAlmacen, Evento

CAMPOS_ALMACEN = frozenset({
    'fecha_limpieza_general', 'limpieza_diaria', 'polvo_humo_gases_vapores',
    'quimicos_combustibles_en_almacen', 'filtracion_agua_almacen', 'drenaje_obstruido',
    'malla_ventana_danada', 'abertura_ingreso_plagas', 'agua_estancada_entorno',
    'residuos_o_maleza_entorno', 'sacos_usados_o_desechos_en_almacen',
    'residuos_de_proceso_sin_retirar', 'programa_control_plagas_documentado',
})


def vigente(sesion: Session, almacen: Almacen, ahora: datetime, id_unidad: uuid.UUID | None = None) -> InspeccionAlmacen | None:
    # La última inspección sustituye a todas las anteriores, incluso si es parcial
    # o ha vencido: no se busca una favorable más antigua.
    fila = sesion.scalar(sa.select(InspeccionAlmacen).where(InspeccionAlmacen.id_almacen == almacen.id)
                         .order_by(InspeccionAlmacen.creada_en.desc(), InspeccionAlmacen.id.desc()).limit(1))
    if fila is None or fila.revision_almacen != almacen.revision or not fila.fecha <= ahora < fila.vigente_hasta:
        return None
    if id_unidad is not None and sesion.scalar(sa.select(Evento.id).where(
        Evento.id_unidad == id_unidad, Evento.tipo == 'EXPOSICION_AGUA', Evento.fecha >= fila.fecha).limit(1)):
        return None
    return fila
