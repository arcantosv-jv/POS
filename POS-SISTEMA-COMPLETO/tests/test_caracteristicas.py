import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from models import db, User, Sucursal, Venta, ConfiguracionSistema
from routes_caracteristicas import caracteristicas_bp
from config import CDMX_TZ


class CaracteristicasTest(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite:///:memory:', JWT_SECRET_KEY='test-secret-key-with-at-least-32-characters')
        db.init_app(app); JWTManager(app); app.register_blueprint(caracteristicas_bp)
        self.context = app.app_context(); self.context.push(); db.create_all()
        self.client = app.test_client()
        self.branches = [Sucursal(id=str(i), nombre=name, direccion='Prueba', is_active=i != 3) for i, name in enumerate(['Centro', 'Norte', 'Sur', 'Inactiva'])]
        db.session.add_all(self.branches)
        self.admin = User(id='admin', username='admin', email='admin@test.com', password_hash='test', role='admin')
        self.employee = User(id='empleado', username='empleado', email='empleado@test.com', password_hash='test', role='employee', sucursal_id='0')
        db.session.add_all([self.admin, self.employee]); db.session.commit()
        self.auth = {u.role: {'Authorization': 'Bearer ' + create_access_token(identity=u.id)} for u in [self.admin, self.employee]}
        self.now = CDMX_TZ.localize(datetime(2026, 10, 8, 12))

    def tearDown(self):
        db.session.remove(); db.drop_all(); self.context.pop()

    def mode(self, value, role='admin'):
        return self.client.put('/api/caracteristicas', json={'panel_ventas': value}, headers=self.auth[role])

    def panel(self):
        with patch('routes_caracteristicas.get_cdmx_now', return_value=self.now):
            return self.client.get('/api/caracteristicas/panel-ventas', headers=self.auth['employee'])

    def sale(self, branch, amount, when):
        db.session.add(Venta(numero_venta='V' + str(Venta.query.count()), sucursal_id=str(branch), cajero_id=self.employee.id, total=amount, forma_pago='efectivo', created_at=when))
        db.session.commit()

    def test_default_global_and_authorization(self):
        self.assertEqual(self.panel().json, {'modo': 'productos'})
        self.assertEqual(self.client.get('/api/caracteristicas').status_code, 401)
        self.assertEqual(self.client.get('/api/caracteristicas', headers=self.auth['employee']).status_code, 403)
        self.assertEqual(self.mode('competencia', 'employee').status_code, 403)
        for mode in ['competencia', 'oculto', 'productos']:
            self.assertEqual(self.mode(mode).status_code, 200)
            db.session.expire_all()
            self.assertEqual(self.panel().json['modo'], mode)
        self.assertEqual(self.mode('ambos').status_code, 400)
        self.assertEqual(self.panel().json, {'modo': 'productos'})
        self.assertEqual(ConfiguracionSistema.query.count(), 1)

    def test_monthly_net_amounts_not_units_and_no_disclosed_amounts(self):
        self.mode('competencia')
        start = CDMX_TZ.localize(datetime(2026, 10, 1))
        end = CDMX_TZ.localize(datetime(2026, 11, 1))
        self.sale(0, 800, start)  # Total neto; las devoluciones ya reducen Venta.total.
        self.sale(1, 200, self.now)
        self.sale(0, 9000, start - timedelta(seconds=1))
        self.sale(1, 9000, end)
        self.sale(3, 90000, self.now)
        result = self.panel()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json['periodo'], '2026-10')
        self.assertEqual([b['nombre'] for b in result.json['sucursales']], ['Centro', 'Norte', 'Sur'])
        self.assertEqual([b['barra'] for b in result.json['sucursales']], [100, 25, 0])
        self.assertEqual([b['lider'] for b in result.json['sucursales']], [True, False, False])
        for row in result.json['sucursales']:
            self.assertEqual(set(row), {'id', 'nombre', 'barra', 'lider'})
        self.assertEqual(result.headers['Cache-Control'], 'no-store')
        self.now = end
        self.assertEqual(self.panel().json['periodo'], '2026-11')
        self.assertEqual(self.panel().json['sucursales'][0]['nombre'], 'Norte')
        self.now = CDMX_TZ.localize(datetime(2026, 12, 31, 23, 59))
        self.assertEqual(self.panel().json['periodo'], '2026-12')

    def test_empty_month_and_ties(self):
        self.mode('competencia')
        empty = self.panel().json
        self.assertFalse(empty['hay_ventas'])
        self.assertTrue(all(b['barra'] == 0 and not b['lider'] for b in empty['sucursales']))
        self.sale(0, 300, self.now); self.sale(1, 300, self.now)
        tied = self.panel().json['sucursales']
        self.assertTrue(tied[0]['lider'] and tied[1]['lider'])
        self.assertEqual(tied[0]['barra'], tied[1]['barra'])
        self.mode('oculto')
        self.assertEqual(self.panel().json, {'modo': 'oculto'})
