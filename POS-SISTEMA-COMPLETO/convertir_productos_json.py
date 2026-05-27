#!/usr/bin/env python3
"""
Script para convertir plantilla CSV de productos a JSON para importación
Uso: python3 convertir_productos_json.py plantilla_productos.csv
"""

import csv
import json
import sys

def convertir_csv_a_json(archivo_csv):
    """Convierte archivo CSV de productos a formato JSON para API"""
    productos = []
    
    try:
        with open(archivo_csv, 'r', encoding='utf-8') as f:
            lector = csv.DictReader(f)
            
            for fila in lector:
                # Saltar filas vacías
                if not fila.get('codigo') or not fila.get('nombre'):
                    continue
                
                # Crear diccionario del producto
                producto = {
                    'codigo': fila.get('codigo', '').strip(),
                    'nombre': fila.get('nombre', '').strip(),
                    'categoria': fila.get('categoria', '').strip() or 'General',
                    'subcategoria': fila.get('subcategoria', '').strip(),  # Nuevo campo
                    'precio': float(fila.get('precio', 0)) if fila.get('precio', '').strip() else 0,
                    'stock': int(fila.get('stock', 0)) if fila.get('stock', '').strip() else 0,
                    'sucursal_id': fila.get('sucursal_id', '').strip() or None,
                }
                
                productos.append(producto)
        
        # Crear estructura final
        datos_importar = {
            'productos': productos
        }
        
        return datos_importar
    
    except FileNotFoundError:
        print(f"Error: Archivo '{archivo_csv}' no encontrado")
        return None
    except Exception as e:
        print(f"Error al procesar archivo: {e}")
        return None

def guardar_json(datos, archivo_salida='productos_importar.json'):
    """Guarda datos en formato JSON"""
    try:
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
        print(f"✓ JSON generado: {archivo_salida}")
        print(f"✓ Total de productos: {len(datos['productos'])}")
    except Exception as e:
        print(f"Error al guardar JSON: {e}")

def mostrar_json(datos):
    """Muestra el JSON en pantalla"""
    print("\n📋 Contenido JSON para importar:")
    print("=" * 50)
    print(json.dumps(datos, indent=2, ensure_ascii=False))
    print("=" * 50)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        archivo_entrada = 'plantilla_productos.csv'
        print(f"Usando: {archivo_entrada}")
    else:
        archivo_entrada = sys.argv[1]
    
    datos = convertir_csv_a_json(archivo_entrada)
    
    if datos:
        archivo_salida = archivo_entrada.replace('.csv', '_json.json')
        guardar_json(datos, archivo_salida)
        mostrar_json(datos)
    else:
        sys.exit(1)
