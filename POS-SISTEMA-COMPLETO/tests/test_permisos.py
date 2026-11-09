import unittest
from decimal import Decimal
import test_operacion_seguimiento as fixtures
from models import db, User, Sucursal, Stock, EntradaInventario, CierreCaja, Venta, ConfiguracionSistema
from routes_admin import admin_bp
from routes_auth import auth_bp
from routes_inventario import inventario_bp
from routes_productos import productos_bp
from routes_reportes import reportes_bp
from routes_permisos import permisos_bp
from routes_comisiones import comisiones_bp
from routes_caracteristicas import caracteristicas_bp
from config import get_cdmx_now


class PermisosTest(unittest.TestCase):
    request = fixtures.OperacionTest.request
    tearDown = fixtures.OperacionTest.tearDown

    def setUp(self):
        fixtures.OperacionTest.setUp(self)
        for bp in (admin_bp, auth_bp, inventario_bp, productos_bp, reportes_bp, permisos_bp, comisiones_bp, caracteristicas_bp):
            self.client.application.register_blueprint(bp)
        self.north = Sucursal(nombre='Norte', direccion='Norte')
        self.south = Sucursal(nombre='Sur', direccion='Sur')
        db.session.add_all([self.north, self.south]); db.session.flush()
        self.employee.permisos = {'inventario': ['ver', 'entradas']}
        self.employee.sucursales_permitidas = [self.branch.id, self.north.id]
        self.north_stock = Stock(producto_id=self.product.id, sucursal_id=self.north.id, cantidad=9)
        self.south_stock = Stock(producto_id=self.product.id, sucursal_id=self.south.id, cantidad=50)
        db.session.add_all([self.north_stock, self.south_stock]); db.session.commit()

    def test_entries_only_with_multiple_branches(self):
        data = {'producto_id': self.product.id, 'sucursal_id': self.branch.id, 'cantidad': 2}
        response = self.request('/api/inventario/entrada', data, role='employee')
        self.assertEqual(response.status_code, 201, response.json)
        self.assertNotIn('nuevo_stock', response.json)
        self.assertEqual(db.session.get(Stock, self.stock.id).cantidad, 7)
        response = self.request('/api/inventario/entrada', {**data, 'sucursal_id': self.north.id}, role='employee')
        self.assertEqual(response.status_code, 403, response.json)
        self.assertEqual(db.session.get(Stock, self.north_stock.id).cantidad, 9)
        self.assertEqual(self.request('/api/inventario/entrada', {**data, 'sucursal_id': self.south.id}, role='employee').status_code, 403)
        self.assertEqual(self.request('/api/inventario/stock/' + self.stock.id, {'cantidad': 0}, role='employee', method='put').status_code, 403)
        self.assertEqual(self.request('/api/inventario/' + self.stock.id, role='employee', method='delete').status_code, 403)
        self.assertEqual(self.request('/api/productos', {'nombre': 'X'}, role='employee').status_code, 403)
        self.assertEqual(self.request('/api/ventas', {'detalles': []}, role='employee').status_code, 403)
        self.assertEqual(self.request('/api/productos/buscar?q=Mica', role='employee', method='get').status_code, 200)
        self.assertEqual(self.request('/api/inventario/stock/' + self.north.id, role='employee', method='get').status_code, 403)
        self.employee.permisos = {'inventario': ['ver', 'entradas', 'ver_stock']}
        db.session.commit()
        self.assertEqual(self.request('/api/inventario/stock/' + self.north.id, role='employee', method='get').status_code, 200)
        self.assertEqual(self.request('/api/inventario/stock/' + self.south.id, role='employee', method='get').status_code, 403)
        branches = self.request('/api/admin/sucursales-publico', role='employee', method='get')
        self.assertEqual({b['id'] for b in branches.json}, {self.branch.id, self.north.id})
        forged = {**self.headers['employee'], 'X-Sucursal-Id': self.south.id}
        self.assertEqual(self.client.get('/api/inventario/entradas', headers=forged).status_code, 403)
        self.assertEqual(EntradaInventario.query.count(), 1)

    def test_read_only_closures_scope_and_revoke(self):
        self.employee.permisos = {'cierres-caja': ['ver']}
        for branch in (self.branch, self.north, self.south):
            db.session.add(CierreCaja(empleado_id=self.other.id, sucursal_id=branch.id,
                fecha=get_cdmx_now().date(), total_ventas=100, estado='cerrado', closed_at=get_cdmx_now()))
        db.session.commit()
        today = get_cdmx_now().date().isoformat()
        endpoint = '/api/ventas/reportes/cierres-caja-detalle?fecha_inicio=' + today + '&fecha_fin=' + today
        report = self.request(endpoint, role='employee', method='get')
        self.assertEqual(report.status_code, 200, report.json)
        self.assertEqual({c['sucursal_id'] for c in report.json['cierres']}, {self.branch.id, self.north.id})
        for endpoint in ('/api/ventas/cierre-caja', '/api/ventas/cierre-caja/corregir', '/api/ventas/cierre-caja/nuevo'):
            self.assertEqual(self.request(endpoint, {}, role='employee').status_code, 403)
        self.employee.permisos = {}; db.session.commit()
        self.assertEqual(self.request('/api/ventas/reportes/cierres-caja', role='employee', method='get').status_code, 403)
        self.assertEqual(self.request('/api/permisos/mi-acceso', role='employee', method='get').json['permisos'], {})

    def test_admin_assignments_and_no_privilege_escalation(self):
        endpoint = '/api/permisos/usuarios/' + self.employee.id
        data = {'permisos': {'inventario': ['ver', 'entradas']}, 'sucursales_permitidas': [self.branch.id]}
        self.assertEqual(self.request(endpoint, data, role='employee', method='put').status_code, 403)
        # Legacy employees cannot use the new permission administration endpoint either.
        self.assertEqual(self.request(endpoint, role='other', method='get').status_code, 403)
        saved = self.request(endpoint, data, method='put')
        self.assertEqual(saved.status_code, 200, saved.json)
        self.assertEqual(saved.json['sucursales_permitidas'], [self.branch.id])
        for bad in ({**data, 'permisos': {'usuarios': ['crear']}}, {**data, 'sucursales_permitidas': []},
                    {**data, 'permisos': {'inventario': ['crear']}}, {**data, 'permisos': {'inventario': ['entradas']}}):
            self.assertEqual(self.request(endpoint, bad, method='put').status_code, 400)
        self.assertEqual(self.request('/api/permisos/usuarios/' + self.admin.id, data, method='put').status_code, 400)
        payload = {'username': 'nuevo', 'email': 'nuevo@test.com', 'password': '123456', 'role': 'employee', 'sucursal_id': self.branch.id}
        self.assertEqual(self.client.post('/api/auth/register', json=payload).status_code, 401)
        self.assertEqual(self.request('/api/auth/register', payload, role='employee').status_code, 403)
        created = self.request('/api/auth/register', payload)
        self.assertEqual(created.status_code, 201, created.json)
        self.assertEqual(created.json['user']['permisos'], {})

    def test_stock_object_scope_and_reports_aggregates(self):
        self.employee.permisos = {'inventario': ['ver', 'ver_stock', 'ajustar', 'exportar'], 'dashboard': ['ver']}
        db.session.commit()
        self.assertEqual(self.request('/api/inventario/stock/' + self.south_stock.id, {'cantidad': 1}, role='employee', method='put').status_code, 404)
        self.assertEqual(self.request('/api/inventario/stock/' + self.north_stock.id, {'cantidad': 10}, role='employee', method='put').status_code, 200)
        exported = self.request('/api/inventario/exportar', role='employee', method='get')
        self.assertEqual(exported.status_code, 200, exported.json)
        self.assertNotIn('Sur', exported.data.decode('utf-8-sig').splitlines()[0])
        for i, branch in enumerate((self.branch, self.north, self.south)):
            db.session.add(Venta(numero_venta='S' + str(i), sucursal_id=branch.id, cajero_id=self.other.id, total=100 * (i+1), forma_pago='efectivo'))
        db.session.commit()
        response = self.request('/api/reportes/dashboard-ventas', role='employee', method='get')
        self.assertEqual(response.status_code, 200, response.json)
        self.assertEqual(response.json['resumen']['total_ventas'], 300)
        self.assertNotIn(self.south.nombre, str(response.json))
        self.assertNotIn(self.south.id, str(response.json))

    def test_commissions_feature_still_required_and_legacy(self):
        self.employee.permisos = {'comisiones': ['ver', 'crear']}
        db.session.add(ConfiguracionSistema(id=1, comisiones_habilitadas=False)); db.session.commit()
        self.assertEqual(self.request('/api/comisiones', role='employee', method='get').status_code, 403)
        self.assertEqual(self.request('/api/comisiones', method='get').status_code, 200)
        legacy = self.request('/api/permisos/mi-acceso', role='other', method='get')
        self.assertIn('crear', legacy.json['permisos']['ventas'])
        self.assertEqual(self.request('/api/inventario/entrada', {}, role='other').status_code, 403)
