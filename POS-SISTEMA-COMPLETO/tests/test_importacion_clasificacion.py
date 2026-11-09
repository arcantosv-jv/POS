import csv
import tempfile
import unittest
from pathlib import Path
import test_operacion_seguimiento as fixtures
from models import db, Categoria, Subcategoria, Producto
from routes_importar import importar_bp
from reclasificar_productos import CAMPOS, ejecutar

class ClasificacionTest(unittest.TestCase):
    request = fixtures.OperacionTest.request
    tearDown = fixtures.OperacionTest.tearDown

    def setUp(self):
        fixtures.OperacionTest.setUp(self)
        self.client.application.register_blueprint(importar_bp)
        cat = Categoria(nombre='Audifonos')
        db.session.add(cat); db.session.flush()
        self.destino = Subcategoria(nombre='Bluetooth', categoria_id=cat.id)
        db.session.add(self.destino); db.session.commit()

    def test_reimportar_corrige_clasificacion(self):
        response = self.request('/api/productos/importar', {'productos': [{
            'codigo': self.product.codigo, 'nombre': self.product.nombre,
            'categoria': 'Audifonos', 'subcategoria': 'Bluetooth'}]})
        self.assertEqual(response.json['errores'], [])
        self.assertEqual(db.session.get(Producto, self.product.id).subcategoria_id, self.destino.id)
        response = self.request('/api/productos/importar', {'productos': [{
            'codigo': self.product.codigo, 'nombre': self.product.nombre, 'precio': 150}]})
        self.assertEqual(response.json['errores'], [])
        self.assertEqual(db.session.get(Producto, self.product.id).subcategoria_id, self.destino.id)

    def test_script_preview_apply_idempotent_and_stale(self):
        anterior = self.product.subcategoria_id
        precio, stock = self.product.precio, self.stock.cantidad
        with tempfile.TemporaryDirectory() as folder:
            archivo = Path(folder) / 'plan.csv'
            with archivo.open('w', newline='') as f:
                w = csv.DictWriter(f, fieldnames=CAMPOS); w.writeheader()
                w.writerow({'codigo': self.product.codigo, 'nombre': self.product.nombre,
                    'subcategoria_id_actual': anterior, 'categoria_destino': 'Audifonos', 'subcategoria_destino': 'Bluetooth'})
            self.assertEqual(len(ejecutar(archivo)), 1)
            self.assertEqual(self.product.subcategoria_id, anterior)
            ejecutar(archivo, True, Path(folder) / 'backup.json')
            self.assertEqual(self.product.subcategoria_id, self.destino.id)
            self.assertEqual(self.product.precio, precio)
            self.assertEqual(self.stock.cantidad, stock)
            self.assertEqual(ejecutar(archivo), [])
            self.product.subcategoria_id = anterior; db.session.commit()
            contenido = archivo.read_text().replace(anterior, 'incorrecto')
            archivo.write_text(contenido)
            with self.assertRaises(ValueError): ejecutar(archivo, True, Path(folder) / 'otro.json')
            self.assertEqual(self.product.subcategoria_id, anterior)

    def test_automatico_corrige_solo_clasificacion_y_no_repite(self):
        from reclasificar_productos import automatizar
        cat = Categoria(nombre='Fundas')
        db.session.add(cat); db.session.flush()
        sub = Subcategoria(nombre='Funda', categoria_id=cat.id)
        db.session.add(sub); db.session.flush()
        self.product.nombre = 'Funda iPhone 15'
        self.product.subcategoria_id = self.destino.id
        db.session.commit()
        nombre, precio, stock = self.product.nombre, self.product.precio, self.stock.cantidad
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(len(automatizar(Path(folder) / 'simular')), 1)
            self.assertEqual(self.product.subcategoria_id, self.destino.id)
            self.assertEqual(len(automatizar(Path(folder) / 'aplicar', True)), 1)
            self.assertEqual(self.product.subcategoria_id, sub.id)
            self.assertEqual((self.product.nombre, self.product.precio, self.stock.cantidad), (nombre, precio, stock))
            self.assertEqual(automatizar(Path(folder) / 'repetir', True), [])
            self.assertTrue((Path(folder) / 'aplicar' / 'respaldo.json').exists())
