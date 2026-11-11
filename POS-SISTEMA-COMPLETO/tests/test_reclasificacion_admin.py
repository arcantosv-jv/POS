import unittest
from unittest.mock import patch
import test_operacion_seguimiento as fixtures
from models import db, Categoria, Subcategoria, RevisionClasificacion, Producto
from routes_reclasificacion import reclasificacion_bp


class ReclasificacionAdminTest(unittest.TestCase):
    request = fixtures.OperacionTest.request
    tearDown = fixtures.OperacionTest.tearDown

    def setUp(self):
        fixtures.OperacionTest.setUp(self)
        self.client.application.register_blueprint(reclasificacion_bp)
        c = Categoria(nombre='Audio')
        db.session.add(c); db.session.flush()
        self.destino = Subcategoria(nombre='Bluetooth', categoria_id=c.id)
        db.session.add(self.destino); db.session.commit()
        self.base = '/api/reclasificacion'

    def crear(self):
        response = self.request(self.base, {})
        self.assertEqual(response.status_code, 201)
        return response.json

    def accion(self, revision, accion, **data):
        return self.request(self.base + '/' + revision['id'] + '/' + accion,
                            {'version': revision['version'], **data})

    def procesar(self, revision, ambiguo=False, nueva=False):
        respuesta = [{'codigo': self.product.codigo, 'categoria': 'Bisutería' if nueva else 'Audio',
                      'subcategoria': 'Aretes' if nueva else 'Bluetooth', 'ambiguo': ambiguo, 'motivo': 'Prueba'}]
        with patch('routes_reclasificacion.consultar', return_value=respuesta):
            result = self.accion(revision, 'procesar')
        self.assertEqual(result.status_code, 200)
        return result.json

    def test_exclusivo_admin_y_catalogo_global_inactivos(self):
        self.assertEqual(self.request(self.base, {}, role='employee').status_code, 403)
        self.assertEqual(self.request(self.base, role='employee', method='get').status_code, 403)
        self.product.is_active = False; db.session.commit()
        r = self.crear()
        self.assertEqual(r['total'], 1)
        self.assertEqual(r['filas'][0]['id'], self.product.id)
        self.assertEqual(self.request(self.base + '/' + r['id'] + '/aplicar', {'version': r['version']}, role='employee').status_code, 403)

    def test_ambiguo_solo_se_aplica_tras_editar_y_no_toca_otros_campos(self):
        antes = self.product.subcategoria_id
        r = self.procesar(self.crear(), ambiguo=True)
        self.assertEqual(r['resumen'], {'pendiente': 1})
        r = self.accion(r, 'aplicar').json
        self.assertEqual(self.product.subcategoria_id, antes)
        r = self.accion(r, 'editar', producto_id=self.product.id, subcategoria_id=self.destino.id).json
        self.assertTrue(r['filas'][0]['editada'])
        r = self.accion(r, 'aplicar').json
        self.assertEqual(self.product.subcategoria_id, self.destino.id)
        self.assertEqual((self.product.nombre, self.product.precio, self.stock.cantidad), ('Mica', 100, 5))
        self.assertEqual(r['filas'][0]['subcategoria_id_actual'], antes)
        self.assertEqual(self.accion(r, 'aplicar').json['resumen'], {'aplicado': 1})

    def test_nueva_requiere_aprobacion_antes_de_crear(self):
        r = self.procesar(self.crear(), nueva=True)
        self.assertEqual(r['resumen'], {'nueva': 1})
        r = self.accion(r, 'aplicar').json
        self.assertIsNone(Categoria.query.filter_by(nombre='Bisutería').first())
        r = self.accion(r, 'aprobar', categoria='Bisutería', subcategoria='Aretes').json
        self.assertIsNone(Categoria.query.filter_by(nombre='Bisutería').first())
        r = self.accion(r, 'aplicar').json
        self.assertEqual(r['resumen'], {'aplicado': 1})
        self.assertEqual(self.product.subcategoria.categoria.nombre, 'Bisutería')

    def test_automatico_editable_y_version_concurrente(self):
        r = self.procesar(self.crear())
        self.assertEqual(r['resumen'], {'listo': 1})
        original = self.product.subcategoria_id
        nuevo = self.accion(r, 'editar', producto_id=self.product.id, subcategoria_id=original).json
        self.assertEqual(nuevo['resumen'], {'correcto': 1})
        self.assertEqual(self.accion(r, 'aplicar').status_code, 409)
        self.assertEqual(self.product.subcategoria_id, original)

    def test_persistencia_y_error_ia_reintentable(self):
        r = self.crear()
        with patch('routes_reclasificacion.consultar', side_effect=ValueError('sin cuota')):
            self.assertEqual(self.accion(r, 'procesar').status_code, 400)
        db.session.remove()
        r = self.request(self.base + '/' + r['id'], method='get').json
        self.assertFalse(r['ocupado'])
        self.assertEqual(r['resumen'], {'sin_revisar': 1})
        # Evitar usar objetos separados de la sesión en el helper.
        with patch('routes_reclasificacion.consultar', return_value=[{'codigo': 'P1', 'categoria': 'Audio', 'subcategoria': 'Bluetooth', 'ambiguo': False, 'motivo': ''}]):
            self.assertEqual(self.accion(r, 'procesar').json['resumen'], {'listo': 1})

    def test_lote_invalido_no_sobrescribe_avance(self):
        r = self.crear()
        with patch('routes_reclasificacion.consultar', return_value=[]):
            self.assertEqual(self.accion(r, 'procesar').status_code, 400)
        r = self.request(self.base + '/' + r['id'], method='get').json
        self.assertEqual(r['procesados'], 0)
        self.assertFalse(r['ocupado'])

    def test_cambio_producto_cancela_toda_transaccion(self):
        # El primer producto debe crear un destino; el segundo falla después.
        self.product.id = 'a'
        segundo = Producto(id='z', codigo='P2', nombre='Otro', precio=20, subcategoria_id=self.product.subcategoria_id)
        db.session.add(segundo); db.session.commit()
        r = self.crear()
        for p in (self.product, segundo):
            r = self.accion(r, 'editar', producto_id=p.id, categoria='Nueva', subcategoria='Nueva').json
        r = self.accion(r, 'aprobar', categoria='Nueva', subcategoria='Nueva').json
        segundo.nombre = 'Modificado'; db.session.commit()
        response = self.accion(r, 'aplicar')
        self.assertEqual(response.status_code, 409)
        self.assertIsNone(Categoria.query.filter_by(nombre='Nueva').first())
        self.assertEqual(self.product.subcategoria.categoria.nombre, 'Accesorios')
        self.assertEqual(db.session.get(RevisionClasificacion, r['id']).filas[0]['estado'], 'listo')

    def test_edicion_manual_nueva_tambien_necesita_aprobacion(self):
        r = self.procesar(self.crear(), ambiguo=True)
        r = self.accion(r, 'editar', producto_id=self.product.id, categoria='Nueva', subcategoria='Otra').json
        self.assertEqual(r['resumen'], {'nueva': 1})
        r = self.accion(r, 'aplicar').json
        self.assertIsNone(Categoria.query.filter_by(nombre='Nueva').first())

    def test_lease_impide_doble_lote_y_edicion(self):
        import time
        r = self.crear()
        model = db.session.get(RevisionClasificacion, r['id'])
        model.token_lote = 'otro'; model.bloqueado_hasta = time.time() + 60; db.session.commit()
        self.assertEqual(self.accion(r, 'procesar').status_code, 409)
        self.assertEqual(self.accion(r, 'editar', producto_id=self.product.id, subcategoria_id=self.destino.id).status_code, 409)
        model.bloqueado_hasta = 0; db.session.commit()
        self.assertEqual(self.procesar(r)['resumen'], {'listo': 1})
