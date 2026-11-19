import unittest
from unittest.mock import patch
from datetime import datetime, timezone
import test_operacion_seguimiento as fixtures
from models import db, Venta
from routes_reportes import reportes_bp
from config import CDMX_TZ


class DashboardFechaTest(unittest.TestCase):
    request = fixtures.OperacionTest.request
    tearDown = fixtures.OperacionTest.tearDown

    def setUp(self):
        fixtures.OperacionTest.setUp(self)
        self.client.application.register_blueprint(reportes_bp)

    def test_dia_cdmx_y_limites_del_consolidado(self):
        now = datetime(2026,11,20,2,tzinfo=timezone.utc).astimezone(CDMX_TZ)
        for i, (fecha, total) in enumerate([('2026-11-18T23:59:59',900),('2026-11-19T00:00:00',100),('2026-11-19T23:59:59',200),('2026-11-20T00:00:00',800)]):
            db.session.add(Venta(numero_venta='D'+str(i),sucursal_id=self.branch.id,cajero_id=self.employee.id,total=total,total_impuestos=0,forma_pago='efectivo',created_at=CDMX_TZ.localize(datetime.fromisoformat(fecha))))
        db.session.commit()
        with patch('routes_reportes.get_cdmx_now',return_value=now):
            diario=self.request('/api/reportes/ventas-diarias',method='get').json
        self.assertEqual(diario['fecha'],'2026-11-19')
        self.assertEqual(diario['total_ventas'],300)
        response=self.request('/api/reportes/consolidado-sucursales?fecha_inicio=2026-11-19&fecha_fin=2026-11-19',method='get')
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(response.json['total_general'],300)
        self.assertEqual(response.json['cantidad_transacciones_general'],2)
        self.assertEqual(self.request('/api/reportes/consolidado-sucursales?fecha_inicio=2026-11-20&fecha_fin=2026-11-19',method='get').status_code,400)
