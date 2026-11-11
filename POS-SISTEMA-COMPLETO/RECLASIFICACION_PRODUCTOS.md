# Corrección de categorías y subcategorías

## Hallazgos

El importador del navegador usaba `split(',')` y eliminaba comillas: un nombre como `"Sabritas (Chetos, Doritos)"` desplazaba las columnas siguientes. Ahora respeta comillas, comas y saltos internos y rechaza filas con un número de columnas incorrecto antes de enviar datos.

La reimportación de un código existente ignoraba su clasificación. Ahora actualiza la clasificación cuando se proporciona categoría; si no se proporciona clasificación, conserva la existente. La importación normal sigue actualizando precios y existencias: para corregir **solo clasificación**, usar el script de esta guía.

En localhost/pos_db se revisaron 1,195 productos. Los audífonos encontrados estaban en Audifonos, por lo que el caso de producción no se reprodujo localmente. Se detectó `11091`, nombre `Sabritas (Chetos`, categoría `Doritos)`, subcategoría `Snack`: evidencia consistente con columnas desplazadas. Sin el archivo original no se puede reconstruir con certeza toda esa fila (también podrían haberse desplazado precio/stock).

Se aplicaron en local estas tres correcciones claras:

| Código | Producto | Destino |
|---|---|---|
| 10960 | Adaptador micro SD a usb | Adaptadores / Adaptadores |
| 10985 | Bastón selfie Bluetooth | Soportes / Bastón Selfie |
| 11126 | Funda a07 | Fundas / Funda |

La propuesta y el respaldo se encuentran en `datos_revision/`. Nombres ambiguos como `auto completo apple` (10730), `Bauma` (11001) y `Among us sorpresa` (11084) necesitan confirmar su clasificación. `Mica Samsung a20` (10004) está en General / Micas; hay que confirmar el tipo de mica. No se cambian por inferencia.

## Uso

El script usa `DATABASE_URL` del entorno o `.env`; sin ella utiliza la configuración DB_HOST/DB_NAME del proyecto. No imprime credenciales ni crea tablas. Verifica el entorno elegido antes de aplicar. No uses los IDs de una exportación local sobre producción: exporta de nuevo en el entorno objetivo.

```bash
.venv/bin/python reclasificar_productos.py exportar clasificacion.csv
```

En el CSV conserva código y columnas originales. Completa **categoria_destino** y **subcategoria_destino** únicamente en los productos a corregir. Las demás filas se omiten. Los nombres deben coincidir exactamente con una categoría y subcategoría activas existentes; crea las faltantes previamente en admin.

```bash
.venv/bin/python reclasificar_productos.py revisar clasificacion.csv
.venv/bin/python reclasificar_productos.py aplicar clasificacion.csv --respaldo respaldo_clasificacion.json
```

En Railway o un entorno sin `.venv`, usa `python` con las dependencias del proyecto instaladas. Ejecuta primero `exportar` y `revisar` contra producción y revisa el listado antes de `aplicar`.

El producto pertenece a una subcategoría y la categoría se deriva de ella. Por eso solo se actualiza `productos.subcategoria_id` (y su fecha automática de actualización). No cambia nombres, códigos, precios, impuestos, ventas ni existencias. La clasificación es global y afecta a todas las sucursales.

Se valida todo antes de guardar, en una transacción. Se rechazan códigos repetidos, productos inexistentes, destinos inválidos y asignaciones que hayan cambiado desde la exportación. Aplicar el mismo archivo nuevamente no realiza cambios. El respaldo JSON guarda IDs anteriores y nuevos para reconstruir un CSV inverso si se requiere revertir; no es un respaldo completo de la base.

## Pruebas

```bash
.venv/bin/python -m unittest discover -s tests -p test_importacion_clasificacion.py
node tests/test_frontend_importacion.js
```

## Propuestas automáticas por nombre

Ya no es necesario rellenar manualmente los destinos para los casos cubiertos por reglas:

```bash
python reclasificar_productos.py proponer propuestas.csv --pendientes pendientes.csv
python reclasificar_productos.py revisar propuestas.csv
python reclasificar_productos.py aplicar propuestas.csv --respaldo respaldo_automatico.json
```

`proponer` consulta la base configurada y escribe destinos existentes para fundas, adaptadores, bastones selfie, bocinas, transmisores y audífonos cuyo nombre especifica Bluetooth o cable. Ignora acentos y mayúsculas y contempla la variante `bluethoot`. No modifica la base ni crea categorías. Los accesorios para audífonos no se clasifican como audífonos.

`pendientes.csv` contiene nombres sin regla y destinos faltantes o ambiguos. No significa que esos productos estén mal: se conservan hasta tener evidencia para ampliar las reglas de `clasificacion_productos.py`. Las reglas son heurísticas, no una reconstrucción del archivo original. Revisa las propuestas antes de aplicarlas. Las micas genéricas no permiten inferir si son de cristal, cerámica, privacidad o hidrogel.

La prueba local generó 86 propuestas, 315 coincidencias correctas y 793 pendientes entre productos activos. No se aplicaron estas propuestas. Producción debe generar sus propios archivos.

## Corrección automática en un solo comando

