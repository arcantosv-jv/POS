"""
Rutas para consultar compatibilidad de accesorios (micas de cristal para celulares)
Integración con IA para recomendaciones inteligentes
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, ConsultaCompatibilidad, CompatibilidadVerificada
from business_validation import text_value
from config import get_cdmx_now
from datetime import timedelta
import unicodedata
import os
import requests
import json
import time
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


def _is_transient_ia_error(error_msg):
    """Detecta errores temporales donde conviene reintentar o cambiar de modelo."""
    error_msg = (error_msg or '').lower()
    transient_markers = [
        '503',
        'unavailable',
        'high demand',
        'overloaded',
        'temporarily',
        'timeout',
        '429',
        'quota',
        'rate limit'
    ]
    return any(marker in error_msg for marker in transient_markers)


def _get_gemini_model_candidates():
    """Modelos Gemini a intentar, en orden de preferencia."""
    preferred_models = [
        model.strip()
        for model in os.getenv(
            'GEMINI_PRIMARY_MODELS',
            'gemini-3.1-flash-lite,gemini-2.5-flash'
        ).split(',')
        if model.strip()
    ]
    configured_models = os.getenv(
        'GEMINI_FALLBACK_MODELS',
        os.getenv('GEMINI_MODEL', '')
    )
    fallback_models = ['gemini-2.5-flash-lite', 'gemini-3.5-flash']
    models = preferred_models

    for model in configured_models.split(','):
        model = model.strip()
        if model and model not in models:
            models.append(model)

    for model in fallback_models:
        if model not in models:
            models.append(model)

    return models


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
                    "nivel_compatibilidad": "alta|media|baja"
                }
            ],
            "notas": str
        }
    """
    
    provider = get_ia_provider()
    try:
        if provider == 'openai':
            result = _get_openai_recommendation(modelo_celular)
        elif provider == 'anthropic':
            result = _get_anthropic_recommendation(modelo_celular)
        elif provider == 'gemini':
            result = _get_gemini_recommendation(modelo_celular)
        else:
            result = None
        if not isinstance(result, dict) or 'error' in result:
            result = _get_generic_recommendation(modelo_celular)
            result['_origen'] = 'base_local'
        else:
            result['_origen'] = 'ia'
        return result
    except Exception:
        result = _get_generic_recommendation(modelo_celular)
        result['_origen'] = 'base_local'
        return result


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
- Considera modelos recientes y de hasta 2 años anteriores de la misma marca de un tamaño similar, por ejemplo al Samsung S25 FE le queda excelente el Samsung A37 y viceversa, aunque sean de diferente gama
- Considera principalmente modelos del mismo o un año anterior
- Considera modelos de diferentes marcas que tengan tamaños de pantalla similares aunque tengan más de dos años de haber salido el modelo de otra marca
- Considera que la mica de iPhone 11 también le queda al iPhone 12 y viceversa
- Considera la mica de huawei y9 prime compatible con muchos modelos aunque tengan diferencia de tiempo de lanzamiento
- Considera que la mica de Samsung A80 le queda a muchos modelos, al igual que motorola g9 plus, por sus dimensiones y forma de pantalla
- Considera que las dimensiones no varien mucho, por ejemplo a un iphone 12 de 6.1", un iPhone 11 pro de 5.8" tiene de diferencia .3, lo que es mucho para adaptarla, queda mejor la del iPhone 11
- Considera que las dimensiones de pantalla son más importantes que la marca, y que 6.1 y 6.2 son muy similares, por lo que la mica de un modelo de 6.1 le queda a uno de 6.2 y viceversa
- Considera que al oppo reno 7 4g le queda bien motorola g31
- Proporciona EXACTAMENTE 10 opciones de micas compatibles (incluye el modelo exacto y 9 alternativas)
- Varía entre compatibilidad alta, media y baja
- Proporciona modelos de diferentes marcas para dar más opciones
- Considera modelos de marcas comerciales populares en Latinoamérica (Samsung, Motorola, Apple, Oppo, Huawei) para mayor relevancia 
- Omite modelos de marcas no comerciales como vivo, realme, etc que no son comunes en la región
- Omite el modelo solicitado en las recomendaciones, solo incluye alternativas compatibles
- Para modelos curvos, considera solo micas curvas, para modelos planos solo micas planas, por ejemplo, al s25 ultra no le puede quedar la del s23 ultra porque el s23 ultra es curvo

