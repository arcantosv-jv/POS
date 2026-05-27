# 🔧 Troubleshooting: Error 400 en Importación

Si recibes **"Error 400: No hay productos para importar"**, aquí está cómo resolver:

---

## 🔍 Checklist Rápido

- [ ] ¿El archivo es **.csv** (no .xlsx, .numbers)?
- [ ] ¿Tiene las columnas: `codigo`, `nombre`?
- [ ] ¿Tiene datos **después del encabezado** (no solo títulos)?
- [ ] ¿Los valores están **separados por comas**?
- [ ] ¿Iniciaste sesión como **admin**?

---

## ✅ Estructura Correcta de CSV

**Archivo debe tener al menos esto:**

```csv
codigo,nombre,categoria,subcategoria,precio,stock,sucursal_id
PROD-001,Mi Producto,General,,0,0,
PROD-002,Otro Producto,General,,0,0,
```

**Notas:**
- Primera línea = encabezado
- Al menos 2 datos después
- Columnas mínimas: `codigo`, `nombre`
- Las otras columnas son opcionales

---

## 🐛 Errores Comunes

### ❌ "Error: No se encontraron las columnas necesarias"
- Tu CSV no tiene las columnas `codigo` y `nombre`
- Solución: Renombra tus columnas o usa la plantilla

### ❌ "Error: No se encontraron productos en el archivo"
- El archivo tiene encabezado pero sin datos
- Solución: Agrega al menos 2 filas de datos

### ❌ "400 Bad Request"
- El servidor no recibió productos para importar
- Solución: Verifica los errores anteriores

---

## 🔍 Cómo Diagnosticar

### 1. Abre la Consola (F12)
```javascript
// Ver qué datos está enviando
// En Network → encuentra POST /api/productos/importar
// Click en ella → pestaña "Payload"
// Verás el JSON que se envía
```

### 2. Verifica la Terminal de la App
```bash
# Busca líneas como:
[DEBUG] Importar productos - Recibidos 0 productos
```

### 3. Verifica tu CSV
Abre en editor de texto (TextEdit, VSCode, NOT Excel):
```
- Primera línea contiene: codigo,nombre,...
- Líneas siguientes tienen datos
- No hay líneas vacías al inicio
```

---

## 📋 Formatos Soportados de Nombres de Columna

El sistema es flexible. Soporta:

| Lo que pones | Sistema reconoce como |
|---|---|
| `codigo` o `ref` o `sku` | Código del producto |
| `nombre` o `producto` | Nombre |
| `categoria` o `categoría` | Categoría |
| `subcategoria` o `subcategoría` | Subcategoría |
| `precio` | Precio |
| `stock` o `cantidad` o `inventario` | Stock |

---

## 🚀 Prueba Rápida

1. Descarga la plantilla: `plantilla_productos.csv`
2. Abre en editor de texto
3. Verifica que tenga:
   ```
   codigo,nombre,categoria,subcategoria,precio,stock,sucursal_id
   MICA-001,Mica Samsung A10,Protección,Protección Pantalla,150.00,50,
   ```
4. Guarda como UTF-8
5. Carga en el sistema

---

## 💾 Cómo Verificar UTF-8

### Mac
```bash
file plantilla_productos.csv
# Debe decir: "ASCII text" o "UTF-8 Unicode text"
```

### Verificar Caracteres
Abre en terminal:
```bash
head -1 plantilla_productos.csv
# Debe mostrar el encabezado correctamente
```

---

## 📞 Si Nada Funciona

1. Comparte el error exacto que ves en consola (F12)
2. Comparte las primeras 2 líneas de tu CSV:
   ```bash
   head -2 tu_archivo.csv
   ```
3. Verifica en terminal:
   ```bash
   cd /Users/santiagodelgado/Documents/GitHub/pos/POS-SISTEMA-COMPLETO
   # Intenta importar desde terminal
   ./obtener_token.sh
   # Copia el token
   ./importar_productos.sh plantilla_productos_json.json <TOKEN>
   ```

