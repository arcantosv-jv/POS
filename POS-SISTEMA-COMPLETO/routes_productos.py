from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Producto, Categoria, Subcategoria, Stock, Sucursal
from sqlalchemy import or_, and_

productos_bp = Blueprint('productos', __name__, url_prefix='/api/productos')

def admin_required(fn):
    """Decorador para verificar permisos de admin"""
    from functools import wraps
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role != 'admin':
            return jsonify({'error': 'Acceso denegado'}), 403
        return fn(*args, **kwargs)
    return wrapper

# ==================== CATEGORÍAS ====================

@productos_bp.route('/categorias', methods=['GET'])
@jwt_required()
def get_categorias():
    """Obtener todas las categorías"""
    try:
        categorias = Categoria.query.filter_by(is_active=True).all()
        return jsonify([c.to_dict() for c in categorias]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@productos_bp.route('/categorias', methods=['POST'])
@admin_required
def create_categoria():
    """Crear nueva categoría"""
    try:
        data = request.get_json()
        
        if not data.get('nombre'):
            return jsonify({'error': 'Nombre es requerido'}), 400
        
        if Categoria.query.filter_by(nombre=data['nombre']).first():
            return jsonify({'error': 'Categoría ya existe'}), 409
        
        categoria = Categoria(
            nombre=data['nombre'],
            descripcion=data.get('descripcion')
        )
        
        db.session.add(categoria)
        db.session.commit()
        
        return jsonify({
            'message': 'Categoría creada exitosamente',
            'categoria': categoria.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@productos_bp.route('/categorias/<categoria_id>', methods=['GET'])
@jwt_required()
def get_categoria(categoria_id):
    """Obtener categoría con sus subcategorías"""
    try:
        categoria = Categoria.query.get(categoria_id)
        if not categoria:
            return jsonify({'error': 'Categoría no encontrada'}), 404
        
        return jsonify({
            **categoria.to_dict(),
            'subcategorias': [s.to_dict() for s in categoria.subcategorias if s.is_active]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@productos_bp.route('/categorias/<categoria_id>', methods=['PUT'])
@admin_required
def update_categoria(categoria_id):
    """Actualizar categoría"""
    try:
        categoria = Categoria.query.get(categoria_id)
        if not categoria:
            return jsonify({'error': 'Categoría no encontrada'}), 404
        
        data = request.get_json()
        
        if 'nombre' in data:
            existing = Categoria.query.filter_by(nombre=data['nombre']).first()
            if existing and existing.id != categoria_id:
                return jsonify({'error': 'Nombre ya existe'}), 409
            categoria.nombre = data['nombre']
        
        if 'descripcion' in data:
            categoria.descripcion = data['descripcion']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Categoría actualizada',
            'categoria': categoria.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@productos_bp.route('/categorias/<categoria_id>', methods=['DELETE'])
@admin_required
def delete_categoria(categoria_id):
    """Eliminar (desactivar) categoría"""
    try:
        categoria = Categoria.query.get(categoria_id)
        if not categoria:
            return jsonify({'error': 'Categoría no encontrada'}), 404
        
        # Verificar si tiene subcategorías con productos
        for subcategoria in categoria.subcategorias:
            if subcategoria.productos:
                return jsonify({'error': 'No se puede eliminar categoría con productos asociados'}), 409
        
        categoria.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'Categoría desactivada exitosamente'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== SUBCATEGORÍAS ====================

@productos_bp.route('/subcategorias', methods=['GET'])
@jwt_required()
def get_subcategorias():
    """Obtener todas las subcategorías"""
    try:
        categoria_id = request.args.get('categoria_id')
        
        if categoria_id:
            subcategorias = Subcategoria.query.filter_by(
                categoria_id=categoria_id,
                is_active=True
            ).all()
        else:
            subcategorias = Subcategoria.query.filter_by(is_active=True).all()
        
        return jsonify([s.to_dict() for s in subcategorias]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@productos_bp.route('/subcategorias', methods=['POST'])
@admin_required
def create_subcategoria():
    """Crear nueva subcategoría"""
    try:
        data = request.get_json()
        
        if not data.get('nombre') or not data.get('categoria_id'):
            return jsonify({'error': 'Nombre y categoría son requeridos'}), 400
        
        # Verificar que la categoría existe
        categoria = Categoria.query.get(data['categoria_id'])
        if not categoria:
            return jsonify({'error': 'Categoría no existe'}), 404
        
        # Verificar duplicado
        existing = Subcategoria.query.filter_by(
            nombre=data['nombre'],
            categoria_id=data['categoria_id']
        ).first()
        if existing:
            return jsonify({'error': 'Subcategoría ya existe en esta categoría'}), 409
        
        subcategoria = Subcategoria(
            nombre=data['nombre'],
            descripcion=data.get('descripcion'),
            categoria_id=data['categoria_id']
        )
        
        db.session.add(subcategoria)
        db.session.commit()
        
        return jsonify({
            'message': 'Subcategoría creada exitosamente',
            'subcategoria': subcategoria.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@productos_bp.route('/subcategorias/<subcategoria_id>', methods=['PUT'])
@admin_required
def update_subcategoria(subcategoria_id):
    """Actualizar subcategoría"""
    try:
        subcategoria = Subcategoria.query.get(subcategoria_id)
        if not subcategoria:
            return jsonify({'error': 'Subcategoría no encontrada'}), 404
        
        data = request.get_json()
        
        if not data.get('nombre') or not data.get('categoria_id'):
            return jsonify({'error': 'Nombre y categoría son requeridos'}), 400
        
        # Verificar que la categoría existe
        categoria = Categoria.query.get(data['categoria_id'])
        if not categoria:
            return jsonify({'error': 'Categoría no existe'}), 404
        
        # Verificar duplicado (considerando la subcategoría actual)
        existing = Subcategoria.query.filter_by(
            nombre=data['nombre'],
            categoria_id=data['categoria_id']
        ).first()
        if existing and existing.id != subcategoria.id:
            return jsonify({'error': 'Subcategoría ya existe en esta categoría'}), 409
        
        subcategoria.nombre = data['nombre']
        subcategoria.descripcion = data.get('descripcion', subcategoria.descripcion)
        subcategoria.categoria_id = data['categoria_id']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Subcategoría actualizada exitosamente',
            'subcategoria': subcategoria.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@productos_bp.route('/subcategorias/<subcategoria_id>', methods=['DELETE'])
@admin_required
def delete_subcategoria(subcategoria_id):
    """Eliminar (desactivar) subcategoría"""
    try:
        subcategoria = Subcategoria.query.get(subcategoria_id)
        if not subcategoria:
            return jsonify({'error': 'Subcategoría no encontrada'}), 404
        
        # Verificar si tiene productos
        if subcategoria.productos:
            return jsonify({'error': 'No se puede eliminar subcategoría con productos asociados'}), 409
        
        subcategoria.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'Subcategoría desactivada exitosamente'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== PRODUCTOS ====================

@productos_bp.route('/buscar', methods=['GET'])
@jwt_required()
def search_productos():
    """Buscar productos por nombre, código o código de barras"""
    try:
        query = request.args.get('q', '').strip()
        sucursal_id = request.args.get('sucursal_id')
        
        if not query or len(query) < 1:
            return jsonify({'error': 'Búsqueda requerida'}), 400
        
        # Buscar cada palabra de forma independiente para permitir términos
        # intermedios, por ejemplo: "mica iphone 17" -> "mica 9d iphone 17".
        terms = list(dict.fromkeys(query.split()))
        term_filters = []
        for term in terms:
            escaped_term = term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            search_term = f"%{escaped_term}%"
            term_filters.append(or_(
                Producto.nombre.ilike(search_term, escape='\\'),
                Producto.codigo.ilike(search_term, escape='\\'),
                Producto.codigo_barras.ilike(search_term, escape='\\')
            ))

        productos = Producto.query.filter(
            Producto.is_active == True,
            and_(*term_filters)
        ).limit(20).all()
        
        result = []
        for producto in productos:
            data = producto.to_dict()
            
            # Si se especifica sucursal, incluir stock
            if sucursal_id:
                stock = Stock.query.filter_by(
                    producto_id=producto.id,
                    sucursal_id=sucursal_id
                ).first()
                data['stock_cantidad'] = stock.cantidad if stock else 0
            
            result.append(data)
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@productos_bp.route('', methods=['GET'])
@jwt_required()
def get_productos():
    """Obtener productos con filtros opcionales"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 5000, type=int)
        subcategoria_id = request.args.get('subcategoria_id')
        categoria_id = request.args.get('categoria_id')
        
        query = Producto.query.filter_by(is_active=True)
        
        if subcategoria_id:
            query = query.filter_by(subcategoria_id=subcategoria_id)
        elif categoria_id:
            query = query.join(Subcategoria).filter(
                Subcategoria.categoria_id == categoria_id
            )
        
        paginated = query.paginate(page=page, per_page=per_page)
        
        return jsonify({
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page,
            'productos': [p.to_dict() for p in paginated.items]
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@productos_bp.route('', methods=['POST'])
@admin_required
def create_producto():
    """Crear nuevo producto"""
    try:
        data = request.get_json()
        
        # Validaciones
        required_fields = ['codigo', 'nombre', 'subcategoria_id']
        if not all(data.get(f) for f in required_fields):
            return jsonify({'error': 'Campos requeridos: código, nombre, subcategoría'}), 400
        
        # Verificar código único
        if Producto.query.filter_by(codigo=data['codigo']).first():
            return jsonify({'error': 'Código de producto ya existe'}), 409
        
        # Verificar subcategoría
        subcategoria = Subcategoria.query.get(data['subcategoria_id'])
        if not subcategoria:
            return jsonify({'error': 'Subcategoría no existe'}), 404
        
        # Procesar precio - puede ser None o vacío
        precio = data.get('precio')
        if precio == '' or precio is None:
            precio = None
        else:
            precio = float(precio)
        
        producto = Producto(
            codigo=data['codigo'],
            nombre=data['nombre'],
            descripcion=data.get('descripcion'),
            precio=precio,
            impuesto=data.get('impuesto', 0),
            subcategoria_id=data['subcategoria_id'],
            codigo_barras=data.get('codigo_barras')
        )
        
        db.session.add(producto)
        db.session.flush()
        
        # Crear stock en todas las sucursales
        sucursales = Sucursal.query.filter_by(is_active=True).all()
        for sucursal in sucursales:
            stock = Stock(
                producto_id=producto.id,
                sucursal_id=sucursal.id,
                cantidad=0
            )
            db.session.add(stock)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Producto creado exitosamente',
            'producto': producto.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@productos_bp.route('/<producto_id>', methods=['GET'])
@jwt_required()
def get_producto(producto_id):
    """Obtener detalle de producto con stocks"""
    try:
        producto = Producto.query.get(producto_id)
        if not producto:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        return jsonify(producto.to_dict(include_stock=True)), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@productos_bp.route('/<producto_id>', methods=['PUT'])
@admin_required
def update_producto(producto_id):
    """Actualizar producto"""
    try:
        producto = Producto.query.get(producto_id)
        if not producto:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        data = request.get_json()
        
        if 'codigo' in data:
            existing = Producto.query.filter_by(codigo=data['codigo']).first()
            if existing and existing.id != producto_id:
                return jsonify({'error': 'Código ya existe'}), 409
            producto.codigo = data['codigo']
        
        if 'nombre' in data:
            producto.nombre = data['nombre']
        if 'descripcion' in data:
            producto.descripcion = data['descripcion']
        if 'precio' in data:
            # Permite precio vacío o None para productos con precio flexible
            precio = data['precio']
            if precio == '' or precio is None:
                producto.precio = None
            else:
                producto.precio = float(precio)
        if 'impuesto' in data:
            producto.impuesto = data['impuesto']
        if 'codigo_barras' in data:
            producto.codigo_barras = data['codigo_barras']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Producto actualizado',
            'producto': producto.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@productos_bp.route('/<producto_id>', methods=['DELETE'])
@admin_required
def delete_producto(producto_id):
    """Eliminar (desactivar) producto"""
    try:
        producto = Producto.query.get(producto_id)
        if not producto:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        producto.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'Producto desactivado'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
