"""Inspecciones compartidas de almacén, sin reescribir evaluaciones."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0006_mamdani_inspecciones'
down_revision = '0005_pasos_captura'
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    # 0001 usa los modelos actuales en una instalación nueva. En una base anterior
    # estos objetos no existen todavía; ambas rutas deben llegar al mismo esquema.
    if not inspector.has_table('inspeccion_almacen', schema='poscosegran'):
        op.create_table('inspeccion_almacen',
            sa.Column('id', sa.Uuid, primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('id_almacen', sa.Uuid, sa.ForeignKey('poscosegran.almacen.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('id_responsable', sa.Uuid, sa.ForeignKey('poscosegran.usuario.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('revision_almacen', sa.Integer, nullable=False),
            sa.Column('fecha', sa.DateTime(timezone=True), nullable=False),
            sa.Column('vigente_hasta', sa.DateTime(timezone=True), nullable=False),
            sa.Column('evidencia', sa.Text, nullable=False),
            sa.Column('observaciones', JSONB, nullable=False),
            sa.Column('creada_en', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
            sa.CheckConstraint('vigente_hasta > fecha', name='vigencia_positiva'),
            sa.CheckConstraint('revision_almacen >= 1', name='revision_positiva'),
            sa.CheckConstraint('length(btrim(evidencia)) > 0', name='evidencia_no_vacia'), schema='poscosegran')
        op.create_index('ix_inspeccion_almacen_id_almacen', 'inspeccion_almacen', ['id_almacen'], schema='poscosegran')
    if 'id_inspeccion_almacen' not in {c['name'] for c in inspector.get_columns('observacion', schema='poscosegran')}:
        op.add_column('observacion', sa.Column('id_inspeccion_almacen', sa.Uuid, nullable=True), schema='poscosegran')
        op.create_foreign_key('fk_observacion_id_inspeccion_almacen_inspeccion_almacen', 'observacion', 'inspeccion_almacen',
                              ['id_inspeccion_almacen'], ['id'], source_schema='poscosegran', referent_schema='poscosegran', ondelete='RESTRICT')
    op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='tg_inspeccion_almacen_inmutable' AND tgrelid='poscosegran.inspeccion_almacen'::regclass) THEN CREATE TRIGGER tg_inspeccion_almacen_inmutable BEFORE UPDATE OR DELETE ON poscosegran.inspeccion_almacen FOR EACH ROW EXECUTE FUNCTION poscosegran.impedir_modificacion(); END IF; END $$")
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='poscosegran_app') THEN GRANT SELECT, INSERT ON poscosegran.inspeccion_almacen TO poscosegran_app; GRANT INSERT, UPDATE ON poscosegran.asignacion_almacen, poscosegran.asignacion_lote TO poscosegran_app; END IF; END $$")


def downgrade() -> None:
    # El historial no se destruye para forzar una reversión.
    if op.get_bind().scalar(sa.text("SELECT EXISTS(SELECT 1 FROM poscosegran.inspeccion_almacen)")):
        raise RuntimeError('La nueva versión tiene historial; no se puede eliminar con downgrade.')
    op.drop_constraint('fk_observacion_id_inspeccion_almacen_inspeccion_almacen', 'observacion', schema='poscosegran', type_='foreignkey')
    op.drop_column('observacion', 'id_inspeccion_almacen', schema='poscosegran')
    op.drop_table('inspeccion_almacen', schema='poscosegran')
