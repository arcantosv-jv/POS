"""Acciones y sucursales autorizadas por usuario; NULL conserva accesos previos."""
from alembic import op
import sqlalchemy as sa
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    columns = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('users')}
    for name in ('permisos', 'sucursales_permitidas'):
        if name not in columns:
            op.add_column('users', sa.Column(name, sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('users', 'sucursales_permitidas')
    op.drop_column('users', 'permisos')
