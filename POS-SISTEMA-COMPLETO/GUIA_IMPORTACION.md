# 📋 Guía de Importación de Productos

## ✨ Nuevas Características

✅ **Detección automática de sucursal** desde el nombre del archivo  
✅ **Creación automática de categorías y subcategorías** si no existen  
✅ **Campo de subcategoría** separado de la categoría

---

## Estructura de la Plantilla

### Archivo: `plantilla_productos.csv`

La plantilla tiene los siguientes **campos**:

| Campo | Requerido | Tipo | Descripción |
|-------|-----------|------|-------------|
| `codigo` | ✅ Sí | Texto | Código único del producto (ej: MICA-001) |
| `nombre` | ✅ Sí | Texto | Nombre del producto (ej: Mica Samsung A10) |
| `categoria` | ❌ No | Texto | Categoría padre (ej: Protección, Accesorios). Si no existe, se crea automáticamente |
| `subcategoria` | ❌ No | Texto | Subcategoría específica (ej: Protección Pantalla). Si no existe, se crea automáticamente |
| `precio` | ❌ No | Decimal | Precio del producto (ej: 150.00). Si es 0 o vacío, no asigna precio |
| `stock` | ❌ No | Número | Cantidad en inventario (ej: 50). Si es vacío, usa 0 |
| `sucursal_id` | ❌ No | Texto | ID de la sucursal (se auto-detecta del nombre del archivo) |

### Ejemplo de Fila:
```csv
MICA-001,Mica Samsung A10,Protección,Protección Pantalla,150.00,50,
```

---

## 🚀 Nombres de Archivo Soportados

El sistema auto-detecta la sucursal del nombre del archivo. Formatos válidos:

| Nombre de archivo | Sucursal detectada |
|-------------------|-------------------|
| `productos_Sucursal_Centro.csv` | Sucursal Centro |
| `productos_Sucursal_Norte.csv` | Sucursal Norte |
| `productos_sucursal_centro.csv` | Sucursal Centro |
| `Sucursal_Centro_productos.csv` | Sucursal Centro |
| `Centro_productos.csv` | Centro |
| `importar-sucursal-centro.csv` | Sucursal Centro |

**💡 Recomendación:** Usa el formato `productos_[Nombre_Sucursal].csv`

---

## ¿Cómo Usar?

### Opción 1: Desde la Interfaz Web (Más Fácil) ✨

1. **Inicia sesión** como administrador
2. Ve a **Gestión de Productos** → **📤 Importar Excel/CSV**
3. **Carga el archivo** (auto-detecta la sucursal)
4. ✓ **Importar Productos**

---

### Opción 2: Desde Terminal

#### Paso 1: Editar la plantilla
```bash
# Abre el archivo y agrega tus productos
nano plantilla_productos.csv
```

#### Paso 2: Convertir CSV a JSON (opcional)
```bash
python3 convertir_productos_json.py plantilla_productos.csv
```
Esto genera: `plantilla_productos_json.json`

#### Paso 3: Obtener Token de Autenticación
```bash
./obtener_token.sh
# o con usuario y contraseña diferentes:
./obtener_token.sh mi_usuario mi_contraseña
```

Copiar el token que aparece.

#### Paso 4: Importar Productos
```bash
./importar_productos.sh plantilla_productos_json.json <PEGA_EL_TOKEN_AQUI>
```

### Opción 3: Usando cURL Directamente

```bash
# 1. Obtener token
TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 2. Importar productos
curl -X POST http://localhost:5000/api/productos/importar \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d @plantilla_productos_json.json
```

---

## Formatos de Datos

### Código de Producto
- Caracteres: Letras, números, guiones
- Ejemplos: `MICA-001`, `FUNDA-001`, `ACC-USB-C`

### Categoría y Subcategoría
- Se crean automáticamente si no existen
- Ejemplos:
  - Categoría: `Protección` → Subcategoría: `Protección Pantalla`
  - Categoría: `Accesorios` → Subcategoría: `Cables`

### Precio
- Formato: Número decimal con punto (no coma)
- Ejemplos: `150.00`, `1250.50`, `0.99`

