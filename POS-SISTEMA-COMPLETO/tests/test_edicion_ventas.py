import unittest
from decimal import Decimal
from datetime import timedelta
import test_operacion_seguimiento as fixtures
from models import db, Producto, Stock, CierreCaja, Comision
from edicion_ventas import edicion_ventas_bp
from config import get_cdmx_now

class EdicionVentasTest(unittest.TestCase):
    request=fixtures.OperacionTest.request
    tearDown=fixtures.OperacionTest.tearDown
    sale=fixtures.OperacionTest.sale
    refund=fixtures.OperacionTest.refund
    def setUp(self):
        fixtures.OperacionTest.setUp(self)
        self.client.application.register_blueprint(edicion_ventas_bp)
        self.employee.permisos={'ventas-del-dia':['ver','editar']}
        self.venta=self.sale(method='efectivo')
        self.stock.cantidad=2
        db.session.commit()
        self.url='/api/ventas/'+self.venta.id+'/edicion'
    def payload(self):
        r=self.request(self.url,role='employee',method='get')
        self.assertEqual(r.status_code,200,r.json)
        return dict(**r.json['venta'],version=r.json['version'],motivo='Corrección del cobro')
    def save(self,p):return self.request(self.url,p,role='employee',method='put')
    def test_price_quantity_payments_and_history(self):
        p=self.payload();p['detalles'][0].update(cantidad=2,precio_unitario=150)
        p['pagos']=[dict(metodo_pago='tarjeta',monto=100),dict(metodo_pago='efectivo',monto=200)]
        r=self.save(p);self.assertEqual(r.status_code,200,r.json)
        self.assertEqual(self.stock.cantidad,3)
        self.assertEqual(self.venta.total,300)
        self.assertEqual(self.venta.forma_pago,'mixto')
        self.assertEqual(len(self.venta.ediciones),1)
        self.assertEqual(self.venta.ediciones[0]['antes']['detalles'][0]['cantidad'],3)
        self.assertEqual(self.venta.ediciones[0]['despues']['detalles'][0]['cantidad'],2)
        self.assertEqual(self.save(p).status_code,409)
        self.assertEqual(self.stock.cantidad,3)
    def test_replace_out_of_stock_does_not_invent_stock(self):
        new=Producto(codigo='NEW',nombre='Tipo C',subcategoria_id=self.product.subcategoria_id,precio=150,costo_compra=27)
        db.session.add(new);db.session.commit()
        p=self.payload();p['detalles'][0].update(producto_id=new.id,cantidad=1,precio_unitario=150);p['pagos']=[dict(metodo_pago='efectivo',monto=150)]
        r=self.save(p);self.assertEqual(r.status_code,200,r.json)
        self.assertEqual(self.stock.cantidad,5);self.assertTrue(self.venta.detalles[0].sin_stock)
        self.assertEqual(self.venta.detalles[0].costo_compra_unitario,27)
        p=self.payload();p['detalles'][0].update(producto_id=self.product.id)
        self.assertEqual(self.save(p).status_code,200)
        self.assertEqual(self.stock.cantidad,4)
        self.assertIsNone(Stock.query.filter_by(producto_id=new.id).first())
    def test_closed_and_previous_day_apartado(self):
        p=self.payload()
        cierre=CierreCaja(empleado_id=self.employee.id,sucursal_id=self.branch.id,fecha=get_cdmx_now().date(),estado='cerrado')
        db.session.add(cierre);db.session.flush();self.venta.cierre_caja_id=cierre.id;db.session.commit()
        self.assertEqual(self.save(p).status_code,409)
        self.venta.cierre_caja_id=None;self.venta.created_at=get_cdmx_now()-timedelta(days=1);db.session.commit()
        self.assertEqual(self.save(p).status_code,409)
        self.venta.created_at=get_cdmx_now();self.venta.numero_venta='AP-test';db.session.commit()
        self.assertEqual(self.save(p).status_code,409)
    def test_permissions_branch_and_validation(self):
        p=self.payload()
        self.employee.permisos={'ventas-del-dia':['ver']};db.session.commit()
        self.assertEqual(self.save(p).status_code,403)
        self.employee.permisos=None;db.session.commit()
        self.assertEqual(self.save(p).status_code,403)
        self.employee.permisos={'ventas-del-dia':['ver','editar']};self.employee.sucursales_permitidas=[];db.session.commit()
        self.assertEqual(self.save(p).status_code,403)
        self.employee.sucursales_permitidas=[self.branch.id];db.session.commit()
        p['pagos'][0]['monto']=1
        self.assertEqual(self.save(p).status_code,400)
        self.assertEqual(self.stock.cantidad,2)
        p=self.payload();p['motivo']=' '
        self.assertEqual(self.save(p).status_code,400)
        p=self.payload();p['detalles'][0]['cantidad']=1.5
        self.assertEqual(self.save(p).status_code,400)
    def test_returns_and_commissions(self):
        p=self.payload()
        c=Comision(sucursal_id=self.branch.id,creado_por_id=self.employee.id,dispositivo='Tablet',costo=100,metodo_pago='efectivo',nombre_empleado='Empleado',detalle_venta_id=self.venta.detalles[0].id,unidad=1)
        db.session.add(c);db.session.commit()
        self.assertEqual(self.save(p).status_code,409)
        db.session.delete(c);db.session.commit()
        r=self.refund(self.venta,{'efectivo':100});self.assertEqual(r.status_code,201,r.json)
        self.assertEqual(self.save(p).status_code,409)
