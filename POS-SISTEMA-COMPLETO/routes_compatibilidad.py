"""
Rutas para consultar compatibilidad de accesorios (micas de cristal para celulares)
Integración con IA para recomendaciones inteligentes
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import requests
import json
from dotenv import load_dotenv
import logging

# Configurar logging
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

compatibilidad_bp = Blueprint('compatibilidad', __name__, url_prefix='/api/compatibilidad')


def get_ia_provider():
    """Obtener el proveedor de IA configurado (OpenAI, Anthropic, etc)"""
    provider = os.getenv('IA_PROVIDER', 'gemini').lower()
    return provider


def get_compatibility_recommendation(modelo_celular):
    """
    Obtener recomendación de micas compatibles usando IA
    Con fallback automático a base de datos local si IA falla
    
    Args:
        modelo_celular: str - Modelo del celular (ej: "Motorola G9 Play")
    
    Returns:
        dict - {
            "modelo_solicitado": str,
            "compatibles": [
                {
                    "modelo": str,
                    "marca": str,
                    "razon": str,
                    "nivel_compatibilidad": "alta|media|baja"
                }
            ],
            "notas": str
        }
    """
    
    provider = get_ia_provider()
    result = None
    
    try:
        if provider == 'openai':
            result = _get_openai_recommendation(modelo_celular)
        elif provider == 'anthropic':
            result = _get_anthropic_recommendation(modelo_celular)
        elif provider == 'gemini':
            result = _get_gemini_recommendation(modelo_celular)
        else:
            result = _get_generic_recommendation(modelo_celular)
        
        # Si hay error, usar fallback local
        if result and 'error' in result:
            return _get_generic_recommendation(modelo_celular)
        
        return result
    except Exception as e:
        # Fallback a base de datos local si algo falla
        return _get_generic_recommendation(modelo_celular)


def _get_openai_recommendation(modelo_celular):
    """Usar OpenAI API para obtener recomendaciones"""
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return {
            "error": "OpenAI API Key no configurada",
            "mensaje": "Por favor configura OPENAI_API_KEY en las variables de entorno"
        }
    
    prompt = f"""
Eres un experto en accesorios para celulares, especialmente en micas de cristal templado para protección de pantalla.

Tu tarea es dar recomendaciones de micas COMPATIBLES para el modelo: {modelo_celular}

IMPORTANTE:
- Es común que las micas de un modelo sirvan para otros modelos similares
- Los modelos de la misma marca y generación similar suelen compartir dimensiones
- Considera modelos de diferentes marcas que tengan tamaños de pantalla similares
- Proporciona EXACTAMENTE 10 opciones de micas compatibles (incluye el modelo exacto y 9 alternativas)
- Varía entre compatibilidad alta, media y baja
- Proporciona modelos de diferentes marcas para dar más opciones

FORMATO DE RESPUESTA (JSON):
{{
    "modelo_solicitado": "{modelo_celular}",
    "compatibles": [
        {{
            "modelo": "Nombre exacto del modelo",
            "marca": "Marca",
            "razon": "Por qué es compatible (explicación breve técnica)",
            "nivel_compatibilidad": "alta|media|baja"
        }}
    ],
    "notas": "Advertencias o consideraciones importantes"
}}

Responde SOLO con el JSON, sin explicaciones adicionales. Asegúrate de que el array 'compatibles' tenga EXACTAMENTE 10 elementos.
"""
    
    try:
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.7,
                'max_tokens': 1000
            }
        )
        
        if response.status_code != 200:
            return {
                'error': 'Error en OpenAI API',
                'detalles': response.json()
            }
        
        content = response.json()['choices'][0]['message']['content']
        data = json.loads(content)
        return data
        
    except Exception as e:
        return {'error': f'Error procesando respuesta: {str(e)}'}


def _get_anthropic_recommendation(modelo_celular):
    """Usar Anthropic Claude API para obtener recomendaciones"""
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        return {
            "error": "Anthropic API Key no configurada",
            "mensaje": "Por favor configura ANTHROPIC_API_KEY en las variables de entorno"
        }
    
    prompt = f"""
