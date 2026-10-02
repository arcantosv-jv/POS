"""Create devoluciones_venta table

Revision ID: 005
Revises: 001
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    # Create devoluciones_venta table
    op.create_table(
        'devoluciones_venta',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('venta_id', sa.String(36), sa.ForeignKey('ventas.id'), nullable=False, index=True),
        sa.Column('detalle_venta_id', sa.String(36), sa.ForeignKey('detalles_venta.id'), nullable=False),
        sa.Column('cantidad_devuelta', sa.Integer(), nullable=False),
        sa.Column('motivo', sa.Text(), nullable=True),
        sa.Column('usuario_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    # Drop table
    op.drop_table('devoluciones_venta')
