#!/bin/bash
# Script para verificar la implementación de Devoluciones

echo "🔍 Verificando Sistema de Devoluciones..."
echo ""

# Check Python syntax
echo "1️⃣ Verificando sintaxis de Python..."
python3 -m py_compile routes_devoluciones.py 2>/dev/null && echo "   ✅ routes_devoluciones.py - OK" || echo "   ❌ routes_devoluciones.py - ERROR"

# Check files exist
echo ""
echo "2️⃣ Verificando archivos creados..."
test -f "routes_devoluciones.py" && echo "   ✅ routes_devoluciones.py" || echo "   ❌ routes_devoluciones.py"
test -f "migrations/versions/005_create_devoluciones_venta.py" && echo "   ✅ migrations/versions/005_create_devoluciones_venta.py" || echo "   ❌ migrations/versions/005_create_devoluciones_venta.py"
test -f "DEVOLUCIONES.md" && echo "   ✅ DEVOLUCIONES.md" || echo "   ❌ DEVOLUCIONES.md"
test -f "DEVOLUCIONES_TECNICO.md" && echo "   ✅ DEVOLUCIONES_TECNICO.md" || echo "   ❌ DEVOLUCIONES_TECNICO.md"
test -f "RESUMEN_DEVOLUCIONES.md" && echo "   ✅ RESUMEN_DEVOLUCIONES.md" || echo "   ❌ RESUMEN_DEVOLUCIONES.md"

# Check modifications
echo ""
echo "3️⃣ Verificando modificaciones a archivos existentes..."
grep -q "devoluciones_bp" app.py && echo "   ✅ app.py - Blueprint registrado" || echo "   ❌ app.py - Blueprint NO registrado"
grep -q "DevolucionVenta" models.py && echo "   ✅ models.py - Modelo agregado" || echo "   ❌ models.py - Modelo NO agregado"
grep -q "'devoluciones-view': DevolucionesView" static/app.js && echo "   ✅ app.js - Componente registrado" || echo "   ❌ app.js - Componente NO registrado"
grep -q "DevolucionesView" static/components.js && echo "   ✅ components.js - Componente creado" || echo "   ❌ components.js - Componente NO creado"
grep -q "devoluciones" static/index.html && echo "   ✅ index.html - Link agregado" || echo "   ❌ index.html - Link NO agregado"

echo ""
echo "4️⃣ Próximos pasos:"
echo "   a) Ejecutar migración Alembic:"
echo "      flask --app app:create_app db upgrade"
echo "   b) Reiniciar la aplicación"
echo "   c) Navegar a 'Devoluciones' en el menú"
echo ""
echo "✅ Verificación completada"
