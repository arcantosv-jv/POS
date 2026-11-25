"""Catálogo de empleados y pagos semanales independientes de caja."""
from alembic import op
import sqlalchemy as sa
revision='021'
down_revision='020'
branch_labels=None
depends_on=None

def upgrade():
    bind=op.get_bind()
    if not sa.inspect(bind).has_table('empleados_comisiones'):
        op.create_table('empleados_comisiones',sa.Column('id',sa.String(36),primary_key=True),sa.Column('nombre',sa.String(150),nullable=False),sa.Column('sucursal_id',sa.String(36),sa.ForeignKey('sucursales.id'),nullable=False),sa.Column('dia_pago',sa.Integer(),nullable=False),sa.Column('activo',sa.Boolean(),nullable=False))
    if not sa.inspect(bind).has_table('pagos_comisiones'):
        op.create_table('pagos_comisiones',sa.Column('id',sa.String(36),primary_key=True),sa.Column('empleado_id',sa.String(36),sa.ForeignKey('empleados_comisiones.id'),nullable=False),sa.Column('sucursal_id',sa.String(36),sa.ForeignKey('sucursales.id'),nullable=False),sa.Column('empleado_nombre',sa.String(150),nullable=False),sa.Column('usuario_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),sa.Column('usuario_nombre',sa.String(150),nullable=False),sa.Column('desde',sa.Date(),nullable=False),sa.Column('hasta',sa.Date(),nullable=False),sa.Column('fecha_pago',sa.DateTime(timezone=True),nullable=False),sa.Column('monto',sa.Numeric(10,2),nullable=False),sa.Column('detalles',sa.JSON(),nullable=False))
    cols={c['name'] for c in sa.inspect(bind).get_columns('comisiones')}
    for name,table in [('empleado_comision_id','empleados_comisiones'),('pago_comision_id','pagos_comisiones')]:
        if name not in cols:
            with op.batch_alter_table('comisiones') as batch:
                batch.add_column(sa.Column(name,sa.String(36),nullable=True))
                batch.create_foreign_key('fk_comisiones_'+name,table,[name],['id'])
                batch.create_index('ix_comisiones_'+name,[name])

def downgrade():
    with op.batch_alter_table('comisiones') as batch:
        batch.drop_column('pago_comision_id');batch.drop_column('empleado_comision_id')
    op.drop_table('pagos_comisiones');op.drop_table('empleados_comisiones')
