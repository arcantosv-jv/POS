"""Vincular comisiones a unidades vendidas, conservando registros históricos."""
from alembic import op
import sqlalchemy as sa
revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    existentes = {c['name'] for c in inspector.get_columns('comisiones')}
    with op.batch_alter_table('comisiones') as batch:
        for column in [sa.Column('detalle_venta_id', sa.String(36)), sa.Column('unidad', sa.Integer()),
                       sa.Column('fecha_venta', sa.DateTime(timezone=True)),
                       sa.Column('producto_nombre', sa.String(255)), sa.Column('numero_venta', sa.String(50))]:
            if column.name not in existentes:
                batch.add_column(column)
        if not any(f['constrained_columns'] == ['detalle_venta_id'] for f in inspector.get_foreign_keys('comisiones')):
            batch.create_foreign_key('fk_comision_detalle_venta', 'detalles_venta', ['detalle_venta_id'], ['id'])
        if 'uq_comision_unidad_vendida' not in {u['name'] for u in inspector.get_unique_constraints('comisiones')}:
            batch.create_unique_constraint('uq_comision_unidad_vendida', ['detalle_venta_id', 'unidad'])


def downgrade():
    with op.batch_alter_table('comisiones') as batch:
        batch.drop_constraint('uq_comision_unidad_vendida', type_='unique')
        batch.drop_constraint('fk_comision_detalle_venta', type_='foreignkey')
        for name in ('numero_venta', 'producto_nombre', 'fecha_venta', 'unidad', 'detalle_venta_id'):
            batch.drop_column(name)
