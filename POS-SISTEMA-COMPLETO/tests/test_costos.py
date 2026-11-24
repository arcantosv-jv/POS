import unittest
from unittest.mock import patch
from decimal import Decimal
import test_operacion_seguimiento as fixtures
from models import db, DetalleVenta
from routes_costos import costos_bp
from config import get_cdmx_now


class CostosTest(unittest.TestCase):
    request = fixtures.OperacionTest.request
    tearDown = fixtures.OperacionTest.tearDown
    sale = fixtures.OperacionTest.sale
    refund = fixtures.OperacionTest.refund

    def setUp(self):
        fixtures.OperacionTest.setUp(self)
        self.client.application.register_blueprint(costos_bp)

    def review(self):
        r=self.request('/api/costos/revisiones', {})
        self.assertEqual(r.status_code,201,r.json)
        return r.json

    def edit(self,r,cost):
        result=self.request('/api/costos/revisiones/'+r['id']+'/editar',dict(version=r['version'],producto_id=self.product.id,costo=cost,motivo='Costo confirmado'))
        self.assertEqual(result.status_code,200,result.json)
        return result.json

    def apply(self,r):
        return self.request('/api/costos/revisiones/'+r['id']+'/aplicar',dict(version=r['version']))

    def test_private_and_manual_review(self):
        for endpoint in ('reglas','revisiones','utilidad'):
            self.assertEqual(self.request('/api/costos/'+endpoint,role='employee',method='get').status_code,403)
        original=(self.product.nombre,self.product.precio,self.product.subcategoria_id,self.stock.cantidad)
        r=self.edit(self.review(),'5.50')
        self.assertIsNone(self.product.costo_compra)
        response=self.apply(r);self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(self.product.costo_compra,Decimal('5.50'))
        self.assertEqual(original,(self.product.nombre,self.product.precio,self.product.subcategoria_id,self.stock.cantidad))
        self.assertNotIn('costo_compra',self.product.to_dict())
        self.assertEqual(self.review()['filas'][0]['estado'],'conservado')
        self.assertEqual(self.apply(r).status_code,409)
        self.assertEqual(self.apply(response.json).status_code,200)

    def test_conflict_and_invalid_amount(self):
        r=self.edit(self.review(),'18')
        self.product.nombre='Cambio';db.session.commit()
        self.assertEqual(self.apply(r).status_code,409)
        self.assertIsNone(self.product.costo_compra)
        for cost in ('NaN',-1,'1.234'):
            response=self.request('/api/costos/revisiones/'+r['id']+'/editar',dict(version=r['version'],producto_id=self.product.id,costo=cost,motivo='Costo'))
            self.assertEqual(response.status_code,400)

    def test_ai_only_selects_manual_rule_and_changed_rule_blocks(self):
        rule=self.request('/api/costos/reglas',dict(nombre='Mica',criterio='Mica sencilla',costo=5.5,activa=True)).json
        r=self.review()
        with patch('routes_costos.identificar',return_value=[dict(codigo='P1',regla_id=rule['id'],ambiguo=False,motivo='Coincide')]):
            response=self.request('/api/costos/revisiones/'+r['id']+'/procesar',{})
        self.assertEqual(response.status_code,200,response.json)
        r=response.json;self.assertEqual(Decimal(r['filas'][0]['costo_propuesto']),Decimal('5.5'))
        self.assertIsNone(self.product.costo_compra)
        rule['costo']=6
        self.assertEqual(self.request('/api/costos/reglas/'+rule['id'],rule,method='put').status_code,200)
        self.assertEqual(self.apply(r).status_code,409)
        r=self.edit(r,6)
        self.assertEqual(self.apply(r).status_code,200)

    def test_ambiguous_and_provider_failure_do_not_apply(self):
        rule=self.request('/api/costos/reglas',dict(nombre='Mica',criterio='Mica sencilla',costo=5.5,activa=True)).json
        r=self.review();url='/api/costos/revisiones/'+r['id']+'/procesar'
        with patch('routes_costos.identificar',return_value=[dict(codigo='P1',regla_id=rule['id'],ambiguo=False,motivo='Coincide',costo=999)]):
            self.assertEqual(self.request(url,{}).status_code,400)
        with patch('routes_costos.identificar',return_value=[dict(codigo='P1',regla_id=None,ambiguo=True,motivo='No identificado')]):
            r=self.request(url,{}).json
        self.assertFalse(r['ocupado']);self.assertEqual(r['filas'][0]['estado'],'pendiente')
        self.assertEqual(self.apply(r).status_code,200);self.assertIsNone(self.product.costo_compra)

    def test_report_missing_estimated_snapshot_and_returns(self):
        sale=self.sale(method='efectivo')
        date=get_cdmx_now().date().isoformat()
        url='/api/costos/utilidad?fecha_inicio='+date+'&fecha_fin='+date
        def report(): return self.request(url,method='get').json['resumen']
        self.assertIsNone(report()['utilidad']);self.assertEqual(report()['unidades_sin_costo'],3)
        self.product.costo_compra=Decimal('5.5');db.session.commit()
        self.assertEqual(report()['utilidad'],283.5);self.assertEqual(report()['unidades_estimadas'],3)
        sale.detalles[0].costo_compra_unitario=Decimal('10');db.session.commit()
        self.assertEqual(report()['utilidad'],270)
        response=self.refund(sale,{'efectivo':100})
        self.assertEqual(response.status_code,201,response.json)
        self.assertEqual(report()['utilidad'],180);self.assertEqual(report()['ventas'],200)
        for group in ('producto','categoria','sucursal'):
            self.assertEqual(self.request(url+'&agrupar='+group,method='get').json['resumen']['utilidad'],180)
        self.assertEqual(self.request(url+'&sucursal_id=inexistente',method='get').json['filas'],[])

    def test_new_sale_captures_cost_and_does_not_expose_it(self):
        self.product.costo_compra=Decimal('18');db.session.commit()
        result=self.request('/api/ventas',dict(forma_pago='efectivo',detalles=[dict(producto_id=self.product.id,cantidad=1,costo_compra_unitario=1)]),role='employee')
        self.assertEqual(result.status_code,201,result.json)
        detail=DetalleVenta.query.one()
        self.assertEqual(detail.costo_compra_unitario,Decimal('18'))
        self.assertNotIn('costo_compra_unitario',detail.to_dict())
        self.product.costo_compra=Decimal('35');db.session.commit()
        self.assertEqual(detail.costo_compra_unitario,Decimal('18'))

    def test_product_form_optional_cost_and_admin_privacy(self):
        from routes_productos import productos_bp
        self.client.application.register_blueprint(productos_bp)
        url='/api/productos/'+self.product.id
        response=self.request(url,{'costo_compra':'5.50'},method='put')
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(response.json['producto']['costo_compra'],5.5)
        self.assertEqual(self.request('/api/productos',method='get').json['productos'][0]['costo_compra'],5.5)
        self.assertNotIn('costo_compra',self.request(url,role='employee',method='get').json)
        self.assertNotIn('costo_compra',self.request('/api/productos',role='employee',method='get').json['productos'][0])
        # A delegated product editor still cannot change private costs.
        with patch('routes_productos.delegated_access',return_value=True):
            denied=self.request(url,{'costo_compra':1},role='employee',method='put')
            self.assertEqual(denied.status_code,403)
            allowed=self.request(url,{'nombre':'Mica nueva'},role='employee',method='put')
            self.assertEqual(allowed.status_code,200)
        self.assertEqual(self.product.costo_compra,Decimal('5.50'))
        self.assertEqual(self.request(url,{'costo_compra':-1},method='put').status_code,400)
        self.assertEqual(self.product.costo_compra,Decimal('5.50'))
        self.assertEqual(self.request(url,{'costo_compra':''},method='put').status_code,200)
        self.assertIsNone(self.product.costo_compra)
        for code,cost in [('NEW1',None),('NEW2',0),('NEW3',18)]:
            data=dict(codigo=code,nombre=code,subcategoria_id=self.product.subcategoria_id)
            if cost is not None: data['costo_compra']=cost
            response=self.request('/api/productos',data)
            self.assertEqual(response.status_code,201,response.json)
            self.assertEqual(response.json['producto']['costo_compra'],cost)
