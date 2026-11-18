# Pronósticos de ventas

Disponible en el menú **Pronósticos de ventas**. Admin tiene acceso completo. En **Administración → Usuarios → Accesos**, habilitar:

- **Ver**: opciones, proyecciones guardadas, resultados reales e históricos mensuales.
- **Generar pronósticos**: crear nuevas versiones y solicitar la explicación de Gemini.
- **Administrar históricos manuales**: capturar o reemplazar un mes completo para una sucursal.

El usuario solo puede consultar sus sucursales autorizadas. Un pronóstico general que incluye sucursales no autorizadas no se muestra, ni siquiera parcialmente. Las solicitudes se validan en servidor.

## Uso

1. Elegir sucursal o todas las autorizadas, y próximos días, próximos meses o fechas futuras.
2. Pulsar **Generar pronóstico**. Se guarda una versión con importe y unidades, total y por categoría.
3. Consultar escenarios, gráfica, detalle diario e historial mensual utilizado. La explicación de Gemini se solicita después de guardar y se puede reintentar si falla.
4. Abrir una versión desde **Historial y resultados** para comparar sus cifras con las ventas reales. La comparación usa solo los días completos transcurridos y muestra error absoluto porcentual; si la venta real es cero, el porcentaje no aplica.

El horizonte empieza mañana, según CDMX, y admite hasta 24 meses (732 días). Las cifras de un pronóstico ya guardado no se editan. Una nueva generación crea otra versión.

## Histórico manual

En **Datos históricos**, elegir sucursal, mes completo anterior al actual y categorías con importe neto y unidades netas. El total mensual se calcula sumando las categorías. Indicar fuente/motivo y confirmar el reemplazo.

- Reemplaza **todo el mes de esa sucursal**, no se suma al sistema. Las categorías omitidas cuentan como cero.
- Descontar devoluciones al capturar los valores. No se vuelven a descontar las del sistema sobre el manual.
- Se distribuye uniformemente entre los días del mes porque no se conoce su distribución real; la pantalla lo advierte.
- Se conserva auditoría de cada versión manual (usuario, fecha, motivo, valores anteriores y nuevos).
- No altera ventas, caja, productos, inventario ni pronósticos anteriores.
- La comparación posterior usa ventas reales del sistema, sin reemplazos manuales.

## Cálculo y actualización

`pronostico_motor.py` implementa `promedio-semanal-ponderado-v1`: utiliza todos los días desde el primer dato hasta ayer, incluidos ceros, con peso exponencial (escala de 180 días), patrón semanal desde 28 días y tendencia de los últimos dos bloques de 28 días limitada y amortiguada. No modela explícitamente temporadas anuales, inflación ni promociones. Los escenarios usan dispersión histórica y amplitud creciente con el horizonte; **no son intervalos de confianza calibrados** ni garantías de ingreso. Menos de 90 días de historial genera advertencia de baja fiabilidad. Las unidades estimadas pueden ser decimales.

Los totales se obtienen sumando las categorías. Los importes son precio unitario por unidades netas (ventas, no utilidad). Las devoluciones se atribuyen al día original de la venta. Los apartados solo cuentan cuando su entrega genera una Venta; no se suman anticipos por separado. Se utiliza CDMX en los límites de fecha.

Tablas:

- `pronostico_estados`: controla si hay que reconstruir el resumen de una sucursal.
- `pronostico_resumenes`: importe y unidades netos por día, sucursal y categoría.
- `pronostico_historicos`: reemplazo mensual y auditoría manual.
- `pronosticos`: fechas, sucursales, resultados, histórico mensual utilizado, reemplazos aplicados, versión del algoritmo y explicación de IA.

La primera generación construye los resúmenes. Cambios ORM en ventas, detalles, devoluciones, productos o subcategorías invalidan el caché dentro de la misma transacción. Al generar o comparar se actualiza lo pendiente; las lecturas sin cambios reutilizan la tabla. Cambios SQL externos a la aplicación requieren invalidar el caché explícitamente:

```sql
UPDATE pronostico_estados SET pendiente = TRUE;
```

Gemini usa la clave y selección de modelos existentes. Solo recibe agregados de ventas y nombres de categorías; no clientes, empleados, tickets ni datos de pago. La explicación es texto plano y nunca modifica los resultados estadísticos. Una llamada puede consumir la cuota de Gemini existente.

## Migración y pruebas

Migración `migrations/versions/018_pronosticos.py`. Railway ejecuta el mecanismo existente de `railway_migrate.py` al desplegar. No requiere variables ni dependencias nuevas.

```sh
.venv/bin/python railway_migrate.py
.venv/bin/python -m unittest discover -s tests -p 'test_pronosticos.py'
.venv/bin/python -m unittest discover -s tests -p 'test_migration_operacion.py'
node tests/test_frontend_pronosticos.js
```

Para comprobar plantillas con el runtime Vue disponible localmente:

```sh
node tests/test_frontend_plantillas.js /ruta/vue.global.prod.js
```
