"""Reembolsos por método, egresos detallados, reparaciones y compatibilidades."""
from alembic import op
import sqlalchemy as sa

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    additions = {
        'cierres_caja': [sa.Column('egresos', sa.JSON(), nullable=True),
                        sa.Column('reembolsos_efectivo', sa.Numeric(10, 2), nullable=False, server_default='0')],
        'devoluciones_venta': [sa.Column('fecha_movimiento', sa.Date(), nullable=True),
                              sa.Column('reembolsos', sa.JSON(), nullable=True),
                              sa.Column('caja_empleado_id', sa.String(36), nullable=True)],
        'reparaciones': [sa.Column('diagnostico', sa.Text(), nullable=True),
                        sa.Column('tecnico', sa.String(120), nullable=True),
                        sa.Column('fecha_prometida', sa.Date(), nullable=True),
                        sa.Column('anticipo', sa.Numeric(10, 2), nullable=False, server_default='0'),
                        sa.Column('historial', sa.JSON(), nullable=True)],
    }
    for table, columns in additions.items():
        existing = {c['name'] for c in sa.inspect(op.get_bind()).get_columns(table)}
        for column in columns:
            if column.name not in existing:
                op.add_column(table, column)
    # Los egresos antiguos se leen como un renglón sin inventar comprobantes.
    # Reembolsos históricos quedan NULL: no se presume por qué medio se pagaron.
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if 'consultas_compatibilidad' not in tables:
        op.create_table('consultas_compatibilidad',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('usuario_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('modelo', sa.String(200), nullable=False),
            sa.Column('resultado', sa.JSON(), nullable=False),
            sa.Column('origen', sa.String(20), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False))
        op.create_index('ix_consultas_compatibilidad_modelo', 'consultas_compatibilidad', ['modelo'])
        op.create_index('ix_consultas_compatibilidad_created_at', 'consultas_compatibilidad', ['created_at'])
    if 'compatibilidades_verificadas' not in tables:
        op.create_table('compatibilidades_verificadas',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('modelo', sa.String(200), nullable=False),
            sa.Column('mica', sa.String(200), nullable=False),
            sa.Column('marca', sa.String(100), nullable=False),
            sa.Column('notas', sa.Text(), nullable=False),
            sa.Column('usuario_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('activa', sa.Boolean(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.UniqueConstraint('modelo', 'mica', name='uq_compatibilidad_verificada'))
        op.create_index('ix_compatibilidades_verificadas_modelo', 'compatibilidades_verificadas', ['modelo'])


def downgrade():
    op.drop_table('compatibilidades_verificadas')
    op.drop_table('consultas_compatibilidad')
    for table, columns in {
        'reparaciones': ['historial', 'anticipo', 'fecha_prometida', 'tecnico', 'diagnostico'],
        'devoluciones_venta': ['caja_empleado_id', 'reembolsos', 'fecha_movimiento'],
        'cierres_caja': ['egresos', 'reembolsos_efectivo'],
    }.items():
        for column in columns:
            op.drop_column(table, column)
