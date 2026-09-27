"""Evaluación y su traza.

Una evaluación es una instantánea inmutable: guarda la entrada efectiva, los
motivos con su evidencia y fuente, las reglas disparadas y las versiones de
conocimiento, parámetros y motor. La vigencia NO se guarda aquí: se calcula al
consultar, con el reloj del servidor.

Con el sistema de inferencia difusa se persisten además las evaluaciones
graduales: la fuzzificación (grado de pertenencia de cada lectura a cada término),
el grado de activación de cada producción y la altura de recorte de cada
consecuente de la variable de salida. La curva agregada no se guarda: se
reconstruye con las alturas y la versión de la base.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..base import AHORA, Base, columna_id, enum_texto, fk_uuid
from ..enums import (
    DECISION,
    FASE,
    FUNDAMENTO_MOTIVO,
    OPERADOR,
    ORIGEN_DECISION,
    RAMA_R30,
    RESPONSABLE_REQUERIDO,
    TIPO_ESTIMACION,
    UNIDAD_DATO,
)


class Evaluacion(Base):
    __tablename__ = "evaluacion"

    id: Mapped[uuid.UUID] = columna_id()
    id_unidad: Mapped[uuid.UUID] = fk_uuid("unidad.id", index=True)
    id_lote: Mapped[uuid.UUID] = fk_uuid("lote.id")
    id_recipiente: Mapped[uuid.UUID] = fk_uuid("recipiente.id")
    id_almacen: Mapped[uuid.UUID] = fk_uuid("almacen.id")

    fecha_evaluacion: Mapped[datetime] = mapped_column(
        server_default=AHORA, comment="Reloj del servidor; el cliente no la impone."
    )
    fase: Mapped[str | None] = mapped_column(enum_texto("fase", FASE), nullable=True)
    decision_final: Mapped[str] = mapped_column(enum_texto("decision", DECISION))
    rama_r30: Mapped[str] = mapped_column(enum_texto("rama_r30", RAMA_R30))

    entrada_efectiva: Mapped[dict[str, Any]] = mapped_column(JSONB)
    revision_unidad_usada: Mapped[int] = mapped_column(sa.Integer)
    revision_almacen_usada: Mapped[int] = mapped_column(sa.Integer)

    reglas_activadas: Mapped[list[str]] = mapped_column(
        ARRAY(sa.Text), server_default=sa.text("'{}'::text[]")
    )

    vida_consumida: Mapped[Decimal | None] = mapped_column(sa.Numeric(8, 4), nullable=True)
    vida_minima_documentada: Mapped[Decimal | None] = mapped_column(sa.Numeric(8, 4), nullable=True)
    vida_proyectada: Mapped[Decimal | None] = mapped_column(sa.Numeric(8, 4), nullable=True)
    tiempo_referencia_actual: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    celda_tabla_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    celda_humedad_fila: Mapped[Decimal | None] = mapped_column(sa.Numeric(6, 2), nullable=True)
    celda_temperatura_columna_f: Mapped[Decimal | None] = mapped_column(
        sa.Numeric(6, 2), nullable=True
    )
    celda_dias_referencia: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)

    fecha_proximo_control: Mapped[datetime | None] = mapped_column(nullable=True)
    fecha_vencimiento_autorizacion: Mapped[datetime | None] = mapped_column(nullable=True)

    indice_severidad: Mapped[Decimal | None] = mapped_column(
        sa.Numeric(6, 3), nullable=True, comment="Centroide del conjunto difuso agregado (0–100)."
    )
    banda_severidad: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    metodo_defuzzificacion: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    origen_decision: Mapped[str | None] = mapped_column(
        enum_texto("origen_decision", ORIGEN_DECISION), nullable=True
    )
    borrosidad: Mapped[Decimal | None] = mapped_column(sa.Numeric(5, 4), nullable=True)

    version_base: Mapped[str] = mapped_column(sa.Text)
    version_parametros: Mapped[str] = mapped_column(sa.Text)
    version_motor: Mapped[str] = mapped_column(sa.Text)
    id_version_conocimiento: Mapped[uuid.UUID] = fk_uuid("version_conocimiento.id")

    id_responsable: Mapped[uuid.UUID] = fk_uuid("usuario.id")

    __table_args__ = (
        sa.Index("ix_evaluacion_unidad_fecha", "id_unidad", sa.text("fecha_evaluacion DESC"), "id"),
        sa.CheckConstraint(
            "vida_consumida IS NULL OR vida_consumida >= 0", name="vida_no_negativa"
        ),
        sa.CheckConstraint(
            "fecha_vencimiento_autorizacion IS NULL "
            "OR decision_final IN ('AUTORIZAR_ALMACENAMIENTO', 'AUTORIZAR_CON_MONITOREO')",
            name="vencimiento_solo_si_autoriza",
        ),
        sa.CheckConstraint(
            "(celda_tabla_id IS NULL) = (celda_dias_referencia IS NULL)",
            name="celda_completa_o_ausente",
        ),
        sa.CheckConstraint(
            "indice_severidad IS NULL OR indice_severidad BETWEEN 0 AND 100",
            name="indice_severidad_en_rango",
        ),
        sa.CheckConstraint(
            "borrosidad IS NULL OR borrosidad BETWEEN 0 AND 1", name="borrosidad_en_rango"
        ),
    )


class Motivo(Base):
    __tablename__ = "evaluacion_motivo"

    id: Mapped[uuid.UUID] = columna_id()
    id_evaluacion: Mapped[uuid.UUID] = fk_uuid("evaluacion.id", index=True)
    orden: Mapped[int] = mapped_column(sa.SmallInteger)
    codigo: Mapped[str] = mapped_column(sa.Text, comment="Motivo.id del contrato.")
    regla: Mapped[str] = mapped_column(sa.Text, index=True)
    mensaje: Mapped[str] = mapped_column(sa.Text)
    fundamento: Mapped[str] = mapped_column(enum_texto("fundamento_motivo", FUNDAMENTO_MOTIVO))
    grado_activacion: Mapped[Decimal] = mapped_column(
        sa.Numeric(5, 4), default=Decimal(1), server_default=sa.text("1"),
        comment="Grado α de la regla (Modus Ponens Generalizado); 1 en evaluaciones nítidas.",
    )

    __table_args__ = (
        sa.UniqueConstraint("id_evaluacion", "orden"),
        sa.CheckConstraint("grado_activacion BETWEEN 0 AND 1", name="grado_activacion_en_rango"),
    )


class MotivoEvidencia(Base):
    """Valor observado frente a umbral, con el operador que los comparó."""

    __tablename__ = "motivo_evidencia"

    id: Mapped[uuid.UUID] = columna_id()
    id_motivo: Mapped[uuid.UUID] = fk_uuid("evaluacion_motivo.id", index=True)
    orden: Mapped[int] = mapped_column(sa.SmallInteger)
    campo: Mapped[str] = mapped_column(sa.Text)
    unidad_dato: Mapped[str | None] = mapped_column(
        enum_texto("unidad_dato", UNIDAD_DATO), nullable=True
    )
    fecha_observacion: Mapped[datetime | None] = mapped_column(nullable=True)
    operador: Mapped[str | None] = mapped_column(enum_texto("operador", OPERADOR), nullable=True)

    valor_numero: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 4), nullable=True)
    valor_booleano: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    valor_texto: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    umbral_numero: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 4), nullable=True)
    umbral_booleano: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    umbral_texto: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    termino: Mapped[str | None] = mapped_column(sa.Text, nullable=True, comment="Término lingüístico (PERTENENCIA).")
    grado: Mapped[Decimal | None] = mapped_column(sa.Numeric(5, 4), nullable=True)

    __table_args__ = (
        sa.UniqueConstraint("id_motivo", "orden"),
        sa.CheckConstraint("grado IS NULL OR grado BETWEEN 0 AND 1", name="grado_en_rango"),
        sa.CheckConstraint(
            "(CASE WHEN valor_numero IS NOT NULL THEN 1 ELSE 0 END) "
            "+ (CASE WHEN valor_booleano IS NOT NULL THEN 1 ELSE 0 END) "
            "+ (CASE WHEN valor_texto IS NOT NULL THEN 1 ELSE 0 END) <= 1",
            name="un_solo_valor",
        ),
        sa.CheckConstraint(
            "(CASE WHEN umbral_numero IS NOT NULL THEN 1 ELSE 0 END) "
            "+ (CASE WHEN umbral_booleano IS NOT NULL THEN 1 ELSE 0 END) "
            "+ (CASE WHEN umbral_texto IS NOT NULL THEN 1 ELSE 0 END) <= 1",
            name="un_solo_umbral",
        ),
    )


class MotivoFuente(Base):
    __tablename__ = "motivo_fuente"

    id: Mapped[uuid.UUID] = columna_id()
    id_motivo: Mapped[uuid.UUID] = fk_uuid("evaluacion_motivo.id", index=True)
    id_fuente: Mapped[str] = mapped_column(sa.Text, comment="S01–S09 del catálogo.")
    localizador: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    __table_args__ = (sa.UniqueConstraint("id_motivo", "id_fuente", "localizador"),)


class AccionRequerida(Base):
    __tablename__ = "evaluacion_accion"

    id: Mapped[uuid.UUID] = columna_id()
    id_evaluacion: Mapped[uuid.UUID] = fk_uuid("evaluacion.id", index=True)
    orden: Mapped[int] = mapped_column(sa.SmallInteger)
    codigo: Mapped[str] = mapped_column(sa.Text)
    descripcion: Mapped[str] = mapped_column(sa.Text)
    responsable_requerido: Mapped[str] = mapped_column(
        enum_texto("responsable_requerido", RESPONSABLE_REQUERIDO)
    )
    id_incidencia: Mapped[uuid.UUID | None] = fk_uuid("incidencia.id", nullable=True)

    __table_args__ = (sa.UniqueConstraint("id_evaluacion", "orden"),)


class DatoPendiente(Base):
    __tablename__ = "evaluacion_dato_pendiente"

    id: Mapped[uuid.UUID] = columna_id()
    id_evaluacion: Mapped[uuid.UUID] = fk_uuid("evaluacion.id", index=True)
    orden: Mapped[int] = mapped_column(sa.SmallInteger)
    campo: Mapped[str] = mapped_column(sa.Text)
    motivo: Mapped[str] = mapped_column(sa.Text)
    paso: Mapped[int] = mapped_column(sa.SmallInteger)

    __table_args__ = (
        sa.UniqueConstraint("id_evaluacion", "orden"),
        sa.CheckConstraint("paso BETWEEN 1 AND 6", name="paso_valido"),
    )


class Estimacion(Base):
    """Sustitución declarada: qué se reemplazó y por qué. Nunca se presenta como medición."""

    __tablename__ = "evaluacion_estimacion"

    id: Mapped[uuid.UUID] = columna_id()
    id_evaluacion: Mapped[uuid.UUID] = fk_uuid("evaluacion.id", index=True)
    orden: Mapped[int] = mapped_column(sa.SmallInteger)
    tipo: Mapped[str] = mapped_column(enum_texto("tipo_estimacion", TIPO_ESTIMACION))
    descripcion: Mapped[str] = mapped_column(sa.Text)
    campos: Mapped[list[str]] = mapped_column(ARRAY(sa.Text))
    id_tabla: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    __table_args__ = (sa.UniqueConstraint("id_evaluacion", "orden"),)


class Pertenencia(Base):
    """Fuzzificación: grado de pertenencia de una lectura a un término lingüístico."""

    __tablename__ = "evaluacion_pertenencia"

    id: Mapped[uuid.UUID] = columna_id()
    id_evaluacion: Mapped[uuid.UUID] = fk_uuid("evaluacion.id", index=True)
    variable: Mapped[str] = mapped_column(sa.Text)
    termino: Mapped[str] = mapped_column(sa.Text)
    valor_nitido: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 4), nullable=True)
    unidad: Mapped[str] = mapped_column(sa.Text)
    grado: Mapped[Decimal] = mapped_column(sa.Numeric(5, 4))

    __table_args__ = (
        sa.UniqueConstraint("id_evaluacion", "variable", "termino"),
        sa.CheckConstraint("grado BETWEEN 0 AND 1", name="grado_en_rango"),
    )


class Activacion(Base):
    """Grado de activación de cada disparo de una producción (traza gradual)."""

    __tablename__ = "evaluacion_activacion"

    id: Mapped[uuid.UUID] = columna_id()
    id_evaluacion: Mapped[uuid.UUID] = fk_uuid("evaluacion.id", index=True)
    orden: Mapped[int] = mapped_column(sa.SmallInteger)
    produccion: Mapped[str] = mapped_column(sa.Text)
    regla: Mapped[str] = mapped_column(sa.Text, index=True)
    etapa: Mapped[str] = mapped_column(sa.Text)
    pasada: Mapped[int] = mapped_column(sa.SmallInteger)
    grado_inf: Mapped[Decimal] = mapped_column(sa.Numeric(5, 4))
    grado_sup: Mapped[Decimal] = mapped_column(sa.Numeric(5, 4))
    hallazgo: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    terminos_salida: Mapped[list[str]] = mapped_column(
        ARRAY(sa.Text), server_default=sa.text("'{}'::text[]")
    )
    soportes: Mapped[list[str]] = mapped_column(ARRAY(sa.Text), server_default=sa.text("'{}'::text[]"))

    __table_args__ = (
        sa.UniqueConstraint("id_evaluacion", "orden"),
        sa.CheckConstraint(
            "grado_inf >= 0 AND grado_inf <= grado_sup AND grado_sup <= 1", name="grados_ordenados"
        ),
    )


class SalidaDifusa(Base):
    """Altura de recorte de cada consecuente de la variable de salida."""

    __tablename__ = "evaluacion_salida_difusa"

    id: Mapped[uuid.UUID] = columna_id()
    id_evaluacion: Mapped[uuid.UUID] = fk_uuid("evaluacion.id", index=True)
    variable: Mapped[str] = mapped_column(sa.Text)
    termino: Mapped[str] = mapped_column(sa.Text)
    altura: Mapped[Decimal] = mapped_column(sa.Numeric(5, 4))

    __table_args__ = (
        sa.UniqueConstraint("id_evaluacion", "variable", "termino"),
        sa.CheckConstraint("altura BETWEEN 0 AND 1", name="altura_en_rango"),
    )


class ObservacionAplicada(Base):
    """Observaciones efectivamente usadas, incluidas las recuperadas del historial."""

    __tablename__ = "observacion_aplicada"

    id: Mapped[uuid.UUID] = columna_id()
    id_evaluacion: Mapped[uuid.UUID] = fk_uuid("evaluacion.id", index=True)
    id_observacion: Mapped[uuid.UUID] = fk_uuid("observacion.id")
    orden: Mapped[int] = mapped_column(sa.SmallInteger)
    creada_en: Mapped[datetime] = mapped_column(server_default=AHORA)

    __table_args__ = (
        sa.UniqueConstraint("id_evaluacion", "id_observacion"),
        sa.UniqueConstraint("id_evaluacion", "orden"),
    )