Eres un experto en accesorios para celulares, especialmente en micas de cristal templado para protección de pantalla.

Tu tarea es dar recomendaciones de micas COMPATIBLES para el modelo: {modelo_celular}

IMPORTANTE:
- Es común que las micas de un modelo sirvan para otros modelos similares
- Los modelos de la misma marca y generación similar suelen compartir dimensiones
- Considera modelos de diferentes marcas que tengan tamaños de pantalla similares
- Proporciona EXACTAMENTE 10 opciones de micas compatibles (incluye el modelo exacto y 9 alternativas)
- Varía entre compatibilidad alta, media y baja
- Proporciona modelos de diferentes marcas para dar más opciones

FORMATO DE RESPUESTA (JSON):
{{
    "modelo_solicitado": "{modelo_celular}",
    "compatibles": [
        {{
            "modelo": "Nombre exacto del modelo",
            "marca": "Marca",
            "razon": "Por qué es compatible (explicación breve técnica)",
            "nivel_compatibilidad": "alta|media|baja"
        }}
    ],
    "notas": "Advertencias o consideraciones importantes"
}}

Responde SOLO con el JSON, sin explicaciones adicionales. Asegúrate de que el array 'compatibles' tenga EXACTAMENTE 10 elementos.
"""
    
    try:
        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json'
            },
            json={
                'model': 'claude-3-haiku-20240307',
                'max_tokens': 1000,
                'messages': [
                    {'role': 'user', 'content': prompt}
                ]
            }
        )
        
        if response.status_code != 200:
            return {
                'error': 'Error en Anthropic API',
                'detalles': response.json()
            }
        
        content = response.json()['content'][0]['text']
        data = json.loads(content)
        return data
        
    except Exception as e:
        return {'error': f'Error procesando respuesta: {str(e)}'}


def _get_gemini_recommendation(modelo_celular):
    """Usar Google Gemini API para obtener recomendaciones"""
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return {
            "error": "Gemini API Key no configurada",
            "mensaje": "Por favor configura GEMINI_API_KEY en las variables de entorno"
        }
    
    prompt = f"""
Eres un experto en accesorios para celulares, especialmente en micas de cristal templado para protección de pantalla.

Tu tarea es dar recomendaciones de micas COMPATIBLES para el modelo: {modelo_celular}

IMPORTANTE:
- Es común que las micas de un modelo sirvan para otros modelos similares
- Los modelos de la misma marca y generación similar suelen compartir dimensiones
- Considera modelos de diferentes marcas que tengan tamaños de pantalla similares
- Proporciona EXACTAMENTE 10 opciones de micas compatibles (incluye el modelo exacto y 9 alternativas)
- Varía entre compatibilidad alta, media y baja
- Proporciona modelos de diferentes marcas para dar más opciones

FORMATO DE RESPUESTA (JSON):
{{
    "modelo_solicitado": "{modelo_celular}",
    "compatibles": [
        {{
            "modelo": "Nombre exacto del modelo",
            "marca": "Marca",
            "razon": "Por qué es compatible (explicación breve técnica)",
            "nivel_compatibilidad": "alta|media|baja"
        }}
    ],
    "notas": "Advertencias o consideraciones importantes"
}}

