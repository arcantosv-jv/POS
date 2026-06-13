"""
Rutas para el módulo de Ayuda
Integración con IA para proporcionar soluciones de troubleshooting de dispositivos
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
from google import genai
from dotenv import load_dotenv
import logging

# Configurar logging
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

ayuda_bp = Blueprint('ayuda', __name__, url_prefix='/api/ayuda')

# Configurar API de Google Generative AI (google-genai)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai_client = None
if GEMINI_API_KEY:
    genai_client = genai.Client(api_key=GEMINI_API_KEY)

GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash')

CATEGORY_MAP = {
    'formateo': 'Formateo',
    'gmail': 'Gmail',
    'icloud': 'iCloud',
    'bateria': 'Bateria',
    'otro': 'Otro',
}


def get_device_os_info(modelo):
    """
    Determinar el tipo de dispositivo y la versión de SO más reciente
    
    Args:
        modelo: str - Modelo del dispositivo (ej: "iPhone 13", "Samsung Galaxy S24")
    
    Returns:
        dict - {"os": "iOS|Android", "version": "X", "modelo": "..."}
    """
    modelo_lower = modelo.lower()
    
    # Detectar tipo de dispositivo
    if 'iphone' in modelo_lower:
        # Extraer número de iPhone (13, 14, 15, 16, 17, etc)
        import re
        match = re.search(r'iphone\s*(\d+)', modelo_lower)
        if match:
            iphone_number = int(match.group(1))
            # iOS 17 = iPhone 15, iOS 18 = iPhone 16, iOS 26 = iPhone 17
            ios_version = str(17 + max(0, iphone_number - 15))
        else:
            ios_version = '18'  # Default
        
        return {
            'os': 'iOS',
            'version': ios_version,
            'modelo_tipo': 'iPhone'
        }
    
    elif any(keyword in modelo_lower for keyword in ['samsung', 'galaxy']):
        return {
            'os': 'Android',
            'version': '15',
            'modelo_tipo': 'Samsung Galaxy'
        }
    
    elif 'pixel' in modelo_lower:
        return {
            'os': 'Android',
            'version': '15',
            'modelo_tipo': 'Google Pixel'
        }
    
    elif 'xiaomi' in modelo_lower or 'poco' in modelo_lower or 'redmi' in modelo_lower:
        return {
            'os': 'Android',
            'version': '15',
            'modelo_tipo': 'Xiaomi'
        }
    
    else:
        # Default para Android
        return {
            'os': 'Android',
            'version': '15',
            'modelo_tipo': 'Android Device'
        }


def get_solution_from_ai(modelo, categoria, version_so, requerimiento_especifico):
    """
    Generar solución usando Google Generative AI (Gemini)
    
    Args:
        modelo: str - Modelo del dispositivo
        categoria: str - Categoría del problema (Formateo, Gmail, iCloud, Batería, Otro)
        version_so: str - Versión de SO (opcional)
        requerimiento_especifico: str - Descripción específica si categoria='Otro'
    
    Returns:
        dict - {"solucion": "texto de la solución", "error": None/str}
    """
    
    if not GEMINI_API_KEY:
        return {
            "solucion": None,
            "error": "No hay clave API de Google configurada. Contacta al administrador."
        }
    
    try:
        # Obtener información del dispositivo
        device_info = get_device_os_info(modelo)
        
        # Usar versión de SO proporcionada o la detectada
        version_so_final = version_so if version_so else device_info['version']
        
        # Construir prompt según categoría
        if categoria == 'Formateo':
            prompt = f"""
Tu eres un experto técnico en dispositivos móviles.

El usuario tiene un {device_info['modelo_tipo']} modelo: {modelo}
Sistema operativo: {device_info['os']} {version_so_final}

El usuario necesita: FORMATEAR EL DISPOSITIVO

Proporciona una guía detallada paso a paso para formatear este dispositivo.
Incluye:
1. Precauciones importantes antes de formatear
2. Pasos precisos para hacer backup
3. Instrucciones claras para realizar el formateo
4. Qué esperar después del formateo

Mantén la respuesta técnica pero accesible.
"""
        elif categoria == 'Gmail':
            prompt = f"""
Tu eres un experto técnico en dispositivos móviles.

El usuario tiene un {device_info['modelo_tipo']} modelo: {modelo}
Sistema operativo: {device_info['os']} {version_so_final}

El usuario necesita: CREAR/CONFIGURAR UNA CUENTA DE GMAIL

Proporciona una guía detallada paso a paso para crear o configurar una cuenta de Gmail en este dispositivo.
Incluye:
1. Verificación de requisitos
2. Pasos exactos para crear o agregar cuenta
3. Solución de problemas comunes
4. Verificación de 2 factores si aplica

Mantén la respuesta técnica pero accesible.
"""
        elif categoria == 'iCloud':
            prompt = f"""
Tu eres un experto técnico en dispositivos móviles.

