"""Costos globales privados, instantáneas de venta y revisión de reglas."""
from alembic import op
import sqlalchemy as sa
from decimal import Decimal
revision = '019'
down_revision = '018'
branch_labels = None
depends_on = None

REGLAS = [
    ('mica-sencilla', 'Mica de cristal sencilla', 'Mica de cristal sencilla o básica; excluir 9D, premium, cerámica, privacidad e hidrogel.', '5.50'),
    ('mica-9d', 'Mica 9D', 'Mica de cristal 9D; excluir premium, privacidad, cerámica e hidrogel.', '11'),
    ('mica-premium', 'Mica premium', 'Mica expresamente premium; no inferir premium de un modelo. Excluir hidrogel, cerámica y privacidad.', '45'),
    ('mica-ceramica', 'Mica cerámica', 'Mica cerámica sin privacidad; excluir cristal e hidrogel.', '18'),
    ('mica-privacidad', 'Mica de cristal privacidad', 'Mica de cristal con privacidad; excluir hidrogel y cerámica.', '35'),
    ('hidrogel-hd', 'Hidrogel HD', 'Hidrogel identificado como HD; excluir matte y privacidad.', '15'),
    ('hidrogel-matte', 'Hidrogel Matte', 'Hidrogel mate o matte; excluir privacidad.', '35'),
    ('hidrogel-privacidad', 'Hidrogel Privacidad', 'Hidrogel con privacidad, no mica de cristal.', '45'),
    ('fundas', 'Fundas (promedio)', 'Fundas para celular. Promedio autorizado; excluir estuches de otros artículos y accesorios diferentes.', '65'),
    ('cargador-cc', 'Cargador C-C / C-iPhone 20W o 22W', 'Cargador con conexión C-C o C-iPhone, de 20W o 22W. Debe identificarse cargador, conexión y potencia; no cable vendido solo.', '35'),
    ('cargador-usb', 'Cargador USB-C / V8 / USB-iPhone', 'Cargador USB a tipo C, V8 (micro USB) o iPhone. Excluir C-C, C-iPhone, 65W, 67W y cables vendidos solos. Si conexión o tipo no es claro, dejar pendiente.', '27'),
    ('cargador-potencia', 'Cargador 1Hora 65W / Gtide 67W', 'Solo cargador marca 1Hora (1 Hora) de 65W o Gtide (G-Tide) de 67W. No otras marcas o potencias; no cable solo.', '75'),
]


def upgrade():
    bind = op.get_bind()
    for table, field in [('productos', 'costo_compra'), ('detalles_venta', 'costo_compra_unitario')]:
        if field not in {c['name'] for c in sa.inspect(bind).get_columns(table)}:
            op.add_column(table, sa.Column(field, sa.Numeric(10, 2), nullable=True))
    existing = set(sa.inspect(bind).get_table_names())
    if 'reglas_costos' not in existing:
        op.create_table('reglas_costos', sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('nombre', sa.String(120), nullable=False), sa.Column('criterio', sa.Text(), nullable=False),
            sa.Column('costo', sa.Numeric(10, 2), nullable=False), sa.Column('activa', sa.Boolean(), nullable=False),
            sa.Column('version', sa.Integer(), nullable=False))
    if 'revisiones_costos' not in existing:
        op.create_table('revisiones_costos', sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('creado_por_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False), sa.Column('filas', sa.JSON(), nullable=False),
            sa.Column('version', sa.Integer(), nullable=False), sa.Column('token_lote', sa.String(36)),
            sa.Column('bloqueado_hasta', sa.Float(), nullable=False))
    table = sa.table('reglas_costos', sa.column('id'), sa.column('nombre'), sa.column('criterio'),
                     sa.column('costo', sa.Numeric(10,2)), sa.column('activa', sa.Boolean()), sa.column('version'))
    ids = set(bind.execute(sa.select(table.c.id)).scalars())
    for key, name, criterion, cost in REGLAS:
        if key not in ids:
            bind.execute(table.insert().values(id=key, nombre=name, criterio=criterion, costo=Decimal(cost), activa=True, version=1))


def downgrade():
    op.drop_table('revisiones_costos'); op.drop_table('reglas_costos')
    op.drop_column('detalles_venta', 'costo_compra_unitario')
    op.drop_column('productos', 'costo_compra')
