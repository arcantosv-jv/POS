#!/usr/bin/env python3
"""Exportar, revisar y aplicar clasificación por código; sin importar app.py."""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask
from models import db, Producto, Categoria, Subcategoria

CAMPOS = ['codigo', 'nombre', 'subcategoria_id_actual', 'categoria_actual',
          'subcategoria_actual', 'categoria_destino', 'subcategoria_destino']


def exportar(archivo):
    productos = Producto.query.order_by(Producto.codigo).all()
    with open(archivo, 'x', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS)
        writer.writeheader()
        for p in productos:
            sub = p.subcategoria
            writer.writerow(dict(zip(CAMPOS, [p.codigo, p.nombre, p.subcategoria_id,
                sub.categoria.nombre, sub.nombre, '', ''])))


def proponer_automaticamente(archivo, pendientes):
    from clasificacion_productos import proponer, normalizar
    destinos = {}
    for sub in Subcategoria.query.join(Categoria).filter(
            Subcategoria.is_active.is_(True), Categoria.is_active.is_(True)).all():
        clave = (normalizar(sub.categoria.nombre), normalizar(sub.nombre))
        destinos.setdefault(clave, []).append(sub)
    propuestas, revisar, correctos = [], [], 0
    for p in Producto.query.order_by(Producto.codigo).all():
        actual = p.subcategoria
        fila = dict(zip(CAMPOS, [p.codigo, p.nombre, p.subcategoria_id,
            actual.categoria.nombre, actual.nombre, '', '']))
        sugerencia = proponer(p.nombre)
        if not sugerencia:
            revisar.append({**fila, 'motivo': 'Sin regla inequívoca; conservar y revisar si es necesario'})
            continue
        opciones = destinos.get(tuple(normalizar(x) for x in sugerencia), [])
        if len(opciones) != 1:
            revisar.append({**fila, 'motivo': 'Destino inexistente o ambiguo: ' + ' / '.join(sugerencia)})
            continue
        destino = opciones[0]
        if destino.id == p.subcategoria_id:
            correctos += 1
            continue
        fila['categoria_destino'] = destino.categoria.nombre
        fila['subcategoria_destino'] = destino.nombre
        propuestas.append(fila)
    # Nunca sobrescribir archivos de una revisión anterior.
    if Path(archivo).exists() or Path(pendientes).exists() or Path(archivo).resolve() == Path(pendientes).resolve():
        raise ValueError('Utiliza dos archivos de salida nuevos y distintos')
    for ruta, filas, campos in [(archivo, propuestas, CAMPOS), (pendientes, revisar, CAMPOS + ['motivo'])]:
        with open(ruta, 'x', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=campos)
            writer.writeheader(); writer.writerows(filas)
    print(f'{len(propuestas)} correcciones propuestas, {correctos} ya correctos, {len(revisar)} sin clasificación automática.')
    print('No se modificó la base. Usa revisar y aplicar sobre el archivo de propuestas.')


