"""Comisiones independientes y control de acceso global."""
from alembic import op
import sqlalchemy as sa
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if 'comisiones_habilitadas' not in {c['name'] for c in sa.inspect(bind).get_columns('configuracion_sistema')}:
        op.add_column('configuracion_sistema', sa.Column('comisiones_habilitadas', sa.Boolean(), nullable=False, server_default=sa.false()))
    if not sa.inspect(bind).has_table('comisiones'):
        op.create_table('comisiones',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('sucursal_id', sa.String(36), sa.ForeignKey('sucursales.id'), nullable=False),
            sa.Column('creado_por_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('dispositivo', sa.String(10), nullable=False),
            sa.Column('costo', sa.Numeric(10, 2), nullable=False),
            sa.Column('metodo_pago', sa.String(20), nullable=False),
            sa.Column('nombre_empleado', sa.String(150), nullable=False),
            sa.Column('monto_comision', sa.Numeric(10, 2)),
            sa.Column('aprobada', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
        op.create_index('ix_comisiones_sucursal_id', 'comisiones', ['sucursal_id'])


def downgrade():
    op.drop_table('comisiones')
    op.drop_column('configuracion_sistema', 'comisiones_habilitadas')
