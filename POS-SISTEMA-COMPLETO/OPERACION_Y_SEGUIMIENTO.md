# Operación y seguimiento

## Devoluciones y caja

- El administrador registra el importe a devolver por efectivo, tarjeta y/o transferencia. La suma debe coincidir con los productos devueltos y no superar el saldo de cada método de la venta.
- Los pagos de la venta conservan el saldo neto después del reembolso. No se permite reemplazar el desglose de una venta con reembolsos registrados.
- El efectivo esperado se calcula como cobros en efectivo menos reembolsos del día menos egresos. El reembolso se asigna al empleado que realizó la venta, en su sucursal.
- Una devolución de una venta anterior afecta la caja del día del reembolso. El total neto de ventas sigue asociado a la fecha de la venta, como antes.
- Una caja cerrada conserva sus cifras. No admite nuevos reembolsos en ese día; las correcciones de efectivo y egresos siguen disponibles. Revertir una devolución exige que sea del día, que la caja siga abierta y que exista inventario suficiente.
- Las devoluciones históricas sin desglose quedan señaladas como «método no registrado». La migración no inventa su método ni altera sus importes. Si los pagos mixtos históricos no coinciden con la venta neta, requieren conciliación antes de registrar nuevas devoluciones.
- Los productos vendidos sin stock no agregan existencias ficticias al devolverlos.

## Egresos

El cierre y su corrección admiten varios movimientos con importe positivo, concepto obligatorio y referencia opcional de comprobante (folio o texto; no se adjuntan archivos). Se muestra cada movimiento al administrador y se suma automáticamente. Los egresos anteriores se presentan como un solo movimiento. El total de ventas no se reduce por estos egresos.

## Reparaciones

- Estados: registrada, en diagnóstico, esperando refacción, en reparación, lista para entregar, entregada y cancelada.
- Diagnóstico, técnico responsable de texto libre, fecha prometida, filtros de estado y atrasos.
- Anticipos/abonado acumulado y saldo pendiente. No se permiten importes negativos ni abonos superiores al costo. Este registro de seguimiento no genera ventas ni movimientos de caja; registrar el cobro sigue siendo un proceso separado.
- Editar actualiza la reparación existente; no crea otra. Se conserva un historial con usuario, fecha y cambios, incluido el abonado acumulado.
- Los empleados consultan y editan sus reparaciones. El administrador puede gestionar todas y confirmar la entrega.

## Compatibilidades

Las consultas se guardan con fecha, modelo, origen y resultado. Los empleados ven su historial y el administrador puede consultar el conjunto. Se pueden recuperar resultados y filtrar por modelo.

La búsqueda normal prioriza compatibilidades comprobadas por el personal y después consultas previas de hasta 30 días. El botón «Consultar nuevas sugerencias de IA» solicita un resultado nuevo. Si el proveedor utiliza la base local de respaldo, se registra ese origen.

Para verificar una compatibilidad se requieren notas de la prueba y confirmar explícitamente que se comprobó físicamente. Las sugerencias no se marcan como verificadas automáticamente. El autor o un administrador puede retirar una verificación. Al volver a consultar el historial se muestra su condición vigente.

## Migración y verificación

Revisión `009_operacion_y_seguimiento.py`, posterior a `008`. Se aplica con:

```sh
.venv/bin/python railway_migrate.py
```

Railway ya ejecuta el mismo proceso antes del despliegue y Docker al arrancar. El proceso reconoce bases heredadas y comprueba las nuevas columnas/tablas. No elimina datos históricos.

Pruebas de servidor y migración en bases temporales:

```sh
.venv/bin/python -m unittest discover -s tests -q
node --check static/components.js
node tests/test_frontend_operacion.js
```

Las pruebas de JavaScript validan la lógica de los componentes; no sustituyen una comprobación visual en navegador.
