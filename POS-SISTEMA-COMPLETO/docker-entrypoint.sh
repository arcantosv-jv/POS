#!/bin/bash
set -e

echo "🚀 Iniciando POS Sistema..."
echo "📌 Entorno: ${FLASK_ENV:-development}"

# Usar DATABASE_URL si está disponible (Railway), sino construir desde variables
if [ -z "$DATABASE_URL" ]; then
  echo "🔧 Construyendo DATABASE_URL desde variables individuales..."
  export DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
fi

echo "⏳ Esperando a PostgreSQL..."
DB_HOST=$(echo $DATABASE_URL | grep -oP '(?<=@)[^:]+')
DB_PORT=$(echo $DATABASE_URL | grep -oP '(?<=:)[0-9]+(?=/)')

# Esperar a que PostgreSQL esté listo
max_attempts=30
attempt=1
while ! nc -z ${DB_HOST:-db} ${DB_PORT:-5432}; do
  if [ $attempt -ge $max_attempts ]; then
    echo "❌ PostgreSQL no respondió después de $max_attempts intentos"
    exit 1
  fi
  echo "PostgreSQL aún no está listo... ($attempt/$max_attempts)"
  sleep 2
  ((attempt++))
done

echo "✅ PostgreSQL está listo"

# Ejecutar migraciones
echo "🔄 Ejecutando migraciones..."
flask db upgrade || {
  echo "⚠️  Migraciones fallaron, pero continuando..."
}

echo "✅ Sistema listo para recibir tráfico"

# Ejecutar el comando principal
exec "$@"

