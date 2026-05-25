# Configuración de IA para Compatibilidad

## Google Gemini (Recomendado - Gratis con límites)

### Paso 1: Crear una API Key
1. Ve a [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Haz clic en "Create API Key"
3. Selecciona "Create API key in new project"
4. Copia la API Key

### Paso 2: Configurar en .env
```bash
IA_PROVIDER=gemini
GEMINI_API_KEY=tu_api_key_aqui
```

### Paso 3: Instalar dependencia
```bash
pip install google-generativeai
```

### Ventajas de Gemini:
- ✅ Totalmente gratis (hasta cierto límite de requests)
- ✅ Muy rápido
- ✅ Excelente calidad de respuestas
- ✅ No requiere tarjeta de crédito

---

## Alternativas

### OpenAI (GPT-3.5 / GPT-4)
```bash
IA_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxxxxxxxxx
```
- Requiere pago
- Muy preciso
- Modelo más potente

### Anthropic (Claude)
```bash
IA_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
```
- Requiere pago
- Excelente razonamiento
- Conversaciones muy naturales

---

## Verificar configuración

Para probar tu API Key, usa:

```bash
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
provider = os.getenv('IA_PROVIDER', 'gemini')
print(f'Provider: {provider}')
if provider == 'gemini':
    print(f'API Key configurada: {'✅' if os.getenv('GEMINI_API_KEY') else '❌'}')
"
```

---

## Cambiar entre proveedores

Simplemente edita tu `.env` y reinicia el servidor:

```bash
# De OpenAI a Gemini
IA_PROVIDER=gemini
GEMINI_API_KEY=AIzaSyD...

# De Gemini a OpenAI
IA_PROVIDER=openai
OPENAI_API_KEY=sk-proj-...
```
