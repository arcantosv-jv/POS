import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch
import test_operacion_seguimiento as fixtures
from models import (db, Venta, DetalleVenta, Sucursal, Categoria, Subcategoria, Producto,
    HistoricoPronostico, Pronostico, ResumenPronostico, EstadoResumenPronostico, DevolucionVenta)
from routes_pronosticos import pronosticos_bp
from pronostico_motor import refrescar, serie, generar, estimar
from config import CDMX_TZ

NOW = CDMX_TZ.localize(datetime(2026,11,18,12))


class PronosticosTest(unittest.TestCase):
    tearDown = fixtures.OperacionTest.tearDown
    request = fixtures.OperacionTest.request

    def setUp(self):
        fixtures.OperacionTest.setUp(self)
        self.client.application.register_blueprint(pronosticos_bp)
        self.employee.permisos = {'pronosticos':['ver','generar','historico']}
        self.employee.sucursales_permitidas = [self.branch.id]
        self.norte = Sucursal(nombre='Norte', direccion='Norte')
        db.session.add(self.norte); db.session.commit()
        self.clock = patch('routes_pronosticos.get_cdmx_now', return_value=NOW); self.clock.start()
        self.addCleanup(self.clock.stop)
        self.data = dict(inicio='2026-11-19', fin='2026-11-25', sucursal_id=self.branch.id)

    def venta(self, day='2026-10-01', cantidad=2, branch=None, product=None):
        v = Venta(numero_venta='P'+str(Venta.query.count()), sucursal_id=branch or self.branch.id,
            cajero_id=self.employee.id, total=cantidad*100, total_impuestos=0, forma_pago='efectivo',
            created_at=CDMX_TZ.localize(datetime.fromisoformat(day+'T12:00:00')))
        v.detalles.append(DetalleVenta(producto_id=(product or self.product).id, cantidad=cantidad,
            precio_unitario=100, impuesto_unitario=0, subtotal=cantidad*100))
        db.session.add(v); db.session.commit(); return v

    def test_branch_and_actions(self):
        self.venta(); self.venta(branch=self.norte.id, cantidad=500)
        denied=self.request('/api/pronosticos',self.data,role='other')
        self.assertEqual(denied.status_code,403)  # legacy cannot acquire new access implicitly
        response=self.request('/api/pronosticos',{**self.data,'sucursal_id':None},role='employee')
        self.assertEqual(response.status_code,201,response.json)
        self.assertEqual(response.json['sucursales'],[self.branch.id])
        self.assertEqual(response.json['resultado']['total']['meses'][0]['importe'],200)
        self.assertEqual(self.request('/api/pronosticos',{**self.data,'sucursal_id':self.norte.id},role='employee').status_code,403)
        general=self.request('/api/pronosticos',{**self.data,'sucursal_id':None}).json
        self.assertEqual(self.request('/api/pronosticos/'+general['id'],role='employee',method='get').status_code,404)
        self.assertEqual(len(self.request('/api/pronosticos',role='employee',method='get').json['pronosticos']),1)
        self.employee.permisos={'pronosticos':['ver']};db.session.commit()
        self.assertEqual(self.request('/api/pronosticos',self.data,role='employee').status_code,403)
        self.assertEqual(self.request('/api/pronosticos/historicos',self.manual(),role='employee',method='put').status_code,403)

    def manual(self):
        return dict(sucursal_id=self.branch.id,mes='2026-10',categorias=[dict(categoria_id=self.product.subcategoria.categoria_id,importe='3100',unidades=31)],motivo='Reporte previo')

    def test_manual_replaces_whole_month_and_not_sales(self):
        self.venta(cantidad=10)
        cat=Categoria(nombre='Otro'); db.session.add(cat);db.session.flush()
        sub=Subcategoria(nombre='Otra',categoria_id=cat.id);db.session.add(sub);db.session.flush()
        product=Producto(codigo='otro',nombre='Otro',precio=100,subcategoria_id=sub.id);db.session.add(product);db.session.commit()
        self.venta(product=product)
        r=self.request('/api/pronosticos/historicos',self.manual(),role='employee',method='put')
        self.assertEqual(r.status_code,200,r.json)
        result=self.request('/api/pronosticos',self.data).json['resultado']
        self.assertEqual(result['total']['meses'][0]['importe'],3100)
        self.assertEqual(result['total']['meses'][0]['unidades'],31)
        self.assertEqual(len(result['categorias']),1)
        self.assertEqual(sum(v.total for v in Venta.query.all()),1200)
        self.assertEqual(len(result['manuales']),1)
        revised=self.manual();revised['categorias'][0]['importe']='6200'
        self.request('/api/pronosticos/historicos',revised,method='put')
        self.assertEqual(len(HistoricoPronostico.query.one().cambios),2)
        self.assertEqual(Pronostico.query.one().resultado['total']['meses'][0]['importe'],3100)

    def test_manual_fractional_daily_distribution_keeps_month_total(self):
        data=self.manual();data['categorias'][0].update(importe='100.01',unidades=2)
        self.request('/api/pronosticos/historicos',data,method='put')
        result=self.request('/api/pronosticos',self.data).json['resultado']
        self.assertEqual(result['total']['meses'][0]['importe'],100.01)
        self.assertEqual(result['total']['meses'][0]['unidades'],2)

    def test_manual_validation(self):
        for values in [{'mes':'2026-11'},{'mes':'2026-12'},{'mes':'bad'},{'categorias':[]},{'motivo':''},
                       {'categorias':[dict(categoria_id='unknown',importe=1,unidades=1)]},
                       {'categorias':[dict(categoria_id='',importe='NaN',unidades=1)]},
                       {'categorias':[dict(categoria_id='',importe=100,unidades=1.5)]}]:
            self.assertEqual(self.request('/api/pronosticos/historicos',{**self.manual(),**values},method='put').status_code,400)
        r=self.manual();r['categorias']*=2
        self.assertEqual(self.request('/api/pronosticos/historicos',r,method='put').status_code,400)
        self.assertEqual(HistoricoPronostico.query.count(),0)

    def test_cache_returns_and_cancellation(self):
        v=self.venta()
        refrescar([self.branch.id]);db.session.commit()
        self.assertFalse(EstadoResumenPronostico.query.one().pendiente)
        with patch('pronostico_motor.fecha_cdmx',side_effect=AssertionError('must use cache')):
            refrescar([self.branch.id])
        ret=DevolucionVenta(venta_id=v.id,detalle_venta_id=v.detalles[0].id,cantidad_devuelta=1,usuario_id=self.admin.id)
        db.session.add(ret);db.session.commit()
        self.assertTrue(EstadoResumenPronostico.query.one().pendiente)
        refrescar([self.branch.id]);db.session.commit()
        row=ResumenPronostico.query.one();self.assertEqual((row.importe,row.unidades),(100,1))
        db.session.delete(ret);db.session.commit();refrescar([self.branch.id]);db.session.commit()
        row=ResumenPronostico.query.one();self.assertEqual((row.importe,row.unidades),(200,2))
        v.detalles[0].cantidad=3;v.total=300;db.session.commit()
        self.assertTrue(EstadoResumenPronostico.query.one().pendiente)

    def test_timezone_and_delivery_sale(self):
        v=self.venta('2026-11-17')
        v.numero_venta='AP-old-apartado';v.created_at=datetime(2026,11,18,5,30,tzinfo=timezone.utc)
        db.session.commit()
        # SQLite loses timezone offsets: verify conversion independently and simulate PG aware rows.
        from comisiones_ventas import fecha_cdmx
        self.assertEqual(fecha_cdmx(datetime(2026,11,18,5,30,tzinfo=timezone.utc)).date(),date(2026,11,17))
        v.created_at=CDMX_TZ.localize(datetime(2026,11,17,23,30));db.session.commit()
        self.venta('2026-11-18',cantidad=99)
        response=self.request('/api/pronosticos',self.data)
        self.assertEqual(response.status_code,201,response.json)
        self.assertEqual(response.json['resultado']['total']['meses'][0]['importe'],200)

    def test_snapshot_and_actual_comparison(self):
        self.venta()
        r=self.request('/api/pronosticos',self.data).json
        original=r['resultado']
        self.venta('2026-11-19',cantidad=3)
        self.venta('2026-11-20',cantidad=20) # current incomplete day must not count
        with patch('routes_pronosticos.get_cdmx_now',return_value=CDMX_TZ.localize(datetime(2026,11,20,15))):
            detail=self.request('/api/pronosticos/'+r['id'],method='get').json
        self.assertEqual(detail['comparacion']['hasta'],'2026-11-19')
        self.assertEqual(detail['comparacion']['categorias'][0]['real'],[300,3])
        self.assertFalse(detail['comparacion']['completo'])
        self.assertEqual(detail['resultado'],original)
        self.assertEqual(self.request('/api/pronosticos/'+r['id'],{'resultado':{}},method='put').status_code,405)

    def test_empty_and_range_validation(self):
        self.assertEqual(self.request('/api/pronosticos',self.data).status_code,400)
        self.venta()
        for values in [{'inicio':'2026-11-18'},{'fin':'2026-11-18'},{'fin':'2030-01-01'},{'inicio':'bad'}]:
            self.assertEqual(self.request('/api/pronosticos',{**self.data,**values}).status_code,400)
        self.assertEqual(Pronostico.query.count(),0)

    def test_ai_failure_preserves_forecast_and_payload(self):
        self.venta();r=self.request('/api/pronosticos',self.data).json
        with patch.dict('os.environ',{},clear=True):
            fail=self.request('/api/pronosticos/'+r['id']+'/explicar',{})
        self.assertEqual(fail.status_code,503)
        self.assertEqual(Pronostico.query.count(),1)
        with patch.dict('os.environ',{'GEMINI_API_KEY':'test'}), patch('requests.post') as post:
            post.return_value.json.return_value={'candidates':[{'content':{'parts':[{'text':'Estimación orientativa.'}]}}]}
            ok=self.request('/api/pronosticos/'+r['id']+'/explicar',{})
            self.assertEqual(ok.status_code,200,ok.json)
            prompt=post.call_args.kwargs['json']['contents'][0]['parts'][0]['text']
            self.assertNotIn(self.employee.username,prompt)
            self.assertNotIn(self.employee.email,prompt)
        self.assertEqual(Pronostico.query.one().resultado,r['resultado'])


class MotorTest(unittest.TestCase):
    def test_zero_days_and_coherent_categories(self):
        data={(date(2026,1,1),'a'):[3100,31],(date(2026,1,1),'b'):[6200,62]}
        result=generar(data,date(2026,2,1),date(2026,2,7),date(2026,1,31),{'a':'A','b':'B'})
        self.assertEqual(result['dias_historial'],31)
        self.assertEqual(result['total']['historico'][1]['importe'],0)
        for i,d in enumerate(result['total']['dias']):
            for metric in ('importe','unidades'):
                vals=d[metric];self.assertTrue(0<=vals[0]<=vals[1]<=vals[2])
                for j in range(3): self.assertAlmostEqual(vals[j],sum(c['dias'][i][metric][j] for c in result['categorias']),places=2)

    def test_constant_sales_and_all_zero_history(self):
        dates=[date(2026,1,1)+timedelta(days=i) for i in range(100)]
        result=estimar([100]*100,dates,[dates[-1]+timedelta(days=1)])
        self.assertEqual(result[0][1],100)
        self.assertEqual(estimar([0]*100,dates,[dates[-1]+timedelta(days=1)]),[[0,0,0]])
