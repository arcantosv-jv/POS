#!/bin/bash

# Script para importar productos al POS
# Uso: ./importar_productos.sh <archivo.json> <token>

ARCHIVO_JSON="${1:-productos_importar.json}"
TOKEN="${2:-}"
API_URL="http://localhost:5000/api/productos/importar"

if [ ! -f "$ARCHIVO_JSON" ]; then
    echo "❌ Error: Archivo '$ARCHIVO_JSON' no encontrado"
    echo ""
    echo "Pasos:"
    echo "1. Edita plantilla_productos.csv con tus productos"
    echo "2. Ejecuta: python3 convertir_productos_json.py plantilla_productos.csv"
    echo "3. Obtén un token con: ./obtener_token.sh"
    echo "4. Ejecuta: ./importar_productos.sh productos_importar.json <TOKEN>"
    exit 1
fi

if [ -z "$TOKEN" ]; then
    echo "❌ Error: Token no proporcionado"
    echo ""
    echo "Obtén el token ejecutando:"
    echo "  ./obtener_token.sh"
    echo ""
    echo "Luego usa:"
    echo "  ./importar_productos.sh $ARCHIVO_JSON <TOKEN>"
    exit 1
fi

echo "📤 Importando productos desde: $ARCHIVO_JSON"
echo "📡 Enviando a: $API_URL"
echo ""

# Realizar la petición
respuesta=$(curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d @"$ARCHIVO_JSON")

echo "📋 Respuesta del servidor:"
echo "$respuesta" | python3 -m json.tool 2>/dev/null || echo "$respuesta"
