# migrations/versions/003_add_cierres_caja.py
"""Add cierres_caja table for daily cash register closures

Revision ID: 003
Revises: 002
Create Date: 2026-05-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Crear tabla cierres_caja
    op.create_table(
        'cierres_caja',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('empleado_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('sucursal_id', sa.String(36), sa.ForeignKey('sucursales.id'), nullable=False),
        sa.Column('fecha', sa.Date, nullable=False, index=True),
        sa.Column('total_ventas', sa.Numeric(10, 2), server_default='0'),
        sa.Column('total_efectivo', sa.Numeric(10, 2), server_default='0'),
        sa.Column('total_tarjeta', sa.Numeric(10, 2), server_default='0'),
        sa.Column('total_transferencia', sa.Numeric(10, 2), server_default='0'),
        sa.Column('efectivo_reportado', sa.Numeric(10, 2), nullable=True),
        sa.Column('diferencia', sa.Numeric(10, 2), nullable=True),
        sa.Column('estado', sa.String(20), server_default='abierto'),
        sa.Column('observaciones', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('cierres_caja')
