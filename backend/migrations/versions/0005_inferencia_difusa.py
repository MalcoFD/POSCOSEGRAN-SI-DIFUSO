"""Sistema de inferencia difusa: persistencia de las evaluaciones graduales.

Revisión: 0005_inferencia_difusa
Revisión anterior: 0004_version_superada

* evaluacion: índice de severidad (centroide), banda, método de defuzzificación,
  origen de la decisión y borrosidad de la fuzzificación.
* evaluacion_motivo.grado_activacion: grado α de la regla (1 en filas nítidas).
* motivo_evidencia: término lingüístico y grado de pertenencia; el operador
  admite PERTENENCIA.
* Tablas nuevas, inmutables como el resto de la evaluación:
  evaluacion_pertenencia, evaluacion_activacion y evaluacion_salida_difusa.

Es idempotente a propósito: 0001 crea el esquema desde los modelos actuales, así
que en una base nueva todo esto ya existe y aquí solo se reafirman restricciones
y triggers; en una base anterior se añade. Las filas existentes conservan su
significado: una evaluación nítida no tiene índice ni fuzzificación.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from poscosegran.db.enums import OPERADOR, ORIGEN_DECISION
from poscosegran.db.modelos.evaluacion import Activacion, Pertenencia, SalidaDifusa

revision = "0005_inferencia_difusa"
down_revision = "0004_version_superada"
branch_labels = None
depends_on = None

ESQUEMA = "poscosegran"
TABLAS_NUEVAS = ("evaluacion_pertenencia", "evaluacion_activacion", "evaluacion_salida_difusa")
OPERADOR_ANTERIOR = tuple(o for o in OPERADOR if o != "PERTENENCIA")


def _lista(valores: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def _columnas(tabla: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(tabla, schema=ESQUEMA)}


def _tablas() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names(schema=ESQUEMA))


def _check(tabla: str, nombre: str, expresion: str) -> None:
    op.execute(sa.text(f"ALTER TABLE {ESQUEMA}.{tabla} DROP CONSTRAINT IF EXISTS {nombre}"))
    op.execute(sa.text(f"ALTER TABLE {ESQUEMA}.{tabla} ADD CONSTRAINT {nombre} CHECK ({expresion})"))


def upgrade() -> None:
    nuevas_evaluacion = [
        sa.Column("indice_severidad", sa.Numeric(6, 3), nullable=True,
                  comment="Centroide del conjunto difuso agregado (0–100)."),
        sa.Column("banda_severidad", sa.Text, nullable=True),
        sa.Column("metodo_defuzzificacion", sa.Text, nullable=True),
        sa.Column("origen_decision", sa.String(max(len(v) for v in ORIGEN_DECISION)), nullable=True),
        sa.Column("borrosidad", sa.Numeric(5, 4), nullable=True),
    ]
    presentes = _columnas("evaluacion")
    for columna in nuevas_evaluacion:
        if columna.name not in presentes:
            op.add_column("evaluacion", columna, schema=ESQUEMA)
    _check("evaluacion", "ck_evaluacion_origen_decision", f"origen_decision IN ({_lista(ORIGEN_DECISION)})")
    _check(
        "evaluacion", "ck_evaluacion_indice_severidad_en_rango",
        "indice_severidad IS NULL OR indice_severidad BETWEEN 0 AND 100",
    )
    _check("evaluacion", "ck_evaluacion_borrosidad_en_rango", "borrosidad IS NULL OR borrosidad BETWEEN 0 AND 1")

    if "grado_activacion" not in _columnas("evaluacion_motivo"):
        op.add_column(
            "evaluacion_motivo",
            sa.Column(
                "grado_activacion", sa.Numeric(5, 4), nullable=False, server_default=sa.text("1"),
                comment="Grado α de la regla (Modus Ponens Generalizado); 1 en evaluaciones nítidas.",
            ),
            schema=ESQUEMA,
        )
    _check("evaluacion_motivo", "ck_evaluacion_motivo_grado_activacion_en_rango", "grado_activacion BETWEEN 0 AND 1")

    presentes = _columnas("motivo_evidencia")
    if "termino" not in presentes:
        op.add_column(
            "motivo_evidencia",
            sa.Column("termino", sa.Text, nullable=True, comment="Término lingüístico (PERTENENCIA)."),
            schema=ESQUEMA,
        )
    if "grado" not in presentes:
        op.add_column("motivo_evidencia", sa.Column("grado", sa.Numeric(5, 4), nullable=True), schema=ESQUEMA)
    _check("motivo_evidencia", "ck_motivo_evidencia_grado_en_rango", "grado IS NULL OR grado BETWEEN 0 AND 1")
    op.execute(sa.text(
        f"ALTER TABLE {ESQUEMA}.motivo_evidencia ALTER COLUMN operador TYPE VARCHAR({max(len(o) for o in OPERADOR)})"
    ))
    _check("motivo_evidencia", "ck_motivo_evidencia_operador", f"operador IN ({_lista(OPERADOR)})")

    conexion = op.get_bind()
    for tabla in (Pertenencia.__table__, Activacion.__table__, SalidaDifusa.__table__):
        tabla.create(bind=conexion, checkfirst=True)

    for tabla in TABLAS_NUEVAS:
        op.execute(sa.text(
            f"""
            CREATE OR REPLACE TRIGGER tg_{tabla}_inmutable
            BEFORE UPDATE OR DELETE ON {ESQUEMA}.{tabla}
            FOR EACH ROW EXECUTE FUNCTION {ESQUEMA}.impedir_modificacion();
            """
        ))


def downgrade() -> None:
    presentes = _tablas()
    for tabla in TABLAS_NUEVAS:
        if tabla in presentes:
            op.execute(sa.text(f"DROP TRIGGER IF EXISTS tg_{tabla}_inmutable ON {ESQUEMA}.{tabla}"))
            op.drop_table(tabla, schema=ESQUEMA)
    op.execute(sa.text(f"DELETE FROM {ESQUEMA}.motivo_evidencia WHERE operador = 'PERTENENCIA'"))
    _check("motivo_evidencia", "ck_motivo_evidencia_operador", f"operador IN ({_lista(OPERADOR_ANTERIOR)})")
    op.execute(sa.text(f"ALTER TABLE {ESQUEMA}.motivo_evidencia DROP CONSTRAINT IF EXISTS ck_motivo_evidencia_grado_en_rango"))
    for columna in ("grado", "termino"):
        if columna in _columnas("motivo_evidencia"):
            op.drop_column("motivo_evidencia", columna, schema=ESQUEMA)
    op.execute(sa.text(
        f"ALTER TABLE {ESQUEMA}.evaluacion_motivo DROP CONSTRAINT IF EXISTS ck_evaluacion_motivo_grado_activacion_en_rango"
    ))
    if "grado_activacion" in _columnas("evaluacion_motivo"):
        op.drop_column("evaluacion_motivo", "grado_activacion", schema=ESQUEMA)
    for nombre in (
        "ck_evaluacion_origen_decision", "ck_evaluacion_indice_severidad_en_rango", "ck_evaluacion_borrosidad_en_rango",
    ):
        op.execute(sa.text(f"ALTER TABLE {ESQUEMA}.evaluacion DROP CONSTRAINT IF EXISTS {nombre}"))
    for columna in ("borrosidad", "origen_decision", "metodo_defuzzificacion", "banda_severidad", "indice_severidad"):
        if columna in _columnas("evaluacion"):
            op.drop_column("evaluacion", columna, schema=ESQUEMA)
