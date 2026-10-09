"""Vincular ventas y reembolsos a su cierre para admitir varios por día."""
from datetime import datetime, timedelta
import pytz
from alembic import op
import sqlalchemy as sa

revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    for name in ('ventas', 'devoluciones_venta'):
        columns = {c['name'] for c in sa.inspect(bind).get_columns(name)}
        if 'cierre_caja_id' not in columns:
            with op.batch_alter_table(name) as batch:
                batch.add_column(sa.Column('cierre_caja_id', sa.String(36), nullable=True))
                batch.create_foreign_key('fk_' + name + '_cierre', 'cierres_caja', ['cierre_caja_id'], ['id'])
        indexes = {index['name'] for index in sa.inspect(bind).get_indexes(name)}
        index_name = 'ix_' + name + '_cierre_caja_id'
        if index_name not in indexes:
            op.create_index(index_name, name, ['cierre_caja_id'])

    metadata = sa.MetaData()
    closes = sa.Table('cierres_caja', metadata, autoload_with=bind)
    sales = sa.Table('ventas', metadata, autoload_with=bind)
    refunds = sa.Table('devoluciones_venta', metadata, autoload_with=bind)
    tz = pytz.timezone('America/Mexico_City')
    # Conservar las cifras históricas; solo asociar movimientos no asignados.
    rows = bind.execute(sa.select(closes).where(closes.c.estado == 'cerrado')
                        .order_by(closes.c.fecha, closes.c.closed_at, closes.c.created_at, closes.c.id)).mappings().all()
    for row in rows:
        start = tz.localize(datetime.combine(row['fecha'], datetime.min.time()))
        end = start + timedelta(days=1)
        cutoff = row['closed_at']
        if cutoff and cutoff.tzinfo is None:
            cutoff = tz.localize(cutoff)
        sale_conditions = [sales.c.cierre_caja_id.is_(None), sales.c.cajero_id == row['empleado_id'],
                           sales.c.sucursal_id == row['sucursal_id'], sales.c.created_at >= start, sales.c.created_at < end]
        refund_conditions = [refunds.c.cierre_caja_id.is_(None), refunds.c.caja_empleado_id == row['empleado_id'],
                             refunds.c.fecha_movimiento == row['fecha'],
                             refunds.c.venta_id.in_(sa.select(sales.c.id).where(sales.c.sucursal_id == row['sucursal_id']))]
        if cutoff:
            sale_conditions.append(sales.c.created_at <= cutoff)
            refund_conditions.append(refunds.c.created_at <= cutoff)
        bind.execute(sales.update().where(*sale_conditions).values(cierre_caja_id=row['id']))
        bind.execute(refunds.update().where(*refund_conditions).values(cierre_caja_id=row['id']))


def downgrade():
    for name in ('devoluciones_venta', 'ventas'):
        foreign_keys = sa.inspect(op.get_bind()).get_foreign_keys(name)
        with op.batch_alter_table(name, naming_convention={'fk': 'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s'}) as batch:
            for fk in foreign_keys:
                if fk['constrained_columns'] == ['cierre_caja_id']:
                    batch.drop_constraint(fk['name'] or f'fk_{name}_cierre_caja_id_cierres_caja', type_='foreignkey')
            batch.drop_index('ix_' + name + '_cierre_caja_id')
            batch.drop_column('cierre_caja_id')
