from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Sucursal
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

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

# Endpoint público de sucursales (accesible para todos los usuarios autenticados)
@admin_bp.route('/sucursales-publico', methods=['GET'])
@jwt_required()
def get_sucursales_publico():
    """Obtener todas las sucursales (acceso público para empleados y admins)"""
    try:
        sucursales = Sucursal.query.all()  # Devolver todas las sucursales, activas e inactivas
        return jsonify([s.to_dict() for s in sucursales]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== SUCURSALES ====================

@admin_bp.route('/sucursales', methods=['GET'])
@admin_required
def get_sucursales():
    """Obtener todas las sucursales"""
    try:
        sucursales = Sucursal.query.filter_by(is_active=True).all()
        return jsonify([s.to_dict() for s in sucursales]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/sucursales', methods=['POST'])
@admin_required
def create_sucursal():
    """Crear nueva sucursal"""
    try:
        data = request.get_json()
        
        if not data.get('nombre') or not data.get('direccion'):
            return jsonify({'error': 'Nombre y dirección son requeridos'}), 400
        
        # Verificar si ya existe
        if Sucursal.query.filter_by(nombre=data['nombre']).first():
            return jsonify({'error': 'La sucursal ya existe'}), 409
        
        sucursal = Sucursal(
            nombre=data['nombre'],
            direccion=data['direccion'],
            telefono=data.get('telefono'),
            ciudad=data.get('ciudad')
        )
        
        db.session.add(sucursal)
        db.session.commit()
        
        return jsonify({
            'message': 'Sucursal creada exitosamente',
            'sucursal': sucursal.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/sucursales/<sucursal_id>', methods=['GET'])
@admin_required
def get_sucursal(sucursal_id):
    """Obtener detalle de sucursal"""
    try:
        sucursal = Sucursal.query.get(sucursal_id)
        if not sucursal:
            return jsonify({'error': 'Sucursal no encontrada'}), 404
        
        return jsonify(sucursal.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/sucursales/<sucursal_id>', methods=['PUT'])
@admin_required
def update_sucursal(sucursal_id):
    """Actualizar sucursal"""
    try:
        sucursal = Sucursal.query.get(sucursal_id)
        if not sucursal:
            return jsonify({'error': 'Sucursal no encontrada'}), 404
        
        data = request.get_json()
        
        if 'nombre' in data:
            # Verificar si el nombre ya existe
            existing = Sucursal.query.filter_by(nombre=data['nombre']).first()
            if existing and existing.id != sucursal_id:
                return jsonify({'error': 'El nombre ya está en uso'}), 409
            sucursal.nombre = data['nombre']
        
        if 'direccion' in data:
            sucursal.direccion = data['direccion']
        if 'telefono' in data:
            sucursal.telefono = data['telefono']
        if 'ciudad' in data:
            sucursal.ciudad = data['ciudad']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Sucursal actualizada exitosamente',
            'sucursal': sucursal.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/sucursales/<sucursal_id>', methods=['DELETE'])
@admin_required
def delete_sucursal(sucursal_id):
    """Eliminar (desactivar) sucursal"""
    try:
        sucursal = Sucursal.query.get(sucursal_id)
        if not sucursal:
            return jsonify({'error': 'Sucursal no encontrada'}), 404
        
        # Verificar si tiene usuarios activos
        usuarios_activos = User.query.filter_by(sucursal_id=sucursal_id, is_active=True).count()
        if usuarios_activos > 0:
            return jsonify({'error': 'No se puede eliminar sucursal con usuarios activos'}), 409
        
        sucursal.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'Sucursal desactivada exitosamente'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== USUARIOS ====================

@admin_bp.route('/usuarios', methods=['GET'])
@admin_required
def get_usuarios():
    """Obtener todos los usuarios"""
    try:
        usuarios = User.query.filter_by(is_active=True).all()
        return jsonify([u.to_dict() for u in usuarios]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/usuarios/<usuario_id>', methods=['GET'])
@admin_required
def get_usuario(usuario_id):
    """Obtener detalle de usuario"""
    try:
        usuario = User.query.get(usuario_id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        return jsonify(usuario.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/usuarios/<usuario_id>', methods=['PUT'])
@admin_required
def update_usuario(usuario_id):
    """Actualizar usuario"""
    try:
        usuario = User.query.get(usuario_id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        data = request.get_json()
        
        if 'email' in data:
            # Verificar si el email ya existe
            existing = User.query.filter_by(email=data['email']).first()
            if existing and existing.id != usuario_id:
                return jsonify({'error': 'El email ya está en uso'}), 409
            usuario.email = data['email']
        
        if 'sucursal_id' in data and usuario.role == 'employee':
            usuario.sucursal_id = data['sucursal_id']
        
        if 'is_active' in data:
            usuario.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Usuario actualizado exitosamente',
            'usuario': usuario.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/usuarios/<usuario_id>', methods=['DELETE'])
@admin_required
def delete_usuario(usuario_id):
    """Eliminar (desactivar) usuario"""
    try:
        usuario = User.query.get(usuario_id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        usuario.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'Usuario desactivado exitosamente'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/usuarios/<usuario_id>/reset-password', methods=['POST'])
@admin_required
def reset_usuario_password(usuario_id):
    """Resetear contraseña de usuario (admin)"""
    try:
        usuario = User.query.get(usuario_id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        data = request.get_json()
        new_password = data.get('new_password')
        
        if not new_password or len(new_password) < 6:
            return jsonify({'error': 'Nueva contraseña debe tener al menos 6 caracteres'}), 400
        
        usuario.set_password(new_password)
        db.session.commit()
        
        return jsonify({'message': 'Contraseña resetada exitosamente'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
