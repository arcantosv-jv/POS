import unittest
from decimal import Decimal
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from models import db, User, Sucursal, CierreCaja, Venta
from routes_ventas import ventas_bp
from config import get_cdmx_now


class CierreEgresoTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
                               JWT_SECRET_KEY='test-secret-key-with-at-least-32-characters')
        db.init_app(self.app)
        JWTManager(self.app)
        self.app.register_blueprint(ventas_bp)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        sucursal = Sucursal(nombre='Prueba', direccion='Prueba')
        db.session.add(sucursal)
        db.session.flush()
        empleado = User(username='empleado', email='e@test.com', password_hash='test',
                        role='employee', sucursal_id=sucursal.id)
        admin = User(username='admin', email='a@test.com', password_hash='test', role='admin')
        db.session.add_all([empleado, admin])
        db.session.flush()
        self.cierre = CierreCaja(empleado_id=empleado.id, sucursal_id=sucursal.id,
                                fecha=get_cdmx_now().date(), total_ventas=1500,
                                total_efectivo=1000, total_tarjeta=500)
        db.session.add_all([
            Venta(numero_venta='E1', sucursal_id=sucursal.id, cajero_id=empleado.id, total=1000, forma_pago='efectivo'),
            Venta(numero_venta='T1', sucursal_id=sucursal.id, cajero_id=empleado.id, total=500, forma_pago='tarjeta')
        ])
        db.session.add(self.cierre)
        db.session.commit()
        self.headers = {'Authorization': 'Bearer ' + create_access_token(identity=empleado.id)}
        self.admin_headers = {'Authorization': 'Bearer ' + create_access_token(identity=admin.id)}
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def post(self, data, corregir=False):
        return self.client.post('/api/ventas/cierre-caja' + ('/corregir' if corregir else ''),
                                json=data, headers=self.headers)

    def test_egreso_correccion_y_reportes(self):
        response = self.post(dict(efectivo_reportado=800, egreso=200, concepto_egreso=' Sueldo '))
        self.assertEqual(response.status_code, 200)
        cierre = response.json['cierre']
        self.assertEqual((cierre['total_ventas'], cierre['total_efectivo'], cierre['efectivo_esperado'], cierre['diferencia']), (1500, 1000, 800, 0))
        for endpoint in ('cierres-caja', 'cierres-caja-detalle'):
            report = self.client.get('/api/ventas/reportes/' + endpoint, headers=self.admin_headers, query_string={'fecha_inicio': self.cierre.fecha.isoformat(), 'fecha_fin': self.cierre.fecha.isoformat()})
            self.assertEqual(report.status_code, 200, report.json)
            self.assertEqual(report.json['cierres'][0]['concepto_egreso'], 'Sueldo')
            self.assertEqual(report.json['cierres'][0]['egreso'], 200)
        preserved = self.post(dict(efectivo_reportado=800), True)
        self.assertEqual(preserved.json['cierre']['egreso'], 200)
        corrected = self.post(dict(efectivo_reportado=700, egreso=300, concepto_egreso='Transporte'), True)
        self.assertEqual(corrected.json['cierre']['diferencia'], 0)
        removed = self.post(dict(efectivo_reportado=1000, egreso=0), True)
        self.assertEqual(removed.json['cierre']['efectivo_esperado'], 1000)
        self.assertIsNone(removed.json['cierre']['concepto_egreso'])

    def test_sin_egreso_y_efectivo_cero(self):
        response = self.post(dict(efectivo_reportado=0))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['cierre']['efectivo_reportado'], 0)
        self.assertEqual(response.json['cierre']['diferencia'], -1000)
        self.assertEqual(response.json['cierre']['egreso'], 0)

    def test_rechaza_egreso_invalido_sin_modificar_cierre(self):
        for corregir in (False, True):
            for egreso, concepto in [(10, ''), (10, '  '), (-1, 'Sueldo'), ('NaN', 'X'),
                                      ('Infinity', 'X'), ('abc', 'X'), (1.001, 'X'), (100000000, 'X')]:
                with self.subTest(egreso=egreso, corregir=corregir):
                    response = self.post(dict(efectivo_reportado=800, egreso=egreso, concepto_egreso=concepto), corregir)
                    self.assertEqual(response.status_code, 400)
                    db.session.refresh(self.cierre)
                    self.assertEqual(self.cierre.estado, 'abierto')
                    self.assertEqual(self.cierre.egreso, Decimal('0'))


if __name__ == '__main__':
    unittest.main()
