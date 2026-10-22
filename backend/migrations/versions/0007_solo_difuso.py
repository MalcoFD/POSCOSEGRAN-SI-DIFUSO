"""Decisión únicamente Mamdani: retira el selector R30 del esquema.

Revisión: 0007_solo_difuso
Revisión anterior: 0006_mamdani_inspecciones

* `evaluacion.rama_r30` deja de existir: toda decisión procede del centroide de la
  inferencia Mamdani final y la columna solo repetía `MAMDANI_FINAL`.
* `regla.es_rama` deja de existir: el catálogo describe R01–R52. Las filas de ramas
  de versiones ya registradas se conservan, porque el historial es inmutable; el
  catálogo activo ya no las contiene.

Es idempotente: 0001 crea el esquema desde los modelos actuales, así que en una
base nueva las columnas no existen y la revisión no hace nada.
"""

from __future__ import annotations

from alembic import op

revision = "0007_solo_difuso"
down_revision = "0006_mamdani_inspecciones"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE poscosegran.evaluacion DROP CONSTRAINT IF EXISTS ck_evaluacion_rama_r30")
    op.execute("ALTER TABLE poscosegran.evaluacion DROP COLUMN IF EXISTS rama_r30")
    op.execute("ALTER TABLE poscosegran.regla DROP CONSTRAINT IF EXISTS uq_regla_id_version_es_rama_orden")
    op.execute("ALTER TABLE poscosegran.regla DROP COLUMN IF EXISTS es_rama")


def downgrade() -> None:
    # El historial no se reconstruye: la columna retirada no tiene valor que recuperar.
    raise RuntimeError("0007_solo_difuso no admite downgrade: el selector R30 no se restituye.")
