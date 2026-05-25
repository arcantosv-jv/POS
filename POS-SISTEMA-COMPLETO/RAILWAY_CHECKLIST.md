📋 CHECKLIST DE DEPLOYMENT - RAILWAY

## ✅ Fase 1: Preparación Local (Ejecutar en tu máquina)

- [ ] Clonar/actualizar repositorio
- [ ] Ejecutar `pip install -r requirements.txt`
- [ ] Crear `.env` local con variables de prueba
- [ ] Ejecutar `flask db upgrade` localmente
- [ ] Probar app: `python3 app.py`
- [ ] Verificar endpoints clave:
  - [ ] GET `/api/productos`
  - [ ] POST `/api/auth/login`
  - [ ] GET `http://localhost:5000` (frontend)
- [ ] Ejecutar validación: `bash validate-railway.sh`
- [ ] Revisar logs locales para errores

---

## ✅ Fase 2: Preparación GitHub

- [ ] Crear repositorio en GitHub
- [ ] `git init && git add .`
- [ ] `git commit -m "Initial commit"`
- [ ] `git remote add origin https://github.com/tu-usuario/pos.git`
- [ ] `git branch -M main`
- [ ] `git push -u origin main`
- [ ] Verificar que todos los archivos están en GitHub
- [ ] Verificar que `.env` NO está en el repo (solo `.env.example`)
- [ ] `.gitignore` incluye: `.env`, `__pycache__`, `*.db`, `venv/`

---

## ✅ Fase 3: Crear Proyecto en Railway

- [ ] Crear cuenta en https://railway.app
- [ ] Crear nuevo proyecto
- [ ] Conectar GitHub
- [ ] Seleccionar repositorio `pos`
- [ ] Railway detecta `Dockerfile` automáticamente
- [ ] Ver progreso del build inicial

---

## ✅ Fase 4: Configurar Base de Datos

- [ ] En Railway Dashboard: Add Plugin → PostgreSQL
- [ ] Esperar que PostgreSQL se provisione (2-3 minutos)
- [ ] Copiar `DATABASE_URL` (Railway la crea automáticamente)
- [ ] Verificar que aparece en Variables: `DATABASE_URL`
- [ ] **NO necesitas crear tablas manualmente** (migraciones las crean)

---

## ✅ Fase 5: Variables de Entorno (CRÍTICO)

En Railway Dashboard → Settings → Variables, añadir:

**Seguridad:**
```
FLASK_ENV=production
FLASK_APP=app.py
SECRET_KEY=usa_una_clave_aleatoria_muy_larga_minimo_32_caracteres
JWT_SECRET_KEY=usa_otra_clave_aleatoria_muy_larga_minimo_32_caracteres
```

**Aplicación:**
```
TIMEZONE=America/Mexico_City
ENVIRONMENT=production
PORT=8000
```

**IA (Compatibilidad):**
```
IA_PROVIDER=gemini
GEMINI_API_KEY=tu_api_key_de_google_aqui
```

Opcionalmente:
```
OPENAI_API_KEY=sk-xxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
```

⚠️ **IMPORTANTE**: Railway añade automáticamente:
- `DATABASE_URL` (no la edites)
- `PORT` (se reconfigura a 8000)

---

## ✅ Fase 6: Ejecutar Migraciones

En Railway Dashboard:

1. Ir a Deployments (o el build actual)
2. Ver logs
3. Las migraciones se ejecutan automáticamente:
   ```
   🔄 Ejecutando migraciones...
   ✅ PostgreSQL está listo
   ✓ Datos iniciales creados/verificados
   ```

Si las migraciones fallan:
```bash
# Ejecutar manualmente:
railway run flask db upgrade
```

---

## ✅ Fase 7: Verificación Inicial

- [ ] Build completado sin errores
- [ ] Logs muestran "Running on" (gunicorn activo)
- [ ] URL pública de Railway activa (ej: `https://pos-xxxxxx.railway.app`)
- [ ] GET `/api/productos` retorna 200 OK
- [ ] POST `/api/auth/login` retorna 200 con token
- [ ] Frontend carga en `https://pos-xxxxxx.railway.app`
- [ ] Admin login funciona: admin/admin123

---

## ✅ Fase 8: Pruebas Funcionales

**Login:**
- [ ] Acceder con admin/admin123
- [ ] Verificar token JWT se almacena
- [ ] Logout funciona

**Productos:**
- [ ] Listar productos
- [ ] Crear producto
- [ ] Editar producto
- [ ] Eliminar producto

**Inventario:**
- [ ] Ver stock por sucursal
- [ ] Registrar entrada de inventario
- [ ] Editar mínimos de stock

**Ventas:**
- [ ] Crear venta
- [ ] Agregar productos a venta
- [ ] Procesar pago
- [ ] Devolver productos

**Compatibilidad:**
- [ ] Buscar micas compatibles
- [ ] Ver 10 resultados
- [ ] Fallback a BD local si no hay IA

**Cierre de Caja (Empleado):**
- [ ] Cerrar caja
- [ ] Editar cierre
- [ ] Ver historial

---

## ✅ Fase 9: Monitoreo

- [ ] Revisar logs regularmente:
  ```bash
  railway logs --follow
  ```
- [ ] Buscar errores o warnings
- [ ] Verificar DB connections
- [ ] Revisar lentitud en requests

---

## ⚠️ Troubleshooting Común

| Error | Solución |
|-------|----------|
| "ModuleNotFoundError" | Verificar que todas las dependencias están en `requirements.txt` |
| "Connection refused to PostgreSQL" | Esperar a que PostgreSQL se provisione, agregar plugin si no existe |
| "DATABASE_URL not set" | Railway debe establecerla automáticamente, si no, crearla manualmente |
| "Port already in use" | Railway configura automáticamente el puerto, no cambiar |
| "Static files 404" | Verificar que `static/` tiene los archivos, Flask los sirve automáticamente |
| "Build timeout" | Aumentar timeout en Railway settings si es necesario |
| "502 Bad Gateway" | Ver logs, probablemente error en app.py o migraciones |

---

## 📞 Escalabilidad Futura

Si la app crece:

1. **Agregar más replicas**: Railway → Settings → Replicas
2. **Aumentar memoria**: Railway → Settings → Memory
3. **Agregar Redis**: Railway → Add Plugin → Redis (para caching)
4. **Configurar dominio personalizado**: Railway → Settings → Domains
5. **Habilitar auto-scaling**: Railway → Settings → Auto-scaling

---

## 📊 Comandos Útiles de Railway

```bash
# Ver logs
railway logs

# Ver logs en tiempo real
railway logs --follow

# Ver status
railway status

# Ver variables
railway variables

# Ejecutar comando
railway run python3 -c "import app; print('OK')"

# Conectar a BD PostgreSQL
railway run psql

# Ejecutar migración manualmente
railway run flask db upgrade

# Ver consumo
railway resource-metrics
```

---

## ✨ Post-Deployment

1. **Monitoreo**: Revisar logs diariamente
2. **Backups**: Configurar backups automáticos de BD
3. **SSL**: Railway lo hace automáticamente
4. **Dominio**: Pedir dominio personalizado si es necesario
5. **Users**: Crear usuarios de producción
6. **API Keys**: Configurar keys propias de IA si lo necesitas

---

**🎉 ¡Deployment completado! Tu app está en producción.**

Accede en: `https://tu-proyecto.railway.app`
