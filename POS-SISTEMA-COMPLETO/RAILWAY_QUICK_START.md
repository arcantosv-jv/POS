🚀 POS SISTEMA - LISTO PARA RAILWAY
=====================================

## ⚡ Quick Start (5 minutos)

### 1️⃣ Preparar GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/tu-usuario/pos.git
git push -u origin main
```

### 2️⃣ Crear en Railway
- Ir a https://railway.app
- Nuevo proyecto → Conectar GitHub
- Seleccionar repositorio `pos`
- Railway detecta Dockerfile automáticamente

### 3️⃣ Agregar PostgreSQL
- Dashboard → Add → PostgreSQL plugin
- Esperar 2-3 minutos mientras se provisiona

### 4️⃣ Variables de Entorno (¡IMPORTANTE!)
En Railway → Settings → Variables:

```
FLASK_ENV=production
FLASK_APP=app.py
SECRET_KEY=genera_una_clave_aleatoria_muy_larga_minimo_32_caracteres
JWT_SECRET_KEY=genera_otra_clave_aleatoria_muy_larga_minimo_32_caracteres
TIMEZONE=America/Mexico_City
ENVIRONMENT=production
IA_PROVIDER=gemini
GEMINI_API_KEY=tu_google_api_key
```

DATABASE_URL se agrega automáticamente cuando agregues PostgreSQL ✓

### 5️⃣ Deploy
- Railway redeploya automáticamente desde GitHub
- Ver logs: `railway logs --follow`
- Tu app en: `https://tu-proyecto.railway.app`

---

## 📁 Estructura de Archivos

```
✓ Dockerfile              → Imagen Docker optimizada para Railway
✓ Procfile               → Define cómo ejecutar la app
✓ railway.json           → Configuración de Railway
✓ docker-entrypoint.sh   → Script de inicialización
✓ gunicorn_config.py     → Configuración de Gunicorn
✓ .dockerignore          → Optimizar tamaño de imagen
✓ validate-railway.sh    → Validar antes de deployar
✓ DEPLOYMENT_RAILWAY.md  → Guía completa de deployment
✓ RAILWAY_CHECKLIST.md   → Checklist paso a paso
✓ DATABASE_SCHEMA.md     → Schema de base de datos
```

---

## 🔍 Verificación Rápida

```bash
# Validar todo está listo
bash validate-railway.sh

# Si algo falla, revisar:
# 1. requirements.txt tiene todas las dependencias
# 2. Dockerfile está en la raíz del proyecto
# 3. .env NO está en git (usar .env.example)
# 4. migrations/ tiene los archivos
```

---

## 📚 Documentación

1. **DEPLOYMENT_RAILWAY.md** - Guía completa (45 min)
2. **RAILWAY_CHECKLIST.md** - Checklist paso a paso (20 min)
3. **DATABASE_SCHEMA.md** - Schema de BD y migraciones

---

## ⚠️ Cosas Importantes

❌ NO hacer esto:
- No cambiar PORT en Railway (se configura automáticamente)
- No subir `.env` a GitHub (solo `.env.example`)
- No perder las SECRET_KEY y JWT_SECRET_KEY (guardar en lugar seguro)

✅ SI hacer esto:
- Usar contraseñas muy seguras (min 32 caracteres aleatorios)
- Revisar logs después de deployar
- Hacer backup de datos antes de cambios mayores
- Usar dominio personalizado para producción

---

## 🆘 Si Algo Falla

1. Ver logs: `railway logs`
2. Buscar error específico
3. Revisar RAILWAY_CHECKLIST.md sección "Troubleshooting"
4. Revisar DEPLOYMENT_RAILWAY.md para soluciones detalladas

---

## 💡 Próximos Pasos

1. ✅ Deployar en Railway (HOY)
2. ⏳ Configurar dominio personalizado
3. ⏳ Agregar users de producción
4. ⏳ Configurar backups automáticos
5. ⏳ Monitorear y optimizar

---

## 📞 Links Útiles

- Railway Docs: https://docs.railway.app
- Railway Status: https://status.railway.app
- PostgreSQL Docs: https://www.postgresql.org/docs/
- Flask Docs: https://flask.palletsprojects.com/
- Gunicorn: https://gunicorn.org/

---

**🎉 ¡Listo para despegar!**

Sigue RAILWAY_CHECKLIST.md para un deployment seguro y sin errores.
