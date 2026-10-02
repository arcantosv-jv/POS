# migrations/versions/002_add_pagos_venta.py
"""Add pagos_venta table for mixed payment support

Revision ID: 002
Revises: 001
Create Date: 2026-05-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Crear tabla pagos_venta
    op.create_table(
        'pagos_venta',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('venta_id', sa.String(36), sa.ForeignKey('ventas.id'), nullable=False),
        sa.Column('metodo_pago', sa.String(50), nullable=False),
        sa.Column('monto', sa.Numeric(10, 2), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('pagos_venta')