def automatizar(carpeta, aplicar=False):
    """Una ejecución completa, con archivos únicos para auditoría y respaldo."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=False)
    propuestas = carpeta / 'propuestas.csv'
    pendientes = carpeta / 'pendientes.csv'
    proponer_automaticamente(propuestas, pendientes)
    cambios = ejecutar(propuestas, aplicar, carpeta / 'respaldo.json')
    with (carpeta / 'resultado.json').open('x', encoding='utf-8') as f:
        json.dump({'modo': 'aplicado' if aplicar else 'simulacion',
                   'cantidad_cambios': len(cambios), 'cambios': cambios},
                  f, ensure_ascii=False, indent=2)
    return cambios


def planificar(archivo):
    cambios, vistos = [], set()
    with open(archivo, encoding='utf-8-sig', newline='') as f:
        lector = csv.DictReader(f)
        if not set(CAMPOS).issubset(lector.fieldnames or []):
            raise ValueError('Usa el CSV generado por exportar, conservando sus columnas.')
        for numero, row in enumerate(lector, 2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f'Fila {numero}: columnas incorrectas')
            row = {k: v.strip() for k, v in row.items()}
            categoria, subcategoria = row['categoria_destino'], row['subcategoria_destino']
            if not categoria and not subcategoria:
                continue
            if not categoria or not subcategoria:
                raise ValueError(f'Fila {numero}: completa ambos destinos')
            codigo = row['codigo']
            if codigo in vistos:
                raise ValueError(f'Código repetido: {codigo}')
            vistos.add(codigo)
            p = Producto.query.filter_by(codigo=codigo).with_for_update().first()
            if not p:
                raise ValueError(f'Producto inexistente: {codigo}')
            if p.nombre != row['nombre']:
                raise ValueError(f'{codigo}: el nombre cambió desde la revisión; vuelve a generar propuestas')
            destinos = Subcategoria.query.join(Categoria).filter(
                Categoria.nombre == categoria, Categoria.is_active.is_(True),
                Subcategoria.nombre == subcategoria, Subcategoria.is_active.is_(True)).all()
            if len(destinos) != 1:
                raise ValueError(f'{codigo}: destino inexistente, inactivo o ambiguo: {categoria} / {subcategoria}')
            destino = destinos[0]
            if p.subcategoria_id == destino.id:
                continue  # Permite repetir un archivo ya aplicado.
            if p.subcategoria_id != row['subcategoria_id_actual']:
                raise ValueError(f'{codigo}: cambió desde la exportación; vuelve a exportar y revisar')
            cambios.append({'codigo': codigo, 'nombre': p.nombre,
                'subcategoria_id_anterior': p.subcategoria_id, 'subcategoria_id_nueva': destino.id,
                'antes': f'{p.subcategoria.categoria.nombre} / {p.subcategoria.nombre}',
                'despues': f'{categoria} / {subcategoria}'})
    return cambios


def ejecutar(archivo, aplicar=False, respaldo=None):
    try:
        cambios = planificar(archivo)
        for c in cambios:
            print(f"{c['codigo']} | {c['nombre']} | {c['antes']} -> {c['despues']}")
        if aplicar and cambios:
            if not respaldo:
                raise ValueError('Especifica --respaldo con un archivo nuevo')
            with open(respaldo, 'x', encoding='utf-8') as f:
                json.dump({'fecha_utc': datetime.now(timezone.utc).isoformat(), 'cambios': cambios}, f, ensure_ascii=False, indent=2)
            for c in cambios:
                p = Producto.query.filter_by(codigo=c['codigo']).one()
                p.subcategoria_id = c['subcategoria_id_nueva']
            db.session.commit()
        else:
            db.session.rollback()
        print(f"{len(cambios)} cambios {'aplicados' if aplicar else 'propuestos (sin modificar datos)' }.")
        return cambios
    except Exception:
        db.session.rollback()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='comando', required=True)
    ia = sub.add_parser('ia', help='Vista previa con Gemini, sin modificar la base')
    ia.add_argument('--salida', required=True)
    aprobar = sub.add_parser('aplicar-ia', help='Aplicar revisión; crear solo destinos aprobados')
    aprobar.add_argument('--salida', required=True)
    automatico = sub.add_parser('automatico', help='Clasificar y corregir por nombre sin editar CSV')
    automatico.add_argument('--salida', required=True, help='Carpeta nueva para esta ejecución')
    automatico.add_argument('--aplicar', action='store_true', help='Guardar correcciones; sin esta opción solo simula')
    auto = sub.add_parser('proponer'); auto.add_argument('archivo'); auto.add_argument('--pendientes', required=True)
    exp = sub.add_parser('exportar'); exp.add_argument('archivo')
    rev = sub.add_parser('revisar'); rev.add_argument('archivo')
    app = sub.add_parser('aplicar'); app.add_argument('archivo'); app.add_argument('--respaldo', required=True)
    args = parser.parse_args()
    # Lee configuración, pero nunca crea tablas ni datos iniciales.
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).with_name('.env'))
    from config import Config
    flask_app = Flask(__name__)
    flask_app.config.from_object(Config)
    db.init_app(flask_app)
    with flask_app.app_context():
        try:
            if args.comando == 'ia':
                from clasificacion_gemini import vista_previa
                vista_previa(args.salida)
            elif args.comando == 'aplicar-ia':
                from clasificacion_gemini import aplicar_revision
                aplicar_revision(args.salida)
            elif args.comando == 'automatico':
                automatizar(args.salida, args.aplicar)
            elif args.comando == 'proponer':
                proponer_automaticamente(args.archivo, args.pendientes)
            elif args.comando == 'exportar':
                exportar(args.archivo)
                print(f'Catálogo exportado a {args.archivo}; completa solo los destinos a corregir.')
            else:
                ejecutar(args.archivo, args.comando == 'aplicar', getattr(args, 'respaldo', None))
        except Exception as exc:
            db.session.rollback()
            # No imprimir URLs de conexión ni credenciales en errores del driver.
            if isinstance(exc, (ValueError, OSError)):
                parser.exit(1, f'Error: {exc}\n')
            parser.exit(1, 'Error de base de datos; operación cancelada. Revisa la conexión y el esquema.\n')


if __name__ == '__main__':
    main()
