"""Historial de correcciones de ventas anteriores al cierre."""
from alembic import op
import sqlalchemy as sa
revision='020'
down_revision='019'
branch_labels=None
depends_on=None

def upgrade():
    if 'ediciones' not in {c['name'] for c in sa.inspect(op.get_bind()).get_columns('ventas')}:
        op.add_column('ventas',sa.Column('ediciones',sa.JSON(),nullable=True))

def downgrade():
    op.drop_column('ventas','ediciones')