```bash
# Simular: consulta todos los productos (activos e inactivos) y no cambia datos.
python reclasificar_productos.py automatico --salida revision_01

# Generar y aplicar automáticamente las correcciones reconocidas.
python reclasificar_productos.py automatico --aplicar --salida correccion_01
```

No requiere editar CSV. Cada ejecución necesita una carpeta nueva. Guarda propuestas, pendientes y resultado; si aplica cambios, también guarda el respaldo de las asignaciones anteriores. Si el producto ya está bien clasificado no lo actualiza. Los nombres sin regla y destinos inexistentes o ambiguos se omiten. Antes de escribir verifica que ni el nombre ni la clasificación hayan cambiado desde la lectura. Las categorías se derivan de la subcategoría: el único campo de negocio actualizado es `subcategoria_id`.

Este comando se ejecuta bajo demanda; no se ha configurado una tarea periódica ni se ha ejecutado la corrección automática contra producción. Usa las variables de conexión del entorno objetivo.

## Revisión con Gemini y aprobación de destinos nuevos

Reutiliza `GEMINI_API_KEY` y la selección de modelos de la integración de compatibilidad
(`GEMINI_PRIMARY_MODELS`, `GEMINI_FALLBACK_MODELS`, `GEMINI_MODEL`). No requiere otra clave
ni proveedor. Las consultas consumen la cuota de esa misma cuenta de Gemini.

Desde la raíz del proyecto, con el entorno conectado a la base local:

```sh
.venv/bin/python reclasificar_productos.py ia --salida datos_revision/mi_revision_gemini
```

La carpeta debe ser nueva. Consulta todos los productos, incluidos inactivos, en lotes de 25.
Solo envía código, nombre y clasificación actual, junto con las categorías activas existentes.
No modifica la base. Genera:

- `revision.csv`: clasificación anterior, propuesta, motivo y estado (`correcto`, `corregir`,
  `pendiente` por ambigüedad o `requiere_aprobacion` para destinos nuevos).
- `nuevas.json`: pares categoría/subcategoría propuestos, todos con `aprobada: false`.

Revisa la vista previa. Para autorizar un destino nuevo cambia únicamente su `aprobada`
a `true` en `nuevas.json`. Puedes excluir cualquier corrección cambiando su estado a
`pendiente` en `revision.csv`. Los productos ambiguos quedan intactos. Después de revisar:

```sh
.venv/bin/python reclasificar_productos.py aplicar-ia --salida datos_revision/mi_revision_gemini
```

Este comando sí escribe: crea únicamente destinos aprobados y aplica las correcciones
hacia destinos existentes y nuevos aprobados. Guarda `aprobadas.csv` y `respaldo.json`
con las asignaciones anteriores. Si un producto cambió de nombre o clasificación desde
la revisión, cancela la operación completa, incluidas las categorías nuevas. Los archivos
no se sobrescriben; después de un intento fallido genera otra revisión en una carpeta nueva.
No modifica nombre, precio, inventario ni estado activo del producto.

Para producción, primero valida el resultado en local y luego genera una revisión nueva
contra producción con su configuración de conexión. No reutilices una revisión local:
los identificadores y el catálogo pueden diferir. Revisa sus archivos antes de aplicar.

## Desde el panel de administración

En **Administración → Categorías → Re Clasificar Productos**:

1. Pulsa **Iniciar revisión** (o **Nueva revisión**). Revisa todos los productos, incluidos
   inactivos, sin filtrar por sucursal. Gemini usa la configuración existente.
2. El avance se guarda en la base por lotes de diez. **Pausar revisión** termina el lote
   actual y se detiene. Si sales, vuelve y pulsa **Continuar revisión**. Un fallo de Gemini
   conserva el lote pendiente para reintentar; no modifica productos.
3. Revisa las propuestas; usa los filtros y **Editar** para cambiar cualquier clasificación
   aún no aplicada. Los ambiguos solo quedan listos después de guardar una selección manual.
4. Si propones una categoría/subcategoría nueva, pulsa **Aprobar destino**. Todavía no se
   crea: se creará al aplicar. Los destinos activos existentes se reutilizan.
5. **Aplicar cambios** guarda solo las filas listas, incluidas las corregidas manualmente.
   Omite los pendientes, los destinos sin aprobar, los correctos y los ya aplicados.

Las revisiones anteriores se consultan en **Revisión guardada**. Cada fila aplicada conserva
la clasificación anterior y la nueva, el administrador y la fecha de aplicación. Las
revisiones del script CSV no se importan automáticamente al panel.

Solo administradores acceden a estas APIs. Las acciones se validan en el servidor, incluso
si se intenta acceder directamente. La revisión usa versiones para evitar sobrescribir
ediciones de otra sesión. Antes de aplicar se comprueba que el nombre y clasificación del
producto no hayan cambiado; si existe un conflicto se revierte toda la transacción.

La migración `016_revision_clasificacion.py` crea `revisiones_clasificacion`. El despliegue
Railway existente ejecuta `railway_migrate.py` antes del arranque y aplica esta migración.
No se necesitan otras claves de IA ni nuevos servicios. Las consultas usan la cuota de Gemini.

Pruebas del panel:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -p 'test_reclasificacion_admin.py'
node tests/test_frontend_reclasificacion.js
```