### Stock
- Formato: Número entero positivo
- Ejemplos: `50`, `100`, `0`

---

## Ejemplos Completos

### Ejemplo 1: Productos Variados con Categorías
```csv
codigo,nombre,categoria,subcategoria,precio,stock,sucursal_id
MICA-001,Mica Samsung A10,Protección,Protección Pantalla,150.00,50,
MICA-002,Mica Samsung A20,Protección,Protección Pantalla,150.00,45,
FUNDA-001,Funda Negra Samsung A10,Accesorios,Fundas,120.00,60,
CABLE-001,Cable USB-C 2 metros,Accesorios,Cables,60.00,80,
CARGADOR-001,Cargador Rápido 30W,Accesorios,Cargadores,350.00,20,
```

### Ejemplo 2: Mínimo Requerido
```csv
codigo,nombre,categoria,subcategoria,precio,stock,sucursal_id
PROD-001,Mi Producto,General,,0,0,
PROD-002,Otro Producto,General,,0,0,
```

### Ejemplo 3: Con Archivo Nombrado Correctamente
```bash
# Archivo: productos_Sucursal_Centro.csv
# El sistema auto-asignará a Sucursal Centro
codigo,nombre,categoria,subcategoria,precio,stock,sucursal_id
MICA-001,Mica Samsung A10,Protección,Protección Pantalla,150.00,50,
```

---

## Respuesta Esperada

### Éxito
```json
{
  "importados": 5,
  "total": 5,
  "errores": [],
  "mensaje": "5 productos importados exitosamente"
}
```

### Con Errores
```json
{
  "importados": 3,
  "total": 5,
  "errores": [
    "Producto sin código o nombre: ",
    "Error en producto desconocido: invalid literal for int() with base 10: 'abc'"
  ],
  "mensaje": "3 de 5 productos importados. Hubo 2 errores."
}
```

---

## Troubleshooting

### ❌ "Sucursal no encontrada"
- Verifica que el nombre de la sucursal sea exacto
- Intenta usar el selector manual si la auto-detección no funciona
- Formatos válidos: `productos_Centro.csv`, `productos_Sucursal_Centro.csv`

### ❌ "Archivo no encontrado"
Verifica que estés en el directorio correcto:
```bash
cd /Users/santiagodelgado/Documents/GitHub/pos/POS-SISTEMA-COMPLETO
ls -la plantilla_productos.csv
```

### ❌ "Error al convertir a JSON"
Verifica que el CSV tenga formato correcto:
- Separador: comas (`,`)
- Encabezado: primera fila
- Sin espacios extras alrededor de comas

### ❌ "Token no válido"
Regenera un token nuevo:
```bash
./obtener_token.sh
```

### ❌ "Código de producto ya existe"
El sistema actualizará el precio y stock si el código ya existe. Para crear uno nuevo, cambia el código.

---

## Notas Importantes

✅ **Lo que el sistema hace automáticamente:**
- ✓ Crea categorías si no existen
- ✓ Crea subcategorías si no existen
- ✓ Crea stock en TODAS las sucursales activas
- ✓ Detecta la sucursal del nombre del archivo
- ✓ Actualiza precios y stocks si el código ya existe

⚠️ **Limitaciones:**
- Solo administradores pueden importar
- No se puede actualizar el código de un producto existente
- La sucursal se detecta automáticamente o se selecciona manualmente

---

## 📊 Video Tutorial

Para ver en acción cómo se importan los productos:
```bash
# Opción 1: Interfaz Web (Recomendado)
# 1. Ve a http://localhost:5000
# 2. Inicia sesión como admin/admin123
# 3. Ve a Gestión de Productos → Importar Excel/CSV
# 4. Arrastra tu archivo (ej: productos_Sucursal_Centro.csv)
# 5. ¡Click en Importar!

# Opción 2: Terminal
echo "1. Convertir CSV a JSON..."
python3 convertir_productos_json.py plantilla_productos.csv

echo "2. Obtener token..."
./obtener_token.sh

echo "3. Importar productos..."
# (copiar y pegar el token en el siguiente comando)
./importar_productos.sh plantilla_productos_json.json <TOKEN>
```


