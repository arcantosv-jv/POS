"""Make precio nullable in productos table

Revision ID: 004
Revises: 003_add_cierres_caja
Create Date: 2026-05-22 03:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # Cambiar el precio de productos para que sea nullable
    op.alter_column('productos', 'precio',
               existing_type=sa.Numeric(precision=10, scale=2),
               nullable=True,
               existing_nullable=False)


def downgrade():
    # Revertir el cambio
    op.alter_column('productos', 'precio',
               existing_type=sa.Numeric(precision=10, scale=2),
               nullable=False,
               existing_nullable=True)
