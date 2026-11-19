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

    def test_modelo_solo_nombre_csv_y_reaplicacion(self):
        from reclasificar_productos import ejecutar
        self.product.nombre='Samsung A10/A10s';db.session.commit()
        respuesta=[dict(codigo='P1',categoria='Accesorios',subcategoria='Micas',ambiguo=False,solo_modelo_celular=True,motivo='Modelo confirmado, mica actual')]
        with tempfile.TemporaryDirectory() as tmp:
            salida=Path(tmp)/'revision'
            with patch('clasificacion_gemini.consultar',return_value=respuesta): vista_previa(salida)
            self.assertEqual(self.product.nombre,'Samsung A10/A10s')
            import csv
            with (salida/'revision.csv').open(encoding='utf-8-sig') as f: row=list(csv.DictReader(f))[0]
            self.assertEqual(row['nombre_destino'],'Mica Samsung A10/A10s')
            self.assertEqual(row['estado'],'corregir')
            aplicar_revision(salida)
            self.assertEqual(self.product.nombre,'Mica Samsung A10/A10s')
            self.assertEqual(self.product.precio,100);self.assertEqual(self.stock.cantidad,5)
            self.assertEqual(ejecutar(salida/'aprobadas.csv'),[])
            backup=json.loads((salida/'respaldo.json').read_text())['cambios'][0]
            self.assertEqual(backup['nombre'],'Samsung A10/A10s')
            self.assertEqual(backup['nombre_nuevo'],'Mica Samsung A10/A10s')

    def test_prefijos_limitados(self):
        from nombres_clasificacion import propuesta_nombre, validar_nombre
        for categoria,sub,prefijo in [('Micas','Cristal sencilla','Mica'),('Micas','Cerámica','Mica'),('Accesorios','Micas privacidad','Mica'),('Micas','Hidrogel 9D','Mica'),('Fundas','Silicón','Funda')]:
            row=dict(nombre='Samsung A10/A10s',categoria_actual=categoria,subcategoria_actual=sub)
            self.assertEqual(propuesta_nombre(row,dict(ambiguo=False,solo_modelo_celular=True)),prefijo+' Samsung A10/A10s')
            self.assertEqual(propuesta_nombre(row,dict(ambiguo=True,solo_modelo_celular=True)),row['nombre'])
            self.assertEqual(propuesta_nombre(row,dict(ambiguo=False,solo_modelo_celular=False)),row['nombre'])
            with self.assertRaises(ValueError): validar_nombre(row,'Mica Otro modelo',categoria,sub)
        for name in ['Cargador Samsung A10','Mica Samsung A10','Funda Samsung A10','Airpods 4','Tablet Samsung A9','Apple watch s9','Cable A10']:
            row=dict(nombre=name,categoria_actual='Micas',subcategoria_actual='Cristal')
            self.assertEqual(propuesta_nombre(row,dict(ambiguo=False,solo_modelo_celular=True)),name)
