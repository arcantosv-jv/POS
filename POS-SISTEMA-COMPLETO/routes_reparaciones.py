from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import (db, User, MarcaDispositivo, ModeloDispositivo, 
                    TipoReparacion, CatalogoReparacion, Reparacion)
from functools import wraps
from config import get_cdmx_now, CDMX_TZ
from datetime import datetime
from business_validation import money, text_value

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
        
        if user.role == 'employee' and sucursal_id != user.sucursal_id:
            return jsonify({'error': 'Solo puedes registrar reparaciones en tu sucursal'}), 403

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

ESTADOS_REPARACION = ('registrada', 'diagnostico', 'esperando_refaccion', 'en_reparacion', 'lista', 'entregada', 'cancelada')


def editar_seguimiento(reparacion, data, user):
    if user.role not in ('admin', 'employee') or (user.role == 'employee' and reparacion.empleado_id != user.id):
        raise PermissionError('No tienes permiso para modificar esta reparación')
    costo = money(data.get('costo', reparacion.costo), 'Costo')
    anticipo = money(data.get('anticipo', reparacion.anticipo or 0) or 0, 'Abonado acumulado')
    if anticipo > costo:
        raise ValueError('El abonado acumulado no puede superar el costo de la reparación')
    estado = data.get('estado', reparacion.estado or 'registrada')
    if estado not in ESTADOS_REPARACION:
        raise ValueError('Estado de reparación inválido')
    if estado == 'entregada' and user.role != 'admin' and reparacion.estado != 'entregada':
        raise PermissionError('Solo un administrador puede confirmar la entrega')
    fields = {'costo': costo, 'anticipo': anticipo, 'estado': estado}
    for field, maximum in [('diagnostico', 4000), ('tecnico', 120), ('nombre_cliente', 100), ('telefono_cliente', 20)]:
        if field in data:
            fields[field] = text_value(data[field], field, maximum, field in ('nombre_cliente', 'telefono_cliente'))
    for field in ('fecha', 'fecha_prometida'):
        if field in data:
            value = data[field]
            if not value and field == 'fecha_prometida':
                fields[field] = None
            else:
                try:
                    fields[field] = datetime.strptime(value, '%Y-%m-%d').date()
                except (TypeError, ValueError):
                    raise ValueError(f'{field}: utiliza una fecha válida (AAAA-MM-DD)')
    changes = {}
    for field, value in fields.items():
        previous = getattr(reparacion, field)
        if previous != value:
            changes[field] = {'antes': str(previous) if previous is not None else None,
                              'despues': str(value) if value is not None else None}
    if reparacion.estado != estado:
        reparacion.fecha_entrega = get_cdmx_now() if estado == 'entregada' else None
    for field, value in fields.items():
        setattr(reparacion, field, value)
    if changes:
        reparacion.historial = (reparacion.historial or []) + [{
            'fecha': get_cdmx_now().isoformat(), 'usuario': user.username, 'usuario_id': user.id,
            'cambios': changes}]


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
        estado = request.args.get('estado')
        if estado:
            if estado not in ESTADOS_REPARACION:
                return jsonify({'error': 'Estado inválido'}), 400
            query = query.filter_by(estado=estado)
        if request.args.get('atrasadas') == 'true':
            query = query.filter(Reparacion.fecha_prometida < get_cdmx_now().date(), Reparacion.estado.notin_(['entregada', 'cancelada']))
        
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
    except PermissionError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 403
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
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
        
        required_fields = ['nombre_cliente', 'telefono_cliente', 'marca_id',
                          'tipo_reparacion_id', 'costo']
        if not all(field in data for field in required_fields):
            return jsonify({'error': f'Campos requeridos: {", ".join(required_fields)}'}), 400

        modelo_nombre = (data.get('modelo_nombre') or data.get('modelo') or '').strip()
        if not data.get('modelo_id') and not modelo_nombre:
            return jsonify({'error': 'modelo_nombre es requerido'}), 400
        
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
        
        modelo = None
        if data.get('modelo_id'):
            modelo = ModeloDispositivo.query.get(data['modelo_id'])
            if not modelo:
                return jsonify({'error': 'Modelo no encontrado'}), 404
            if modelo.marca_id != data['marca_id']:
                return jsonify({'error': 'El modelo no pertenece a la marca seleccionada'}), 400
        else:
            modelo = ModeloDispositivo.query.filter(
                ModeloDispositivo.marca_id == data['marca_id'],
                db.func.lower(ModeloDispositivo.nombre) == modelo_nombre.lower()
            ).first()
            if modelo:
                if not modelo.is_active:
                    modelo.is_active = True
            else:
                modelo = ModeloDispositivo(
                    marca_id=data['marca_id'],
                    nombre=modelo_nombre
                )
                db.session.add(modelo)
                db.session.flush()
        
        tipo = TipoReparacion.query.get(data['tipo_reparacion_id'])
        if not tipo:
            return jsonify({'error': 'Tipo de reparación no encontrado'}), 404
        
        reparacion = Reparacion(
            fecha=get_cdmx_now().date(),
            nombre_cliente=data['nombre_cliente'],
            telefono_cliente=data['telefono_cliente'],
            marca_id=data['marca_id'],
            modelo_id=modelo.id,
            tipo_reparacion_id=data['tipo_reparacion_id'],
            costo=data['costo'],
            sucursal_id=sucursal_id,
            empleado_id=user_id
        )
        editar_seguimiento(reparacion, data, user)
        db.session.add(reparacion)
        db.session.commit()
        
        return jsonify(reparacion.to_dict()), 201
    except PermissionError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 403
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
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
        
        user = db.session.get(User, get_jwt_identity())
        if user.role != 'admin' and reparacion.empleado_id != user.id:
            return jsonify({'error': 'Acceso denegado'}), 403
        return jsonify(reparacion.to_dict()), 200
    except PermissionError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 403
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
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
        
        editar_seguimiento(reparacion, data, user)

        db.session.commit()
        return jsonify(reparacion.to_dict()), 200
    except PermissionError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 403
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
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
        
        user = db.session.get(User, get_jwt_identity())
        editar_seguimiento(reparacion, {'estado': 'entregada'}, user)

        db.session.commit()
        return jsonify(reparacion.to_dict()), 200
    except PermissionError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 403
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
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
    except PermissionError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 403
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
