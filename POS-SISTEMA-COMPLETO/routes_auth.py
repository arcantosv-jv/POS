from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import db, User, Sucursal
from datetime import datetime, timedelta
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Validación de email
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@auth_bp.route('/register', methods=['POST'])
def register():
    """Registrar nuevo usuario (solo admin)"""
    try:
        data = request.get_json()
        
        # Validaciones
        if not data.get('username') or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Username, email y password son requeridos'}), 400
        
        if not is_valid_email(data['email']):
            return jsonify({'error': 'Email inválido'}), 400
        
        if len(data['password']) < 6:
            return jsonify({'error': 'La contraseña debe tener al menos 6 caracteres'}), 400
        
        # Verificar si usuario existe
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Usuario ya existe'}), 409
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email ya está registrado'}), 409
        
        # Verificar sucursal si es empleado
        sucursal_id = None
        if data.get('role') == 'employee':
            if not data.get('sucursal_id'):
                return jsonify({'error': 'Sucursal es requerida para empleados'}), 400
            
            sucursal = Sucursal.query.get(data['sucursal_id'])
            if not sucursal:
                return jsonify({'error': 'Sucursal no existe'}), 404
            
            sucursal_id = data['sucursal_id']
        
        # Crear usuario
        user = User(
            username=data['username'],
            email=data['email'],
            role=data.get('role', 'employee'),
            sucursal_id=sucursal_id
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'message': 'Usuario creado exitosamente',
            'user': user.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login de usuario"""
    try:
        data = request.get_json()
        
        if not data.get('username') or not data.get('password'):
            return jsonify({'error': 'Username y password son requeridos'}), 400
        
        user = User.query.filter_by(username=data['username']).first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Credenciales inválidas'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Usuario inactivo'}), 401
        
        # Crear token
        access_token = create_access_token(
            identity=user.id,
            expires_delta=timedelta(days=30)
        )
        
        return jsonify({
            'access_token': access_token,
            'user': user.to_dict()
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Obtener perfil del usuario autenticado"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        return jsonify(user.to_dict()), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Cambiar contraseña"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        if not user.check_password(data.get('current_password', '')):
            return jsonify({'error': 'Contraseña actual es incorrecta'}), 401
        
        if len(data.get('new_password', '')) < 6:
            return jsonify({'error': 'Nueva contraseña debe tener al menos 6 caracteres'}), 400
        
        user.set_password(data['new_password'])
        db.session.commit()
        
        return jsonify({'message': 'Contraseña cambiada exitosamente'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
