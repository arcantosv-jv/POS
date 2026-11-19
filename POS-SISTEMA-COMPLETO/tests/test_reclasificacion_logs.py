import unittest
from unittest.mock import patch, Mock
import requests
from reclasificacion_logs import registrar_error
from clasificacion_gemini import consultar


class ReclasificacionLogsTest(unittest.TestCase):
    def test_error_real_sin_clave_ni_producto(self):
        response = Mock(status_code=429)
        response.json.return_value = {'error': {'status': 'RESOURCE_EXHAUSTED', 'message': 'Quota exceeded key=secreto Producto privado'}}
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'secreto'}), self.assertLogs('reclasificacion', level='ERROR') as logs:
            registrar_error(requests.HTTPError('429'), etapa='consulta_web', respuesta=response,
                modelo='modelo', revision='rev', lote='lote', productos=[{'nombre':'Producto privado', 'codigo':'P1'}])
        text = logs.output[0]
        self.assertIn('http=429', text)
        self.assertIn('RESOURCE_EXHAUSTED', text)
        self.assertIn('Quota exceeded', text)
        self.assertNotIn('secreto', text)
        self.assertNotIn('Producto privado', text)

    def test_reintentos_registran_error_original(self):
        with patch.dict('os.environ', {'GEMINI_API_KEY':'secreto'}), patch('requests.post', side_effect=requests.Timeout('Read timed out')), patch('routes_compatibilidad._get_gemini_model_candidates', return_value=['modelo1','modelo2']), self.assertLogs('reclasificacion', level='ERROR') as logs:
            with self.assertRaises(ValueError): consultar([], [], web=True, revision='rev', lote='lote')
        self.assertEqual(len(logs.output), 2)
        self.assertIn('tipo=Timeout', logs.output[0])
        self.assertIn('Read timed out', logs.output[0])
        self.assertIn('revision=rev lote=lote', logs.output[1])
