# Características del punto de venta

En **Administrador → Características** se elige un único contenido global:

- **Productos recientes**: conserva el panel existente (opción inicial).
- **Competencia mensual**: sustituye ese panel por barras comparativas de las sucursales activas.
- **Ocultar ambos**: no muestra ninguno de los dos contenidos.

La búsqueda de productos y el carrito permanecen disponibles en cualquiera de los modos. El ajuste se guarda en la base de datos y aplica a todas las sucursales y usuarios. Se actualiza al entrar en Ventas, después de una venta y cada 30 segundos mientras se muestra Ventas.

La competencia compara la suma de `Venta.total` del mes calendario actual, en horario de Ciudad de México. Ese total ya descuenta las devoluciones; los egresos de caja no afectan la competencia. No incluye cobros de reparaciones registrados únicamente como seguimiento. La gráfica se reinicia con el nuevo mes y señala a todas las sucursales empatadas en cabeza. Sin ventas no marca un ganador.

Se muestran nombres y barras sin importes, porcentajes visibles, ejes numéricos ni información numérica al pasar el cursor. El endpoint entrega únicamente proporciones para dibujar las barras; no entrega importes de ventas.

Migración: `010_caracteristicas_ventas.py`. El proceso existente `python railway_migrate.py` la aplica en local/producción y conserva una selección previamente guardada. No se calculan ni se pagan bonos automáticamente.
