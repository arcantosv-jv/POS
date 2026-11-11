import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import test_operacion_seguimiento as fixtures
from models import db, Categoria
from clasificacion_gemini import vista_previa, aplicar_revision, validar

class GeminiTest(unittest.TestCase):
    setUp = fixtures.OperacionTest.setUp
    tearDown = fixtures.OperacionTest.tearDown

    def respuesta(self, ambiguo=False):
        return [{'codigo': 'P1', 'categoria': 'Audio', 'subcategoria': 'Bluetooth',
                 'ambiguo': ambiguo, 'motivo': 'Audífonos inalámbricos'}]

    def test_preview_inactivos_aprobacion_y_preservacion(self):
        self.product.nombre = 'Airpods 4'
        self.product.is_active = False
        db.session.commit()
        anterior = self.product.subcategoria_id
        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp) / 'revision'
            with patch('clasificacion_gemini.consultar', return_value=self.respuesta()) as call:
                vista_previa(salida)
                self.assertEqual(call.call_args.args[0][0]['nombre'], 'Airpods 4')
            self.assertEqual(self.product.subcategoria_id, anterior)
            self.assertIsNone(Categoria.query.filter_by(nombre='Audio').first())
            aprob = json.loads((salida / 'nuevas.json').read_text())
            self.assertFalse(aprob[0]['aprobada'])
            aprob[0]['aprobada'] = True
            (salida / 'nuevas.json').write_text(json.dumps(aprob))
            aplicar_revision(salida)
            self.assertEqual(self.product.subcategoria.categoria.nombre, 'Audio')
            self.assertEqual(self.product.nombre, 'Airpods 4')
            self.assertEqual(self.product.precio, 100)
            self.assertEqual(self.stock.cantidad, 5)
            self.assertFalse(self.product.is_active)

    def test_sin_aprobacion_no_crea(self):
        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp) / 'revision'
            with patch('clasificacion_gemini.consultar', return_value=self.respuesta()):
                vista_previa(salida)
            aplicar_revision(salida)
            self.assertIsNone(Categoria.query.filter_by(nombre='Audio').first())

    def test_ambiguos_no_cambian(self):
        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp) / 'revision'
            with patch('clasificacion_gemini.consultar', return_value=self.respuesta(True)):
                vista_previa(salida)
            self.assertEqual(json.loads((salida / 'nuevas.json').read_text()), [])
            aplicar_revision(salida)
            self.assertEqual(self.product.subcategoria.nombre, 'Micas')

    def test_rechaza_respuestas_incompletas_o_duplicadas(self):
        for respuesta in ([], self.respuesta() * 2, [{**self.respuesta()[0], 'codigo': 'extra'}]):
            with self.assertRaises(ValueError):
                validar(respuesta, [{'codigo': 'P1'}])

    def test_cambio_concurrente_revierte_categoria_nueva(self):
        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp) / 'revision'
            with patch('clasificacion_gemini.consultar', return_value=self.respuesta()):
                vista_previa(salida)
            aprob = json.loads((salida / 'nuevas.json').read_text())
            aprob[0]['aprobada'] = True
            (salida / 'nuevas.json').write_text(json.dumps(aprob))
            self.product.nombre = 'Otro nombre'; db.session.commit()
            with self.assertRaises(ValueError): aplicar_revision(salida)
            self.assertIsNone(Categoria.query.filter_by(nombre='Audio').first())

    def test_lote_invalido_queda_pendiente(self):
        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp) / 'revision'
            with patch('clasificacion_gemini.consultar', return_value=[]):
                vista_previa(salida)
            aplicar_revision(salida)
            self.assertEqual(self.product.subcategoria.nombre, 'Micas')
            self.assertIn('pendiente', (salida / 'revision.csv').read_text(encoding='utf-8-sig'))
            self.assertTrue((salida / 'lote_0001.json').exists())
