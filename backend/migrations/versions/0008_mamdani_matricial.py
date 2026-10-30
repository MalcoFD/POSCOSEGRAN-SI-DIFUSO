"""Añade la recomendación de suspensión independiente de la fase.

Revision ID: 0008_mamdani_matricial
Revises: 0007_solo_difuso
"""
from alembic import op
import sqlalchemy as sa

revision = '0008_mamdani_matricial'
down_revision = '0007_solo_difuso'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conexion = op.get_bind()
    filas = conexion.execute(sa.text("SELECT conname FROM pg_constraint WHERE conrelid = 'poscosegran.evaluacion'::regclass AND contype = 'c' AND pg_get_constraintdef(oid) LIKE '%decision_final%' AND pg_get_constraintdef(oid) NOT LIKE '%fecha_vencimiento%'")).scalars().all()
    for nombre in filas:
        op.drop_constraint(op.f(nombre), 'evaluacion', schema='poscosegran', type_='check')
    valores = "'CUARENTENA','BLOQUEAR_INGRESO','RETIRAR_LOTE','CORREGIR_Y_REEVALUAR','SIN_CONCLUSION_AUTOMATICA','AUTORIZAR_CON_MONITOREO','AUTORIZAR_ALMACENAMIENTO','SUSPENDER_ALMACENAMIENTO'"
    op.create_check_constraint('decision', 'evaluacion', f'decision_final IN ({valores})', schema='poscosegran')


def downgrade() -> None:
    raise RuntimeError('No se elimina un valor de decisión si puede existir historial matricial.')
