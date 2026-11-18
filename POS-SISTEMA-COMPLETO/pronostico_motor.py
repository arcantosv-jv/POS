"""Pronóstico estadístico reproducible; Gemini no calcula ni altera cifras."""
import calendar
import math
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from statistics import mean
from sqlalchemy import event, select, func, update, delete
from sqlalchemy.orm import Session
from models import (db, Venta, DetalleVenta, DevolucionVenta, Producto, Subcategoria,
                    EstadoResumenPronostico, ResumenPronostico, HistoricoPronostico)
from config import get_cdmx_now
from comisiones_ventas import fecha_cdmx

VERSION = 'promedio-semanal-ponderado-v1'


@event.listens_for(Session, 'after_flush')
def invalidar_resumen(session, context):
    # También cubre cancelaciones de devolución, entregas y reclasificaciones.
    if any(isinstance(row, (Venta, DetalleVenta, DevolucionVenta, Producto, Subcategoria))
           for row in session.new.union(session.dirty).union(session.deleted)):
        session.connection().execute(update(EstadoResumenPronostico.__table__).values(pendiente=True))


def refrescar(sucursales):
    """Bloqueo del caché: una venta concurrente lo vuelve a marcar pendiente al confirmar."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    insert = pg_insert if db.engine.dialect.name == 'postgresql' else sqlite_insert
    table = EstadoResumenPronostico.__table__
    for sid in sorted(sucursales):
        db.session.execute(insert(table).values(sucursal_id=sid, pendiente=True).on_conflict_do_nothing())
        state = EstadoResumenPronostico.query.filter_by(sucursal_id=sid).with_for_update().one()
        if not state.pendiente:
            continue
        v, d, p, sub, ret = (m.__table__ for m in (Venta, DetalleVenta, Producto, Subcategoria, DevolucionVenta))
        returns = select(ret.c.detalle_venta_id, func.sum(ret.c.cantidad_devuelta).label('qty')).group_by(ret.c.detalle_venta_id).subquery()
        rows = db.session.execute(select(v.c.created_at, sub.c.categoria_id, d.c.cantidad,
            d.c.precio_unitario, returns.c.qty).select_from(v.join(d, d.c.venta_id == v.c.id)
            .join(p, p.c.id == d.c.producto_id).outerjoin(sub, sub.c.id == p.c.subcategoria_id)
            .outerjoin(returns, returns.c.detalle_venta_id == d.c.id)).where(v.c.sucursal_id == sid))
        buckets = defaultdict(lambda: [Decimal('0'), 0])
        for fecha, categoria, cantidad, precio, devuelta in rows:
            key = (fecha_cdmx(fecha).date(), categoria or '')
            units = max(0, cantidad - (devuelta or 0))
            buckets[key][0] += precio * units
            buckets[key][1] += units
        db.session.execute(delete(ResumenPronostico).where(ResumenPronostico.sucursal_id == sid))
        if buckets:
            db.session.execute(ResumenPronostico.__table__.insert(), [dict(sucursal_id=sid, fecha=day,
                categoria_id=cat, importe=val[0], unidades=val[1]) for (day, cat), val in buckets.items()])
        state.pendiente = False
        state.actualizado = get_cdmx_now()
    db.session.flush()


def serie(sucursales, hasta, manual=True):
    """Mes manual completo reemplaza todas las categorías de ese mes/sucursal."""
    overrides = HistoricoPronostico.query.filter(HistoricoPronostico.sucursal_id.in_(sucursales)).all() if manual else []
    reemplazos = {(r.sucursal_id, r.mes) for r in overrides}
    data = defaultdict(lambda: [0.0, 0.0])
    for row in ResumenPronostico.query.filter(ResumenPronostico.sucursal_id.in_(sucursales), ResumenPronostico.fecha <= hasta).all():
        if (row.sucursal_id, row.fecha.strftime('%Y-%m')) not in reemplazos:
            val = data[(row.fecha, row.categoria_id)]
            val[0] += float(row.importe); val[1] += row.unidades
    usados = []
    for row in overrides:
        first = date.fromisoformat(row.mes + '-01')
        if first > hasta:
            continue
        days = calendar.monthrange(first.year, first.month)[1]
        usados.append(dict(sucursal_id=row.sucursal_id, mes=row.mes, categorias=row.categorias))
        for offset in range(days):
            day = first + timedelta(days=offset)
            if day > hasta: break
            for item in row.categorias:
                val = data[(day, item['categoria_id'])]
                val[0] += float(item['importe']) / days
                val[1] += item['unidades'] / days
    return data, usados


def dias(inicio, fin):
    return [inicio + timedelta(days=i) for i in range((fin - inicio).days + 1)]


def estimar(values, fechas, futuras):
    """Todo el historial, decaimiento de 180 días, patrón semanal y tendencia amortiguada."""
    n = len(values)
    weights = [math.exp(-(n-1-i)/180) for i in range(n)]
    base = sum(v*w for v, w in zip(values, weights)) / sum(weights)
    weekly = {}
    for dow in range(7):
        indices = [i for i, d in enumerate(fechas) if d.weekday() == dow]
        weekly[dow] = (sum(values[i]*weights[i] for i in indices)/sum(weights[i] for i in indices)) if n >= 28 and indices else base
    recent = mean(values[-28:])
    previous = mean(values[-56:-28]) if n >= 56 else recent
    trend = max(-.3, min(.3, (recent-previous)/previous)) if previous > 0 and n >= 56 else 0
    residual = mean(abs(v-weekly[d.weekday()]) for v, d in zip(values, fechas))
    output = []
    for day in futuras:
        distance = (day-fechas[-1]).days
        expected = max(0, weekly[day.weekday()] * (1 + trend * min(distance/28, 2)))
        # Escenarios orientativos, NO intervalos de confianza calibrados.
        spread = max(expected * (.5 if n < 90 else .25), residual) * math.sqrt(1 + distance/180)
        output.append([round(max(0, expected-spread), 2), round(expected, 2), round(expected+spread, 2)])
    return output


def generar(data, inicio, fin, corte, nombres):
    if not data:
        raise ValueError('No hay historial de días completos para generar un pronóstico.')
    first = min(day for day, cat in data)
    fechas = dias(first, corte)
    futuras = dias(inicio, fin)
    if not fechas:
        raise ValueError('Se necesita al menos un día completo de historial.')
    cats = sorted({cat for _, cat in data})
    categorias = []
    for cat in cats:
        values = [data.get((day, cat), [0, 0]) for day in fechas]
        importes = estimar([v[0] for v in values], fechas, futuras)
        unidades = estimar([v[1] for v in values], fechas, futuras)
        categorias.append(dict(id=cat, nombre=nombres.get(cat, 'Sin categoría'),
            dias=[dict(fecha=day.isoformat(), importe=importes[i], unidades=unidades[i]) for i, day in enumerate(futuras)],
            historico=[dict(fecha=day.isoformat(), importe=values[i][0], unidades=values[i][1]) for i, day in enumerate(fechas)]))
    total = dict(id='total', nombre='Total', dias=[], historico=[])
    for field, ds in [('dias', futuras), ('historico', fechas)]:
        for i, day in enumerate(ds):
            if field == 'dias':
                entry = {metric: [round(sum(c[field][i][metric][j] for c in categorias), 2) for j in range(3)] for metric in ('importe', 'unidades')}
            else:
                entry = {metric: sum(c[field][i][metric] for c in categorias) for metric in ('importe', 'unidades')}
            total[field].append(dict(fecha=day.isoformat(), **entry))
    for c in [total, *categorias]:
        c['totales'] = {metric: [round(sum(d[metric][j] for d in c['dias']), 2) for j in range(3)] for metric in ('importe', 'unidades')}
        # Guardar historial mensual completo y últimos 60 días para gráfica.
        meses = defaultdict(lambda: dict(importe=0, unidades=0))
        for d in c['historico']:
            for metric in ('importe', 'unidades'): meses[d['fecha'][:7]][metric] += d[metric]
        c['meses'] = [dict(mes=k, **{m: round(v, 2) for m, v in vals.items()}) for k, vals in sorted(meses.items())]
        c['historico'] = [dict(fecha=d['fecha'], importe=round(d['importe'], 2), unidades=round(d['unidades'], 2)) for d in c['historico'][-60:]]
    warnings = ['Escenarios orientativos; no son ingresos garantizados ni intervalos de confianza.',
                'No incluye utilidad, inflación, promociones ni estacionalidad anual explícita.',
                'Las devoluciones se descuentan del día de la venta original; los días sin registro valen cero.']
    if len(fechas) < 90: warnings.append('Historial menor a 90 días: estimación de baja fiabilidad.')
    if (fin-corte).days > 90: warnings.append('El horizonte supera 90 días; la incertidumbre aumenta con la distancia.')
    return dict(version=VERSION, corte=corte.isoformat(), historial_desde=first.isoformat(), dias_historial=len(fechas),
        advertencias=warnings, total=total, categorias=categorias)
