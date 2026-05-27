# 📊 Cómo Convertir Excel o Numbers a CSV

El sistema de importación **solo acepta archivos CSV (.csv)**. Aquí te muestro cómo convertir.

---

## 🔄 Opción 1: Excel a CSV (En cualquier plataforma)

### Mac (Excel)
1. Abre tu archivo en Excel
2. Ve a **Archivo** → **Guardar como**
3. En "Formato:", selecciona **CSV UTF-8 (.csv)**
4. Elige la ubicación y haz clic en **Guardar**

### Windows (Excel)
1. Abre tu archivo en Excel
2. Ve a **Archivo** → **Guardar como**
3. En "Tipo de archivo:", selecciona **CSV (Delimitado por comas) (.csv)**
4. Haz clic en **Guardar**

### Google Sheets
1. Abre tu hoja de cálculo
2. Ve a **Archivo** → **Descargar** → **Valores separados por comas (.csv)**
3. Listo, ya tendrás el CSV

---

## 🍎 Opción 2: Numbers (Mac) a CSV

### Método 1: Desde Numbers
1. Abre tu archivo Numbers
2. Ve a **Archivo** → **Exportar**
3. En "Formato:", selecciona **Excel (.xlsx)**
4. Haz clic en **Siguiente**
5. Guarda el archivo
6. Luego abre el archivo Excel y sigue los pasos de "Excel a CSV" arriba

### Método 2: Más Directo (Numbers en iCloud)
1. Abre tu archivo en iCloud.com
2. Selecciona la tabla
3. Presiona **Ctrl+C** para copiar
4. Abre un editor de texto (Notas, TextEdit, etc.)
5. Presiona **Ctrl+V** para pegar
6. Guarda como `.csv`

---

## ✅ Verificar que tu CSV es Correcto

Antes de subir, asegúrate que el archivo tenga:

**Encabezado (Primera fila):**
```
codigo,nombre,categoria,subcategoria,precio,stock,sucursal_id
```

**Datos (Filas siguientes):**
```
MICA-001,Mica Samsung A10,Protección,Protección Pantalla,150.00,50,
MICA-002,Mica Samsung A20,Protección,Protección Pantalla,150.00,45,
```

---

## 🚀 Pasos Finales

1. Convierte el archivo a CSV
2. Abre en un editor de texto para verificar que se vea bien
3. Sube el archivo en la interfaz: **Gestión de Productos** → **📤 Importar**
4. ¡Listo!

---

## 🆘 Troubleshooting

### ❌ "El archivo debe ser CSV"
- Verifica que el archivo termine en `.csv`
- Windows: A veces la extensión está oculta. Haz clic en Ver → Extensiones de archivo

### ❌ "No se ven bien los caracteres especiales"
- Asegúrate de guardar como **UTF-8**
- En Excel Mac: **Archivo** → **Guardar como** → Opciones → Encoding: **UTF-8**

### ❌ "El archivo se ve corrupto en el editor"
- Abre con un editor de texto como:
  - **Mac**: TextEdit (Formato → Texto sin formato) o VSCode
  - **Windows**: Notepad o VSCode
- NO abras en Word o Pages (pueden agregar formato extra)

---

## 💡 Pro Tips

✓ Usa siempre **UTF-8** (soporta acentos y caracteres especiales)  
✓ Verifica que NO haya espacios extras en las columnas  
✓ Copia tu CSV original como backup antes de hacer cambios  
✓ Si tienes muchas hojas, solo se convierte la primera visible  

