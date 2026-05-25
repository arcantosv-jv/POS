@echo off
REM Script para inicializar la base de datos en Windows

echo 🚀 Inicializando POS Sistema...

REM Crear carpeta migrations si no existe
if not exist "migrations" (
    echo 📁 Creando carpeta migrations...
    flask db init
)

REM Crear o actualizar tablas
echo 🔄 Actualizando base de datos...
flask db upgrade

echo ✅ Base de datos inicializada correctamente
echo.
echo 📊 Usuario admin creado:
echo    Usuario: admin
echo    Contraseña: admin123
echo.
echo 🏪 Sucursales creadas:
echo    - Sucursal Centro
echo    - Sucursal Norte
echo.
echo 🚀 Inicia la aplicación con: python app.py

pause
