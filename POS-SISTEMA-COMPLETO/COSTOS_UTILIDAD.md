# Costos de compra y utilidad

Disponible exclusivamente para administradores, tanto en pantalla como en la API. Los permisos de empleados no permiten delegar este acceso.

## Asignar costos

1. Abre **Administración → Costos de compra → Reglas de costo**. Se incluyen las 12 reglas iniciales autorizadas. Puedes editar sus importes y criterios o agregar otras.
2. En **Revisar costos de productos**, inicia una revisión del catálogo.
3. Pulsa **Continuar revisión**. El servicio de IA existente asocia artículos con reglas; el servidor toma el importe de la regla, nunca de la IA. Cada lote guarda el avance.
4. Revisa las propuestas. Los casos ambiguos quedan pendientes y requieren **Editar costo**, importe y motivo.
5. Pulsa **Aplicar cambios**: guarda únicamente las propuestas listas. No cambia nombres, precios de venta, categorías ni inventario.

Los productos con costo se conservan automáticamente. Para corregir uno explícitamente, usa el filtro Todos o Costo conservado y edítalo antes de aplicar. Un costo de cero es válido y distinto de un costo sin capturar.

Si una regla o producto cambia durante la revisión, la aplicación se rechaza completa para evitar sobrescribir cambios. Inicia otra revisión o confirma manualmente la propuesta cuando corresponda. Las revisiones anteriores permanecen consultables.

## Utilidad

Abre **Reportes → Utilidad**. Filtra fechas de CDMX y sucursal, y agrupa por producto, categoría o sucursal.

- Utilidad bruta = importe de las unidades vendidas menos su costo de compra, descontando unidades devueltas.
- El importe usa el precio unitario registrado en la venta, coherente con el total cobrado; no suma nuevamente el impuesto informativo.
- Las ventas nuevas, incluidos apartados entregados, guardan el costo disponible al vender.
- Los detalles sin costo guardado usan el costo actual como estimación; se identifican por separado.
- Si tampoco hay costo actual, sus ingresos se excluyen de la utilidad y se muestran como pendientes de costo. No se supone costo cero.
- Las devoluciones reducen la venta original aunque se hayan registrado después. Los agrupamientos usan la clasificación actual del producto.
- No incluye sueldos, renta, comisiones ni otros gastos.

## Migración y validación

La migración `019_costos_utilidad.py` agrega costos opcionales, reglas y revisiones; no asigna costos a productos ni modifica ventas históricas. `railway_migrate.py` la aplica en el flujo existente de despliegue. No necesita nuevas variables: reutiliza `GEMINI_API_KEY` y la selección de modelos existente.

```sh
.venv/bin/python railway_migrate.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -p 'test_costos.py'
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -p 'test_migration_operacion.py'
node tests/test_frontend_permisos.js
```

Las pruebas de IA usan respuestas simuladas; no consumen llamadas al proveedor.
