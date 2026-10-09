"""Conservar efectivo acumulado entre cierres de la sucursal y fechas con zona."""
from alembic import op
import sqlalchemy as sa

revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {c['name'] for c in sa.inspect(bind).get_columns('cierres_caja')}
    if 'efectivo_inicial' not in columns:
        op.add_column('cierres_caja', sa.Column('efectivo_inicial', sa.Numeric(10, 2), nullable=True))
    # Los valores anteriores eran reportes individuales: dejarlos NULL conserva
    # sus importes y diferencias. Los nuevos cierres guardan su arrastre explícito.
    if bind.dialect.name == 'postgresql':
        column = next(c for c in sa.inspect(bind).get_columns('ventas') if c['name'] == 'created_at')
        if not column['type'].timezone:
            # PostgreSQL convirtió las fechas aware de Python a la zona de la sesión
            # al guardarlas como timestamp. Reconstruir ese instante, sin restar 6 h.
            op.alter_column('ventas', 'created_at', type_=sa.DateTime(timezone=True),
                            postgresql_using="created_at AT TIME ZONE current_setting('TimeZone')")


def downgrade():
    if op.get_bind().dialect.name == 'postgresql':
        op.alter_column('ventas', 'created_at', type_=sa.DateTime(timezone=False),
                        postgresql_using="created_at AT TIME ZONE current_setting('TimeZone')")
    op.drop_column('cierres_caja', 'efectivo_inicial')
