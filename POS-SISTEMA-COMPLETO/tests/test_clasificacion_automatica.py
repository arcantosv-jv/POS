import unittest
from clasificacion_productos import proponer

class ReglasTest(unittest.TestCase):
    def test_casos_claros(self):
        for nombre, destino in [
            ('Audífonos BLUETHOOT', ('Audifonos', 'Audifonos Bluetooth')),
            ('Audífonos Sport Bluetooth Con Cable', ('Audifonos', 'Audifonos Bluetooth')),
            ('Audífono tipo C', ('Audifonos', 'Audifonos Cable')),
            ('Bastón selfie Bluetooth', ('Soportes', 'Bastón Selfie')),
            ('Funda a07', ('Fundas', 'Funda')),
            ('Adaptador micro SD a usb', ('Adaptadores', 'Adaptadores'))]:
            self.assertEqual(proponer(nombre), destino)

    def test_no_adivinar(self):
        for nombre in ['Bauma', 'Mica Samsung a20', 'Samsung A10', 'Audífonos Sony',
                       'Funda para AirPods', 'Adaptador para audífonos', 'Cable para bocina']:
            self.assertIsNone(proponer(nombre))
