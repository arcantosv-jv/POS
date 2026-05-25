#!/bin/bash
# Script para restaurar un backup de la base de datos

# Variables
DB_NAME="${DB_NAME:-pos_db}"
DB_USER="${DB_USER:-pos_user}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

# Verificar que se pase un archivo
if [ -z "$1" ]; then
    echo "❌ Uso: bash restore_db.sh <archivo_backup.sql.gz>"
    echo ""
    echo "Archivos disponibles:"
    ls -lh backups/ 2>/dev/null || echo "No hay backups"
    exit 1
fi

BACKUP_FILE="$1"

# Verificar que el archivo existe
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Archivo no encontrado: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  ADVERTENCIA: Esta operación reemplazará la base de datos actual"
echo "Archivo: $BACKUP_FILE"
read -p "¿Estás seguro? (s/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "Cancelado"
    exit 1
fi

echo "🔄 Restaurando base de datos..."

# Si el archivo está comprimido, descomprimirlo
if [[ $BACKUP_FILE == *.gz ]]; then
    echo "📦 Descomprimiendo..."
    gunzip -c "$BACKUP_FILE" | PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -h $DB_HOST -p $DB_PORT -d $DB_NAME
else
    PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -h $DB_HOST -p $DB_PORT -d $DB_NAME < "$BACKUP_FILE"
fi

if [ $? -eq 0 ]; then
    echo "✅ Restauración completada exitosamente"
else
    echo "❌ Error durante la restauración"
    exit 1
fi