El usuario tiene un {device_info['modelo_tipo']} modelo: {modelo}
Sistema operativo: {device_info['os']} {version_so_final}

El usuario necesita: CREAR/CONFIGURAR UNA CUENTA DE ICLOUD

Proporciona una guía detallada paso a paso para crear o configurar una cuenta de iCloud en este dispositivo.
Incluye:
1. Requisitos previos
2. Pasos exactos para crear o agregar cuenta
3. Validación de identidad
4. Configuración de seguridad

Mantén la respuesta técnica pero accesible.
"""
        elif categoria == 'Bateria':
            prompt = f"""
Tu eres un experto técnico en dispositivos móviles.

El usuario tiene un {device_info['modelo_tipo']} modelo: {modelo}
Sistema operativo: {device_info['os']} {version_so_final}

El usuario necesita: REVISAR EL ESTADO DE LA BATERÍA

Proporciona una guía detallada para revisar el estado de la batería en este dispositivo.
Incluye:
1. Dónde encontrar información de batería
2. Qué significa cada métrica
3. Cómo interpretar el estado de salud de la batería
4. Recomendaciones si la batería está degradada
5. Consejos para maximizar la vida de la batería

Mantén la respuesta técnica pero accesible.
"""
        else:  # 'Otro'
            prompt = f"""
Tu eres un experto técnico en dispositivos móviles.

El usuario tiene un {device_info['modelo_tipo']} modelo: {modelo}
Sistema operativo: {device_info['os']} {version_so_final}

El usuario tiene el siguiente problema o requerimiento:
{requerimiento_especifico}

Proporciona una solución detallada y paso a paso para resolver esto.
Incluye:
1. Diagnóstico del problema
2. Soluciones recomendadas en orden de probabilidad
3. Pasos específicos para implementar cada solución
4. Cuándo contactar soporte técnico

Mantén la respuesta técnica pero accesible.
"""
        
        # Llamar a Google Generative AI con fallback de modelos
        modelos_intentos = [GEMINI_MODEL, 'gemini-3.5-flash']
        respuesta_obtenida = False
        ultimo_error = None
        
        if not genai_client:
            logger.error("Cliente de Google Generative AI no configurado")
            raise Exception("No hay clave API de Google configurada")
        
        for modelo_intento in modelos_intentos:
            try:
                logger.info(f"Intentando con modelo: {modelo_intento}")
                response = genai_client.models.generate_content(
                    model=modelo_intento,
                    contents=prompt,
                )
                respuesta_obtenida = True
                logger.info(f"✓ Respuesta obtenida con modelo: {modelo_intento}")
                break
            except Exception as model_error:
                logger.warning(f"Error con modelo {modelo_intento}: {str(model_error)}")
                ultimo_error = model_error
                continue
        
        if not respuesta_obtenida:
            logger.error(f"No se pudo obtener respuesta con ningún modelo. Último error: {str(ultimo_error)}")
            raise ultimo_error
        
        solucion = response.text if response and response.text else "No se pudo generar una solución"
        
        return {
            "solucion": solucion,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Error en generación de solución: {str(e)}", exc_info=True)
        return {
            "solucion": None,
            "error": f"Error generando solución: {str(e)}"
        }


@ayuda_bp.route('/obtener-solucion', methods=['POST'])
@jwt_required()
def obtener_solucion():
    """
    Endpoint para obtener solución de troubleshooting con IA
    
    Request body:
    {
        "modelo": "iPhone 13",  # requerido
        "categoria": "Formateo|Gmail|iCloud|Bateria|Otro",  # requerido
        "version_so": "iOS 17",  # opcional
        "requerimiento_especifico": "..."  # requerido si categoria="Otro"
    }
    """
    
    try:
        _user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        # Validar datos requeridos
        modelo = data.get('modelo', '').strip()
        categoria = data.get('categoria', '').strip().lower()
        version_so = data.get('version_so', '').strip()
        requerimiento_especifico = data.get('requerimiento_especifico', '').strip()
        
        # Validaciones
        if not modelo:
            return jsonify({"error": "El modelo es requerido"}), 400
        
        if not categoria or categoria not in CATEGORY_MAP:
            return jsonify({"error": "Categoría no válida"}), 400

        categoria_normalizada = CATEGORY_MAP[categoria]
        
        if categoria_normalizada == 'Otro' and not requerimiento_especifico:
            return jsonify({"error": "Debe proporcionar detalles en 'requerimiento_especifico' cuando elige 'Otro'"}), 400
        
        # Generar solución
        resultado = get_solution_from_ai(
            modelo=modelo,
            categoria=categoria_normalizada,
            version_so=version_so,
            requerimiento_especifico=requerimiento_especifico
        )
        
        if resultado['error']:
            return jsonify({"error": resultado['error']}), 500
        
        return jsonify({
            "solucion": resultado['solucion'],
            "dispositivo": {
                "modelo": modelo,
                "categoria": categoria_normalizada,
                "version_so": version_so or "Automática"
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error en obtener_solucion: {str(e)}")
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500
