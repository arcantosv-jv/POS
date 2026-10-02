"""Add explicit cash-register closure timestamp

Revision ID: 007
Revises: 006
Create Date: 2026-10-02

"""
from alembic import op
import sqlalchemy as sa


revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column['name'] for column in sa.inspect(bind).get_columns('cierres_caja')}
    if 'closed_at' not in columns:
        op.add_column('cierres_caja', sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    bind = op.get_bind()
    columns = {column['name'] for column in sa.inspect(bind).get_columns('cierres_caja')}
    if 'closed_at' in columns:
        op.drop_column('cierres_caja', 'closed_at')
