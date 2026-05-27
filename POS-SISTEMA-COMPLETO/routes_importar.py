from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Producto, Subcategoria, Categoria, Stock, Sucursal
from sqlalchemy.exc import IntegrityError

importar_bp = Blueprint('importar', __name__, url_prefix='/api/productos')

@importar_bp.route('/importar', methods=['POST'])
@jwt_required()
def importar_productos():
    """Importar productos desde CSV/Excel"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Solo admin puede importar
        if user.role != 'admin':
            return jsonify({'error': 'Acceso denegado'}), 403
        
        data = request.get_json()
        productos_data = data.get('productos', [])
        
        print(f"[DEBUG] Importar productos - Recibidos {len(productos_data)} productos")
        print(f"[DEBUG] Data completa: {data}")
        
        if not productos_data:
            print("[ERROR] No hay productos en el request")
            return jsonify({
                'error': 'No hay productos para importar',
                'detalles': 'El archivo CSV no contiene datos válidos. Verifica que:\n1. El archivo sea CSV\n2. Tenga al menos código y nombre\n3. Tenga datos después del encabezado'
            }), 400
        
        importados = 0
        errores = []
        
        for prod in productos_data:
            try:
                codigo = prod.get('codigo', '').strip()
                nombre = prod.get('nombre', '').strip()
                categoria_nombre = prod.get('categoria', '').strip()
                subcategoria_nombre = prod.get('subcategoria', '').strip() or categoria_nombre
                precio = float(prod.get('precio', 0)) if prod.get('precio') else 0
                stock_cantidad = int(prod.get('stock', 0)) if prod.get('stock') else 0
                sucursal_id = str(prod.get('sucursal_id', '')).strip() if prod.get('sucursal_id') else None
                
                print(f"[DEBUG] Producto: codigo={codigo}, stock={stock_cantidad}, sucursal_id={sucursal_id}")
                
                # Validaciones
                if not codigo or not nombre:
                    errores.append(f"Producto sin código o nombre: {nombre}")
                    continue
                
                # Verificar si el producto ya existe
                producto_existente = Producto.query.filter_by(codigo=codigo).first()
                
                if producto_existente:
                    # Actualizar precio si es diferente
                    if precio > 0:
                        producto_existente.precio = precio
                    
                    # Actualizar o crear stock para la sucursal especificada
                    if sucursal_id:
                        stock = Stock.query.filter_by(
                            producto_id=producto_existente.id,
                            sucursal_id=sucursal_id
                        ).first()
                        
                        if stock:
                            stock.cantidad = stock_cantidad
                        else:
                            stock = Stock(
                                producto_id=producto_existente.id,
                                sucursal_id=sucursal_id,
                                cantidad=stock_cantidad
                            )
                            db.session.add(stock)
                    
                    db.session.commit()
                    importados += 1
                    continue
                
                # Crear categoría si no existe
                categoria = None
                if categoria_nombre:
                    categoria = Categoria.query.filter_by(nombre=categoria_nombre).first()
                    if not categoria:
                        categoria = Categoria(nombre=categoria_nombre, descripcion=f'Categoría {categoria_nombre}')
                        db.session.add(categoria)
                        db.session.flush()
                else:
                    # Si no hay categoría, usar General
                    categoria = Categoria.query.filter_by(nombre='General').first()
                    if not categoria:
                        categoria = Categoria(nombre='General', descripcion='Categoría General')
                        db.session.add(categoria)
                        db.session.flush()
                
                # Crear subcategoría si no existe
                subcategoria = Subcategoria.query.filter_by(
                    nombre=subcategoria_nombre,
                    categoria_id=categoria.id
                ).first()
                
                if not subcategoria:
                    subcategoria = Subcategoria(
                        nombre=subcategoria_nombre,
                        descripcion=f'Subcategoría {subcategoria_nombre}',
                        categoria_id=categoria.id
                    )
                    db.session.add(subcategoria)
                    db.session.flush()
                
                # Crear producto
                producto = Producto(
                    codigo=codigo,
                    nombre=nombre,
                    precio=precio,
                    subcategoria_id=subcategoria.id
                )
                
                db.session.add(producto)
                db.session.flush()
                
                # Crear stock en todas las sucursales
                sucursales = Sucursal.query.filter_by(is_active=True).all()
                for sucursal in sucursales:
                    cantidad = stock_cantidad if sucursal.id == sucursal_id else 0
                    stock = Stock(
                        producto_id=producto.id,
                        sucursal_id=sucursal.id,
                        cantidad=cantidad
                    )
                    db.session.add(stock)
                
                db.session.commit()
                importados += 1
            
            except ValueError as e:
                errores.append(f"Error en producto {prod.get('nombre', 'desconocido')}: {str(e)}")
            except Exception as e:
                db.session.rollback()
                print(f"[ERROR] Excepción no esperada: {str(e)}")
                print(f"[ERROR] Producto: {prod}")
                errores.append(f"Error procesando producto: {str(e)}")
        
        resultado = {
            'importados': importados,
            'total': len(productos_data),
            'errores': errores
        }
        
        if errores:
            resultado['mensaje'] = f'{importados} de {len(productos_data)} productos importados. Hubo {len(errores)} errores.'
        else:
            resultado['mensaje'] = f'{importados} productos importados exitosamente'
        
        return jsonify(resultado), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
