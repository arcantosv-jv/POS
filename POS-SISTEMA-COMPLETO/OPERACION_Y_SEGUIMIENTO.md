# Operación y seguimiento

## Devoluciones y caja

- El administrador registra el importe a devolver por efectivo, tarjeta y/o transferencia. La suma debe coincidir con los productos devueltos y no superar el saldo de cada método de la venta.
- Los pagos de la venta conservan el saldo neto después del reembolso. No se permite reemplazar el desglose de una venta con reembolsos registrados.
- El efectivo esperado suma el efectivo reportado acumulado de los turnos anteriores de la sucursal más los cobros en efectivo del turno actual, menos sus reembolsos y egresos. Los movimientos pendientes de la sucursal se asignan una sola vez al confirmar el cierre, aunque cambie el cajero.
- Una devolución de una venta anterior afecta la caja del día del reembolso. En el cierre, el reembolso de una venta de un cierre anterior reduce el total neto del cierre que registra esa salida. Los reportes generales de ventas mantienen la fecha original de la venta.
- Una caja cerrada conserva sus cifras. Para registrar más movimientos se puede iniciar otro cierre del mismo día; las correcciones de efectivo y egresos se aplican al cierre seleccionado. Revertir una devolución exige que sea del día, que exista una caja abierta, que el reembolso aún no pertenezca a un cierre confirmado y que exista inventario suficiente.
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


## Varios cierres en un día

Después de confirmar un cierre, «Iniciar otro cierre de caja» abre un formulario limpio con los movimientos pendientes del día. Volver a pulsar el botón no crea otra caja abierta. Cada venta y cada reembolso se vincula a un solo cierre al confirmarlo. Las ventas, egresos y reembolsos pertenecen únicamente a ese turno. El efectivo reportado es el conteo físico acumulado de la sucursal en el día, incluidos los turnos anteriores. Por ejemplo: primer turno reporta $500, segundo vende $300 y reporta $800; el tercero recibe $800, no $1,300. El historial superior permite desplegar cada cierre y consultar cajero, pagos, egresos y productos.

Administrador → Cierres de Caja agrupa por fecha, muestra la cantidad de cierres y suma sus totales netos confirmados. Cada cierre mantiene su detalle de empleado, sucursal, pagos, egresos y productos. El filtro de sucursal también limita los totales de los grupos.

La migración `011_multiples_cierres.py` añade las asociaciones y vincula movimientos históricos según empleado, sucursal, día y hora de confirmación, sin cambiar los importes guardados. Si un cierre histórico no tiene hora de confirmación, usa el día completo. Los movimientos posteriores quedan sin asignar. El proceso habitual `python railway_migrate.py` aplica esta revisión en local y producción.


## Efectivo acumulado y zona horaria

La migración `012_efectivo_acumulado.py` guarda `efectivo_inicial` en cada cierre. Los cierres históricos conservan NULL para identificar sus reportes individuales, sin cambiar cifras ni diferencias. Al comenzar un turno se suman los reportes anteriores descontando el efectivo que ya habían recibido. Si se corrige un cierre anterior, se recalculan los saldos iniciales y diferencias de los siguientes, conservando sus conteos físicos y movimientos.

Los turnos se agrupan por sucursal y fecha de `America/Mexico_City`. El arrastre empieza en cero al cambiar el día en CDMX. Las horas se muestran explícitamente en esa zona, independientemente del navegador o Railway. En PostgreSQL, la migración convierte `ventas.created_at` a `timestamp with time zone`, reconstruyendo el instante con la zona de la sesión que se usaba para guardar las fechas; los límites del día se consultan con zona CDMX. No se resta un número fijo de horas a los registros.

Pruebas adicionales:

```sh
.venv/bin/python -m unittest discover -s tests -q
node tests/test_frontend_cierres.js
```

Incluyen tres turnos con cambio de cajero, faltantes, egresos, correcciones, cierres históricos, movimientos compartidos sin duplicación, aislamiento entre sucursales y cambio de fecha CDMX cuando UTC ya está en el día siguiente.


