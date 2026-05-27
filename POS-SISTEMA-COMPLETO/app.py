import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from dotenv import load_dotenv
from config import config
from models import db, User, Sucursal, Categoria

# Cargar variables de entorno
load_dotenv()

def create_app(config_name=None):
    """Factory function para crear la aplicación Flask"""
    
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Inicializar extensiones
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    jwt = JWTManager(app)
    migrate = Migrate(app, db)
    
    # Registrar blueprints
    from routes_auth import auth_bp
    from routes_admin import admin_bp
    from routes_productos import productos_bp
    from routes_inventario import inventario_bp
    from routes_ventas import ventas_bp
    from routes_reportes import reportes_bp
    from routes_importar import importar_bp
    from routes_devoluciones import devoluciones_bp
    from routes_compatibilidad import compatibilidad_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(productos_bp)
    app.register_blueprint(inventario_bp)
    app.register_blueprint(ventas_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(importar_bp)
    app.register_blueprint(devoluciones_bp)
    app.register_blueprint(compatibilidad_bp)
    
    # Ruta raíz
    @app.route('/', methods=['GET'])
    def index():
        return jsonify({
            'message': 'POS API - Sistema de Punto de Venta',
            'version': '1.0.0',
            'endpoints': {
                'auth': '/api/auth',
                'admin': '/api/admin',
                'productos': '/api/productos',
                'inventario': '/api/inventario',
                'ventas': '/api/ventas',
                'reportes': '/api/reportes'
            }
        }), 200
    
    # Rutas para archivos estáticos del frontend
    @app.route('/static/<path:filename>')
    def send_static(filename):
        return send_from_directory('static', filename)
    
    @app.route('/<path:filename>')
    def send_frontend(filename):
        # No servir como SPA si es ruta de API
        if filename.startswith('api'):
            return jsonify({'error': 'Recurso no encontrado'}), 404
        
        # Servir archivos del frontend
        if os.path.exists(os.path.join('static', filename)):
            return send_from_directory('static', filename)
        # Para SPA, devolver index.html
        return send_from_directory('static', 'index.html')
    
    # Manejo de errores
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Recurso no encontrado'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Error interno del servidor'}), 500
    
    # Crear contexto de aplicación y base de datos
    with app.app_context():
        db.create_all()
        
        # Crear datos iniciales
        create_initial_data()
    
    return app

def create_initial_data():
    """Crear datos iniciales si no existen"""
    
    # Crear usuario admin por defecto
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@pos.local',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        print("✓ Usuario admin creado: username=admin, password=admin123")
    
    # Crear sucursales por defecto
    sucursal1 = Sucursal.query.filter_by(nombre='Sucursal Centro').first()
    if not sucursal1:
        sucursal1 = Sucursal(
            nombre='Sucursal Centro',
            direccion='Calle Principal 123',
            ciudad='Centro'
        )
        db.session.add(sucursal1)
        print("✓ Sucursal Centro creada")
    
    sucursal2 = Sucursal.query.filter_by(nombre='Sucursal Norte').first()
    if not sucursal2:
        sucursal2 = Sucursal(
            nombre='Sucursal Norte',
            direccion='Avenida Norte 456',
            ciudad='Norte'
        )
        db.session.add(sucursal2)
        print("✓ Sucursal Norte creada")
    
    # Crear categorías por defecto
    categoria_mica = Categoria.query.filter_by(nombre='Mica').first()
    if not categoria_mica:
        categoria_mica = Categoria(
            nombre='Mica',
            descripcion='Protectores de pantalla para celulares'
        )
        db.session.add(categoria_mica)
        print("✓ Categoría Mica creada")
    
    db.session.commit()
    print("✓ Datos iniciales creados/verificados\n")

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=8000)
