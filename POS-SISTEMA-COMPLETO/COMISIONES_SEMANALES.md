# Comisiones por semana

En **Comisiones → Pagos semanales**, admin crea un empleado con nombre, sucursal y día de pago (lunes a domingo). No es una cuenta de acceso: los usuarios de la sucursal pueden consultar los empleados de esa sucursal.

La captura ahora selecciona al empleado del catálogo. Los registros anteriores no se vinculan por coincidencia de nombre: admin elige **Empleado del catálogo** en la tabla y guarda el monto/aprobación. Los registros sin vínculo se cuentan en una advertencia y no se incluyen en pagos semanales.

La semana usa la **fecha de venta**, aunque la comisión se registre después. Para registros históricos sin fecha de venta, se usa su fecha de registro. El corte incluye el día de pago. Por ejemplo, para el lunes 23/11/2026 abarca del martes 17 al lunes 23. Para viernes 27, abarca del sábado 21 al viernes 27.

- **Acumulado sin pagar de la semana:** importes capturados de las comisiones de ese período; las que aún no tienen monto se indican aparte.
- **Aprobado por pagar:** comisiones aprobadas de períodos ya terminados, incluidas las atrasadas. El día de pago sí se incluye, hasta el momento de registrar la entrega.
- **Registrar pago entregado:** exclusivo de admin; confirma una entrega real por el importe mostrado. Guarda fecha actual de CDMX, empleado, administrador, período, importe y detalle. No mueve ventas ni caja.
- **Historial / total entregado:** usa fecha real de pago, con filtros independientes de la fecha de venta o registro. Los totales consideran todas las páginas.

Se permite registrar anticipadamente el total aprobado de la semana mostrada más atrasos, así como pagos después del día programado. La confirmación utiliza las mismas comisiones que el total mostrado. Después de registrar la entrega, ese corte queda cerrado. Una comisión registrada o aprobada después pasa al siguiente corte semanal. Reintentos o formularios desactualizados no vuelven a pagar comisiones ya entregadas. Una comisión pagada no permite cambiar monto, empleado o aprobación. Cambiar el nombre o día de pago del empleado no altera pagos anteriores.

Los registros aprobados anteriormente **no se marcan como pagados automáticamente**. Verifica su situación antes de registrar entregas.

La migración **021** agrega las tablas y vínculos opcionales; se ejecuta con el flujo existente de Railway:

```sh
.venv/bin/python railway_migrate.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -p 'test_comisiones*.py'
node tests/test_frontend_comisiones.js
```
