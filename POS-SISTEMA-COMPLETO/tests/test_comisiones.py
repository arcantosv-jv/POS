import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from flask_jwt_extended import create_access_token
import test_operacion_seguimiento as fixtures
from models import db, ConfiguracionSistema, Comision, User, Sucursal, Venta, CierreCaja
from routes_comisiones import comisiones_bp
from routes_caracteristicas import caracteristicas_bp
from config import CDMX_TZ


class ComisionesTest(unittest.TestCase):
    tearDown = fixtures.OperacionTest.tearDown
    request = fixtures.OperacionTest.request

    def setUp(self):
        fixtures.OperacionTest.setUp(self)
        self.client.application.register_blueprint(comisiones_bp)
        self.client.application.register_blueprint(caracteristicas_bp)
        db.session.add(ConfiguracionSistema(id=1, comisiones_habilitadas=True))
        branch = Sucursal(nombre='Norte', direccion='Norte')
        db.session.add(branch); db.session.flush()
        outsider = User(username='externo', email='externo@test.com', password_hash='x', role='employee', sucursal_id=branch.id)
        db.session.add(outsider); db.session.commit()
        self.headers['externo'] = {'Authorization': 'Bearer ' + create_access_token(identity=outsider.id)}
        self.data = dict(dispositivo='Celular', costo='2500.50', metodo_pago='efectivo', nombre_empleado=' Jazmin ')

    def create(self):
        res = self.request('/api/comisiones', self.data, role='employee')
        self.assertEqual(res.status_code, 201, res.json)
        return res.json

    def test_lifecycle_and_independence(self):
        now = datetime(2026, 10, 10, 5, 30, tzinfo=timezone.utc).astimezone(CDMX_TZ)
        with patch('routes_comisiones.get_cdmx_now', return_value=now):
            row = self.create()
        self.assertTrue(row['created_at'].startswith('2026-10-09T23:30:00'))
        self.assertEqual(row['nombre_empleado'], 'Jazmin')
        self.assertFalse(row['aprobada'])
        url = '/api/comisiones/' + row['id']
        edit = self.request(url, {**self.data, 'dispositivo': 'Tablet', 'metodo_pago': 'transferencia'}, role='employee', method='put')
        self.assertEqual(edit.status_code, 200)
        self.assertEqual(edit.json['created_at'], row['created_at'])
        approved = self.request(url, dict(monto_comision='150.25', aprobada=True), method='put')
        self.assertEqual(approved.status_code, 200, approved.json)
        self.assertTrue(self.request('/api/comisiones', role='employee', method='get').json['comisiones'][0]['aprobada'])
        self.assertEqual(self.request(url, self.data, role='employee', method='put').status_code, 409)
        self.assertEqual(self.request(url, role='employee', method='delete').status_code, 409)
        self.assertEqual(self.request(url, dict(monto_comision=200, aprobada=True), method='put').json['monto_comision'], 200)
        self.assertFalse(self.request(url, dict(monto_comision=200, aprobada=False), method='put').json['aprobada'])
        self.assertEqual(self.request(url, role='employee', method='delete').status_code, 200)
        self.assertEqual((Venta.query.count(), CierreCaja.query.count(), Comision.query.count()), (0, 0, 0))

    def test_scope_toggle_and_protected_fields(self):
        row = self.create(); url = '/api/comisiones/' + row['id']
        self.assertEqual(len(self.request('/api/comisiones', role='other', method='get').json['comisiones']), 1)
        self.assertEqual(self.request(url, self.data, role='other', method='put').status_code, 403)
        self.assertEqual(self.request('/api/comisiones', role='externo', method='get').json['comisiones'], [])
        self.assertEqual(self.request(url, self.data, role='externo', method='put').status_code, 404)
        for key, value in [('aprobada', True), ('monto_comision', 900), ('sucursal_id', self.branch.id), ('created_at', '2000-01-01')]:
            self.assertEqual(self.request(url, {**self.data, key: value}, role='employee', method='put').status_code, 400)
            self.assertEqual(self.request('/api/comisiones', {**self.data, key: value}, role='employee').status_code, 400)
        self.assertEqual(self.request('/api/caracteristicas', dict(panel_ventas='productos', comisiones_habilitadas=False), role='employee', method='put').status_code, 403)
        off = self.request('/api/caracteristicas', dict(panel_ventas='productos', comisiones_habilitadas=False), method='put')
        self.assertEqual(off.status_code, 200)
        for method, endpoint, data in [('get', '/api/comisiones', None), ('post', '/api/comisiones', self.data), ('put', url, self.data), ('delete', url, None)]:
            self.assertEqual(self.request(endpoint, data, role='employee', method=method).status_code, 403)
        self.assertEqual(len(self.request('/api/comisiones', method='get').json['comisiones']), 1)
        self.assertEqual(self.request(url, dict(monto_comision=100, aprobada=True), method='put').status_code, 200)

    def test_validation(self):
        for change in ({'costo': -1}, {'costo': 'NaN'}, {'costo': '1.001'}, {'nombre_empleado': ' '}, {'metodo_pago': 'mixto'}, {'dispositivo': 'Otro'}):
            self.assertEqual(self.request('/api/comisiones', {**self.data, **change}, role='employee').status_code, 400)
        row = self.create()
        for data in ({'monto_comision': -1, 'aprobada': True}, {'monto_comision': 10, 'aprobada': 'false'}, {'aprobada': True}):
            self.assertEqual(self.request('/api/comisiones/' + row['id'], data, method='put').status_code, 400)
