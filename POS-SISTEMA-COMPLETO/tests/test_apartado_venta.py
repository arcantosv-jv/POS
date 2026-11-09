import unittest
from decimal import Decimal
import test_operacion_seguimiento as fixtures
from models import db, Apartado, PagoVenta
from apartado_venta import registrar_venta_entrega
from config import get_cdmx_now

class ApartadoVentaTest(unittest.TestCase):
    tearDown = fixtures.OperacionTest.tearDown
    setUp = fixtures.OperacionTest.setUp

    def apartado(self, metodos):
        return Apartado(id='apartado-test', sucursal_id=self.branch.id, total=200, abonado=200,
            productos=[dict(producto_id=self.product.id, cantidad=2, precio='100')],
            movimientos=[dict(tipo='creacion', pagos=[dict(metodo=metodos[0], monto='50')]),
                         dict(tipo='abonar', pagos=[dict(metodo=metodos[1], monto='150')])])

    def test_mixto_con_precios_acordados_sin_descontar_stock(self):
        self.product.precio=999
        venta=registrar_venta_entrega(self.apartado(['efectivo','tarjeta']),self.employee.id)
        self.assertEqual(venta.forma_pago,'mixto')
        self.assertEqual({p.metodo_pago:p.monto for p in PagoVenta.query.all()}, {'efectivo':50,'tarjeta':150})
        self.assertEqual(venta.total,200)
        self.assertEqual(venta.detalles[0].precio_unitario,100)
        self.assertEqual(self.stock.cantidad,5)
        self.assertEqual(venta.created_at.date(),get_cdmx_now().date())

    def test_unico_metodo_agrega_abonos(self):
        venta=registrar_venta_entrega(self.apartado(['transferencia','transferencia']),self.employee.id)
        self.assertEqual(venta.forma_pago,'transferencia')
        self.assertEqual(PagoVenta.query.one().monto,200)

    def test_rechaza_desglose_inconsistente(self):
        apartado=self.apartado(['efectivo','tarjeta']);apartado.total=300
        with self.assertRaises(ValueError): registrar_venta_entrega(apartado,self.employee.id)
