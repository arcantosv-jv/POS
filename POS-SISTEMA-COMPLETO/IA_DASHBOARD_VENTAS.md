# Dashboard de ventas e IA

## Alcance

El dashboard administrativo utiliza `GET /api/reportes/dashboard-ventas` para mostrar totales netos de venta, impuestos, transacciones, ticket promedio, serie temporal, ranking de sucursales y productos más vendidos globales y por sucursal. Acepta `fecha_inicio`, `fecha_fin` y `sucursal_id`; por omisión cubre los últimos 30 días. Para rangos menores a 90 días, la serie se agrupa por día; para rangos mayores, por mes. El máximo admitido es 366 días.

La comparación usa el periodo inmediatamente anterior de igual duración. Si no hubo ventas en ese periodo base, la variación porcentual se devuelve como `null` y se presenta como "Sin base para comparar".

Los totales monetarios de venta son los almacenados en `Venta.total`, por lo que reflejan los ajustes de devoluciones aplicados a la venta. El ranking de productos usa `DetalleVenta.cantidad` y `DetalleVenta.subtotal`; actualmente las devoluciones no ajustan esos detalles, así que se reportan como ventas originales/brutas. Esa limitación se muestra en la pantalla.

## Gráficas y exportación HTML

La pantalla de Reportes conserva filtros, indicadores, comparativos y tablas, y ahora presenta cuatro gráficas interactivas: tendencia temporal, ventas por sucursal, productos líderes por unidades y productos líderes por sucursal. El botón **Descargar reporte HTML** genera una instantánea del periodo y los filtros seleccionados; incluye KPIs, gráficas, rankings y tablas.

El HTML incrusta las gráficas como imágenes PNG y no depende del servidor, JavaScript externo ni conexión a internet. Es una instantánea estática: al cambiar filtros se genera otro archivo. La interfaz de la aplicación mantiene gráficas interactivas con Chart.js. La vista ya no presenta texto narrativo generado por IA; el endpoint de análisis documentado abajo permanece como API opcional.

## Análisis con IA

`POST /api/reportes/dashboard-ventas/analisis-ia` vuelve a calcular las métricas autorizadas en el servidor. Solo administradores pueden usar ambos endpoints. El modelo recibe agregados de venta y producto; no recibe números de venta, observaciones, empleados, clientes ni datos de autenticación. Si falta la clave, la ruta responde `503` y el dashboard conserva sus métricas sin análisis narrativo.

Modelo predeterminado: `gemini-3.1-flash-lite`, configurable con `GEMINI_DASHBOARD_MODEL`. Se reutiliza Gemini porque la aplicación ya usa la biblioteca `google-genai` y `GEMINI_API_KEY`; este caso es síntesis breve de JSON agregado, no requiere razonamiento multimodal ni justifica el costo operativo de mantener una integración adicional con OpenAI o Anthropic. Se debe medir calidad y latencia con reportes reales anonimizados antes de reconsiderar.

Para producción, configurar `GEMINI_API_KEY` y una cuota/facturación adecuada en el proveedor. Revisar la política de retención y uso de datos correspondiente al plan de Gemini; evitar la API gratuita para información comercial que no deba usarse para mejorar productos.

## Prompt vigente

El backend construye el prompt con las métricas calculadas y lo envía como JSON:

> Actúas como analista comercial para una cadena pequeña de tiendas. Analiza exclusivamente los datos JSON adjuntos. Los valores monetarios están expresados en MXN. No inventes causas, cifras, metas ni predicciones. Distingue observaciones de hipótesis y señala cuando no haya datos suficientes. Compara el periodo actual con el periodo anterior equivalente; identifica sucursales y productos destacados, y propone acciones concretas que un gerente pueda comprobar. No repitas información personal: no se envían nombres de empleados ni números de venta. Responde únicamente JSON válido con estas claves: `resumen` (string), `hallazgos` (array de strings, máximo 5), `recomendaciones` (array de strings, máximo 4), `advertencias` (array de strings, máximo 3).

La salida se solicita en formato JSON con `response_mime_type='application/json'`, temperatura baja y un límite acotado de tokens. Las cifras del dashboard siguen siendo las calculadas por SQL; el texto de IA solo interpreta y recomienda.

## Comparación de proveedores

| Proveedor | Encaje aquí | Consideración |
| --- | --- | --- |
| Gemini | Recomendado ahora. Ya existe en el proyecto y su API/modelos Flash-Lite están orientados a tareas rápidas y de costo controlado. | Revisar la política del nivel contratado: el uso de datos depende del nivel gratuito o pagado. |
| OpenAI API | Alternativa válida si las evaluaciones muestran mejor calidad o se requieren controles organizacionales concretos. | API y ChatGPT son productos/facturación distintos; los controles avanzados de retención pueden requerir elegibilidad y configuración. |
| Claude API | Alternativa válida si calidad narrativa o salidas estructuradas de Claude superan las pruebas internas. | Requiere integrar, asegurar y monitorear otro cliente y sus controles de retención; innecesario para esta primera versión. |

La elección no se basa solo en precio de lista: comparar con un conjunto fijo de reportes anonimizados, criterios de factualidad, calidad de acciones, latencia, disponibilidad, retención y costo por análisis. Consultar tarifas y términos oficiales vigentes antes de comprometerse, ya que cambian con el tiempo.