## Plazo para corregir cierres

El cajero puede corregir sus propios cierres hasta una hora después de la confirmación original, inclusive. La validación se realiza en el servidor y las correcciones no renuevan el plazo. También se permite cruzar medianoche CDMX dentro de esa hora: el cierre del día anterior aparece como editable, sin trasladar sus movimientos al nuevo día. Los cierres históricos sin hora de confirmación no son editables porque no se puede determinar su plazo.

## Comisiones

Admin → Características → «Habilitar Comisiones para empleados» controla el acceso global. Inicialmente está desactivado. El menú del empleado se actualiza al iniciar sesión, al recuperar el foco y cada 30 segundos. El servidor bloquea inmediatamente consulta, captura, edición y eliminación si está desactivado; admin conserva su acceso y los registros.

El empleado registra Celular o Tablet, costo de venta, método de pago (efectivo, tarjeta o transferencia) y nombre libre del empleado. El servidor asigna la sucursal, la cuenta que capturó y la fecha/hora CDMX. Cada empleado consulta los registros de su sucursal y puede editar o eliminar los que capturó mientras estén «No aprobada».

Admin consulta todas las sucursales, asigna la comisión en pesos, pulsa «Aprobada», corrige el importe o quita la aprobación. Un registro aprobado queda bloqueado para edición o eliminación por empleados. El nombre libre se muestra junto a la sucursal; la cuenta real de captura se conserva por separado. El botón «Actualizar» obtiene los cambios de aprobación. Ninguna comisión afecta ventas, stock o cierres de caja.

La migración `013_comisiones.py` crea la tabla y el interruptor. Se aplica con `.venv/bin/python railway_migrate.py`; Railway usa este mismo proceso antes de desplegar.

Pruebas: `.venv/bin/python -m unittest discover -s tests -q` y `node tests/test_frontend_comisiones.js`. Validan permisos, sucursales, aprobación reversible, bloqueo global, importes y fecha CDMX, además de la lógica del formulario y del menú.

## Accesos por usuario y sucursal

En **Admin → Usuarios → Accesos**, selecciona las acciones de cada apartado y las sucursales permitidas. «Ver» es necesario para habilitar otras acciones del apartado. La sucursal principal siempre debe estar incluida. Los catálogos de productos, categorías y reparaciones son globales: sus permisos de edición afectan al catálogo compartido.

Ejemplos:

- **Solo entradas de inventario:** activa Inventario → Ver y Registrar entradas. No actives Ajustar stock, Eliminar ni Exportar. No necesita permiso para crear productos; el buscador de productos existentes está disponible como parte del formulario.
- **Solo consultar cierres:** activa Consultar cierres de caja → Ver. No actives Realizar cierre de caja. Puede consultar los cierres de las sucursales asignadas sin modificar nada.
- **Varias sucursales:** selecciona las sucursales adicionales. El selector superior permite elegir la sucursal activa para registrar ventas, cierres y comisiones. Los filtros de consulta solo ofrecen sucursales permitidas.

Los administradores conservan acceso universal. La gestión de cuentas, sucursales y Características sigue siendo exclusiva de admin. Los empleados nuevos empiezan sin accesos: después de crearlos, configura sus permisos con el botón Accesos. La migración `014_permisos_usuario.py` deja los campos de usuarios existentes en NULL para conservar los accesos anteriores hasta que admin los configure explícitamente.

El servidor comprueba permisos vigentes en cada petición, incluso con un token emitido anteriormente. Se valida la sucursal solicitada, el identificador de los registros y se restringen las consultas, relaciones y reportes a las sucursales asignadas. Los cambios de accesos se reflejan en el menú al recuperar el foco y cada 30 segundos; la API los aplica desde la siguiente petición. Desactivar Comisiones en Características tiene prioridad sobre el permiso individual.

