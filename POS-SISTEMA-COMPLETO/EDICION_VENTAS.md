# Corrección de ventas antes del cierre

En **Administración → Usuarios → Accesos**, habilita **Ventas del día → Ver y Editar**. Admin dispone del acceso por defecto. Los empleados existentes no reciben automáticamente el nuevo permiso.

En **Ventas del día → Editar venta**, se abre un modal para cambiar el producto, la cantidad y el precio unitario de cada renglón. El precio es el importe de venta, no el costo de compra. Se mantienen los renglones originales: no se agregan ni eliminan renglones desde esta corrección.

Distribuye el nuevo total entre efectivo, tarjeta y transferencia e indica un motivo obligatorio. Al guardar se actualizan inventario, total, impuestos informativos y pagos en una sola transacción. Se conserva usuario, fecha CDMX, motivo y valores anteriores/nuevos en **Historial de correcciones**.

- Solo ventas del día actual de CDMX, aún sin cierre asignado.
- Un cierre posterior no habilita ventas ya incluidas en cierres anteriores.
- No se editan ventas con devoluciones, comisiones asignadas o provenientes de apartados.
- Se devuelve al inventario únicamente lo descontado originalmente; la nueva salida sin existencias se permite y se marca como venta sin stock, sin consumir unidades reservadas.
- Si solo cambia el precio, se conserva la instantánea de costo de compra. Al cambiar producto, se utiliza el costo del producto correcto.
- Se rechazan formularios desactualizados para evitar sobrescribir otra modificación.
- El modal permite consultar el historial aun si la venta está bloqueada.

La migración **020** agrega `ventas.ediciones`, sin modificar ventas existentes. El flujo de `railway_migrate.py` la ejecuta al desplegar.

Pruebas:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -p 'test_edicion_ventas.py'
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -p 'test_migration_operacion.py'
node tests/test_frontend_edicion_ventas.js
```
