from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Producto, Stock, EntradaInventario, Sucursal
from datetime import datetime
import uuid
from config import get_cdmx_now

inventario_bp = Blueprint('inventario', __name__, url_prefix='/api/inventario')

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

@inventario_bp.route('/stock/<sucursal_id>', methods=['GET'])
@jwt_required()
def get_stock_sucursal(sucursal_id):
    """Obtener stock de todos los productos en una sucursal"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Verificar acceso: admin ve todo, empleado solo su sucursal
        if user.role == 'employee' and user.sucursal_id != sucursal_id:
            return jsonify({'error': 'Acceso denegado'}), 403
        
        # Verificar que la sucursal existe
        sucursal = Sucursal.query.get(sucursal_id)
        if not sucursal:
            return jsonify({'error': 'Sucursal no encontrada'}), 404
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Obtener stocks con información del producto
        stocks = Stock.query.join(Producto).filter(
            Stock.sucursal_id == sucursal_id,
            Producto.is_active == True
        ).paginate(page=page, per_page=per_page)
        
        result = []
        for stock in stocks.items:
            data = stock.to_dict()
            data['producto_nombre'] = stock.producto.nombre
            data['producto_codigo'] = stock.producto.codigo
            data['precio'] = float(stock.producto.precio) if stock.producto.precio is not None else None
            result.append(data)
        
        return jsonify({
            'sucursal': sucursal.to_dict(),
            'total': stocks.total,
            'pages': stocks.pages,
            'current_page': page,
            'stocks': result
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@inventario_bp.route('/entrada', methods=['POST'])
@admin_required
def registrar_entrada_inventario():
    """Registrar entrada de inventario (suma de stock)"""
    try:
        data = request.get_json()
        
        # Validaciones
        if not data.get('producto_id') or not data.get('sucursal_id') or not data.get('cantidad'):
            return jsonify({'error': 'Producto, sucursal y cantidad son requeridos'}), 400
        
        cantidad = int(data['cantidad'])
        if cantidad <= 0:
            return jsonify({'error': 'La cantidad debe ser mayor a 0'}), 400
        
        # Verificar producto
        producto = Producto.query.get(data['producto_id'])
        if not producto:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        # Verificar sucursal
        sucursal = Sucursal.query.get(data['sucursal_id'])
        if not sucursal:
            return jsonify({'error': 'Sucursal no encontrada'}), 404
        
        # Obtener o crear stock
        stock = Stock.query.filter_by(
            producto_id=data['producto_id'],
            sucursal_id=data['sucursal_id']
        ).first()
        
        if not stock:
            stock = Stock(
                producto_id=data['producto_id'],
                sucursal_id=data['sucursal_id'],
                cantidad=0
            )
            # Aplicar cantidad_minima si se proporciona, si no, usa default de 5
            if data.get('cantidad_minima'):
                stock.cantidad_minima = int(data['cantidad_minima'])
            db.session.add(stock)
        
        # Actualizar cantidad
        stock.cantidad += cantidad
        
        # Registrar entrada
        numero_entrada = f"ENT-{get_cdmx_now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8]}"
        
        entrada = EntradaInventario(
            producto_id=data['producto_id'],
            sucursal_id=data['sucursal_id'],
            cantidad=cantidad,
            numero_entrada=numero_entrada,
            observaciones=data.get('observaciones')
        )
        
        db.session.add(entrada)
        db.session.commit()
        
        return jsonify({
            'message': f'Entrada de inventario registrada. Stock actualizado: {stock.cantidad}',
            'entrada': entrada.to_dict(),
            'nuevo_stock': stock.cantidad
        }), 201
    
    except ValueError:
        return jsonify({'error': 'La cantidad debe ser un número válido'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@inventario_bp.route('/entradas', methods=['GET'])
@jwt_required()
def get_entradas_inventario():
    """Obtener historial de entradas de inventario"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        sucursal_id = request.args.get('sucursal_id')
        
        query = EntradaInventario.query
        
        # Filtrar por sucursal si es empleado
        if user.role == 'employee':
            query = query.filter_by(sucursal_id=user.sucursal_id)
        elif sucursal_id:
            query = query.filter_by(sucursal_id=sucursal_id)
        
        entradas = query.order_by(
            EntradaInventario.created_at.desc()
        ).paginate(page=page, per_page=per_page)
        
        return jsonify({
            'total': entradas.total,
            'pages': entradas.pages,
            'current_page': page,
            'entradas': [e.to_dict() for e in entradas.items]
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@inventario_bp.route('/stock/<stock_id>', methods=['PUT'])
@admin_required
def update_stock(stock_id):
    """Actualizar cantidad de stock directamente (ajuste manual)"""
    try:
        stock = Stock.query.get(stock_id)
        if not stock:
            return jsonify({'error': 'Stock no encontrado'}), 404
        
        data = request.get_json()
        
        if 'cantidad' in data:
            nueva_cantidad = int(data['cantidad'])
            if nueva_cantidad < 0:
                return jsonify({'error': 'La cantidad no puede ser negativa'}), 400
            
            stock.cantidad = nueva_cantidad
        
        if 'cantidad_minima' in data:
            stock.cantidad_minima = int(data['cantidad_minima'])
        
        db.session.commit()
        
        return jsonify({
            'message': 'Stock actualizado',
            'stock': stock.to_dict()
        }), 200
    
    except ValueError:
        return jsonify({'error': 'Valores numéricos inválidos'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@inventario_bp.route('/bajo-stock/<sucursal_id>', methods=['GET'])
@jwt_required()
def get_bajo_stock(sucursal_id):
    """Obtener productos con stock bajo en una sucursal"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Verificar acceso
        if user.role == 'employee' and user.sucursal_id != sucursal_id:
            return jsonify({'error': 'Acceso denegado'}), 403
        
        # Obtener productos con stock menor a la cantidad mínima
        productos_bajo_stock = Stock.query.filter(
            Stock.sucursal_id == sucursal_id,
            Stock.cantidad <= Stock.cantidad_minima
        ).all()
        
        result = []
        for stock in productos_bajo_stock:
            data = stock.to_dict()
            data['producto_nombre'] = stock.producto.nombre
            data['producto_codigo'] = stock.producto.codigo
            result.append(data)
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
