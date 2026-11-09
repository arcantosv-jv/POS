import unittest
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
import test_operacion_seguimiento as fixtures
from models import db, Apartado, ConfiguracionSistema, Producto, Stock, Venta, CierreCaja, Sucursal
from routes_apartados import apartados_bp
from config import get_cdmx_now

class ApartadosTest(unittest.TestCase):
    request = fixtures.OperacionTest.request
    tearDown = fixtures.OperacionTest.tearDown

    def setUp(self):
        fixtures.OperacionTest.setUp(self)
        self.client.application.register_blueprint(apartados_bp)
        self.employee.permisos = {'apartados': ['ver','crear','abonar','entregar'], 'ventas': ['ver','crear']}
        self.employee.sucursales_permitidas = [self.branch.id]
        self.other.permisos = {'apartados': ['ver']}
        db.session.add(ConfiguracionSistema(id=1, apartados_habilitados=True))
        db.session.commit()

    def payload(self):
        return dict(cliente='Cliente', telefono='5512345678', empleado='Jazmín', plazo=15,
                    productos=[{'producto_id':self.product.id,'cantidad':2,'precio':100}], anticipo=50,
                    pagos=[{'metodo':'efectivo','monto':30},{'metodo':'tarjeta','monto':20}])

    def crear(self):
        res=self.request('/api/apartados',self.payload(),role='employee')
        self.assertEqual(res.status_code,201,res.json)
        return res.json

    def test_reserva_abono_entrega_independientes(self):
        r=self.crear()
        self.assertEqual(r['total'],200); self.assertEqual(r['restante'],150)
        self.assertEqual((self.stock.cantidad,self.stock.reservado),(3,2))
        self.assertEqual(r['vence'],(get_cdmx_now().date()+timedelta(days=15)).isoformat())
        url='/api/apartados/'+r['id']
        self.assertEqual(self.request(url+'/entregar',{'empleado':'A'},role='employee').status_code,400)
        self.product.precio=999; db.session.commit()
        res=self.request(url+'/abonar',dict(empleado='B',monto=150,pagos=[{'metodo':'transferencia','monto':150}]),role='employee')
        self.assertEqual(res.json['estado'],'liquidado')
        res=self.request(url+'/entregar',{'empleado':'B'},role='employee')
        self.assertEqual(res.json['estado'],'entregado')
        self.assertEqual((self.stock.cantidad,self.stock.reservado),(3,0))
        self.assertEqual(self.request(url+'/entregar',{'empleado':'B'},role='employee').status_code,400)
        self.assertEqual(Venta.query.count(),1);self.assertEqual(CierreCaja.query.count(),0)
        self.assertEqual(Venta.query.one().forma_pago,'mixto')
        self.assertEqual(res.json['venta_id'],Venta.query.one().id)

    def test_cancelacion_solo_admin_y_una_vez(self):
        r=self.crear(); url='/api/apartados/'+r['id']+'/cancelar'
        body=dict(empleado='Admin',motivo='Cambio solicitado',devolucion=50,pagos=[{'metodo':'efectivo','monto':50}])
        self.assertEqual(self.request(url,body,role='employee').status_code,403)
        self.assertEqual(self.request(url,body).status_code,200)
        self.assertEqual((self.stock.cantidad,self.stock.reservado),(5,0))
        self.assertEqual(self.request(url,body).status_code,400)
        self.assertEqual((self.stock.cantidad,self.stock.reservado),(5,0))

    def test_validaciones_rollback_y_scope(self):
        p=self.payload();p['productos'].append({'producto_id':'inexistente','cantidad':1})
        self.assertEqual(self.request('/api/apartados',p,role='employee').status_code,400)
        self.assertEqual((self.stock.cantidad,self.stock.reservado),(5,0))
        p=self.payload();p['anticipo']=201
        self.assertEqual(self.request('/api/apartados',p,role='employee').status_code,400)
        self.assertEqual(self.stock.cantidad,5)
        r=self.crear()
        another=Sucursal(nombre='Otra',direccion='Otra');db.session.add(another);db.session.flush()
        self.other.sucursal_id=another.id; self.other.sucursales_permitidas=[another.id];db.session.commit()
        self.assertEqual(self.request('/api/apartados',role='other',method='get').json['apartados'],[])
        self.assertEqual(len(self.request('/api/apartados',method='get').json['apartados']),1)
        db.session.get(ConfiguracionSistema,1).apartados_habilitados=False;db.session.commit()
        self.assertEqual(self.request('/api/apartados',role='employee',method='get').status_code,403)
        self.assertEqual(self.request('/api/apartados',method='get').status_code,200)

    def test_reservado_no_se_vende_y_vencimiento_no_cancela(self):
        r=self.crear()
        venta=dict(forma_pago='efectivo',detalles=[dict(producto_id=self.product.id,cantidad=4)])
        self.assertEqual(self.request('/api/ventas',venta,role='employee').status_code,409)
        self.assertEqual(Venta.query.count(),0)
        apartado=db.session.get(Apartado,r['id']);apartado.vence=get_cdmx_now().date()-timedelta(days=1);db.session.commit()
        data=self.request('/api/apartados',role='employee',method='get').json['apartados'][0]
        self.assertTrue(data['vencido']);self.assertEqual(data['estado'],'pendiente')
        self.assertEqual(self.stock.reservado,2)

    def test_varios_productos_sobreabono_y_cancelacion_invalida(self):
        segundo=Producto(codigo='T',nombre='Tablet',precio=250,impuesto=16,subcategoria_id=self.product.subcategoria_id)
        db.session.add(segundo);db.session.flush()
        stock=Stock(producto_id=segundo.id,sucursal_id=self.branch.id,cantidad=4)
        db.session.add(stock);db.session.commit()
        body=self.payload();body['productos'].append({'producto_id':segundo.id,'cantidad':2,'precio':290})
        res=self.request('/api/apartados',body,role='employee')
        self.assertEqual(res.status_code,201,res.json)
        self.assertEqual(res.json['total'],780)
        url='/api/apartados/'+res.json['id']
        self.assertEqual(self.request(url+'/abonar',dict(empleado='A',monto=800,pagos=[{'metodo':'efectivo','monto':800}]),role='employee').status_code,400)
        self.assertEqual(self.request(url+'/cancelar',dict(empleado='Admin',devolucion=51,motivo='Prueba',pagos=[{'metodo':'efectivo','monto':51}])).status_code,400)
        self.assertEqual((stock.cantidad,stock.reservado),(2,2))
        self.assertEqual((self.stock.cantidad,self.stock.reservado),(3,2))
        self.assertEqual(db.session.get(Apartado,res.json['id']).abonado,50)

    def test_telefono_exactamente_diez_digitos(self):
        for telefono in ['551234567', '55123456789', '55123a5678', '+525512345678', '55 1234567', 5512345678, '５５１２３４５６７８']:
            body=self.payload();body['telefono']=telefono
            res=self.request('/api/apartados',body,role='employee')
            self.assertEqual(res.status_code,400,(telefono,res.json))
        self.assertEqual(Apartado.query.count(),0)
        self.assertEqual(self.stock.cantidad,5)
        body=self.payload();body['telefono']='0123456789'
        res=self.request('/api/apartados',body,role='employee')
        self.assertEqual(res.status_code,201,res.json)
        self.assertEqual(res.json['telefono'],'0123456789')

    def test_precio_capturado_y_sucursal_fija(self):
        self.product.precio=999;self.product.impuesto=16;db.session.commit()
        body=self.payload();body['productos'][0]['precio']=75
        res=self.request('/api/apartados',body,role='employee')
        self.assertEqual(res.status_code,201,res.json)
        self.assertEqual(res.json['total'],150)
        self.assertEqual(res.json['productos'][0]['precio'],'75')
        self.assertEqual(self.product.precio,999)
        body=self.payload();body['productos'][0].pop('precio')
        self.assertEqual(self.request('/api/apartados',body,role='employee').status_code,400)
        otra=Sucursal(nombre='Otra permitida',direccion='Otra');db.session.add(otra);db.session.flush()
        self.employee.sucursales_permitidas=[self.branch.id,otra.id];db.session.commit()
        body=self.payload();body['sucursal_id']=otra.id
        self.assertEqual(self.request('/api/apartados',body,role='employee').status_code,403)

    def test_faltantes_privados_cancelacion_y_entrega(self):
        self.stock.cantidad=1;db.session.commit()
        r=self.crear()
        self.assertEqual((self.stock.cantidad,self.stock.reservado),(0,1))
        self.assertNotIn('sin_existencias',r)
        self.assertNotIn('faltantes',r['productos'][0])
        admin=self.request('/api/apartados',method='get').json['apartados'][0]
        self.assertTrue(admin['sin_existencias'])
        self.assertEqual(admin['productos'][0]['faltantes'],1)
        self.assertEqual(admin['productos'][0]['reservados'],1)
        url='/api/apartados/'+r['id']
        res=self.request(url+'/abonar',dict(empleado='A',monto=150,pagos=[{'metodo':'efectivo','monto':150}]),role='employee')
        self.assertNotIn('faltantes',res.json['productos'][0])
        entrega=self.request(url+'/entregar',{'empleado':'A'},role='employee')
        self.assertEqual(entrega.status_code,200,entrega.json)
        self.assertIsNotNone(entrega.json['fecha_entrega'])
        admin=self.request('/api/apartados',method='get').json['apartados'][0]
        self.assertTrue(admin['sin_existencias'])
        self.assertEqual(admin['fecha_entrega'],entrega.json['fecha_entrega'])
        self.assertEqual(admin['productos'][0]['faltantes'],1)
        self.assertEqual((self.stock.cantidad,self.stock.reservado),(0,0))
        r=self.crear()  # Cero disponibles: guardar sin inventar unidades.
        self.assertEqual((self.stock.cantidad,self.stock.reservado),(0,0))
        self.assertEqual(self.request('/api/apartados/'+r['id']+'/cancelar',dict(empleado='Admin',devolucion=0,motivo='Prueba',pagos=[])).status_code,200)
        self.assertEqual((self.stock.cantidad,self.stock.reservado),(0,0))

    def test_apartado_sin_fila_stock(self):
        db.session.delete(self.stock);db.session.commit()
        r=self.crear()
        self.assertEqual(Stock.query.count(),0)
        self.assertEqual(self.request('/api/apartados/'+r['id']+'/cancelar',dict(empleado='Admin',devolucion=0,motivo='Sin stock',pagos=[])).status_code,200)
        self.assertEqual(Stock.query.count(),0)

    def test_entrega_sin_stock_fecha_persistente(self):
        db.session.delete(self.stock);db.session.commit()
        r=self.crear();url='/api/apartados/'+r['id']
        self.assertIsNone(r['fecha_entrega'])
        self.request(url+'/abonar',dict(empleado='A',monto=150,pagos=[{'metodo':'efectivo','monto':150}]),role='employee')
        fecha=get_cdmx_now()
        with patch('routes_apartados.get_cdmx_now',return_value=fecha):
            res=self.request(url+'/entregar',{'empleado':'A'},role='employee')
        self.assertEqual(res.status_code,200,res.json)
        self.assertEqual(res.json['fecha_entrega'],fecha.isoformat())
        self.assertNotIn('sin_existencias',res.json)
        self.assertEqual(Stock.query.count(),0)
        self.assertEqual(self.request(url+'/entregar',{'empleado':'A'},role='employee').status_code,400)
        admin=self.request('/api/apartados',method='get').json['apartados'][0]
        self.assertTrue(admin['sin_existencias'])
        self.assertEqual(admin['fecha_entrega'],fecha.isoformat())

    def test_entrega_entra_al_corte_una_sola_vez(self):
        from cash_accounting import refresh_cash
        r=self.crear();url='/api/apartados/'+r['id']
        self.assertEqual(Venta.query.count(),0)
        self.request(url+'/abonar',dict(empleado='A',monto=150,pagos=[{'metodo':'transferencia','monto':150}]),role='employee')
        self.assertEqual(Venta.query.count(),0)
        entrega=self.request(url+'/entregar',{'empleado':'A'},role='employee')
        self.assertEqual(entrega.status_code,200,entrega.json)
        cierre=CierreCaja(empleado_id=self.employee.id,sucursal_id=self.branch.id,fecha=get_cdmx_now().date(),estado='abierto')
        db.session.add(cierre);db.session.flush()
        refresh_cash(cierre)
        self.assertEqual(cierre.total_ventas,200)
        self.assertEqual(cierre.total_efectivo,30)
        self.assertEqual(cierre.total_tarjeta,20)
        self.assertEqual(cierre.total_transferencia,150)
        db.session.commit()
        self.assertEqual(self.request(url+'/entregar',{'empleado':'A'},role='employee').status_code,400)
        self.assertEqual(Venta.query.count(),1)
        self.assertEqual((self.stock.cantidad,self.stock.reservado),(3,0))
