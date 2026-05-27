#!/bin/bash

# Script para obtener token de autenticación
# Uso: ./obtener_token.sh [usuario] [password]

USUARIO="${1:-admin}"
CONTRASEÑA="${2:-admin123}"
API_URL="http://localhost:5000/api/auth/login"

echo "🔐 Obteniendo token para usuario: $USUARIO"
echo ""

respuesta=$(curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$USUARIO\", \"password\": \"$CONTRASEÑA\"}")

# Extraer el token
token=$(echo "$respuesta" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('access_token', ''))" 2>/dev/null)

if [ -z "$token" ]; then
    echo "❌ Error al obtener token"
    echo "Respuesta: $respuesta"
    exit 1
fi

echo "✅ Token obtenido:"
echo ""
echo "TOKEN: $token"
echo ""
echo "Úsalo con:"
echo "  ./importar_productos.sh productos_importar.json $token"
