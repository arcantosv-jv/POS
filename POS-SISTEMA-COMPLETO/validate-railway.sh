#!/bin/bash
# Script de validación antes de deployar en Railway

echo "🔍 Verificando configuración para Railway..."
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

errors=0
warnings=0

# 1. Verificar Dockerfile
echo -n "✓ Dockerfile... "
if [ -f "Dockerfile" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FALTA${NC}"
    ((errors++))
fi

# 2. Verificar requirements.txt
echo -n "✓ requirements.txt... "
if [ -f "requirements.txt" ]; then
    echo -e "${GREEN}OK${NC}"
    # Verificar dependencias críticas
    grep -q "Flask" requirements.txt && echo "  ✓ Flask presente"
    grep -q "Flask-SQLAlchemy" requirements.txt && echo "  ✓ Flask-SQLAlchemy presente"
    grep -q "psycopg2" requirements.txt && echo "  ✓ psycopg2 presente"
    grep -q "gunicorn" requirements.txt && echo "  ✓ gunicorn presente"
else
    echo -e "${RED}FALTA${NC}"
    ((errors++))
fi

# 3. Verificar app.py
echo -n "✓ app.py... "
if [ -f "app.py" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FALTA${NC}"
    ((errors++))
fi

# 4. Verificar config.py
echo -n "✓ config.py... "
if [ -f "config.py" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FALTA${NC}"
    ((errors++))
fi

# 5. Verificar models.py
echo -n "✓ models.py... "
if [ -f "models.py" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FALTA${NC}"
    ((errors++))
fi

# 6. Verificar docker-entrypoint.sh
echo -n "✓ docker-entrypoint.sh... "
if [ -f "docker-entrypoint.sh" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FALTA${NC}"
    ((errors++))
fi

# 7. Verificar gunicorn_config.py
echo -n "✓ gunicorn_config.py... "
if [ -f "gunicorn_config.py" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FALTA${NC}"
    ((errors++))
fi

# 8. Verificar carpeta static
echo -n "✓ static/... "
if [ -d "static" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FALTA${NC}"
    ((errors++))
fi

# 9. Verificar carpeta migrations
echo -n "✓ migrations/... "
if [ -d "migrations" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FALTA${NC}"
    ((errors++))
fi

# 10. Verificar .env.example
echo -n "✓ .env.example... "
if [ -f ".env.example" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${YELLOW}OPCIONAL${NC}"
    ((warnings++))
fi

# 11. Verificar .dockerignore
echo -n "✓ .dockerignore... "
if [ -f ".dockerignore" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${YELLOW}RECOMENDADO${NC}"
    ((warnings++))
fi

# 12. Verificar railway.json
echo -n "✓ railway.json... "
if [ -f "railway.json" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${YELLOW}OPCIONAL${NC}"
    ((warnings++))
fi

# 13. Verificar Procfile
echo -n "✓ Procfile... "
if [ -f "Procfile" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${YELLOW}OPCIONAL${NC}"
    ((warnings++))
fi

echo ""
echo "═════════════════════════════════════════"

if [ $errors -eq 0 ]; then
    echo -e "${GREEN}✓ Validación completada sin errores${NC}"
else
    echo -e "${RED}✗ Se encontraron $errors errores${NC}"
fi

if [ $warnings -gt 0 ]; then
    echo -e "${YELLOW}⚠ Se encontraron $warnings advertencias${NC}"
fi

echo ""
echo "📋 Checklist de Railway:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[ ] GitHub repo creado y sincronizado"
echo "[ ] Railway cuenta creada (https://railway.app)"
echo "[ ] Agregar variables de entorno:"
echo "    - FLASK_ENV=production"
echo "    - SECRET_KEY (muy segura, min 32 chars)"
echo "    - JWT_SECRET_KEY (muy segura, min 32 chars)"
echo "    - IA_PROVIDER=gemini (u otro)"
echo "    - GEMINI_API_KEY (si usas Gemini)"
echo "    - TIMEZONE=America/Mexico_City"
echo "[ ] Agregar PostgreSQL plugin en Railway"
echo "[ ] DATABASE_URL se configura automáticamente"
echo "[ ] Deploy iniciado desde GitHub"
echo "[ ] Verificar logs en Railway dashboard"
echo ""

exit $errors
