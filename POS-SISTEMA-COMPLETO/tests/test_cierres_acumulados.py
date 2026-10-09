"""Cierres compartidos por sucursal, efectivo acumulado y día CDMX."""
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
import test_operacion_seguimiento as fixtures
from config import CDMX_TZ
from models import db, CierreCaja, Venta, Sucursal


class CierresAcumuladosTest(unittest.TestCase):
    setUp = fixtures.OperacionTest.setUp
    tearDown = fixtures.OperacionTest.tearDown
    request = fixtures.OperacionTest.request
    sale = fixtures.OperacionTest.sale
    cash = fixtures.OperacionTest.cash

    def close(self, current, reported, role='employee', expenses=None):
        response = self.request('/api/ventas/cierre-caja', {
            'cierre_id': current['id'], 'efectivo_reportado': reported,
            'egresos': expenses or []}, role=role)
        self.assertEqual(response.status_code, 200, response.json)
        return response.json['cierre']

    def test_correction_one_hour_window_crosses_cdmx_midnight(self):
        confirmed = CDMX_TZ.localize(datetime(2026, 10, 9, 23, 30))
        with patch('routes_ventas.get_cdmx_now', return_value=confirmed):
            closed = self.close(self.cash(), 100)
        original_time = closed['closed_at']
        correction = {'cierre_id': closed['id'], 'efectivo_reportado': 90}
        with patch('routes_ventas.get_cdmx_now', return_value=confirmed + timedelta(minutes=45)):
            today = self.cash()
            self.assertEqual(today['fecha'], '2026-10-10')
            self.assertEqual(today['cierres_editables_dia_anterior'][0]['id'], closed['id'])
            self.assertTrue(today['cierres_editables_dia_anterior'][0]['puede_corregir'])
            response = self.request('/api/ventas/cierre-caja/corregir', correction, role='employee')
            self.assertEqual(response.status_code, 200, response.json)
            self.assertEqual(response.json['cierre']['closed_at'], original_time)
            self.assertEqual(response.json['cierre']['editable_hasta'], closed['editable_hasta'])
            # Another cashier cannot modify the close, even within the hour.
            self.assertEqual(self.request('/api/ventas/cierre-caja/corregir', correction, role='other').status_code, 400)
        with patch('routes_ventas.get_cdmx_now', return_value=confirmed + timedelta(hours=1)):
            self.assertEqual(self.request('/api/ventas/cierre-caja/corregir', correction, role='employee').status_code, 200)
        with patch('routes_ventas.get_cdmx_now', return_value=confirmed + timedelta(hours=1, seconds=1)):
            response = self.request('/api/ventas/cierre-caja/corregir', {**correction, 'efectivo_reportado': 10}, role='employee')
            self.assertEqual(response.status_code, 409, response.json)
            db.session.expire_all()
            self.assertEqual(db.session.get(CierreCaja, closed['id']).efectivo_reportado, 90)
            self.assertEqual(self.cash()['cierres_editables_dia_anterior'], [])

    def test_sales_total_includes_all_payment_methods_once(self):
        for method in ('efectivo', 'tarjeta', 'transferencia', 'mixto'):
            self.sale(method=method)
        current = self.cash()
        self.assertEqual(current['total_ventas'], 1200)
        self.assertEqual((current['total_efectivo'], current['total_tarjeta'], current['total_transferencia']), (500, 400, 300))
        closed = self.close(current, 450, expenses=[{'monto': 50, 'concepto': 'Transporte'}])
        self.assertEqual(closed['total_ventas'], 1200)
        self.assertEqual(closed['efectivo_esperado'], 450)
        next_shift = self.request('/api/ventas/cierre-caja/nuevo', {}, role='employee').json['cierre']
        self.assertEqual(next_shift['total_ventas'], 0)
        self.assertEqual(next_shift['cierres_anteriores'][0]['total_ventas'], 1200)

    def test_three_shifts_different_cashiers_and_correction(self):
        first_sale = self.sale(method='efectivo')
        first = self.close(self.cash(), 290)
        self.assertEqual(first['diferencia'], -10)
        second = self.request('/api/ventas/cierre-caja/hoy', role='other', method='get').json
        self.assertEqual(second['total_ventas'], 0)
        self.assertEqual(second['productos'], [])
        self.assertEqual(second['efectivo_esperado'], 290)
        self.assertEqual(second['cierres_anteriores'][0]['empleado_id'], self.employee.id)
        self.assertEqual(second['cierres_anteriores'][0]['productos'][0]['unidades'], 3)
        second_sale = self.sale(method='efectivo')
        second_sale.cajero_id = self.other.id
        db.session.commit()
        second = self.close(second, 540, role='other', expenses=[{'monto': 40, 'concepto': 'Transporte'}])
        self.assertEqual((second['total_ventas'], second['efectivo_esperado'], second['diferencia']), (300, 550, -10))
        self.assertEqual(second_sale.cierre_caja_id, second['id'])
        third = self.request('/api/ventas/cierre-caja/nuevo', {}, role='employee').json['cierre']
        self.assertEqual(third['efectivo_esperado'], 540)  # No 290 + 540.
        self.assertEqual(third['numero_turno'], 3)
        self.assertEqual([c['aportacion_reportada'] for c in third['cierres_anteriores']], [290, 250])
        self.assertEqual((third['total_ventas'], third['total_efectivo'], third['egreso']), (0, 0, 0))
        self.sale(method='efectivo')
        third = self.close(third, 840)
        self.assertEqual(third['diferencia'], 0)
        self.assertEqual(first_sale.cierre_caja_id, first['id'])
        # Corregir el primer conteo ajusta el arrastre y diferencia del segundo,
        # sin cambiar el efectivo físico que reportaron los siguientes cajeros.
        corrected = self.request('/api/ventas/cierre-caja/corregir', {
            'cierre_id': first['id'], 'efectivo_reportado': 280}, role='employee')
        self.assertEqual(corrected.status_code, 200, corrected.json)
        db.session.expire_all()
        saved_second = db.session.get(CierreCaja, second['id'])
        self.assertEqual((saved_second.efectivo_inicial, saved_second.efectivo_reportado, saved_second.diferencia), (280, 540, 0))
        self.assertEqual(db.session.get(CierreCaja, third['id']).efectivo_inicial, 540)
        self.assertEqual(self.request('/api/ventas/cierre-caja/corregir', {
            'cierre_id': first['id'], 'efectivo_reportado': 0}, role='other').status_code, 400)

    def test_cdmx_day_boundary_and_other_branch(self):
        # Railway UTC ya está en el día 10, pero CDMX sigue en el día 9.
        utc_now = datetime(2026, 10, 10, 5, 59, tzinfo=timezone.utc)
        local_now = utc_now.astimezone(CDMX_TZ)
        other_branch = Sucursal(nombre='Otra', direccion='Otra')
        db.session.add(other_branch)
        db.session.flush()
        db.session.add(CierreCaja(empleado_id=self.other.id, sucursal_id=other_branch.id,
            fecha=local_now.date(), estado='cerrado', efectivo_reportado=9000,
            closed_at=local_now, efectivo_inicial=0))
        for name, when, amount in [('ayer', local_now - timedelta(days=1), 500),
                                  ('hoy', local_now, 100),
                                  ('manana', local_now + timedelta(minutes=2), 200)]:
            db.session.add(Venta(numero_venta=name, sucursal_id=self.branch.id, cajero_id=self.employee.id,
                total=amount, forma_pago='efectivo', created_at=when))
        db.session.commit()
        with patch('routes_ventas.get_cdmx_now', return_value=local_now):
            current = self.cash()
            self.assertEqual(current['fecha'], '2026-10-09')
            self.assertEqual(current['total_ventas'], 100)
            self.assertEqual(current['cierres_anteriores'], [])
            self.close(current, 100)
        with patch('routes_ventas.get_cdmx_now', return_value=local_now + timedelta(minutes=2)):
            tomorrow = self.cash()
            self.assertEqual(tomorrow['fecha'], '2026-10-10')
            self.assertEqual(tomorrow['efectivo_inicial'], 0)
            self.assertEqual(tomorrow['efectivo_esperado'], 200)
            self.assertEqual(tomorrow['cierres_anteriores'], [])

    def test_pending_branch_sales_are_assigned_once_and_legacy_balance(self):
        current = self.cash()
        # Un cierre previo al cambio conserva su reporte individual (NULL).
        legacy = CierreCaja(empleado_id=self.other.id, sucursal_id=self.branch.id,
            fecha=db.session.get(CierreCaja, current['id']).fecha, estado='cerrado',
            efectivo_reportado=100, total_efectivo=100)
        db.session.add(legacy)
        db.session.flush()
        legacy.efectivo_inicial = None
        db.session.commit()
        other_open = self.request('/api/ventas/cierre-caja/hoy', role='other', method='get').json
        # El otro cajero abre un cierre nuevo después de su cierre histórico.
        other_open = self.request('/api/ventas/cierre-caja/nuevo', {}, role='other').json['cierre']
        sale = self.sale(method='efectivo')
        sale.cajero_id = self.other.id
        db.session.commit()
        first = self.close(current, 400)
        self.assertEqual(first['efectivo_inicial'], 100)
        self.assertEqual(sale.cierre_caja_id, current['id'])
        second = self.request('/api/ventas/cierre-caja/hoy', role='other', method='get').json
        self.assertEqual(second['id'], other_open['id'])
        self.assertEqual(second['total_ventas'], 0)
        self.assertEqual(second['efectivo_esperado'], 400)
        self.assertEqual(second['cantidad_ventas'], 0)


if __name__ == '__main__':
    unittest.main()
