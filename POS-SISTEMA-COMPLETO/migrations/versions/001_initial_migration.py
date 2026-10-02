# migrations/versions/001_initial_migration.py
"""Initial migration - Crear todas las tablas

Revision ID: 001
Revises: 
Create Date: 2024-05-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Crear tabla users
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('username', sa.String(80), unique=True, nullable=False, index=True),
        sa.Column('email', sa.String(120), unique=True, nullable=False, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='employee'),
        sa.Column('sucursal_id', sa.String(36), sa.ForeignKey('sucursales.id'), nullable=True),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    # Crear tabla sucursales
    op.create_table(
        'sucursales',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('nombre', sa.String(120), unique=True, nullable=False),
        sa.Column('direccion', sa.String(255), nullable=False),
        sa.Column('telefono', sa.String(20), nullable=True),
        sa.Column('ciudad', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # Crear tabla categorias
    op.create_table(
        'categorias',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('nombre', sa.String(100), unique=True, nullable=False),
        sa.Column('descripcion', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # Crear tabla subcategorias
    op.create_table(
        'subcategorias',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('nombre', sa.String(100), nullable=False),
        sa.Column('descripcion', sa.Text, nullable=True),
        sa.Column('categoria_id', sa.String(36), sa.ForeignKey('categorias.id'), nullable=False),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_unique_constraint('uq_subcategoria_nombre_categoria', 'subcategorias', ['nombre', 'categoria_id'])

    # Crear tabla productos
    op.create_table(
        'productos',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('codigo', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('nombre', sa.String(255), nullable=False),
        sa.Column('descripcion', sa.Text, nullable=True),
        sa.Column('precio', sa.Numeric(10, 2), nullable=False),
        sa.Column('impuesto', sa.Numeric(5, 2), server_default='0'),
        sa.Column('subcategoria_id', sa.String(36), sa.ForeignKey('subcategorias.id'), nullable=False),
        sa.Column('codigo_barras', sa.String(100), nullable=True, index=True),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    # Crear tabla stocks
    op.create_table(
        'stocks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('producto_id', sa.String(36), sa.ForeignKey('productos.id'), nullable=False),
        sa.Column('sucursal_id', sa.String(36), sa.ForeignKey('sucursales.id'), nullable=False),
        sa.Column('cantidad', sa.Integer, server_default='0'),
        sa.Column('cantidad_minima', sa.Integer, server_default='5'),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_unique_constraint('uq_stock_producto_sucursal', 'stocks', ['producto_id', 'sucursal_id'])

    # Crear tabla entradas_inventario
    op.create_table(
        'entradas_inventario',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('producto_id', sa.String(36), sa.ForeignKey('productos.id'), nullable=False),
        sa.Column('sucursal_id', sa.String(36), sa.ForeignKey('sucursales.id'), nullable=False),
        sa.Column('cantidad', sa.Integer, nullable=False),
        sa.Column('numero_entrada', sa.String(50), unique=True, nullable=False),
        sa.Column('observaciones', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # Crear tabla ventas
    op.create_table(
        'ventas',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('numero_venta', sa.String(50), unique=True, nullable=False),
        sa.Column('sucursal_id', sa.String(36), sa.ForeignKey('sucursales.id'), nullable=False),
        sa.Column('cajero_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('total', sa.Numeric(10, 2), nullable=False),
        sa.Column('total_impuestos', sa.Numeric(10, 2), server_default='0'),
        sa.Column('forma_pago', sa.String(50), nullable=False),
        sa.Column('observaciones', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, index=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    # Crear tabla detalles_venta
    op.create_table(
        'detalles_venta',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('venta_id', sa.String(36), sa.ForeignKey('ventas.id'), nullable=False),
        sa.Column('producto_id', sa.String(36), sa.ForeignKey('productos.id'), nullable=False),
        sa.Column('cantidad', sa.Integer, nullable=False),
        sa.Column('precio_unitario', sa.Numeric(10, 2), nullable=False),
        sa.Column('impuesto_unitario', sa.Numeric(5, 2), server_default='0'),
        sa.Column('subtotal', sa.Numeric(10, 2), nullable=False),
    )


def downgrade():
    op.drop_table('detalles_venta')
    op.drop_table('ventas')
    op.drop_table('entradas_inventario')
    op.drop_table('stocks')
    op.drop_table('productos')
    op.drop_table('subcategorias')
    op.drop_table('categorias')
    op.drop_table('users')
    op.drop_table('sucursales')
