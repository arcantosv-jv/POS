"""Apartados independientes y existencias reservadas."""
from alembic import op
import sqlalchemy as sa
revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    for tabla, columna in [('stocks', sa.Column('reservado', sa.Integer(), nullable=False, server_default='0')),
                           ('configuracion_sistema', sa.Column('apartados_habilitados', sa.Boolean(), nullable=False, server_default=sa.false()))]:
        if columna.name not in {c['name'] for c in sa.inspect(bind).get_columns(tabla)}:
            op.add_column(tabla, columna)
    if not sa.inspect(bind).has_table('apartados'):
        op.create_table('apartados',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('sucursal_id', sa.String(36), sa.ForeignKey('sucursales.id'), nullable=False),
            sa.Column('creado_por_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('cliente', sa.String(150), nullable=False),
            sa.Column('telefono', sa.String(40), nullable=False),
            sa.Column('empleado', sa.String(150), nullable=False),
            sa.Column('observaciones', sa.Text(), nullable=False),
            sa.Column('plazo', sa.Integer(), nullable=False),
            sa.Column('fecha', sa.Date(), nullable=False),
            sa.Column('vence', sa.Date(), nullable=False),
            sa.Column('estado', sa.String(20), nullable=False),
            sa.Column('total', sa.Numeric(10,2), nullable=False),
            sa.Column('abonado', sa.Numeric(10,2), nullable=False),
            sa.Column('productos', sa.JSON(), nullable=False),
            sa.Column('movimientos', sa.JSON(), nullable=False))
        op.create_index('ix_apartados_sucursal_id', 'apartados', ['sucursal_id'])


def downgrade():
    op.drop_table('apartados')
    op.drop_column('stocks', 'reservado')
    op.drop_column('configuracion_sistema', 'apartados_habilitados')
