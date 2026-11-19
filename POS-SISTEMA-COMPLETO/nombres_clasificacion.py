"""Renombrado limitado: solo prefijos autorizados y texto original intacto."""
import re
from clasificacion_productos import normalizar


def familia(categoria, subcategoria):
    texto = normalizar(categoria + ' ' + subcategoria)
    mica = bool(re.search(r'\bmicas?\b', texto))
    funda = bool(re.search(r'\bfundas?\b', texto))
    return 'Mica' if mica and not funda else 'Funda' if funda and not mica else None


def candidato(fila):
    original = fila.get('nombre', '')
    prefijo = familia(fila.get('categoria_actual', ''), fila.get('subcategoria_actual', ''))
    # Defensa adicional aunque Gemini marque erróneamente un artículo como modelo.
    if not prefijo or not original or re.search(
        r'\b(micas?|fundas?|cargador\w*|cables?|adaptador\w*|audifono\w*|airpods?|buds|'
        r'bocinas?|tablets?|ipad\w*|watch\w*|reloj\w*|correas?|baterias?|pantallas?|'
        r'display\w*|centros?|pencil|lapiz|soportes?|estuches?|protectores?|celular\w*|telefonos?)\b', normalizar(original)):
        return None
    proposed = prefijo + ' ' + original
    return proposed if len(proposed) <= 255 else None


def propuesta_nombre(fila, respuesta):
    original = fila.get('nombre', '')
    if respuesta.get('ambiguo') or respuesta.get('solo_modelo_celular') is not True:
        return original
    return candidato(fila) or original


def validar_nombre(fila, destino, categoria, subcategoria):
    original = fila['nombre']
    if destino == original:
        return destino
    if not isinstance(destino, str) or destino != candidato(fila):
        raise ValueError('El nombre solo admite el prefijo Mica o Funda sobre el modelo original elegible.')
    if familia(categoria, subcategoria) != familia(fila['categoria_actual'], fila['subcategoria_actual']):
        raise ValueError('El prefijo del nombre debe coincidir con la clasificación propuesta.')
    return destino
