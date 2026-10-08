"""Configuración global del panel de ventas."""
from alembic import op
import sqlalchemy as sa

revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if not sa.inspect(bind).has_table('configuracion_sistema'):
        op.create_table('configuracion_sistema',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('panel_ventas', sa.String(20), nullable=False, server_default='productos'))
    table = sa.table('configuracion_sistema', sa.column('id', sa.Integer()), sa.column('panel_ventas', sa.String()))
    if bind.execute(sa.select(table.c.id).where(table.c.id == 1)).first() is None:
        bind.execute(table.insert().values(id=1, panel_ventas='productos'))


def downgrade():
    op.drop_table('configuracion_sistema')
