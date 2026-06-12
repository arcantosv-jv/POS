from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import (db, User, MarcaDispositivo, ModeloDispositivo, 
                    TipoReparacion, CatalogoReparacion, Reparacion)
from functools import wraps
from config import get_cdmx_now
from datetime import datetime

reparaciones_bp = Blueprint('reparaciones', __name__, url_prefix='/api/reparaciones')

# Decorador para verificar que el usuario sea admin
def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or user.role != 'admin':
            return jsonify({'error': 'Acceso denegado. Se requieren permisos de administrador'}), 403
        
        return fn(*args, **kwargs)
    return wrapper

# ==================== MARCAS DE DISPOSITIVOS ====================

@reparaciones_bp.route('/marcas', methods=['GET'])
@jwt_required()
def get_marcas():
    """Obtener todas las marcas de dispositivos (paginado)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = MarcaDispositivo.query.filter_by(is_active=True)
        paginated = query.paginate(page=page, per_page=per_page)
        
        return jsonify({
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page,
            'marcas': [m.to_dict() for m in paginated.items]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reparaciones_bp.route('/marcas', methods=['POST'])
@admin_required
def create_marca():
    """Crear nueva marca de dispositivo"""
    try:
        data = request.get_json()
        
        if not data.get('nombre'):
            return jsonify({'error': 'El nombre de la marca es requerido'}), 400
        
        # Verificar que no exista ya
        existing = MarcaDispositivo.query.filter_by(nombre=data['nombre']).first()
        if existing:
            return jsonify({'error': 'La marca ya existe'}), 400
        
        marca = MarcaDispositivo(nombre=data['nombre'])
        db.session.add(marca)
        db.session.commit()
        
        return jsonify(marca.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@reparaciones_bp.route('/marcas/<marca_id>', methods=['PUT'])
@admin_required
def update_marca(marca_id):
    """Actualizar marca de dispositivo"""
    try:
        marca = MarcaDispositivo.query.get(marca_id)
        if not marca:
            return jsonify({'error': 'Marca no encontrada'}), 404
        
        data = request.get_json()
        
        if 'nombre' in data:
            existing = MarcaDispositivo.query.filter_by(nombre=data['nombre']).first()
            if existing and existing.id != marca_id:
                return jsonify({'error': 'El nombre ya existe'}), 400
            marca.nombre = data['nombre']
        
        if 'is_active' in data:
            marca.is_active = data['is_active']
        
        db.session.commit()
        return jsonify(marca.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@reparaciones_bp.route('/marcas/<marca_id>', methods=['DELETE'])
@admin_required
def delete_marca(marca_id):
    """Eliminar marca de dispositivo (soft delete)"""
    try:
        marca = MarcaDispositivo.query.get(marca_id)
        if not marca:
            return jsonify({'error': 'Marca no encontrada'}), 404
        
        marca.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'Marca eliminada'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== MODELOS DE DISPOSITIVOS ====================

@reparaciones_bp.route('/modelos', methods=['GET'])
@jwt_required()
def get_modelos():
    """Obtener todos los modelos de dispositivos (paginado)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        marca_id = request.args.get('marca_id')
        
        query = ModeloDispositivo.query.filter_by(is_active=True)
        
        if marca_id:
            query = query.filter_by(marca_id=marca_id)
        
        paginated = query.paginate(page=page, per_page=per_page)
        return jsonify({
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page,
            'modelos': [m.to_dict() for m in paginated.items]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reparaciones_bp.route('/modelos', methods=['POST'])
@admin_required
def create_modelo():
    """Crear nuevo modelo de dispositivo"""
    try:
        data = request.get_json()
        
        if not data.get('marca_id') or not data.get('nombre'):
            return jsonify({'error': 'marca_id y nombre son requeridos'}), 400
        
        # Verificar que la marca exista
        marca = MarcaDispositivo.query.get(data['marca_id'])
        if not marca:
            return jsonify({'error': 'Marca no encontrada'}), 404
        
        # Verificar que no exista ya para esta marca
        existing = ModeloDispositivo.query.filter_by(
            marca_id=data['marca_id'],
            nombre=data['nombre']
        ).first()
        if existing:
            return jsonify({'error': 'El modelo ya existe para esta marca'}), 400
        
        modelo = ModeloDispositivo(
            marca_id=data['marca_id'],
            nombre=data['nombre']
        )
        db.session.add(modelo)
        db.session.commit()
        
        return jsonify(modelo.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@reparaciones_bp.route('/modelos/<modelo_id>', methods=['PUT'])
@admin_required
def update_modelo(modelo_id):
    """Actualizar modelo de dispositivo"""
    try:
        modelo = ModeloDispositivo.query.get(modelo_id)
        if not modelo:
            return jsonify({'error': 'Modelo no encontrado'}), 404
        
        data = request.get_json()
        
        if 'nombre' in data:
            existing = ModeloDispositivo.query.filter_by(
                marca_id=modelo.marca_id,
                nombre=data['nombre']
            ).first()
            if existing and existing.id != modelo_id:
                return jsonify({'error': 'El nombre ya existe para esta marca'}), 400
            modelo.nombre = data['nombre']
        
        if 'is_active' in data:
            modelo.is_active = data['is_active']
        
        db.session.commit()
        return jsonify(modelo.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@reparaciones_bp.route('/modelos/<modelo_id>', methods=['DELETE'])
@admin_required
def delete_modelo(modelo_id):
    """Eliminar modelo de dispositivo (soft delete)"""
    try:
        modelo = ModeloDispositivo.query.get(modelo_id)
        if not modelo:
            return jsonify({'error': 'Modelo no encontrado'}), 404
        
        modelo.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'Modelo eliminado'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== TIPOS DE REPARACIÓN ====================

@reparaciones_bp.route('/tipos', methods=['GET'])
@jwt_required()
def get_tipos():
    """Obtener todos los tipos de reparación (paginado)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = TipoReparacion.query.filter_by(is_active=True)
        paginated = query.paginate(page=page, per_page=per_page)
        
        return jsonify({
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page,
            'tipos': [t.to_dict() for t in paginated.items]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reparaciones_bp.route('/tipos', methods=['POST'])
@admin_required
def create_tipo():
    """Crear nuevo tipo de reparación"""
    try:
        data = request.get_json()
        
        if not data.get('nombre'):
            return jsonify({'error': 'El nombre del tipo es requerido'}), 400
        
        # Verificar que no exista ya
        existing = TipoReparacion.query.filter_by(nombre=data['nombre']).first()
        if existing:
            return jsonify({'error': 'El tipo de reparación ya existe'}), 400
        
        tipo = TipoReparacion(
            nombre=data['nombre'],
            descripcion=data.get('descripcion')
        )
        db.session.add(tipo)
        db.session.commit()
        
        return jsonify(tipo.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@reparaciones_bp.route('/tipos/<tipo_id>', methods=['PUT'])
@admin_required
def update_tipo(tipo_id):
    """Actualizar tipo de reparación"""
    try:
        tipo = TipoReparacion.query.get(tipo_id)
        if not tipo:
            return jsonify({'error': 'Tipo de reparación no encontrado'}), 404
        
        data = request.get_json()
        
        if 'nombre' in data:
            existing = TipoReparacion.query.filter_by(nombre=data['nombre']).first()
            if existing and existing.id != tipo_id:
                return jsonify({'error': 'El nombre ya existe'}), 400
            tipo.nombre = data['nombre']
        
        if 'descripcion' in data:
            tipo.descripcion = data['descripcion']
        
        if 'is_active' in data:
            tipo.is_active = data['is_active']
        
        db.session.commit()
        return jsonify(tipo.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@reparaciones_bp.route('/tipos/<tipo_id>', methods=['DELETE'])
@admin_required
def delete_tipo(tipo_id):
    """Eliminar tipo de reparación (soft delete)"""
    try:
        tipo = TipoReparacion.query.get(tipo_id)
        if not tipo:
            return jsonify({'error': 'Tipo de reparación no encontrado'}), 404
        
        tipo.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'Tipo de reparación eliminado'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== CATÁLOGO DE REPARACIONES ====================

@reparaciones_bp.route('/catalogo', methods=['GET'])
@jwt_required()
def get_catalogo():
    """Obtener catálogo de reparaciones (paginado)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        marca_id = request.args.get('marca_id')
        modelo_id = request.args.get('modelo_id')
        search = request.args.get('search')
        
        query = CatalogoReparacion.query.filter_by(is_active=True)
        
        if marca_id:
            query = query.filter_by(marca_id=marca_id)
        
        if modelo_id:
            query = query.filter_by(modelo_id=modelo_id)
        
        # Búsqueda por nombre de modelo
        if search:
            search_term = f"%{search}%"
            query = query.join(ModeloDispositivo).filter(
                ModeloDispositivo.nombre.ilike(search_term)
            )
        
        paginated = query.paginate(page=page, per_page=per_page)
        return jsonify({
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page,
            'catalogo': [item.to_dict() for item in paginated.items]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reparaciones_bp.route('/catalogo', methods=['POST'])
@admin_required
def create_catalogo_item():
    """Crear nuevo item en el catálogo de reparaciones"""
    try:
        data = request.get_json()
        
        required_fields = ['marca_id', 'modelo_id', 'tipo_reparacion_id', 'costo']
        if not all(field in data for field in required_fields):
            return jsonify({'error': f'Campos requeridos: {", ".join(required_fields)}'}), 400
        
        # Verificar que existan los registros
        marca = MarcaDispositivo.query.get(data['marca_id'])
        if not marca:
            return jsonify({'error': 'Marca no encontrada'}), 404
        
        modelo = ModeloDispositivo.query.get(data['modelo_id'])
        if not modelo:
            return jsonify({'error': 'Modelo no encontrado'}), 404
        
        tipo = TipoReparacion.query.get(data['tipo_reparacion_id'])
        if not tipo:
            return jsonify({'error': 'Tipo de reparación no encontrado'}), 404
        
        # Verificar que no exista ya
        existing = CatalogoReparacion.query.filter_by(
            marca_id=data['marca_id'],
            modelo_id=data['modelo_id'],
            tipo_reparacion_id=data['tipo_reparacion_id']
        ).first()
        if existing:
            return jsonify({'error': 'Este item ya existe en el catálogo'}), 400
        
        item = CatalogoReparacion(
            marca_id=data['marca_id'],
            modelo_id=data['modelo_id'],
            tipo_reparacion_id=data['tipo_reparacion_id'],
            costo=data['costo']
        )
        db.session.add(item)
        db.session.commit()
        
        return jsonify(item.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@reparaciones_bp.route('/catalogo/<item_id>', methods=['PUT'])
@admin_required
def update_catalogo_item(item_id):
    """Actualizar item del catálogo"""
    try:
        item = CatalogoReparacion.query.get(item_id)
        if not item:
            return jsonify({'error': 'Item no encontrado'}), 404
        
        data = request.get_json()
        
        if 'costo' in data:
            item.costo = data['costo']
        
        if 'is_active' in data:
            item.is_active = data['is_active']
        
        db.session.commit()
        return jsonify(item.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@reparaciones_bp.route('/catalogo/<item_id>', methods=['DELETE'])
@admin_required
def delete_catalogo_item(item_id):
    """Eliminar item del catálogo (soft delete)"""
    try:
        item = CatalogoReparacion.query.get(item_id)
        if not item:
            return jsonify({'error': 'Item no encontrado'}), 404
        
        item.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'Item eliminado del catálogo'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== REPARACIONES ====================

@reparaciones_bp.route('', methods=['GET'])
@jwt_required()
def get_reparaciones():
    """Obtener lista de reparaciones (paginado con filtros)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        sucursal_id = request.args.get('sucursal_id')
        
        query = Reparacion.query
        
        # Si es empleado, solo ver sus propias reparaciones
        if user.role == 'employee':
            query = query.filter_by(empleado_id=user_id)
        # Si es admin, permitir filtrar por sucursal
        elif user.role == 'admin' and sucursal_id:
            query = query.filter_by(sucursal_id=sucursal_id)
        
        # Filtros por fecha
        if fecha_inicio:
            try:
                fecha_inicio_date = datetime.fromisoformat(fecha_inicio).date()
                query = query.filter(Reparacion.fecha >= fecha_inicio_date)
            except:
                pass
        
        if fecha_fin:
            try:
                fecha_fin_date = datetime.fromisoformat(fecha_fin).date()
                query = query.filter(Reparacion.fecha <= fecha_fin_date)
            except:
                pass
        
        paginated = query.order_by(Reparacion.created_at.desc()).paginate(page=page, per_page=per_page)
        return jsonify({
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page,
            'reparaciones': [r.to_dict() for r in paginated.items]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reparaciones_bp.route('', methods=['POST'])
@jwt_required()
def create_reparacion():
    """Crear nueva reparación"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        data = request.get_json()
        
        required_fields = ['nombre_cliente', 'telefono_cliente', 'marca_id', 'modelo_id', 
                          'tipo_reparacion_id', 'costo']
        if not all(field in data for field in required_fields):
            return jsonify({'error': f'Campos requeridos: {", ".join(required_fields)}'}), 400
        
        # Determinar sucursal_id
        sucursal_id = data.get('sucursal_id')
        if not sucursal_id:
            # Si es empleado, usar su sucursal_id; si es admin, es requerido
            if user.role == 'employee':
                sucursal_id = user.sucursal_id
                if not sucursal_id:
                    return jsonify({'error': 'El empleado no tiene una sucursal asignada'}), 400
            else:
                return jsonify({'error': 'Se requiere seleccionar una sucursal'}), 400
        
        # Verificar que existan los registros
        marca = MarcaDispositivo.query.get(data['marca_id'])
        if not marca:
            return jsonify({'error': 'Marca no encontrada'}), 404
        
        modelo = ModeloDispositivo.query.get(data['modelo_id'])
        if not modelo:
            return jsonify({'error': 'Modelo no encontrado'}), 404
        
        tipo = TipoReparacion.query.get(data['tipo_reparacion_id'])
        if not tipo:
            return jsonify({'error': 'Tipo de reparación no encontrado'}), 404
        
        reparacion = Reparacion(
            fecha=data.get('fecha') or get_cdmx_now().date(),
            nombre_cliente=data['nombre_cliente'],
            telefono_cliente=data['telefono_cliente'],
            marca_id=data['marca_id'],
            modelo_id=data['modelo_id'],
            tipo_reparacion_id=data['tipo_reparacion_id'],
            costo=data['costo'],
            sucursal_id=sucursal_id,
            empleado_id=user_id
        )
        db.session.add(reparacion)
        db.session.commit()
        
        return jsonify(reparacion.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@reparaciones_bp.route('/<reparacion_id>', methods=['GET'])
@jwt_required()
def get_reparacion(reparacion_id):
    """Obtener detalles de una reparación"""
    try:
        reparacion = Reparacion.query.get(reparacion_id)
        if not reparacion:
            return jsonify({'error': 'Reparación no encontrada'}), 404
        
        return jsonify(reparacion.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reparaciones_bp.route('/<reparacion_id>', methods=['PUT'])
@jwt_required()
def update_reparacion(reparacion_id):
    """Actualizar reparación"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        reparacion = Reparacion.query.get(reparacion_id)
        if not reparacion:
            return jsonify({'error': 'Reparación no encontrada'}), 404
        
        # Verificar permisos
        if user.role == 'employee' and reparacion.empleado_id != user_id:
            return jsonify({'error': 'No tienes permiso para editar esta reparación'}), 403
        
        data = request.get_json()
        
        # Campos editables
        if 'nombre_cliente' in data:
            reparacion.nombre_cliente = data['nombre_cliente']
        if 'telefono_cliente' in data:
            reparacion.telefono_cliente = data['telefono_cliente']
        if 'costo' in data:
            reparacion.costo = data['costo']
        if 'fecha' in data:
            reparacion.fecha = datetime.fromisoformat(data['fecha']).date() if isinstance(data['fecha'], str) else data['fecha']
        
        # Solo admin puede cambiar estado a entregada
        if 'estado' in data and (user.role == 'admin' or data['estado'] == 'registrada'):
            if data['estado'] == 'entregada':
                reparacion.estado = 'entregada'
                reparacion.fecha_entrega = get_cdmx_now()
            elif data['estado'] == 'registrada':
                reparacion.estado = 'registrada'
                reparacion.fecha_entrega = None
        
        db.session.commit()
        return jsonify(reparacion.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@reparaciones_bp.route('/<reparacion_id>/entregar', methods=['PUT'])
@jwt_required()
def marcar_como_entregada(reparacion_id):
    """Marcar reparación como entregada"""
    try:
        reparacion = Reparacion.query.get(reparacion_id)
        if not reparacion:
            return jsonify({'error': 'Reparación no encontrada'}), 404
        
        reparacion.estado = 'entregada'
        reparacion.fecha_entrega = get_cdmx_now()
        
        db.session.commit()
        return jsonify(reparacion.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@reparaciones_bp.route('/<reparacion_id>', methods=['DELETE'])
@admin_required
def delete_reparacion(reparacion_id):
    """Eliminar una reparación (solo admin)"""
    try:
        reparacion = Reparacion.query.get(reparacion_id)
        if not reparacion:
            return jsonify({'error': 'Reparación no encontrada'}), 404
        
        db.session.delete(reparacion)
        db.session.commit()
        
        return jsonify({'message': 'Reparación eliminada correctamente'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
