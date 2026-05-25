#!/bin/bash
# Script para hacer backup de la base de datos PostgreSQL

# Variables
BACKUP_DIR="./backups"
DB_NAME="${DB_NAME:-pos_db}"
DB_USER="${DB_USER:-pos_user}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/pos_backup_$TIMESTAMP.sql"

# Crear directorio de backups si no existe
mkdir -p "$BACKUP_DIR"

echo "🔄 Iniciando backup de base de datos..."
echo "Base de datos: $DB_NAME"
echo "Host: $DB_HOST"
echo "Archivo: $BACKUP_FILE"

# Hacer backup
PGPASSWORD=$DB_PASSWORD pg_dump -U $DB_USER -h $DB_HOST -p $DB_PORT -d $DB_NAME > "$BACKUP_FILE" 2>/dev/null

if [ $? -eq 0 ]; then
    FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Backup completado exitosamente"
    echo "📊 Tamaño: $FILE_SIZE"
    echo "💾 Ubicación: $BACKUP_FILE"
    
    # Crear gzip del backup
    gzip "$BACKUP_FILE"
    echo "📦 Archivo comprimido: $BACKUP_FILE.gz"
    
    # Eliminar backups antiguos (más de 7 días)
    echo "🧹 Limpiando backups antiguos..."
    find "$BACKUP_DIR" -name "pos_backup_*.sql.gz" -mtime +7 -delete
    echo "✅ Limpieza completada"
else
    echo "❌ Error al hacer backup"
    exit 1
fi
