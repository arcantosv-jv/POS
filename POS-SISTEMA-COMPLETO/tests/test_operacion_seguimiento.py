import unittest
from unittest.mock import patch
from datetime import timedelta
from decimal import Decimal
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from models import (db, User, Sucursal, Categoria, Subcategoria, Producto, Stock, Venta,
                    DetalleVenta, PagoVenta, CierreCaja, DevolucionVenta, MarcaDispositivo,
                    TipoReparacion, Reparacion, ConsultaCompatibilidad, CompatibilidadVerificada)
from routes_ventas import ventas_bp
from routes_devoluciones import devoluciones_bp
from routes_reparaciones import reparaciones_bp
from routes_compatibilidad import compatibilidad_bp
from config import get_cdmx_now


class OperacionTest(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite:///:memory:', JWT_SECRET_KEY='test-secret-key-with-at-least-32-characters')
        db.init_app(app)
        JWTManager(app)
        for bp in (ventas_bp, devoluciones_bp, reparaciones_bp, compatibilidad_bp):
            app.register_blueprint(bp)
        self.context = app.app_context()
        self.context.push()
        db.create_all()
        self.client = app.test_client()
        branch = Sucursal(nombre='Centro', direccion='Centro')
        category = Categoria(nombre='Accesorios')
        db.session.add_all([branch, category]); db.session.flush()
        sub = Subcategoria(nombre='Micas', categoria_id=category.id)
        db.session.add(sub); db.session.flush()
        self.product = Producto(codigo='P1', nombre='Mica', precio=100, subcategoria_id=sub.id)
        self.employee = User(username='cajero', email='c@test.com', password_hash='test', role='employee', sucursal_id=branch.id)
        self.other = User(username='otro', email='o@test.com', password_hash='test', role='employee', sucursal_id=branch.id)
        self.admin = User(username='admin', email='a@test.com', password_hash='test', role='admin')
        self.branch = branch
        self.marca = MarcaDispositivo(nombre='Marca')
        self.tipo = TipoReparacion(nombre='Pantalla')
        db.session.add_all([self.product, self.employee, self.other, self.admin, self.marca, self.tipo]); db.session.flush()
        self.stock = Stock(producto_id=self.product.id, sucursal_id=branch.id, cantidad=5)
        db.session.add(self.stock); db.session.commit()
        self.headers = {u.role if u != self.other else 'other': {'Authorization': 'Bearer ' + create_access_token(identity=u.id)} for u in (self.employee, self.other, self.admin)}

    def tearDown(self):
        db.session.remove(); db.drop_all(); self.context.pop()

    def request(self, path, data=None, role='admin', method='post'):
        return getattr(self.client, method)(path, json=data, headers=self.headers[role])

    def sale(self, method='mixto', yesterday=False, no_stock=False):
        sale = Venta(numero_venta='V' + str(Venta.query.count()), sucursal_id=self.branch.id, cajero_id=self.employee.id,
                     total=300, total_impuestos=0, forma_pago=method,
                     created_at=get_cdmx_now() - timedelta(days=int(yesterday)))
        sale.detalles.append(DetalleVenta(producto_id=self.product.id, cantidad=3, precio_unitario=100, subtotal=300, impuesto_unitario=0, sin_stock=no_stock))
        db.session.add(sale); db.session.flush()
        if method == 'mixto':
            db.session.add_all([PagoVenta(venta_id=sale.id, metodo_pago='efectivo', monto=200), PagoVenta(venta_id=sale.id, metodo_pago='tarjeta', monto=100)])
        db.session.commit()
        return sale

    def refund(self, sale, refunds, quantity=1):
        return self.request('/api/devoluciones', dict(venta_id=sale.id, detalle_venta_id=sale.detalles[0].id, cantidad_devuelta=quantity, reembolsos=refunds, motivo='Prueba'))

    def cash(self):
        res = self.request('/api/ventas/cierre-caja/hoy', role='employee', method='get')
        self.assertEqual(res.status_code, 200, res.json)
        return res.json

    def test_refund_mixed_cash_expenses_and_reverse(self):
        sale = self.sale()
        self.assertEqual(self.cash()['efectivo_esperado'], 200)
        response = self.refund(sale, {'efectivo': 60, 'tarjeta': 40})
        self.assertEqual(response.status_code, 201, response.json)
        cash = self.cash()
        self.assertEqual((cash['total_ventas'], cash['total_efectivo'], cash['total_tarjeta'], cash['reembolsos_efectivo'], cash['efectivo_esperado']), (200, 200, 60, 60, 140))
        self.assertEqual(sum(p.monto for p in sale.pagos), sale.total)
        res = self.request('/api/devoluciones/' + response.json['devolucion']['id'], method='delete')
        self.assertEqual(res.status_code, 200, res.json)
        self.assertEqual(self.cash()['efectivo_esperado'], 200)
        self.assertEqual(self.stock.cantidad, 5)
        self.assertEqual(sum(p.monto for p in sale.pagos), 300)

    def test_multiple_expenses_and_closed_snapshot(self):
        sale = self.sale()
        self.cash()
        self.refund(sale, {'efectivo': 100})
        res = self.request('/api/ventas/cierre-caja', {'efectivo_reportado': 65, 'egresos': [{'monto': 25, 'concepto': 'Sueldo', 'comprobante': 'Folio 1'}, {'monto': 10, 'concepto': 'Transporte'}]}, role='employee')
        self.assertEqual(res.status_code, 200, res.json)
        close = res.json['cierre']
        self.assertEqual((close['egreso'], close['total_ventas'], close['efectivo_esperado'], close['diferencia']), (35, 200, 65, 0))
        self.assertEqual(len(close['egresos']), 2)
        self.assertEqual(self.refund(sale, {'efectivo': 100}).status_code, 400)
        self.assertEqual(self.cash()['efectivo_esperado'], 65)
        bad = self.request('/api/ventas/cierre-caja/corregir', {'efectivo_reportado': 65, 'egresos': [{'monto': 5, 'concepto': ' '}]}, role='employee')
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(self.cash()['egreso'], 35)

    def test_refund_prior_sale_hits_today_only(self):
        sale = self.sale(yesterday=True)
        self.assertEqual(self.cash()['efectivo_esperado'], 0)
        res = self.refund(sale, {'efectivo': 100})
        self.assertEqual(res.status_code, 201, res.json)
        self.assertEqual(self.cash()['efectivo_esperado'], -100)
        self.assertEqual(self.cash()['total_ventas'], -100)

    def test_full_refund_and_no_stock_return(self):
        for method in ('mixto', 'efectivo'):
            sale = self.sale(method=method, no_stock=True)
            amounts = {'efectivo': 200, 'tarjeta': 100} if method == 'mixto' else {'efectivo': 300}
            res = self.refund(sale, amounts, 3)
            self.assertEqual(res.status_code, 201, res.json)
            self.assertEqual(sale.total, 0)
            self.assertEqual(self.stock.cantidad, 5)
            self.assertEqual(self.cash()['efectivo_esperado'], 0)
            reverse = self.request('/api/devoluciones/' + res.json['devolucion']['id'], method='delete')
            self.assertEqual(reverse.status_code, 200, reverse.json)
            self.assertEqual(sale.total, 300)
            # Remove sale to isolate each payment scenario.
            for p in list(sale.pagos): db.session.delete(p)
            db.session.delete(sale); db.session.commit()

    def test_invalid_refunds_are_atomic(self):
        sale = self.sale()
        for refunds in ({'tarjeta': 101}, {'efectivo': -100}, {'efectivo': 'NaN'}, {'efectivo': 90}, {'otro': 100}):
            with self.subTest(refunds=refunds):
                res = self.refund(sale, refunds)
                self.assertEqual(res.status_code, 400, res.json)
                self.assertEqual(DevolucionVenta.query.count(), 0)
                self.assertEqual(sale.total, 300)
                self.assertEqual(self.stock.cantidad, 5)
        self.assertEqual(self.refund(sale, {'tarjeta': 100}).status_code, 201)
        self.assertEqual(self.refund(sale, {'tarjeta': 100}).status_code, 400)

    def repair_data(self):
        return dict(nombre_cliente='Cliente', telefono_cliente='5551234567', marca_id=self.marca.id,
                    modelo_nombre='Modelo', tipo_reparacion_id=self.tipo.id, costo=500, anticipo=100,
                    tecnico='Técnico', diagnostico='Pantalla rota', estado='diagnostico',
                    fecha_prometida=(get_cdmx_now().date() - timedelta(days=1)).isoformat())

    def test_repair_lifecycle_balance_history_permissions(self):
        res = self.request('/api/reparaciones', self.repair_data(), role='employee')
        self.assertEqual(res.status_code, 201, res.json)
        repair = res.json
        self.assertEqual(repair['saldo'], 400)
        self.assertTrue(repair['atrasada'])
        path = '/api/reparaciones/' + repair['id']
        self.assertEqual(self.request(path, {'estado': 'lista', 'anticipo': 500}, role='other', method='put').status_code, 403)
        self.assertEqual(self.request(path, role='other', method='get').status_code, 403)
        self.assertEqual(self.request(path, {'anticipo': 501}, role='employee', method='put').status_code, 400)
        updated = self.request(path, {'estado': 'lista', 'anticipo': 500, 'diagnostico': 'Reemplazo probado'}, role='employee', method='put')
        self.assertEqual(updated.status_code, 200, updated.json)
        self.assertEqual(updated.json['saldo'], 0)
        self.assertEqual(Reparacion.query.count(), 1)
        self.assertEqual(updated.json['historial'][-1]['usuario'], 'cajero')
        self.assertEqual(self.request(path + '/entregar', {}, role='employee', method='put').status_code, 403)
        delivered = self.request(path + '/entregar', {}, method='put')
        self.assertEqual(delivered.status_code, 200)
        self.assertFalse(delivered.json['atrasada'])
        self.assertIsNotNone(delivered.json['fecha_entrega'])

    def test_repair_invalid_creation_rolls_back_model(self):
        for amount in (-1, 'NaN', 501):
            data = self.repair_data(); data['anticipo'] = amount
            self.assertEqual(self.request('/api/reparaciones', data, role='employee').status_code, 400)
            self.assertEqual(Reparacion.query.count(), 0)

    def test_compatibility_cache_history_and_verification(self):
        mock_result = {'compatibles': [{'modelo': 'Mica X', 'marca': 'Marca', 'nivel_compatibilidad': 'alta', 'verificada': True}], 'notas': 'Sugerencia'}
        with patch('routes_compatibilidad.get_compatibility_recommendation', return_value=mock_result) as provider:
            first = self.request('/api/compatibilidad/buscar', {'modelo_celular': ' Modelo  X '}, role='employee')
            self.assertEqual(first.status_code, 200, first.json)
            self.assertFalse(first.json['datos']['compatibles'][0]['verificada'])
            cached = self.request('/api/compatibilidad/buscar', {'modelo_celular': 'modelo x'}, role='employee')
            self.assertEqual(cached.json['origen'], 'historial')
            self.assertEqual(provider.call_count, 1)
            verify = dict(modelo_celular='Modelo X', mica='Mica X', marca='Marca', notas='Probada sin obstruir cámara', confirmada=True)
            verified = self.request('/api/compatibilidad/verificadas', verify, role='employee')
            self.assertEqual(verified.status_code, 200, verified.json)
            confirmed = self.request('/api/compatibilidad/buscar', {'modelo_celular': 'MODELO X'}, role='employee')
            self.assertEqual(confirmed.json['origen'], 'verificadas')
            self.assertTrue(confirmed.json['datos']['compatibles'][0]['verificada'])
            self.assertEqual(provider.call_count, 1)
            history = self.request('/api/compatibilidad/historial', role='employee', method='get')
            self.assertEqual(history.json['total'], 3)
            self.assertEqual(self.request('/api/compatibilidad/historial', role='other', method='get').json['total'], 0)
            url = '/api/compatibilidad/verificadas/' + verified.json['id']
            self.assertEqual(self.request(url, role='other', method='delete').status_code, 403)
            self.assertEqual(self.request(url, role='employee', method='delete').status_code, 200)
            refreshed_history = self.request('/api/compatibilidad/historial', role='employee', method='get').json
            self.assertFalse(refreshed_history['consultas'][0]['resultado']['compatibles'][0]['verificada'])
            self.request('/api/compatibilidad/buscar', {'modelo_celular': 'modelo x', 'actualizar_ia': True}, role='employee')
            self.assertEqual(provider.call_count, 2)

    def test_verification_requires_physical_confirmation_and_notes(self):
        for confirmation, notes in [(False, 'Probada'), (True, '')]:
            res = self.request('/api/compatibilidad/verificadas', dict(modelo_celular='X', mica='Y', notas=notes, confirmada=confirmation), role='employee')
            self.assertEqual(res.status_code, 400)
            self.assertEqual(CompatibilidadVerificada.query.count(), 0)

    def test_multiple_closures_separate_movements_and_corrections(self):
        first_sale = self.sale()
        first_id = self.cash()['id']
        first = self.request('/api/ventas/cierre-caja', {'cierre_id': first_id, 'efectivo_reportado': 200, 'egresos': []}, role='employee')
        self.assertEqual(first.status_code, 200, first.json)
        self.assertEqual(first_sale.cierre_caja_id, first_id)
        original_time = first.json['cierre']['closed_at']
        second = self.request('/api/ventas/cierre-caja/nuevo', {}, role='employee')
        self.assertEqual(second.status_code, 200, second.json)
        second_id = second.json['cierre']['id']
        self.assertNotEqual(first_id, second_id)
        self.assertEqual(second.json['cierre']['total_ventas'], 0)
        self.assertEqual(self.request('/api/ventas/cierre-caja/nuevo', {}, role='employee').json['cierre']['id'], second_id)
        self.assertEqual(CierreCaja.query.count(), 2)
        second_sale = self.sale(method='efectivo')
        refund = self.refund(first_sale, {'efectivo': 100})
        self.assertEqual(refund.status_code, 201, refund.json)
        preview = self.cash()
        self.assertEqual(preview['id'], second_id)
        self.assertEqual((preview['total_ventas'], preview['total_efectivo'], preview['reembolsos_efectivo']), (200, 300, 100))
        # Un formulario anterior no puede confirmar ni cambiar otro cierre.
        stale = self.request('/api/ventas/cierre-caja', {'cierre_id': first_id, 'efectivo_reportado': 1}, role='employee')
        self.assertEqual(stale.status_code, 409)
        saved = self.request('/api/ventas/cierre-caja', {'cierre_id': second_id, 'efectivo_reportado': 350, 'egresos': [{'monto': 50, 'concepto': 'Transporte'}]}, role='employee')
        self.assertEqual(saved.status_code, 200, saved.json)
        self.assertEqual(saved.json['cierre']['diferencia'], 0)
        self.assertEqual(second_sale.cierre_caja_id, second_id)
        self.assertEqual(db.session.get(DevolucionVenta, refund.json['devolucion']['id']).cierre_caja_id, second_id)
        today = get_cdmx_now().date().isoformat()
        report = self.client.get('/api/ventas/reportes/cierres-caja-detalle', query_string={'fecha_inicio': today, 'fecha_fin': today}, headers=self.headers['admin'])
        self.assertEqual(report.status_code, 200, report.json)
        closes = {c['id']: c for c in report.json['cierres']}
        self.assertEqual(sum(c['total_vendido'] for c in closes.values()), 500)
        self.assertEqual(closes[first_id]['total_vendido'], 300)
        self.assertEqual(closes[second_id]['total_vendido'], 200)
        self.assertEqual([c['cantidad_ventas'] for c in closes.values()], [1, 1])
        self.assertEqual([c['productos'][0]['unidades'] for c in closes.values()], [3, 3])
        corrected = self.request('/api/ventas/cierre-caja/corregir', {'cierre_id': first_id, 'efectivo_reportado': 180, 'egresos': [{'monto': 20, 'concepto': 'Corrección'}]}, role='employee')
        self.assertEqual(corrected.status_code, 200, corrected.json)
        self.assertEqual(corrected.json['cierre']['closed_at'], original_time)
        self.assertEqual(db.session.get(CierreCaja, second_id).egreso, 50)
        self.assertEqual(self.request('/api/ventas/cierre-caja/corregir', {'cierre_id': first_id, 'efectivo_reportado': 0}, role='other').status_code, 400)
        self.assertEqual(self.request('/api/ventas/cierre-caja/corregir', {'efectivo_reportado': 0}, role='employee').status_code, 400)
        self.assertEqual(self.cash()['id'], second_id)
        self.assertEqual(CierreCaja.query.count(), 2)
        third = self.request('/api/ventas/cierre-caja/nuevo', {}, role='employee').json['cierre']
        self.assertEqual((third['total_ventas'], third['total_efectivo'], third['reembolsos_efectivo'], third['egreso']), (0, 0, 0, 0))
        reverse = self.request('/api/devoluciones/' + refund.json['devolucion']['id'], method='delete')
        self.assertEqual(reverse.status_code, 409)



if __name__ == '__main__':
    unittest.main()