FORMATO DE RESPUESTA (JSON):
{{
    "modelo_solicitado": "{modelo_celular}",
    "compatibles": [
        {{
            "modelo": "Nombre exacto del modelo",
            "marca": "Marca",
            "nivel_compatibilidad": "alta|media|baja"
        }}
    ],
    "notas": "Advertencias o consideraciones importantes"
}}

Responde SOLO con el JSON, sin explicaciones adicionales. Asegúrate de que el array 'compatibles' tenga EXACTAMENTE 10 elementos.
"""
    
    try:
        from google import genai
        from google.genai import types
        
        # Usar la nueva API de google.genai
        client = genai.Client(api_key=api_key)
        max_retries = int(os.getenv('GEMINI_MAX_RETRIES', '2'))
        max_output_tokens = int(os.getenv('GEMINI_MAX_OUTPUT_TOKENS', '4096'))
        generation_config = types.GenerateContentConfig(
            response_mime_type='application/json',
            max_output_tokens=max_output_tokens,
            temperature=0.4
        )
        last_error = None
        content = ''

        for modelo_gemini in _get_gemini_model_candidates():
            for intento in range(1, max_retries + 1):
                try:
                    logger.info(
                        f"[GEMINI] Solicitando recomendación con {modelo_gemini} "
                        f"(intento {intento}/{max_retries})"
                    )
                    response = client.models.generate_content(
                        model=modelo_gemini,
                        contents=prompt,
                        config=generation_config
                    )
                    logger.info(f"[GEMINI] Respuesta recibida de {modelo_gemini}")

                    content = response.text.strip()

                    if content.startswith("```json"):
                        content = content.replace("```json", "", 1).replace("```", "").strip()
                    elif content.startswith("```"):
                        content = content.replace("```", "").strip()

                    data = json.loads(content)
                    logger.info(f"[GEMINI] ✅ Éxito con {modelo_gemini} - Datos JSON válidos")
                    return data
                except json.JSONDecodeError as json_error:
                    last_error = json_error
                    logger.warning(f"[GEMINI] JSON inválido con {modelo_gemini}: {str(json_error)}")
                    logger.warning(f"[GEMINI] Contenido recibido: {content[:300]}")

                    if intento < max_retries:
                        time.sleep(2 ** (intento - 1))
                    continue
                except Exception as model_error:
                    last_error = model_error
                    error_msg = str(model_error)
                    logger.warning(f"[GEMINI] Error con {modelo_gemini}: {error_msg[:200]}")

                    if not _is_transient_ia_error(error_msg):
                        break

                    if intento < max_retries:
                        time.sleep(2 ** (intento - 1))

        raise last_error
        
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
                    # 'razon': 'Modelo exacto - dimensiones 6.5" con notch en gota',
                    'nivel_compatibilidad': 'alta'
                },
                {
                    'modelo': 'Motorola Moto G Power (2021)',
                    'marca': 'Motorola',
                    # 'razon': 'Mismo tamaño de pantalla 6.5" y bisel similar',
                    'nivel_compatibilidad': 'alta'
                },
                {
                    'modelo': 'Motorola G8 Play',
                    'marca': 'Motorola',
                    # 'razon': 'Generación anterior, dimensiones muy similares',
                    'nivel_compatibilidad': 'alta'
                },
                {
                    'modelo': 'Samsung Galaxy A11',
                    'marca': 'Samsung',
                    # 'razon': 'Pantalla 6.5" con dimensiones similares',
                    'nivel_compatibilidad': 'media'
                },
                {
                    'modelo': 'Samsung Galaxy A12',
                    'marca': 'Samsung',
                    # 'razon': 'Pantalla 6.5" con mismo tamaño',
                    'nivel_compatibilidad': 'media'
                },
                {
                    'modelo': 'Redmi Note 9',
                    'marca': 'Xiaomi',
                    # 'razon': 'Pantalla 6.53" con biseles comparables',
                    'nivel_compatibilidad': 'media'
                },
                {
                    'modelo': 'Redmi Note 10',
                    'marca': 'Xiaomi',
                    # 'razon': 'Pantalla 6.5" con marco similar',
                    'nivel_compatibilidad': 'media'
                },
                {
                    'modelo': 'TCL 30',
                    'marca': 'TCL',
                    # 'razon': 'Pantalla 6.5" con dimensiones compatibles',
                    'nivel_compatibilidad': 'media'
                },
                {
                    'modelo': 'Oppo A15',
                    'marca': 'Oppo',
                    # 'razon': 'Pantalla 6.5" con bisel estándar',
                    'nivel_compatibilidad': 'baja'
                },
                {
                    'modelo': 'Vivo Y12',
                    'marca': 'Vivo',
                    # 'razon': 'Pantalla 6.5" con dimensiones aproximadas',
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
                    # 'razon': 'Modelo exacto - siempre la mejor opción',
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


def _eliminar_razones(recomendaciones):
    """Excluir la razón aunque el proveedor de IA la incluya en su respuesta."""
    if not recomendaciones or 'compatibles' not in recomendaciones:
        return recomendaciones

    for mica in recomendaciones.get('compatibles', []):
        mica.pop('razon', None)

    return recomendaciones


def normalizar_modelo(value):
    return ' '.join(unicodedata.normalize('NFKC', text_value(value, 'Modelo', 200, True)).casefold().split())


def resultados_actuales(modelo, resultado):
    confirmed = CompatibilidadVerificada.query.filter_by(modelo=modelo, activa=True).order_by(CompatibilidadVerificada.mica).all()
    user = db.session.get(User, get_jwt_identity())
    items = [{**row.to_dict(), 'puede_retirar': user.role == 'admin' or row.usuario_id == user.id} for row in confirmed]
    names = {row.mica for row in confirmed}
    for item in resultado.get('compatibles', []):
        name = normalizar_modelo(item.get('modelo', ''))
        if name not in names:
            items.append({'modelo': item['modelo'], 'marca': item.get('marca', ''),
                          'nivel_compatibilidad': item.get('nivel_compatibilidad', 'media'), 'verificada': False})
            names.add(name)
    return {'modelo_solicitado': modelo, 'compatibles': items, 'notas': resultado.get('notas', '')}


def validar_resultado_ia(result):
    if not isinstance(result, dict) or not isinstance(result.get('compatibles'), list):
        raise ValueError('El proveedor devolvió un resultado de compatibilidad inválido')
    items = []
    for item in result['compatibles'][:30]:
        if not isinstance(item, dict):
            continue
        name = text_value(item.get('modelo', ''), 'Modelo compatible', 200, True)
        level = item.get('nivel_compatibilidad', 'media')
        items.append({'modelo': name, 'marca': text_value(item.get('marca', ''), 'Marca', 100),
                      'nivel_compatibilidad': level if level in ('alta', 'media', 'baja') else 'media'})
    return {'compatibles': items, 'notas': text_value(result.get('notas', '') or '', 'Notas', 10000)}


@compatibilidad_bp.route('/buscar', methods=['POST'])
@jwt_required()
def buscar_compatibilidad():
    try:
        data = request.get_json() or {}
        modelo = normalizar_modelo(data.get('modelo_celular', ''))
        if len(modelo) < 2:
            raise ValueError('Ingresa al menos dos caracteres')
        refresh = data.get('actualizar_ia') is True
        confirmed = CompatibilidadVerificada.query.filter_by(modelo=modelo, activa=True).first()
        cached = ConsultaCompatibilidad.query.filter(
            ConsultaCompatibilidad.modelo == modelo,
            ConsultaCompatibilidad.origen.in_(['ia', 'base_local']),
            ConsultaCompatibilidad.created_at >= get_cdmx_now() - timedelta(days=30)
        ).order_by(ConsultaCompatibilidad.created_at.desc()).first()
        if confirmed and not refresh:
            result, origin = {'compatibles': [], 'notas': 'Consulta la condición de verificación de cada opción.'}, 'verificadas'
        elif cached and not refresh:
            result, origin = cached.resultado, 'historial'
        else:
            response = get_compatibility_recommendation(modelo)
            if 'error' in response:
                return jsonify(response), 503
            result, origin = validar_resultado_ia(response), response.get('_origen', 'ia')
        result = resultados_actuales(modelo, result)
        consulta = ConsultaCompatibilidad(usuario_id=get_jwt_identity(), modelo=modelo, resultado=result, origen=origin)
        db.session.add(consulta)
        db.session.commit()
        return jsonify({'exito': True, 'datos': result, 'origen': origin, 'consulta_id': consulta.id}), 200
    except ValueError as error:
        db.session.rollback()
        return jsonify({'error': str(error)}), 400
    except Exception:
        db.session.rollback()
        logger.exception('Error consultando compatibilidad')
        return jsonify({'error': 'No se pudo completar la consulta de compatibilidad'}), 500


@compatibilidad_bp.route('/historial', methods=['GET'])
@jwt_required()
def historial_consultas():
    user = db.session.get(User, get_jwt_identity())
    query = ConsultaCompatibilidad.query
    if user.role != 'admin':
        query = query.filter_by(usuario_id=user.id)
    search = request.args.get('modelo', '').strip()
    if search:
        query = query.filter(ConsultaCompatibilidad.modelo.contains(search.casefold(), autoescape=True))
    page = max(1, request.args.get('page', 1, type=int))
    result = query.order_by(ConsultaCompatibilidad.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    items = []
    for row in result.items:
        item = row.to_dict()
        # Mostrar verificaciones vigentes aunque se abra una consulta anterior.
        item['resultado'] = resultados_actuales(row.modelo, row.resultado)
        items.append(item)
    return jsonify({'consultas': items, 'pages': result.pages, 'page': page, 'total': result.total})


@compatibilidad_bp.route('/verificadas', methods=['POST'])
@jwt_required()
def verificar_compatibilidad():
    try:
        user = db.session.get(User, get_jwt_identity())
        if user.role not in ('admin', 'employee'):
            return jsonify({'error': 'Acceso denegado'}), 403
        data = request.get_json() or {}
        if data.get('confirmada') is not True:
            raise ValueError('Confirma que comprobaste físicamente esta compatibilidad')
        modelo = normalizar_modelo(data.get('modelo_celular', ''))
        mica = normalizar_modelo(data.get('mica', ''))
        notas = text_value(data.get('notas', ''), 'Resultado de la comprobación', 2000, True)
        marca = text_value(data.get('marca', ''), 'Marca', 100)
        row = CompatibilidadVerificada.query.filter_by(modelo=modelo, mica=mica).first()
        if row and row.usuario_id != user.id and user.role != 'admin':
            return jsonify({'error': 'Solo quien verificó esta compatibilidad o un administrador puede cambiarla'}), 403
        if not row:
            row = CompatibilidadVerificada(modelo=modelo, mica=mica)
            db.session.add(row)
        row.notas, row.marca, row.usuario_id, row.activa = notas, marca, user.id, True
        db.session.commit()
        return jsonify(row.to_dict()), 200
    except ValueError as error:
        db.session.rollback()
        return jsonify({'error': str(error)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'No se pudo guardar la verificación; vuelve a consultar e intenta nuevamente'}), 409


@compatibilidad_bp.route('/verificadas/<registro_id>', methods=['DELETE'])
@jwt_required()
def retirar_verificacion(registro_id):
    user = db.session.get(User, get_jwt_identity())
    row = db.session.get(CompatibilidadVerificada, registro_id)
    if not row:
        return jsonify({'error': 'Verificación no encontrada'}), 404
    if user.role != 'admin' and row.usuario_id != user.id:
        return jsonify({'error': 'Solo quien verificó esta compatibilidad o un administrador puede retirarla'}), 403
    row.activa = False
    db.session.commit()
    return jsonify({'message': 'Verificación retirada'})
