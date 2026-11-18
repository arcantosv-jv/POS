"""Resúmenes, históricos manuales y versiones inmutables de pronósticos."""
from alembic import op
import sqlalchemy as sa
revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if 'pronostico_estados' not in existing:
        op.create_table('pronostico_estados',
            sa.Column('sucursal_id', sa.String(36), sa.ForeignKey('sucursales.id'), primary_key=True),
            sa.Column('pendiente', sa.Boolean(), nullable=False), sa.Column('actualizado', sa.DateTime(timezone=True)))
    if 'pronostico_resumenes' not in existing:
        op.create_table('pronostico_resumenes',
            sa.Column('sucursal_id', sa.String(36), sa.ForeignKey('sucursales.id'), primary_key=True),
            sa.Column('fecha', sa.Date(), primary_key=True), sa.Column('categoria_id', sa.String(36), primary_key=True),
            sa.Column('importe', sa.Numeric(18, 2), nullable=False), sa.Column('unidades', sa.Integer(), nullable=False))
    if 'pronostico_historicos' not in existing:
        op.create_table('pronostico_historicos',
            sa.Column('sucursal_id', sa.String(36), sa.ForeignKey('sucursales.id'), primary_key=True),
            sa.Column('mes', sa.String(7), primary_key=True), sa.Column('categorias', sa.JSON(), nullable=False),
            sa.Column('cambios', sa.JSON(), nullable=False), sa.Column('actualizado', sa.DateTime(timezone=True), nullable=False))
    if 'pronosticos' not in existing:
        op.create_table('pronosticos', sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('creado_por_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False), sa.Column('sucursales', sa.JSON(), nullable=False),
            sa.Column('inicio', sa.Date(), nullable=False), sa.Column('fin', sa.Date(), nullable=False),
            sa.Column('resultado', sa.JSON(), nullable=False), sa.Column('explicacion', sa.Text()))


def downgrade():
    for table in ('pronosticos', 'pronostico_historicos', 'pronostico_resumenes', 'pronostico_estados'):
        op.drop_table(table)
