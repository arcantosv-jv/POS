"""Add optional cash outflow to register closures."""
from alembic import op
import sqlalchemy as sa

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    columns = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('cierres_caja')}
    if 'egreso' not in columns:
        op.add_column('cierres_caja', sa.Column('egreso', sa.Numeric(10, 2), nullable=False, server_default='0'))
    if 'concepto_egreso' not in columns:
        op.add_column('cierres_caja', sa.Column('concepto_egreso', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('cierres_caja', 'concepto_egreso')
    op.drop_column('cierres_caja', 'egreso')
