"""Conciliación de cobros netos y reembolsos por fecha de movimiento."""
from datetime import datetime, timedelta
from decimal import Decimal
from models import db, Venta, CierreCaja, DevolucionVenta, PagoVenta
from config import get_cdmx_now, CDMX_TZ
from business_validation import money

METHODS = ('efectivo', 'tarjeta', 'transferencia')


def net_payments(venta):
    totals = dict.fromkeys(METHODS, Decimal('0'))
    if venta.pagos:
        for pago in venta.pagos:
            if pago.metodo_pago not in METHODS:
                raise ValueError('La venta tiene un método de pago no reconocido')
            totals[pago.metodo_pago] += money(pago.monto)
    elif venta.forma_pago in METHODS:
        totals[venta.forma_pago] = money(venta.total)
    elif venta.total == 0 and any(d.reembolsos for d in venta.devoluciones):
        pass  # Venta totalmente reembolsada; no quedan pagos netos.
    else:
        raise ValueError('La venta mixta no tiene desglose de pagos; corrígelo antes de devolver')
    if sum(totals.values()) != venta.total:
        raise ValueError('El desglose de pagos no coincide con el total neto de la venta; concilia sus pagos antes de devolver')
    return totals


def set_net_payments(venta, totals):
    # Mantener un registro por método; la suma representa lo retenido de la venta.
    for pago in list(venta.pagos):
        db.session.delete(pago)
    db.session.flush()
    db.session.expire(venta, ['pagos'])
    for method, amount in totals.items():
        if amount > 0:
            db.session.add(PagoVenta(venta_id=venta.id, metodo_pago=method, monto=amount))
    db.session.flush()
    db.session.expire(venta, ['pagos'])


def validate_refunds(data, total, available):
    if not isinstance(data, dict) or not data or set(data) - set(METHODS):
        raise ValueError('Indica el reembolso por efectivo, tarjeta o transferencia')
    refunds = {method: money(amount, 'Reembolso') for method, amount in data.items()}
    if sum(refunds.values()) != total:
        raise ValueError('La suma de reembolsos debe coincidir con el importe de la devolución')
    if any(amount > available[method] for method, amount in refunds.items()):
        raise ValueError('El reembolso supera el saldo disponible del método de pago')
    return {method: amount for method, amount in refunds.items() if amount > 0}


def ensure_cash_open(employee_id, branch_id, day=None):
    day = day or get_cdmx_now().date()
    cierre = CierreCaja.query.filter_by(empleado_id=employee_id, sucursal_id=branch_id, fecha=day).with_for_update().first()
    if cierre and cierre.estado == 'cerrado':
        raise ValueError('La caja de este empleado ya está cerrada; no se puede modificar con un reembolso')


def refresh_cash(cierre):
    start = CDMX_TZ.localize(datetime.combine(cierre.fecha, datetime.min.time()))
    end = start + timedelta(days=1)
    sales = Venta.query.filter(Venta.cajero_id == cierre.empleado_id,
        Venta.sucursal_id == cierre.sucursal_id, Venta.created_at >= start, Venta.created_at < end).all()
    totals = dict.fromkeys(METHODS, Decimal('0'))
    cierre.total_ventas = sum((v.total for v in sales), Decimal('0'))
    for sale in sales:
        # Pagos guardados son netos. Reincorporar reembolsos identificados para
        # reconstruir el cobro original, sin atribuirlo al día del reembolso.
        if sale.pagos:
            for payment in sale.pagos:
                if payment.metodo_pago in totals:
                    totals[payment.metodo_pago] += payment.monto
        elif sale.forma_pago in totals:
            totals[sale.forma_pago] += sale.total
        for refund in sale.devoluciones:
            for method, amount in (refund.reembolsos or {}).items():
                totals[method] += Decimal(str(amount))
    refunds = DevolucionVenta.query.join(Venta).filter(
        DevolucionVenta.caja_empleado_id == cierre.empleado_id,
        Venta.sucursal_id == cierre.sucursal_id,
        DevolucionVenta.fecha_movimiento == cierre.fecha).all()
    refunded = dict.fromkeys(METHODS, Decimal('0'))
    for refund in refunds:
        for method, amount in (refund.reembolsos or {}).items():
            refunded[method] += Decimal(str(amount))
    cierre.total_efectivo = totals['efectivo']
    cierre.reembolsos_efectivo = refunded['efectivo']
    cierre.total_tarjeta = totals['tarjeta'] - refunded['tarjeta']
    cierre.total_transferencia = totals['transferencia'] - refunded['transferencia']


def refresh_open_cash(employee_id, branch_id):
    cierre = CierreCaja.query.filter_by(empleado_id=employee_id, sucursal_id=branch_id,
                                       fecha=get_cdmx_now().date(), estado='abierto').first()
    if cierre:
        refresh_cash(cierre)
