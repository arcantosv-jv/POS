# 🚀 GUÍA DE DEPLOYMENT EN RAILWAY

## Requisitos Previos

1. **Cuenta en Railway**: https://railway.app
2. **GitHub**: Repositorio con el código
3. **PostgreSQL**: Railway lo proporciona
4. **API Keys**: Gemini, OpenAI (opcional)

---

## 📋 Paso 1: Preparar Repositorio

```bash
# Asegurar que el código está en GitHub
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/tu-usuario/pos.git
git push -u origin main
```

---

## 🔑 Paso 2: Variables de Entorno Necesarias

En Railway, establece estas variables en **Project Settings > Variables**:

### Base de Datos (Railway crea automáticamente)
```
DATABASE_URL=postgresql://usuario:password@host:puerto/dbname
```

### Aplicación
```
FLASK_ENV=production
FLASK_APP=app.py
SECRET_KEY=tu_clave_secreta_muy_segura_minimo_32_caracteres
JWT_SECRET_KEY=tu_clave_jwt_muy_segura_minimo_32_caracteres
PORT=8000
ENVIRONMENT=production
TIMEZONE=America/Mexico_City
```

### IA (Compatibilidad)
```
IA_PROVIDER=gemini
GEMINI_API_KEY=tu_api_key_de_google
```

Opcionalmente (si usas otros proveedores):
```
OPENAI_API_KEY=sk-xxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
```

---

## 🐳 Paso 3: Conectar en Railway

### Opción A: Via Railway CLI (Recomendado)

```bash
# 1. Instalar Railway CLI
npm i -g @railway/cli

# 2. Login
railway login

# 3. Inicializar proyecto
railway init

# 4. Seleccionar GitHub repo
# Railway detectará automáticamente el Dockerfile

# 5. Agregar base de datos PostgreSQL
railway add --service postgresql

# 6. Deploy
railway up
```

### Opción B: Via Web Dashboard

1. Ir a https://railway.app/dashboard
2. Crear nuevo proyecto
3. Conectar GitHub repo
4. Railway detecta Dockerfile automáticamente
5. Agregar PostgreSQL plugin
6. Configurar variables de entorno
7. Deploy automático

---

## ✅ Paso 4: Verificar Deployment

```bash
# Ver logs
railway logs

# Ver status
railway status

# Ver variables
railway variables

# Acceder a la app
https://tu-proyecto.railway.app
```

---

## 🔧 Paso 5: Configurar Dominio Personalizado (Opcional)

1. En Railway Dashboard → Settings → Domains
2. Agregar dominio personalizado
3. Seguir instrucciones de DNS

---

## 📊 Arquitectura en Railway

```
┌─────────────────────────────┐
│   Railway Project           │
├─────────────────────────────┤
│ Frontend (Static)           │
│ - index.html                │
│ - components.js             │
│ - app.js                    │
│ - CSS                       │
├─────────────────────────────┤
│ Backend (Flask + Gunicorn)  │
│ - app.py                    │
│ - routes_*.py               │
│ - models.py                 │
├─────────────────────────────┤
│ PostgreSQL Database         │
│ - Tablas (usuarios, etc)    │
│ - Migraciones (Alembic)     │
└─────────────────────────────┘
```

---

## 🐛 Troubleshooting

### Error: "Build failed"
- Verificar que `Dockerfile` está en la raíz
- Verificar `requirements.txt` está actualizado
- Ver logs: `railway logs --failed`

### Error: "Connection refused to PostgreSQL"
- Verificar que PostgreSQL plugin está agregado
- Esperar 2-3 minutos después de agregar BD
- Revisar `DATABASE_URL` está correcta

### Error: "ModuleNotFoundError"
- Ejecutar: `pip install -r requirements.txt`
- Asegurar que todas las dependencias están en requirements.txt
- Verificar: `pip list | grep -E "flask|sqlalchemy|google"`

### Error: "Static files not found"
- Verificar que `static/` tiene los archivos
- Flask sirve automáticamente desde `static/`
- Verificar rutas en `app.py`

### Base de datos vacía
- Migraciones se ejecutan automáticamente (ver `Procfile`)
- Si no se ejecutan: `railway run flask db upgrade`
- Verificar: `railway run flask db current`

---

## 📈 Monitoreo y Logs

```bash
# Ver logs en tiempo real
railway logs --follow

# Ver solo errores
railway logs --error

# Ejecutar comando en Railway
railway run python3 -c "import app; print('OK')"

# Ver consumo de recursos
railway status
```

---

## 💾 Backup y Base de Datos

```bash
# Conectar a PostgreSQL en Railway
railway run psql

# Exportar datos
railway run pg_dump > backup.sql

# Ver tablas
railway run psql -c "\dt"
```

---

## 🔄 Actualizaciones y Redeploy

```bash
# Hacer cambios locales
git add .
git commit -m "Update feature"

# Push a GitHub (Railway redeploya automáticamente)
git push origin main

# O forzar redeploy
railway redeploy
```

---

## 📞 Soporte

- Railway Docs: https://docs.railway.app
- Railway Community: https://railway.app/community
- Status: https://status.railway.app

---

## ✨ Tips para Producción

1. **Seguridad**
   - Cambiar todas las contraseñas/secrets
   - Usar variables de entorno para todo sensible
   - Habilitar SSL (Railway lo hace automáticamente)

2. **Rendimiento**
   - Gunicorn con 4-8 workers
   - PostgreSQL con índices en campos clave
   - Caché de estáticos con CDN

3. **Monitoreo**
   - Revisar logs regularmente
   - Configurar alertas
   - Hacer backups periódicos

4. **Escalabilidad**
   - Aumentar memory si es necesario
   - Usar múltiples replicas
   - Agregar Redis para caching

---

**¡Tu app está lista para producción! 🚀**
