"""Diagnóstico de lotes sin volcar solicitudes, respuestas completas ni credenciales."""
import logging
import os
import re
import traceback

logger = logging.getLogger('reclasificacion')


def registrar_error(error, *, etapa, modelo=None, revision=None, lote=None, productos=(), respuesta=None):
    mensaje = str(error)
    status = getattr(respuesta, 'status_code', None)
    codigo = None
    if respuesta is not None:
        try:
            detalle = respuesta.json().get('error', {})
            if isinstance(detalle, dict):
                codigo = detalle.get('status')
                mensaje = detalle.get('message') or mensaje
        except (ValueError, AttributeError, TypeError):
            pass
    secretos = [os.getenv('GEMINI_API_KEY', '')]
    for producto in productos:
        secretos.extend(str(producto.get(k, '')) for k in ('nombre', 'codigo'))
    def limpiar(value):
        text = str(value or '')
        for secreto in sorted(filter(None, secretos), key=len, reverse=True):
            text = text.replace(secreto, '[oculto]')
        text = re.sub(r'(?i)(key|token|authorization|password)([=:\s]+)[^\s&,;]+', r'\1\2[oculto]', text)
        return text.replace('\n', ' ').replace('\r', ' ')[:1500]
    # Ubicación del fallo sin texto fuente, variables locales ni excepción sin filtrar.
    ubicacion = ' > '.join(f'{os.path.basename(f.filename)}:{f.lineno}:{f.name}'
                           for f in traceback.extract_tb(error.__traceback__)[-5:])
    logger.error('Fallo reclasificacion etapa=%s revision=%s lote=%s modelo=%s productos=%d '
                 'tipo=%s http=%s codigo=%s detalle=%s ubicacion=%s',
                 etapa, revision or '-', lote or '-', limpiar(modelo), len(productos),
                 type(error).__name__, status or '-', limpiar(codigo), limpiar(mensaje), ubicacion)
