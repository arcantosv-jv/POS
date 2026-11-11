"""Revisiones de clasificación de productos desde administración."""
from alembic import op
import sqlalchemy as sa
revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade():
    if not sa.inspect(op.get_bind()).has_table('revisiones_clasificacion'):
        op.create_table('revisiones_clasificacion',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('creado_por_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('filas', sa.JSON(), nullable=False),
            sa.Column('version', sa.Integer(), nullable=False),
            sa.Column('token_lote', sa.String(36)),
            sa.Column('bloqueado_hasta', sa.Float(), nullable=False))


def downgrade():
    op.drop_table('revisiones_clasificacion')
