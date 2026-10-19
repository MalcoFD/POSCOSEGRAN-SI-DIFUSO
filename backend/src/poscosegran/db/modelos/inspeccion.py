"""Inspecciones compartidas por almacén; cada registro es inmutable."""
import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..base import AHORA, Base, columna_id, fk_uuid


class InspeccionAlmacen(Base):
    __tablename__ = 'inspeccion_almacen'
    id: Mapped[uuid.UUID] = columna_id()
    id_almacen: Mapped[uuid.UUID] = fk_uuid('almacen.id', index=True)
    id_responsable: Mapped[uuid.UUID] = fk_uuid('usuario.id')
    revision_almacen: Mapped[int] = mapped_column(sa.Integer)
    fecha: Mapped[datetime] = mapped_column()
    vigente_hasta: Mapped[datetime] = mapped_column()
    evidencia: Mapped[str] = mapped_column(sa.Text)
    observaciones: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    creada_en: Mapped[datetime] = mapped_column(server_default=AHORA)
    __table_args__ = (
        sa.CheckConstraint('vigente_hasta > fecha', name='vigencia_positiva'),
        sa.CheckConstraint('revision_almacen >= 1', name='revision_positiva'),
        sa.CheckConstraint('length(btrim(evidencia)) > 0', name='evidencia_no_vacia'),
    )
