# 🚀 Configuración para Deploy en Railway

## ✅ Estado de Configuración

Tu proyecto está **100% listo** para Railway. Aquí está lo que ya está configurado:

### ✓ Archivos de Configuración
- ✅ `Dockerfile` - Optimizado con Python 3.11 slim
- ✅ `railway.json` - Configuración de Railway
- ✅ `docker-entrypoint.sh` - Script de inicialización
- ✅ `gunicorn_config.py` - Servidor WSGI configurado
- ✅ `requirements.txt` - Todas las dependencias actualizadas
- ✅ `.env.example` - Variables de referencia

### ✓ Dependencias de IA
- ✅ `google-genai==0.3.0` - Gemini API actualizada
- ✅ `routes_compatibilidad.py` - Corrección de import (from google import genai)
- ✅ `routes_ayuda.py` - Corrección de import y modelo actualizado
- ✅ Modelos disponibles: `gemini-3.5-flash` con cuota

---

## 📋 Pasos para Deploy en Railway

### Paso 1: Preparar GitHub
```bash
# Ir a tu repositorio local
cd /Users/santiagodelgado/Documents/GitHub/pos/POS-SISTEMA-COMPLETO

# Inicializar git (si no lo has hecho)
git init
git add .
git commit -m "Initial POS System commit"
git branch -M main

# Agregar tu repositorio remoto
git remote add origin https://github.com/TU_USUARIO/pos.git
git push -u origin main
```

### Paso 2: Acceder a Railway
1. Ve a https://railway.app
2. Inicia sesión (crea cuenta si no tienes)
3. Haz clic en "New Project"

### Paso 3: Conectar Repositorio
1. Selecciona "Deploy from GitHub"
2. Conecta tu cuenta de GitHub
3. Selecciona el repositorio `pos`
4. Autoriza a Railway

### Paso 4: Agregar PostgreSQL
1. En el Dashboard del proyecto → "Add"
2. Busca "PostgreSQL" en los plugins
3. Haz clic para agregar
4. Espera 2-3 minutos mientras se provisiona
5. Railway asignará automáticamente `DATABASE_URL`

### Paso 5: Configurar Variables de Entorno
En Railway Dashboard → Settings → Variables, agrega:

```
FLASK_ENV=production
FLASK_APP=app.py
SECRET_KEY=tu_clave_secreta_nueva_y_segura_123456789
JWT_SECRET_KEY=tu_clave_jwt_nueva_y_segura_987654321
TIMEZONE=America/Mexico_City
IA_PROVIDER=gemini
GEMINI_API_KEY=AIzaSy... (tu API key de Google Gemini)
GEMINI_PRIMARY_MODELS=gemini-3.1-flash-lite,gemini-2.5-flash
GEMINI_FALLBACK_MODELS=gemini-2.5-flash-lite,gemini-3.5-flash
```

⚠️ **IMPORTANTE**: 
- `DATABASE_URL` se configura automáticamente cuando agregas PostgreSQL
- NO incluyas el `.env` con datos sensibles en el repositorio
- Usa valores únicos y seguros para `SECRET_KEY` y `JWT_SECRET_KEY`

### Paso 6: Verificar Logs
1. Ve a "Deployments" en tu proyecto
2. Observa los logs durante el build y deploy
3. Busca el mensaje "✅ Sistema listo para recibir tráfico"

---

## 🔑 Variables de Entorno en Detalle

### Variables Automáticas de Railway
```
DATABASE_URL=postgresql://user:password@host:port/dbname
RAILWAY_ENVIRONMENT=production
```

### Variables Requeridas

| Variable | Ejemplo | Descripción |
|----------|---------|-------------|
| `FLASK_ENV` | `production` | Modo de Flask |
| `SECRET_KEY` | `abc123...` | Clave de sesión (generar con: `python -c "import secrets; print(secrets.token_urlsafe())"`) |
| `JWT_SECRET_KEY` | `xyz789...` | Clave JWT (generar con: `python -c "import secrets; print(secrets.token_urlsafe())"`) |
| `GEMINI_API_KEY` | `AIzaSy...` | Clave de Google Gemini |

### Variables Opcionales
```
TIMEZONE=America/Mexico_City           # Tu zona horaria
OPENAI_API_KEY=sk-...                 # Si usas OpenAI
ANTHROPIC_API_KEY=sk-ant-...          # Si usas Anthropic
```

---

## 🔗 Obtener GEMINI_API_KEY

1. Ve a https://ai.google.dev
2. Haz clic en "Get API Key"
3. Crea o selecciona un proyecto
4. Copia la API Key
5. Pega en la variable `GEMINI_API_KEY` en Railway

---

## 🧪 Verificar el Deploy

Una vez que Railway termine el deploy:

### 1. Obtener la URL
- En Railway Dashboard → tu app → "Domains"
- Copia la URL (algo como: `pos-prod-...railway.app`)

### 2. Probar Endpoints
```bash
# Test endpoint público
curl https://pos-prod-...railway.app/health

# Test con autenticación
curl -X POST https://pos-prod-...railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'
```

### 3. Ver Logs
En Railway:
- Dashboard → tu app → "Logs"
- Monitorea en tiempo real

---

## ❌ Solucionar Problemas

### Error: "ModuleNotFoundError: No module named 'google'"
✅ **SOLUCIONADO**: `requirements.txt` está actualizado

### Error: "RESOURCE_EXHAUSTED" (Gemini)
✅ **SOLUCIONADO**: Usando `gemini-3.5-flash` que tiene cuota disponible

### Error: "DATABASE_URL not found"
❌ **Acción**: Asegúrate de haber agregado PostgreSQL en Railway

### Error: "ImportError: from google import genai"
✅ **SOLUCIONADO**: Ambos archivos (routes_compatibilidad.py y routes_ayuda.py) están corregidos

---

## 📊 Monitoreo en Railway

Railway proporciona:
- ✅ Logs en tiempo real
- ✅ Métricas de CPU y memoria
- ✅ Historial de deployments
- ✅ Alertas automáticas
- ✅ Redeploy automático en push a main

---

## 🔄 Actualizar Código

Después del primer deploy, para actualizar tu código:

```bash
git add .
git commit -m "Feature: Nueva funcionalidad"
git push origin main
```

Railway detectará el cambio y iniciará un nuevo deploy automáticamente.

---

## 📞 Soporte

Si necesitas ayuda:
- 📖 Docs de Railway: https://railway.app/docs
- 🐛 Issues: Revisa los logs en Railway Dashboard
- 🔧 Migraciones: Se ejecutan automáticamente en el docker-entrypoint.sh

---

## ✨ Resumen Final

✅ Tu aplicación está 100% lista para Railway
✅ Dockerfile optimizado
✅ Dependencias actualizadas
✅ Variables de entorno documentadas
✅ PostgreSQL listo para provisionar
✅ IA (Gemini) funcionando correctamente

**Próximo paso**: Sigue los 6 pasos de arriba para hacer el deploy. ¡Debería tomar menos de 15 minutos!
