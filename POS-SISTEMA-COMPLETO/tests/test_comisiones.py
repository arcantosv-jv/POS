import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from flask_jwt_extended import create_access_token
import test_operacion_seguimiento as fixtures
from models import db, ConfiguracionSistema, Comision, User, Sucursal, Venta, CierreCaja, DetalleVenta, DevolucionVenta
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
        self.product.subcategoria.categoria.nombre = 'Celulares'
        self.venta = Venta(numero_venta='COM-1', sucursal_id=self.branch.id, cajero_id=self.employee.id,
                           total=5001, total_impuestos=0, forma_pago='mixto',
                           created_at=CDMX_TZ.localize(datetime(2026, 11, 18, 14)))
        self.detalle = DetalleVenta(producto_id=self.product.id, cantidad=2, precio_unitario='2500.50',
                                    impuesto_unitario=0, subtotal=5001)
        self.venta.detalles.append(self.detalle); db.session.add(self.venta); db.session.commit()
        self.data = dict(detalle_venta_id=self.detalle.id, unidad=1, nombre_empleado=' Jazmin ')

    def create(self):
        res = self.request('/api/comisiones', self.data, role='employee')
        self.assertEqual(res.status_code, 201, res.json)
        return res.json

    def test_lifecycle_and_independence(self):
        now = datetime(2026, 11, 20, 5, 30, tzinfo=timezone.utc).astimezone(CDMX_TZ)
        with patch('routes_comisiones.get_cdmx_now', return_value=now):
            row = self.create()
        self.assertTrue(row['created_at'].startswith('2026-11-19T23:30:00'))
        self.assertEqual(row['nombre_empleado'], 'Jazmin')
        self.assertFalse(row['aprobada'])
        url = '/api/comisiones/' + row['id']
        edit = self.request(url, {'nombre_empleado': 'Corregida'}, role='employee', method='put')
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
        self.assertEqual((Venta.query.count(), CierreCaja.query.count(), Comision.query.count()), (1, 0, 0))

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

    def pendientes(self, fecha='2026-11-18', role='employee'):
        return self.request('/api/comisiones/pendientes?fecha=' + fecha, role=role, method='get')

    def test_dos_unidades_solo_dos_comisiones(self):
        self.assertEqual(len(self.pendientes().json['unidades']), 2)
        uno = self.create()
        self.assertEqual(uno['metodo_pago'], 'mixto')
        self.assertEqual(uno['costo'], 2500.5)
        self.assertEqual(uno['fecha_venta'][:10], '2026-11-18')
        disponibles = self.pendientes().json['unidades']
        self.assertEqual([u['unidad'] for u in disponibles], [2])
        self.assertEqual(self.request('/api/comisiones', self.data, role='employee').status_code, 400)
        dos = self.request('/api/comisiones', {**self.data, 'unidad': 2}, role='employee')
        self.assertEqual(dos.status_code, 201)
        self.assertEqual(self.pendientes().json['unidades'], [])
        self.assertEqual(self.request('/api/comisiones', {**self.data, 'unidad': 3}, role='employee').status_code, 400)
        self.request('/api/comisiones/' + uno['id'], method='delete', role='employee')
        self.assertEqual([u['unidad'] for u in self.pendientes().json['unidades']], [1])
        self.assertEqual(self.stock.cantidad, 5)
        self.assertEqual(self.venta.total, 5001)

    def test_fecha_corte_sucursal_categoria_y_devoluciones(self):
        self.assertEqual(self.pendientes('2026-11-17').status_code, 400)
        self.assertEqual(self.pendientes(role='externo').json['unidades'], [])
        self.assertEqual(self.request('/api/comisiones', self.data, role='externo').status_code, 400)
        self.venta.created_at = CDMX_TZ.localize(datetime(2026, 11, 17, 23, 59)); db.session.commit()
        self.assertEqual(self.pendientes().json['unidades'], [])
        self.assertEqual(self.request('/api/comisiones', self.data, role='employee').status_code, 400)
        self.venta.created_at = CDMX_TZ.localize(datetime(2026, 11, 18)); db.session.commit()
        self.assertEqual(len(self.pendientes().json['unidades']), 2)
        self.product.subcategoria.categoria.nombre = 'Fundas'; db.session.commit()
        self.assertEqual(self.pendientes().json['unidades'], [])
        self.product.subcategoria.categoria.nombre = 'Tablet'; db.session.commit()
        dev = DevolucionVenta(venta_id=self.venta.id, detalle_venta_id=self.detalle.id,
                              cantidad_devuelta=1, motivo='Prueba', usuario_id=self.admin.id)
        db.session.add(dev); db.session.commit()
        self.assertEqual(len(self.pendientes().json['unidades']), 1)
        self.create()
        self.assertEqual(self.pendientes().json['unidades'], [])

    def test_historicos_se_conservan_sin_vincular(self):
        viejo = Comision(sucursal_id=self.branch.id, creado_por_id=self.employee.id, dispositivo='Tablet',
                         costo=500, metodo_pago='efectivo', nombre_empleado='Anterior', aprobada=True,
                         monto_comision=50, created_at=CDMX_TZ.localize(datetime(2026, 11, 17)))
        db.session.add(viejo); db.session.commit()
        listado = self.request('/api/comisiones', role='employee', method='get').json['comisiones']
        self.assertTrue(listado[0]['historica'])
        self.assertEqual(listado[0]['monto_comision'], 50)
        self.assertEqual(len(self.pendientes().json['unidades']), 2)
        self.assertEqual(self.request('/api/comisiones', dict(dispositivo='Tablet', costo=1, metodo_pago='efectivo', nombre_empleado='X'), role='employee').status_code, 400)

    def test_apartado_anterior_entregado_el_18(self):
        from apartado_venta import registrar_venta_entrega
        from models import Apartado
        from datetime import date
        self.product.subcategoria.categoria.nombre = 'Tablet'
        apartado = Apartado(sucursal_id=self.branch.id, creado_por_id=self.employee.id,
                            cliente='Cliente', telefono='5512345678', empleado='Empleado', plazo=30,
                            fecha=date(2026, 10, 30), vence=date(2026, 11, 29), total=100, abonado=100,
                            productos=[dict(producto_id=self.product.id, nombre=self.product.nombre, precio=100, cantidad=1)],
                            movimientos=[dict(tipo='creacion', pagos=[dict(metodo='efectivo', monto=100)])])
        db.session.add(apartado); db.session.flush()
        with patch('apartado_venta.get_cdmx_now', return_value=CDMX_TZ.localize(datetime(2026, 11, 18, 15))):
            venta = registrar_venta_entrega(apartado, self.admin.id)
        db.session.commit()
        unidades = [u for u in self.pendientes().json['unidades'] if u['venta_id'] == venta.id]
        self.assertEqual(len(unidades), 1)
        self.assertEqual(unidades[0]['fecha_venta'][:10], '2026-11-18')
        self.assertEqual(unidades[0]['metodo_pago'], 'efectivo')

    def test_restriccion_unica_en_base_y_permisos_explicitos(self):
        from sqlalchemy.exc import IntegrityError
        self.employee.permisos = {'comisiones': ['ver', 'crear', 'editar']}
        self.employee.sucursales_permitidas = [self.branch.id]
        db.session.commit()
        self.assertEqual(len(self.pendientes().json['unidades']), 2)
        self.create()
        duplicada = Comision(detalle_venta_id=self.detalle.id, unidad=1, sucursal_id=self.branch.id,
                              creado_por_id=self.employee.id, dispositivo='Celular', costo=10,
                              metodo_pago='efectivo', nombre_empleado='Otra')
        db.session.add(duplicada)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        self.assertEqual(Comision.query.count(), 1)
        self.employee.permisos = {'comisiones': ['ver']}; db.session.commit()
        self.assertEqual(self.pendientes().status_code, 403)

    def test_fecha_cdmx_y_fin_exclusivo(self):
        from comisiones_ventas import fecha_cdmx
        self.assertEqual(fecha_cdmx(datetime(2026, 11, 19, 5, 59, tzinfo=timezone.utc)).date().isoformat(), '2026-11-18')
        self.assertEqual(fecha_cdmx(datetime(2026, 11, 18, 5, 59, tzinfo=timezone.utc)).date().isoformat(), '2026-11-17')
        self.venta.created_at = CDMX_TZ.localize(datetime(2026, 11, 19)); db.session.commit()
        self.assertEqual(self.pendientes().json['unidades'], [])
        self.assertEqual(len(self.pendientes('2026-11-19').json['unidades']), 2)

    def test_filters_pagination_and_full_summary(self):
        for i in range(31):
            db.session.add(Comision(sucursal_id=self.branch.id,creado_por_id=self.employee.id,
                dispositivo='Tablet',costo=100,metodo_pago='efectivo',nombre_empleado='Jazmin',
                monto_comision=10,aprobada=True,created_at=CDMX_TZ.localize(datetime(2026,11,20,23,59))))
        db.session.add(Comision(sucursal_id=self.branch.id,creado_por_id=self.employee.id,
                dispositivo='Celular',costo=100,metodo_pago='efectivo',nombre_empleado='Otro',
                monto_comision=999,aprobada=True,created_at=CDMX_TZ.localize(datetime(2026,11,21,0,0))))
        db.session.commit()
        url='/api/comisiones?desde=2026-11-20&hasta=2026-11-20&empleado=JAZ&dispositivo=Tablet&por_pagina=10'
        r=self.request(url,method='get');self.assertEqual(r.status_code,200,r.json)
        self.assertEqual(r.json['total'],31);self.assertEqual(len(r.json['comisiones']),10)
        self.assertEqual(r.json['resumen']['monto_aprobado'],310)
        r=self.request(url+'&pagina=4',method='get');self.assertEqual(len(r.json['comisiones']),1)
        self.assertEqual(r.json['resumen']['monto_aprobado'],310)
        self.assertEqual(self.request(url+'&estado=pendientes',method='get').json['total'],0)
        self.assertEqual(self.request('/api/comisiones?empleado=%25',method='get').json['total'],0)
        self.assertEqual(self.request(url,role='externo',method='get').json['total'],0)
        self.assertEqual(self.request('/api/comisiones?sucursal_id='+self.branch.id,role='externo',method='get').status_code,403)
        self.assertEqual(self.request('/api/comisiones?desde=2026-11-21&hasta=2026-11-20',method='get').status_code,400)
        self.assertEqual(self.request('/api/comisiones?por_pagina=0',method='get').status_code,400)
