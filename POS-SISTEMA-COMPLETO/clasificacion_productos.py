"""Reglas conservadoras por nombre; no deducir categorías de códigos o stock."""
import re
import unicodedata


def normalizar(texto):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', texto.lower())
                           if not unicodedata.combining(c)).split())


def proponer(nombre):
    n = normalizar(nombre)
    # Los accesorios para otro artículo no son el artículo en sí.
    if re.search(r'\b(funda|estuche|protector|cable|adaptador|repuesto)\b.*\b(audifono|audifonos|airpods|bocina)\b', n):
        return None
    reglas = [
        (r'^fundas?\b', ('Fundas', 'Funda')),
        (r'^adaptador\b', ('Adaptadores', 'Adaptadores')),
        (r'^baston\s+selfie\b', ('Soportes', 'Bastón Selfie')),
        (r'^bocinas?\b', ('Audio', 'Bocinas')),
        (r'^transmisor\s+bluetooth\b', ('Audio', 'Transmisor Bluetooth')),
    ]
    for patron, destino in reglas:
        if re.search(patron, n):
            return destino
    if re.match(r'^audifonos?\b', n):
        if re.search(r'\b(bluetooth|bluethoot|inalambricos?|airpods|buds|tws)\b', n):
            return ('Audifonos', 'Audifonos Bluetooth')
        if re.search(r'\b(cable|jack|usb|tipo c)\b|3[.,]5', n):
            return ('Audifonos', 'Audifonos Cable')
    # No inferir el tipo de mica a partir del modelo del teléfono.
    return None
