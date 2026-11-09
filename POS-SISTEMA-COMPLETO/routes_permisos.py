from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from models import db, User, Sucursal
from permissions import CATALOG, effective_permissions, allowed_branches, validate_access, authorize_request

permisos_bp = Blueprint('permisos', __name__, url_prefix='/api/permisos')
permisos_bp.before_request(authorize_request)


@permisos_bp.route('/mi-acceso')
def mi_acceso():
    user = db.session.get(User, get_jwt_identity())
    branches = Sucursal.query.filter_by(is_active=True)
    if user.role != 'admin':
        branches = branches.filter(Sucursal.id.in_(allowed_branches(user)))
    response = jsonify({'role': user.role, 'permisos': effective_permissions(user),
                       'sucursales': [b.to_dict() for b in branches.order_by(Sucursal.nombre)],
                       'sucursal_id': user.sucursal_id})
    response.headers['Cache-Control'] = 'no-store'
    return response


@permisos_bp.route('/usuarios/<user_id>', methods=['GET', 'PUT'])
def usuario_permisos(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    if request.method == 'PUT':
        if user.role == 'admin':
            return jsonify({'error': 'Los administradores conservan acceso universal'}), 400
        try:
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                raise ValueError('Configuración inválida')
            permisos, sucursales = validate_access(data, user.sucursal_id)
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
        user.permisos = permisos
        user.sucursales_permitidas = sucursales
        db.session.commit()
    return jsonify({'usuario': user.to_dict(), 'permisos': effective_permissions(user),
                    'sucursales_permitidas': allowed_branches(user),
                    'catalogo': [{'id': k, 'nombre': name, 'acciones': actions} for k, (name, actions) in CATALOG.items()]})