Se mantienen las reglas propias de cada operación: comisiones aprobadas bloqueadas, edición de comisiones solo por quien capturó y correcciones de cierre limitadas a una hora. La importación que modifica existencias requiere también Ajustar stock; Registrar entradas no permite modificar el mínimo de stock.

Pruebas específicas: `.venv/bin/python -m unittest discover -s tests -p test_permisos.py -v` y `node tests/test_frontend_permisos.js`. La revisión 014 se aplica con el mismo `railway_migrate.py` que ejecuta Railway antes del despliegue.

## Apartados

Migración `015_apartados.py` (local aplicada; Railway la ejecuta con el proceso normal de migración).

- Admin conserva acceso y puede consultar todas las sucursales. Los empleados solo consultan y operan apartados de su sucursal principal, aunque tengan acceso a otras en otros módulos.
- Habilitar en Administración → Características → Apartados. Después asignar en Usuarios → Accesos: Ver, Crear, Registrar abonos y Marcar entregada. Cancelar y registrar la devolución de dinero son exclusivos de admin.
- Campos: cliente, teléfono, empleado (texto abierto), sucursal, varios productos/cantidades, precio final capturado manualmente, anticipo, desglose efectivo/tarjeta/transferencia (combinables), observaciones y plazo de 15/30/45 días. Fechas CDMX. La cuenta real del usuario queda registrada en cada movimiento.
- Reservar disminuye `stocks.cantidad` (unidades disponibles) y aumenta `stocks.reservado`. Se permite registrar con existencias parciales o nulas; solo se reservan las unidades disponibles. Los faltantes iniciales se guardan por producto y solo se exponen a admin. Entregar requiere saldo cero, libera las unidades reservadas y descuenta únicamente las unidades adicionales disponibles, sin generar stock negativo. Se permite entregar aunque falten existencias registradas. La marca de faltantes iniciales se conserva para admin. La fecha y hora de entrega del historial se muestran en CDMX a empleado y admin, también para entregas anteriores. Cancelar devuelve únicamente las unidades efectivamente reservadas a disponibilidad y registra el motivo y dinero devuelto. Vencer no cancela ni libera inventario.
- Los anticipos y abonos permanecen fuera de ventas y caja hasta la entrega. Al entregar se crea una venta del día (CDMX) en la sucursal del apartado, atribuida al usuario que entrega, con todos los pagos acumulados; entra al corte como una venta normal. Dos o más métodos generan pago mixto, y un solo método conserva su tipo. La entrega, la venta y la liberación de reserva se guardan en una transacción y no pueden repetirse. La cancelación anterior a la entrega no genera venta ni movimientos de caja. La devolución registrada es constancia; no ejecuta transferencias bancarias. El historial muestra las cantidades devueltas; el abonado conserva los cobros originales.
- El precio inicia vacío y se captura manualmente para cada producto. Es el precio final por unidad, sin agregar impuestos del catálogo. Un cambio posterior del precio del catálogo no modifica el acuerdo. Para cambios de productos se cancela mediante admin y se crea un apartado nuevo; no hay edición destructiva del historial.
- Las ventas normales no pueden consumir unidades reservadas. Cuando existen reservas y la cantidad disponible es insuficiente, se rechaza la venta de esa cantidad. Se bloquean filas de stock durante reservas y ventas; no se permite eliminar un registro de stock que tenga reservas.

Pruebas:

```bash
.venv/bin/python -m unittest discover -s tests -p test_apartados.py
.venv/bin/python -m unittest discover -s tests -p test_migration_operacion.py
node tests/test_frontend_apartados.js
```

Admin dispone de la sección «Registrados sin existencias» en Apartados, con faltantes iniciales por producto. Empleados no reciben estos campos en la API ni ven la sección. No requiere otra migración: los datos se conservan en el detalle JSON; los apartados anteriores mantienen su reserva completa.

Este cambio aplica a nuevas entregas. No convierte automáticamente los apartados que ya estaban entregados antes de activarlo, para no alterar cortes históricos. El detalle muestra el ID de la venta creada.