Responde SOLO con el JSON, sin explicaciones adicionales. Asegúrate de que el array 'compatibles' tenga EXACTAMENTE 10 elementos.
"""
    
    try:
        from google import genai
        
        # Usar la nueva API de google.genai
        client = genai.Client(api_key=api_key)
        
        # Usar modelo disponible (gemini-3.5-flash con cuota disponible)
        
        modelo_gemini = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

        response = client.models.generate_content(
            model=modelo_gemini,
            contents=prompt
        )
        logger.info(f"[GEMINI] Solicitando recomendación para modelo")
        logger.info(f"[GEMINI] Respuesta recibida")

        content = response.text.strip()

        if content.startswith("```json"):
            content = content.replace("```json", "", 1).replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()

        data = json.loads(content)
        logger.info(f"[GEMINI] ✅ Éxito - Datos JSON válidos")
        return data
        
    except ImportError as e:
        logger.error(f"[GEMINI] ❌ Import Error: {str(e)}")
        return {
            'error': 'Google Genai no instalado',
            'mensaje': 'Ejecuta: pip install google-genai'
        }
    except json.JSONDecodeError as e:
        logger.error(f"[GEMINI] ❌ JSON Error: {str(e)}")
        logger.error(f"[GEMINI] Contenido recibido: {content[:200]}")
        return {
            'error': 'Respuesta de Gemini no es JSON válido',
            'mensaje': 'Intenta de nuevo o contacta al administrador'
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[GEMINI] ❌ Error: {error_msg}")
        logger.error(f"[GEMINI] Tipo: {type(e).__name__}")
        
        if '429' in error_msg or 'quota' in error_msg.lower():
            return {
                'error': 'Límite de cuota alcanzado',
                'mensaje': 'Has alcanzado el límite de solicitudes. Intenta más tarde',
                'detalles': error_msg[:100]
            }
        return {
            'error': f'Error en Gemini: {error_msg[:100]}', 
            'tipo': type(e).__name__
        }


def _get_generic_recommendation(modelo_celular):
    """Fallback: Respuesta local sin IA (para testing)"""
    
    # Diccionario simple de compatibilidades comunes
    compatibilidades_base = {
        'motorola g9 play': {
            'compatibles': [
                {
                    'modelo': 'Motorola G9 Play',
                    'marca': 'Motorola',
                    'razon': 'Modelo exacto - dimensiones 6.5" con notch en gota',
                    'nivel_compatibilidad': 'alta'
                },
                {
                    'modelo': 'Motorola Moto G Power (2021)',
                    'marca': 'Motorola',
                    'razon': 'Mismo tamaño de pantalla 6.5" y bisel similar',
                    'nivel_compatibilidad': 'alta'
                },
                {
                    'modelo': 'Motorola G8 Play',
                    'marca': 'Motorola',
                    'razon': 'Generación anterior, dimensiones muy similares',
                    'nivel_compatibilidad': 'alta'
                },
                {
                    'modelo': 'Samsung Galaxy A11',
                    'marca': 'Samsung',
                    'razon': 'Pantalla 6.5" con dimensiones similares',
                    'nivel_compatibilidad': 'media'
                },
                {
                    'modelo': 'Samsung Galaxy A12',
                    'marca': 'Samsung',
                    'razon': 'Pantalla 6.5" con mismo tamaño',
                    'nivel_compatibilidad': 'media'
                },
                {
                    'modelo': 'Redmi Note 9',
                    'marca': 'Xiaomi',
                    'razon': 'Pantalla 6.53" con biseles comparables',
                    'nivel_compatibilidad': 'media'
                },
                {
                    'modelo': 'Redmi Note 10',
                    'marca': 'Xiaomi',
                    'razon': 'Pantalla 6.5" con marco similar',
                    'nivel_compatibilidad': 'media'
                },
                {
                    'modelo': 'TCL 30',
                    'marca': 'TCL',
                    'razon': 'Pantalla 6.5" con dimensiones compatibles',
                    'nivel_compatibilidad': 'media'
                },
                {
                    'modelo': 'Oppo A15',
                    'marca': 'Oppo',
                    'razon': 'Pantalla 6.5" con bisel estándar',
                    'nivel_compatibilidad': 'baja'
                },
                {
                    'modelo': 'Vivo Y12',
                    'marca': 'Vivo',
                    'razon': 'Pantalla 6.5" con dimensiones aproximadas',
                    'nivel_compatibilidad': 'baja'
                }
            ],
            'notas': 'Verifica siempre las dimensiones exactas antes de instalar. Las micas de compatibilidad media/baja pueden tener pequeños espacios en los bordes.'
        }
    }
    
    modelo_normalizado = modelo_celular.lower().strip()
    
    if modelo_normalizado in compatibilidades_base:
        data = compatibilidades_base[modelo_normalizado]
        data['modelo_solicitado'] = modelo_celular
        return data
    else:
        return {
            'modelo_solicitado': modelo_celular,
            'compatibles': [
                {
                    'modelo': modelo_celular,
                    'marca': 'Desconocida',
                    'razon': 'Modelo exacto - siempre la mejor opción',
                    'nivel_compatibilidad': 'alta'
                }
            ],
            'notas': 'No tenemos información detallada de este modelo. Por favor configura una API de IA (OpenAI o Anthropic) para obtener recomendaciones más precisas.'
        }


def _ajustar_compatibilidad_por_notch(recomendaciones):
    """
    Post-procesamiento: Si solo difiere el notch (gota o V), elevar la compatibilidad a media mínimo
    
    Detecta en la razón si solo el notch es diferente y ajusta el nivel de baja a media.
    """
    if not recomendaciones or 'compatibles' not in recomendaciones:
        return recomendaciones
    
    for mica in recomendaciones.get('compatibles', []):
        razon = (mica.get('razon', '') or '').lower()
        
        # Palabras clave que indican que solo el notch es diferente
        palabras_clave_notch = [
            'notch', 'gota', 'v-notch', 'pantalla sin notch',
            'diferencia notch', 'solo notch', 'solo diferencia es notch',
            'único cambio', 'cambio solo'
        ]
        
        # Si la razón menciona notch y el nivel es baja, elevar a media
        tiene_notch_mention = any(palabra in razon for palabra in palabras_clave_notch)
        
        if tiene_notch_mention and mica.get('nivel_compatibilidad') == 'baja':
            # Elevamos a media porque el notch no afecta la compatibilidad física
            mica['nivel_compatibilidad'] = 'media'
            # Actualizar también la razón para reflejar el ajuste
            if 'notch' in razon:
                mica['razon'] += ' ✓ Ajustada a media (notch no afecta la instalación de mica)'
    
    return recomendaciones


@compatibilidad_bp.route('/buscar', methods=['POST'])
@jwt_required()
def buscar_compatibilidad():
    """
    Buscar micas compatibles para un modelo de celular
    
    Body:
        {
            "modelo_celular": "Motorola G9 Play"
        }
    """
    
    try:
        data = request.get_json()
        
        if not data.get('modelo_celular'):
            return jsonify({'error': 'modelo_celular es requerido'}), 400
        
        modelo = data['modelo_celular'].strip()
        
        if len(modelo) < 2:
            return jsonify({'error': 'modelo_celular debe tener al menos 2 caracteres'}), 400
        
        # Obtener recomendaciones
        recomendaciones = get_compatibility_recommendation(modelo)
        
        if 'error' in recomendaciones:
            return jsonify(recomendaciones), 503
        
        # Post-procesamiento: Ajustar compatibilidad cuando solo difiere el notch
        recomendaciones = _ajustar_compatibilidad_por_notch(recomendaciones)
        
        return jsonify({
            'exito': True,
            'datos': recomendaciones
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Error inesperado: {str(e)}'}), 500


@compatibilidad_bp.route('/historial', methods=['GET'])
@jwt_required()
def historial_consultas():
    """Obtener historial de consultas del usuario (opcional)"""
    try:
        user_id = get_jwt_identity()
        # TODO: Implementar guardado de historial en BD si es necesario
        return jsonify({
            'mensaje': 'Historial de consultas - función no implementada aún'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
