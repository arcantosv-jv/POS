import unittest
from datetime import datetime
import test_operacion_seguimiento as fixtures
from models import db, Categoria, Subcategoria, Producto, Venta, DetalleVenta, Sucursal
from routes_reportes import reportes_bp
from config import CDMX_TZ

class CategoriasTest(unittest.TestCase):
    request = fixtures.OperacionTest.request
    tearDown = fixtures.OperacionTest.tearDown

    def setUp(self):
        fixtures.OperacionTest.setUp(self)
        self.client.application.register_blueprint(reportes_bp)
        self.employee.permisos = {'reportes': ['ver']}
        self.employee.sucursales_permitidas = [self.branch.id]
        self.extra = Sucursal(nombre='Otra', direccion='Otra'); db.session.add(self.extra); db.session.flush()
        for i in range(11):
            cat = Categoria(nombre=f'Cat {i:02d}'); db.session.add(cat); db.session.flush()
            sub = Subcategoria(nombre='Sub', categoria_id=cat.id); db.session.add(sub); db.session.flush()
            p = Producto(codigo=f'CAT{i}', nombre='Producto', precio=999, subcategoria_id=sub.id)
            db.session.add(p); db.session.flush()
            v = Venta(numero_venta=f'CAT{i}', sucursal_id=self.branch.id, cajero_id=self.employee.id,
                      total=22*(i+1), forma_pago='mixto', created_at=CDMX_TZ.localize(datetime(2026,11,5,23,59)))
            v.detalles.append(DetalleVenta(producto_id=p.id, cantidad=2, precio_unitario=10*(i+1), impuesto_unitario=i+1, subtotal=20*(i+1)))
            db.session.add(v)
        v = Venta(numero_venta='EXTRA', sucursal_id=self.extra.id, cajero_id=self.employee.id,
                  total=9999, forma_pago='efectivo', created_at=CDMX_TZ.localize(datetime(2026,11,5,12)))
        v.detalles.append(DetalleVenta(producto_id=self.product.id, cantidad=1, precio_unitario=9999, impuesto_unitario=0, subtotal=9999))
        db.session.add(v); db.session.commit()
        self.url='/api/reportes/ventas-categorias?fecha_inicio=2026-11-05&fecha_fin=2026-11-05'

    def test_ranking_ten_historical_price_tax_and_scope(self):
        res=self.request(self.url,role='employee',method='get')
        self.assertEqual(res.status_code,200,res.json)
        rows=res.json['categorias']; self.assertEqual(len(rows),10)
        self.assertEqual(rows[0]['nombre'],'Cat 10')
        self.assertEqual(rows[0]['total'],242)
        self.assertEqual(rows[0]['cantidad'],2)
        self.assertNotIn('Cat 00',[r['nombre'] for r in rows])
        res=self.request(self.url,method='get')
        self.assertEqual(res.json['categorias'][0]['total'],9999)
        res=self.request(self.url+'&sucursal_id='+self.branch.id,method='get')
        self.assertEqual(res.json['categorias'][0]['total'],242)
        self.assertEqual(self.request(self.url+'&sucursal_id='+self.extra.id,role='employee',method='get').status_code,403)

    def test_validation_empty_and_permissions(self):
        self.assertEqual(self.request('/api/reportes/ventas-categorias?fecha_inicio=2026-11-06&fecha_fin=2026-11-05',method='get').status_code,400)
        self.assertEqual(self.request(self.url.replace('2026-11-05','2026-11-06'),method='get').json['categorias'],[])
        self.employee.permisos={}; db.session.commit()
        self.assertEqual(self.request(self.url,role='employee',method='get').status_code,403)

    def test_orden_cantidad_se_aplica_antes_del_limite(self):
        detalle = DetalleVenta.query.join(Venta).filter(Venta.numero_venta == 'CAT0').one()
        detalle.cantidad = 50
        detalle.precio_unitario = 0.1
        detalle.impuesto_unitario = 0
        detalle.subtotal = 5
        db.session.commit()
        por_importe = self.request(self.url, role='employee', method='get').json['categorias']
        self.assertNotIn('Cat 00', [r['nombre'] for r in por_importe])
        respuesta = self.request(self.url + '&orden=cantidad', role='employee', method='get')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json['orden'], 'cantidad')
        filas = respuesta.json['categorias']
        self.assertEqual(len(filas), 10)
        self.assertEqual(filas[0]['nombre'], 'Cat 00')
        self.assertEqual(filas[0]['cantidad'], 50)
        self.assertEqual(filas[1]['nombre'], 'Cat 10')
        self.assertEqual(self.request(self.url + '&orden=invalido', method='get').status_code, 400)
