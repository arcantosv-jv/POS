# migrations/versions/006_add_sin_stock_to_detalles_venta.py
"""Add sin_stock column to detalles_venta table

Revision ID: 006
Revises: 005
Create Date: 2024-12-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    # Agregar columna sin_stock a detalles_venta
    op.add_column('detalles_venta',
        sa.Column('sin_stock', sa.Boolean(), server_default='false', nullable=False)
    )


def downgrade():
    # Eliminar columna sin_stock
    op.drop_column('detalles_venta', 'sin_stock')
