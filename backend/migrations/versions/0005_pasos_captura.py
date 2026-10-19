"""Amplía los pasos de captura para R31–R52; no reescribe historial."""
import sqlalchemy as sa
from alembic import op

revision = '0005_pasos_captura'
down_revision = '0004_version_superada'
branch_labels = None
depends_on = None


def _restriccion(maximo: int) -> None:
    op.execute(sa.text('ALTER TABLE poscosegran.evaluacion_dato_pendiente DROP CONSTRAINT IF EXISTS ck_evaluacion_dato_pendiente_paso_valido'))
    op.execute(sa.text(f'ALTER TABLE poscosegran.evaluacion_dato_pendiente ADD CONSTRAINT ck_evaluacion_dato_pendiente_paso_valido CHECK (paso BETWEEN 1 AND {maximo})'))


def upgrade() -> None:
    _restriccion(10)


def downgrade() -> None:
    if op.get_bind().scalar(sa.text('SELECT count(*) FROM poscosegran.evaluacion_dato_pendiente WHERE paso > 6')):
        raise RuntimeError('Hay historial con pasos ampliados; no se puede reducir la restricción sin perder compatibilidad.')
    _restriccion(6)
