const { ref, reactive, computed, watch } = Vue;

// ============= COMPONENTE: VENTAS (Punto de Venta) =============
const VentasView = {
    props: ['apiUrl', 'token', 'userSucursal', 'userRole'],
    template: `
        <div class="grid grid-2" style="gap: 2rem;">
            <div>
                <div class="card">
                    <div class="card-header">
                        <h3>Buscar Productos</h3>
                    </div>
                    
                    <div class="search-box" style="position: relative;">
                        <input 
                            v-model="searchQuery"
                            type="text"
                            placeholder="Escribe nombre, código o barras... (mín. 1 caracter)"
                            @input="buscarProductos"
                            style="width: 100%; padding: 0.75rem; border: 1px solid var(--gray-300); border-radius: 0.375rem;"
                        >
                        
                        <div v-if="searchResults.length > 0" class="search-results">
                            <div 
                                v-for="producto in searchResults" 
                                :key="producto.id"
                                class="search-result-item"
                                @click="agregarAlCarrito(producto)"
                            >
                                <div class="search-result-name">{{ producto.nombre }}</div>
                                <div class="search-result-code">Código: {{ producto.codigo }}</div>
                                <div class="search-result-price">
                                    <span v-if="producto.precio">💵 \${{ producto.precio }}</span>
                                    <span v-else style="color: var(--warning);">⚠ Precio flexible</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <h3>Productos Recientes</h3>
                    </div>
                    
                    <div v-if="loading" style="text-align: center; padding: 1rem;">
                        <span class="spinner"></span>
                    </div>
                    
                    <div v-else-if="productos.length === 0" style="padding: 1rem; text-align: center; color: var(--gray-600);">
                        No hay productos disponibles
                    </div>
                    
                    <div v-else style="max-height: 600px; overflow-y: auto;">
                        <div 
                            v-for="producto in productos.slice(0, 20)" 
                            :key="producto.id"
                            style="padding: 0.75rem; border-bottom: 1px solid var(--gray-200); cursor: pointer; transition: background-color 0.2s;"
                            @click="agregarAlCarrito(producto)"
                            @mouseover="$event.target.style.backgroundColor = 'var(--gray-100)'"
                            @mouseout="$event.target.style.backgroundColor = 'transparent'"
                        >
                            <div style="font-weight: 600; margin-bottom: 0.25rem;">{{ producto.nombre }}</div>
                            <div style="font-size: 0.875rem; color: var(--gray-600);">{{ producto.codigo }}</div>
                            <div style="font-weight: 500; color: var(--primary);">
                                <span v-if="producto.precio">💵 \${{ producto.precio }}</span>
                                <span v-else style="color: var(--warning);">⚠ Precio flexible</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div>
                <div class="card" style="position: sticky; top: 80px;">
                    <div class="card-header">
                        <h3>🛒 Carrito</h3>
                        <button v-if="carrito.length > 0" @click="limpiarCarrito" class="btn btn-secondary btn-sm">Limpiar</button>
                    </div>
                    
                    <div v-if="carrito.length === 0" style="padding: 2rem; text-align: center; color: var(--gray-600);">
                        Carrito vacío
                    </div>

                    <div v-else style="max-height: 400px; overflow-y: auto; margin-bottom: 1rem;">
                        <div v-for="(item, index) in carrito" :key="index" class="cart-item">
                            <div class="cart-item-info">
                                <div class="cart-item-name">{{ item.nombre }}</div>
                                <div class="cart-item-price">\${{ item.precio }} c/u</div>
                            </div>
                            <div class="cart-item-qty">
                                <button @click="decrementarCantidad(index)">−</button>
                                <input v-model.number="item.cantidad" type="number" min="1" @change="actualizarCarrito">
                                <button @click="incrementarCantidad(index)">+</button>
                            </div>
                            <div style="font-weight: 600; min-width: 70px; text-align: right;">
                                \${{ (item.cantidad * item.precio).toFixed(2) }}
                            </div>
                            <button @click="removerDelCarrito(index)" class="btn btn-danger btn-sm">🗑</button>
                        </div>
                    </div>

                    <div class="cart-summary">
                        <div class="summary-row">
                            <span>Subtotal:</span>
                            <span>\${{ subtotal.toFixed(2) }}</span>
                        </div>
                        <div class="summary-row">
                            <span>Impuestos:</span>
                            <span>\${{ totalImpuestos.toFixed(2) }}</span>
                        </div>
                        <div class="summary-row total">
                            <span>TOTAL:</span>
                            <span>\${{ total.toFixed(2) }}</span>
                        </div>

                        <div class="form-group" style="margin-top: 1rem;">
                            <label for="forma-pago">Forma de Pago</label>
                            <select v-model="formaPago" id="forma-pago" name="forma_pago" style="width: 100%; padding: 0.5rem;">
                                <option value="efectivo">💵 Efectivo</option>
                                <option value="tarjeta">💳 Tarjeta</option>
                                <option value="transferencia">🏦 Transferencia</option>
                                <option value="mixto">🔀 Mixto</option>
                            </select>
                        </div>

                        <button 
                            v-if="carrito.length > 0"
                            @click="registrarVenta"
                            class="btn btn-success"
                            style="width: 100%; margin-top: 1rem;"
                            :disabled="procesandoVenta"
                        >
                            <span v-if="!procesandoVenta">✓ Cobrar \${{ total.toFixed(2) }}</span>
                            <span v-else><span class="spinner"></span> Procesando...</span>
                        </button>
                    </div>
                </div>

                <div v-if="ventaExitosa" class="alert alert-success" style="margin-top: 1rem;">
                    ✓ Venta registrada: {{ ventaExitosa }}
                    <button @click="imprimirTicket" class="btn btn-primary btn-sm" style="margin-top: 0.5rem; width: 100%;">
                        🖨 Imprimir Ticket
                    </button>
                </div>

                <div v-if="error" class="alert alert-danger" style="margin-top: 1rem;">
                    {{ error }}
                </div>
            </div>

            <!-- Modal de precio flexible -->
            <div v-if="mostrarModalPrecioFlexible" class="modal-overlay">
                <div class="modal">
                    <div class="modal-header">
                        <h2>Ingresa el Precio</h2>
                        <button @click="mostrarModalPrecioFlexible = false" class="modal-close">✕</button>
                    </div>
                    <div class="modal-body" v-if="productoSinPrecio">
                        <div style="margin-bottom: 1.5rem;">
                            <p><strong>Producto:</strong> {{ productoSinPrecio.nombre }}</p>
                            <p><strong>Código:</strong> {{ productoSinPrecio.codigo }}</p>
                        </div>
                        <div class="form-group">
                            <label for="precio-flexible">Precio ($)</label>
                            <input 
                                v-model.number="precioFlexible" 
                                id="precio-flexible"
                                name="precio_flexible"
                                type="number" 
                                step="0.01" 
                                min="0.01"
                                placeholder="Ej: 10.99"
                                style="width: 100%; padding: 0.75rem; border: 2px solid var(--primary); border-radius: 0.375rem; font-size: 1.1rem;"
                            >
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button @click="mostrarModalPrecioFlexible = false" class="btn btn-secondary">Cancelar</button>
                        <button @click="agregarProductoFlexibleAlCarrito" class="btn btn-success">Agregar al Carrito</button>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            carrito: [],
            productos: [],
            searchQuery: '',
            searchResults: [],
            formaPago: 'efectivo',
            loading: true,
            procesandoVenta: false,
            error: '',
            ventaExitosa: '',
            ultimaVentaId: '',
            mostrarModalPrecioFlexible: false,
            productoSinPrecio: null,
            precioFlexible: 0,
            productosConStockInsuficiente: {} // Rastrear avisos de stock por ID de producto
        };
    },
    computed: {
        subtotal() {
            return this.carrito.reduce((sum, item) => sum + (item.cantidad * item.precio), 0);
        },
        totalImpuestos() {
            return this.carrito.reduce((sum, item) => {
                const impuesto = item.impuesto || 0;
                return sum + (item.cantidad * item.precio * impuesto / 100);
            }, 0);
        },
        total() {
            return this.subtotal + this.totalImpuestos;
        }
    },
    methods: {
        async cargarProductos() {
            try {
                const response = await axios.get(
                    `${window.location.origin}/api/productos`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.productos = response.data.productos || [];
            } catch (err) {
                this.error = 'Error cargando productos';
                console.error(err);
            } finally {
                this.loading = false;
            }
        },
        async buscarProductos() {
            if (this.searchQuery.length < 1) {
                this.searchResults = [];
                return;
            }
            
            try {
                const response = await axios.get(
                    `${window.location.origin}/api/productos/buscar`,
                    {
                        params: { 
                            q: this.searchQuery,
                            sucursal_id: this.userSucursal
                        },
                        headers: { Authorization: `Bearer ${this.token}` }
                    }
                );
                this.searchResults = response.data;
            } catch (err) {
                console.error(err);
            }
        },
        agregarAlCarrito(producto) {
            // Si el producto no tiene precio, mostrar modal para ingresarlo
            if (!producto.precio && producto.precio !== 0) {
                this.productoSinPrecio = producto;
                this.precioFlexible = 0;
                this.mostrarModalPrecioFlexible = true;
                return;
            }
            
            // Validar stock si es admin
            if (this.userRole === 'admin') {
                this.validarStockProducto(producto);
            }
            
            const existe = this.carrito.find(item => item.id === producto.id);
            if (existe) {
                existe.cantidad++;
            } else {
                this.carrito.push({
                    id: producto.id,
                    nombre: producto.nombre,
                    codigo: producto.codigo,
                    precio: producto.precio ? parseFloat(producto.precio) : 0,
                    impuesto: parseFloat(producto.impuesto || 0),
                    cantidad: 1
                });
            }
            this.searchQuery = '';
            this.searchResults = [];
            this.error = '';
        },
        async validarStockProducto(producto) {
            try {
                const response = await axios.get(
                    `${window.location.origin}/api/ventas/validar-stock/${producto.id}`,
                    {
                        params: { cantidad: 1 },
                        headers: { Authorization: `Bearer ${this.token}` }
                    }
                );
                
                if (!response.data.hay_stock) {
                    // Admin ve el aviso de stock insuficiente
                    this.productosConStockInsuficiente[producto.id] = {
                        nombre: producto.nombre,
                        disponible: response.data.cantidad_disponible,
                        solicitado: response.data.cantidad_solicitada,
                        falta: response.data.falta
                    };
                    
                    this.error = `⚠️ Stock insuficiente para ${producto.nombre}. Disponible: ${response.data.cantidad_disponible}. Falta: ${response.data.falta}`;
                }
            } catch (err) {
                console.error('Error validando stock:', err);
            }
        },
        agregarProductoFlexibleAlCarrito() {
            if (this.precioFlexible <= 0) {
                this.error = 'Ingresa un precio válido (mayor a 0)';
                return;
            }
            
            const existe = this.carrito.find(item => item.id === this.productoSinPrecio.id);
            if (existe) {
                existe.cantidad++;
            } else {
                this.carrito.push({
                    id: this.productoSinPrecio.id,
                    nombre: this.productoSinPrecio.nombre,
                    codigo: this.productoSinPrecio.codigo,
                    precio: parseFloat(this.precioFlexible),
                    impuesto: parseFloat(this.productoSinPrecio.impuesto || 0),
                    cantidad: 1
                });
            }
            
            this.mostrarModalPrecioFlexible = false;
            this.productoSinPrecio = null;
            this.precioFlexible = 0;
            this.searchQuery = '';
            this.searchResults = [];
            this.error = '';
        },
        removerDelCarrito(index) {
            this.carrito.splice(index, 1);
        },
        async incrementarCantidad(index) {
            const item = this.carrito[index];
            const nuevaCantidad = item.cantidad + 1;
            
            // Validar stock si es admin
            if (this.userRole === 'admin') {
                try {
                    const response = await axios.get(
                        `${window.location.origin}/api/ventas/validar-stock/${item.id}`,
                        {
                            params: { cantidad: nuevaCantidad },
                            headers: { Authorization: `Bearer ${this.token}` }
                        }
                    );
                    
                    if (!response.data.hay_stock) {
                        this.error = `⚠️ Stock insuficiente para ${item.nombre}. Disponible: ${response.data.cantidad_disponible}. Solicitado: ${nuevaCantidad}`;
                        return; // No incrementar si no hay stock
                    }
                } catch (err) {
                    console.error('Error validando stock:', err);
                }
            }
            
            item.cantidad++;
        },
        decrementarCantidad(index) {
            if (this.carrito[index].cantidad > 1) {
                this.carrito[index].cantidad--;
            }
        },
        actualizarCarrito() {
            // Se actualiza automáticamente
        },
        limpiarCarrito() {
            this.carrito = [];
            this.error = '';
            this.ventaExitosa = '';
        },
        async registrarVenta() {
            if (this.carrito.length === 0) return;
            
            this.procesandoVenta = true;
            this.error = '';
            
            try {
                const detalles = this.carrito.map(item => ({
                    producto_id: item.id,
                    cantidad: item.cantidad,
                    precio: item.precio  // Enviar precio (puede ser personalizado)
                }));

                const response = await axios.post(
                    `${window.location.origin}/api/ventas`,
                    {
                        detalles,
                        forma_pago: this.formaPago
                    },
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );

                this.ultimaVentaId = response.data.venta.id;
                this.ventaExitosa = response.data.venta.numero_venta;
                this.carrito = [];
                this.formaPago = 'efectivo';
            } catch (err) {
                this.error = err.response?.data?.error || 'Error registrando venta';
            } finally {
                this.procesandoVenta = false;
            }
        },
        async imprimirTicket() {
            try {
                const response = await axios.get(
                    `${window.location.origin}/api/ventas/${this.ultimaVentaId}/ticket`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                
                const ticket = response.data;
                const contenido = this.generarHTMLTicket(ticket);
                
                const ventana = window.open('', '', 'width=400,height=600');
                ventana.document.write(contenido);
                ventana.document.close();
                ventana.print();
            } catch (err) {
                alert('Error generando ticket');
            }
        },
        generarHTMLTicket(ticket) {
            let html = `
                <html>
                <head>
                    <style>
                        body { font-family: monospace; font-size: 12px; padding: 10px; }
                        h1 { text-align: center; font-size: 18px; }
                        .separator { border-bottom: 1px dashed #000; margin: 10px 0; }
                        .item { display: flex; justify-content: space-between; }
                        .total { font-weight: bold; font-size: 14px; }
                    </style>
                </head>
                <body>
                    <h1>TICKET</h1>
                    <p><strong>Venta:</strong> ${ticket.numero_venta}</p>
                    <p><strong>Sucursal:</strong> ${ticket.sucursal}</p>
                    <p><strong>Dirección:</strong> ${ticket.direccion}</p>
                    <p><strong>Fecha:</strong> ${ticket.fecha}</p>
                    <p><strong>Cajero:</strong> ${ticket.cajero}</p>
                    <div class="separator"></div>
                    <h3>Productos</h3>
            `;
            
            ticket.detalles.forEach(detalle => {
                html += `
                    <div class="item">
                        <span>${detalle.producto}</span>
                        <span>${detalle.cantidad}x</span>
                        <span>$${detalle.subtotal.toFixed(2)}</span>
                    </div>
                `;
            });
            
            html += `
                    <div class="separator"></div>
                    <div class="item">
                        <span>SUBTOTAL:</span>
                        <span>$${ticket.subtotal.toFixed(2)}</span>
                    </div>
                    <div class="item">
                        <span>IMPUESTOS:</span>
                        <span>$${ticket.total_impuestos.toFixed(2)}</span>
                    </div>
                    <div class="item total" style="font-size: 16px; margin-top: 10px;">
                        <span>TOTAL:</span>
                        <span>$${ticket.total.toFixed(2)}</span>
                    </div>
                    <p style="text-align: center; margin-top: 20px;">Forma de Pago: ${ticket.forma_pago.toUpperCase()}</p>
                    <p style="text-align: center;">Gracias por su compra</p>
                </body>
                </html>
            `;
            return html;
        }
    },
    mounted() {
        if (this.token) {
            this.cargarProductos();
        }
    }
};

// ============= COMPONENTE: PRODUCTOS (Admin) =============
const ProductosView = {
    props: ['apiUrl', 'token'],
    template: `
        <div>
            <div class="card">
                <div class="card-header">
                    <h3>Gestión de Productos</h3>
                    <div class="btn-group">
                        <button @click="mostrarFormulario = !mostrarFormulario" class="btn btn-primary">
                            {{ mostrarFormulario ? '← Ocultar' : '+ Nuevo Producto' }}
                        </button>
                        <button @click="mostrarImportacion = !mostrarImportacion" class="btn btn-success">
                            📤 Importar Excel/CSV
                        </button>
                    </div>
                </div>

                <!-- Formulario de nuevo/editar producto -->
                <div v-if="mostrarFormulario" style="background-color: var(--gray-50); padding: 1.5rem; border-radius: 0.375rem; margin-bottom: 1.5rem;">
                    <h4 style="margin-bottom: 1rem;">{{ editandoProductoId ? 'Editar Producto' : 'Nuevo Producto' }}</h4>
                    <div class="grid grid-3">
                        <div class="form-group">
                            <label for="producto-codigo">Código</label>
                            <input v-model="nuevoProducto.codigo" id="producto-codigo" name="producto_codigo" type="text" required>
                        </div>
                        <div class="form-group">
                            <label for="producto-nombre">Nombre</label>
                            <input v-model="nuevoProducto.nombre" id="producto-nombre" name="producto_nombre" type="text" required>
                        </div>
                        <div class="form-group">
                            <label for="producto-precio">Precio (opcional)</label>
                            <input v-model.number="nuevoProducto.precio" id="producto-precio" name="producto_precio" type="number" step="0.01">
                        </div>
                    </div>
                    <div class="grid grid-3">
                        <div class="form-group">
                            <label for="producto-impuesto">Impuesto (%)</label>
                            <input v-model.number="nuevoProducto.impuesto" id="producto-impuesto" name="producto_impuesto" type="number" step="0.01" min="0">
                        </div>
                        <div class="form-group">
                            <label for="producto-codigo-barras">Código de Barras</label>
                            <input v-model="nuevoProducto.codigo_barras" id="producto-codigo-barras" name="producto_codigo_barras" type="text">
                        </div>
                        <div class="form-group">
                            <label for="subcategoria">Subcategoría</label>
                            <select v-model="nuevoProducto.subcategoria_id" id="subcategoria" name="subcategoria" required>
                                <option value="">Selecciona subcategoría</option>
                                <option v-for="sub in subcategorias" :key="sub.id" :value="sub.id">
                                    {{ sub.nombre }}
                                </option>
                            </select>
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="producto-descripcion">Descripción</label>
                        <textarea v-model="nuevoProducto.descripcion" id="producto-descripcion" name="producto_descripcion" rows="3"></textarea>
                    </div>
                    <div v-if="error" class="alert alert-danger">{{ error }}</div>
                    <div class="btn-group">
                        <button @click="guardarProducto" class="btn btn-success">
                            {{ editandoProductoId ? 'Actualizar' : 'Guardar' }} Producto
                        </button>
                        <button @click="cancelarEdicion" class="btn btn-secondary">Cancelar</button>
                    </div>
                </div>

                <!-- Importación de CSV/Excel -->
                <div v-if="mostrarImportacion" style="background-color: var(--gray-50); padding: 1.5rem; border-radius: 0.375rem; margin-bottom: 1.5rem;">
                    <h4 style="margin-bottom: 1rem;">Importar Productos desde CSV/Excel</h4>
                    <p style="margin-bottom: 1rem; color: var(--gray-600);">
                        Carga un archivo CSV con las siguientes columnas: Handle, REF, Nombre, Categoria, Precio [Sucursal], En inventario [Sucursal]
                    </p>
                    <div class="form-group">
                        <label for="archivo-importacion">Archivo CSV/Excel</label>
                        <input 
                            id="archivo-importacion"
                            name="archivo_importacion"
                            type="file" 
                            accept=".csv,.xlsx"
                            @change="manejarCargaArchivo"
                            style="width: 100%; padding: 0.5rem; border: 2px dashed var(--primary); border-radius: 0.375rem;"
                        >
                    </div>
                    <div v-if="archivoSeleccionado" style="margin-bottom: 1rem;">
                        <p>📄 {{ archivoSeleccionado.name }}</p>
                        <div class="form-group">
                            <label for="sucursal-importacion">Sucursal para el stock</label>
                            <select v-model="sucursalImportacion" id="sucursal-importacion" name="sucursal_importacion" required>
                                <option value="">Selecciona sucursal</option>
                                <option v-for="suc in sucursales" :key="suc.id" :value="suc.id">
                                    {{ suc.nombre }}
                                </option>
                            </select>
                        </div>
                        <button @click="procesarImportacion" class="btn btn-success" :disabled="importandoProductos">
                            <span v-if="!importandoProductos">✓ Importar Productos</span>
                            <span v-else><span class="spinner"></span> Procesando...</span>
                        </button>
                    </div>
                    <div v-if="mensajeImportacion" :class="['alert', 'alert-' + tipoMensajeImportacion]">
                        {{ mensajeImportacion }}
                    </div>
                </div>

                <!-- Búsqueda y filtros -->
                <div style="margin-bottom: 1rem;">
                    <input 
                        v-model="busquedaProducto"
                        id="buscar-productos"
                        name="buscar_productos"
                        type="text"
                        placeholder="Buscar productos..."
                        style="width: 100%; padding: 0.75rem; border: 1px solid var(--gray-300); border-radius: 0.375rem;"
                    >
                </div>

                <!-- Tabla de productos -->
                <div v-if="loading" style="text-align: center; padding: 2rem;">
                    <span class="spinner"></span>
                </div>
                <div v-else-if="productosFiltrados.length === 0" style="padding: 2rem; text-align: center; color: var(--gray-600);">
                    No hay productos
                </div>
                <div v-else style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Código</th>
                                <th>Nombre</th>
                                <th>Precio</th>
                                <th>Impuesto</th>
                                <th>Categoría</th>
                                <th>Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="producto in productosFiltrados" :key="producto.id">
                                <td>{{ producto.codigo }}</td>
                                <td>{{ producto.nombre }}</td>
                                <td><span v-if="producto.precio">\${{ producto.precio }}</span><span v-else style="color: var(--warning); font-weight: 600;">⚠ Sin precio</span></td>
                                <td>{{ producto.impuesto }}%</td>
                                <td>{{ producto.subcategoria_id }}</td>
                                <td>
                                    <button class="btn btn-primary btn-sm" @click="editarProducto(producto)">Editar</button>
                                    <button class="btn btn-danger btn-sm" @click="eliminarProducto(producto.id)">Eliminar</button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            productos: [],
            subcategorias: [],
            sucursales: [],
            mostrarFormulario: false,
            mostrarImportacion: false,
            loading: true,
            busquedaProducto: '',
            editandoProductoId: null,
            error: '',
            nuevoProducto: {
                codigo: '',
                nombre: '',
                precio: 0,
                impuesto: 0,
                codigo_barras: '',
                subcategoria_id: '',
                descripcion: ''
            },
            archivoSeleccionado: null,
            sucursalImportacion: '',
            importandoProductos: false,
            mensajeImportacion: '',
            tipoMensajeImportacion: 'success'
        };
    },
    computed: {
        productosFiltrados() {
            return this.productos.filter(p => 
                p.nombre.toLowerCase().includes(this.busquedaProducto.toLowerCase()) ||
                p.codigo.toLowerCase().includes(this.busquedaProducto.toLowerCase())
            );
        }
    },
    methods: {
        async cargarProductos() {
            try {
                const res = await axios.get(
                    `${window.location.origin}/api/productos`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.productos = res.data.productos || [];
            } catch (err) {
                console.error(err);
            } finally {
                this.loading = false;
            }
        },
        async cargarSubcategorias() {
            try {
                const res = await axios.get(
                    `${window.location.origin}/api/productos/subcategorias`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.subcategorias = res.data;
            } catch (err) {
                console.error(err);
            }
        },
        async cargarSucursales() {
            try {
                const apiUrl = window.location.origin;
                const res = await axios.get(
                    `${apiUrl}/api/admin/sucursales-publico`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.sucursales = Array.isArray(res.data) ? res.data.filter(s => s && s.nombre) : [];
                console.log('ProductosView - Sucursales cargadas:', this.sucursales);
            } catch (err) {
                console.error('ProductosView - Error cargando sucursales:', err);
                this.sucursales = [];
            }
        },
        async guardarProducto() {
            try {
                this.error = '';
                if (this.editandoProductoId) {
                    // Actualizar producto existente
                    await axios.put(
                        `${window.location.origin}/api/productos/${this.editandoProductoId}`,
                        this.nuevoProducto,
                        { headers: { Authorization: `Bearer ${this.token}` } }
                    );
                } else {
                    // Crear nuevo producto
                    await axios.post(
                        `${window.location.origin}/api/productos`,
                        this.nuevoProducto,
                        { headers: { Authorization: `Bearer ${this.token}` } }
                    );
                }
                this.cancelarEdicion();
                await this.cargarProductos();
            } catch (err) {
                this.error = 'Error: ' + (err.response?.data?.error || err.message);
            }
        },
        editarProducto(producto) {
            this.editandoProductoId = producto.id;
            this.nuevoProducto = {
                codigo: producto.codigo,
                nombre: producto.nombre,
                precio: producto.precio,
                impuesto: producto.impuesto || 0,
                codigo_barras: producto.codigo_barras || '',
                subcategoria_id: producto.subcategoria_id || '',
                descripcion: producto.descripcion || ''
            };
            this.mostrarFormulario = true;
            this.error = '';
        },
        cancelarEdicion() {
            this.mostrarFormulario = false;
            this.editandoProductoId = null;
            this.nuevoProducto = { codigo: '', nombre: '', precio: 0, impuesto: 0, codigo_barras: '', subcategoria_id: '', descripcion: '' };
            this.error = '';
        },
        manejarCargaArchivo(evento) {
            this.archivoSeleccionado = evento.target.files[0];
            this.mensajeImportacion = '';
        },
        async procesarImportacion() {
            if (!this.archivoSeleccionado || !this.sucursalImportacion) {
                alert('Selecciona archivo y sucursal');
                return;
            }

            this.importandoProductos = true;
            this.mensajeImportacion = '';
            
            try {
                const reader = new FileReader();
                reader.onload = async (e) => {
                    try {
                        const csv = e.target.result;
                        const lineas = csv.split('\n');
                        const encabezados = lineas[0].split(',').map(h => h.trim());
                        
                        // Encontrar índices de columnas
                        const idxCodigo = encabezados.findIndex(h => h === 'REF');
                        const idxNombre = encabezados.findIndex(h => h === 'Nombre');
                        const idxCategoria = encabezados.findIndex(h => h === 'Categoria');
                        
                        // Buscar columna de precio para la sucursal
                        const columnaSucursal = encabezados.find(h => h.includes('Precio ['));
                        const idxPrecio = columnaSucursal ? encabezados.indexOf(columnaSucursal) : -1;
                        
                        // Buscar columna de stock para la sucursal
                        const columnaStock = encabezados.find(h => h.includes('En inventario ['));
                        const idxStock = columnaStock ? encabezados.indexOf(columnaStock) : -1;
                        
                        const productosProcesados = [];
                        const errores = [];
                        
                        for (let i = 1; i < lineas.length; i++) {
                            const linea = lineas[i].trim();
                            if (!linea) continue;
                            
                            const valores = linea.split(',').map(v => v.trim().replace(/"/g, ''));
                            
                            const codigo = valores[idxCodigo]?.trim();
                            const nombre = valores[idxNombre]?.trim();
                            const categoria = valores[idxCategoria]?.trim();
                            const precio = parseFloat(valores[idxPrecio]) || 0;
                            const stock = parseInt(valores[idxStock]) || 0;
                            
                            if (codigo && nombre) {
                                productosProcesados.push({
                                    codigo,
                                    nombre,
                                    categoria,
                                    precio,
                                    stock,
                                    sucursal_id: this.sucursalImportacion
                                });
                            }
                        }
                        
                        // Enviar productos procesados al servidor
                        const response = await axios.post(
                            `${window.location.origin}/api/productos/importar`,
                            { productos: productosProcesados },
                            { headers: { Authorization: `Bearer ${this.token}` } }
                        );
                        
                        this.mensajeImportacion = `✓ ${response.data.importados} productos importados exitosamente`;
                        this.tipoMensajeImportacion = 'success';
                        this.archivoSeleccionado = null;
                        await this.cargarProductos();
                    } catch (err) {
                        this.mensajeImportacion = 'Error procesando archivo: ' + (err.response?.data?.error || err.message);
                        this.tipoMensajeImportacion = 'danger';
                    } finally {
                        this.importandoProductos = false;
                    }
                };
                reader.readAsText(this.archivoSeleccionado);
            } catch (err) {
                this.mensajeImportacion = 'Error: ' + err.message;
                this.tipoMensajeImportacion = 'danger';
                this.importandoProductos = false;
            }
        },
        async eliminarProducto(id) {
            if (!confirm('¿Eliminar producto?')) return;
            try {
                await axios.delete(
                    `${window.location.origin}/api/productos/${id}`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                await this.cargarProductos();
            } catch (err) {
                alert('Error: ' + err.response?.data?.error);
            }
        }
    },
    mounted() {
        if (this.token) {
            this.cargarProductos();
            this.cargarSubcategorias();
            this.cargarSucursales();
        }
    },
    watch: {
        token(newToken) {
            if (newToken) {
                this.cargarProductos();
                this.cargarSubcategorias();
                this.cargarSucursales();
            }
        }
    }
};

// ============= COMPONENTE: INVENTARIO (Admin) =============
const InventarioView = {
    props: ['apiUrl', 'token', 'userRole'],
    template: `
        <div>
            <div class="card">
                <div class="card-header">
                    <h3>Gestión de Inventario</h3>
                    <button @click="mostrarEntrada = !mostrarEntrada" class="btn btn-primary">
                        {{ mostrarEntrada ? '← Ocultar' : '+ Registrar Entrada' }}
                    </button>
                </div>

                <!-- Formulario de entrada -->
                <div v-if="mostrarEntrada" style="background-color: var(--gray-50); padding: 1.5rem; border-radius: 0.375rem; margin-bottom: 1.5rem;">
                    <h4 style="margin-bottom: 1rem;">Registrar Entrada de Inventario</h4>
                    <div class="grid grid-3">
                        <div class="form-group">
                            <label for="entrada-sucursal">Sucursal</label>
                            <select v-model="entrada.sucursal_id" id="entrada-sucursal" name="entrada_sucursal" required>
                                <option value="">Selecciona sucursal</option>
                                <option v-for="suc in sucursales" :key="suc.id" :value="suc.id">
                                    {{ suc.nombre }}
                                </option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="buscar-producto">Producto</label>
                            <input 
                                v-model="busquedaProductoEntrada"
                                id="buscar-producto"
                                name="buscar_producto"
                                type="text"
                                placeholder="Busca producto..."
                                style="width: 100%; padding: 0.5rem;"
                            >
                            <div v-if="productosEncontrados.length > 0" style="position: absolute; background: white; border: 1px solid var(--gray-300); border-radius: 0.375rem; width: 100%; max-height: 200px; overflow-y: auto; z-index: 10;">
                                <div 
                                    v-for="prod in productosEncontrados" 
                                    :key="prod.id"
                                    @click="entrada.producto_id = prod.id; busquedaProductoEntrada = prod.nombre;"
                                    style="padding: 0.5rem; cursor: pointer; border-bottom: 1px solid var(--gray-200);"
                                >
                                    {{ prod.nombre }} ({{ prod.codigo }})
                                </div>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="entrada-cantidad">Cantidad</label>
                            <input v-model.number="entrada.cantidad" id="entrada-cantidad" name="entrada_cantidad" type="number" min="1" required>
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="entrada-cantidad-minima">Cantidad Mínima (default: 5)</label>
                        <input v-model.number="entrada.cantidad_minima" id="entrada-cantidad-minima" type="number" name="entrada_cantidad_minima" min="1" placeholder="5" />
                    </div>
                    <div class="form-group">
                        <label for="entrada-observaciones">Observaciones</label>
                        <textarea v-model="entrada.observaciones" id="entrada-observaciones" name="entrada_observaciones" rows="2"></textarea>
                    </div>
                    <div class="btn-group">
                        <button @click="registrarEntrada" class="btn btn-success">{{ entrada.stock_id ? 'Actualizar Stock' : 'Registrar Entrada' }}</button>
                        <button @click="cancelarEdicion" class="btn btn-secondary">Cancelar</button>
                    </div>
                </div>

                <div v-if="mensajeEntrada" :class="['alert', 'alert-' + tipoMensajeEntrada]">
                    {{ mensajeEntrada }}
                </div>

                <!-- Tabla de stock por sucursal -->
                <h4 style="margin-bottom: 1rem; margin-top: 2rem;">Stock Actual por Sucursal</h4>
                <div class="form-group">
                    <label for="sucursal-selector">Selecciona Sucursal</label>
                    <select v-model="sucursalSeleccionada" id="sucursal-selector" name="sucursal_selector">
                        <option value="">Todas</option>
                        <option v-for="suc in sucursales" :key="suc.id" :value="suc.id">
                            {{ suc.nombre }}
                        </option>
                    </select>
                </div>

                <div v-if="cargandoStock" style="text-align: center; padding: 2rem;">
                    <span class="spinner"></span>
                </div>
                <div v-else-if="stocks.length === 0" style="padding: 2rem; text-align: center; color: var(--gray-600);">
                    No hay productos en stock
                </div>
                <div v-else style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Código</th>
                                <th>Producto</th>
                                <th>Cantidad</th>
                                <th>Mínimo</th>
                                <th>Estado</th>
                                <th>Precio</th>
                                <th>Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="stock in stocks" :key="stock.id">
                                <td>{{ stock.producto_codigo }}</td>
                                <td>{{ stock.producto_nombre }}</td>
                                <td style="font-weight: 600;">{{ stock.cantidad }}</td>
                                <td>{{ stock.cantidad_minima }}</td>
                                <td>
                                    <span v-if="stock.cantidad <= stock.cantidad_minima" style="color: var(--danger); font-weight: 600;">
                                        ⚠ Bajo Stock
                                    </span>
                                    <span v-else style="color: var(--success);">✓ OK</span>
                                </td>
                                <td>\${{ stock.precio }}</td>
                                <td>
                                    <div class="btn-group">
                                        <button @click="editarStock(stock)" class="btn btn-primary btn-sm">✏️ Editar</button>
                                        <button @click="eliminarStock(stock.id)" class="btn btn-danger btn-sm">🗑️ Eliminar</button>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            sucursales: [],
            stocks: [],
            productos: [],
            mostrarEntrada: false,
            sucursalSeleccionada: '',
            cargandoStock: false,
            entrada: {
                sucursal_id: '',
                producto_id: '',
                cantidad: 1,
                cantidad_minima: null,
                observaciones: '',
                stock_id: null
            },
            busquedaProductoEntrada: '',
            mensajeEntrada: '',
            tipoMensajeEntrada: 'success'
        };
    },
    computed: {
        productosEncontrados() {
            if (!this.busquedaProductoEntrada) return [];
            return this.productos.filter(p => 
                p.nombre.toLowerCase().includes(this.busquedaProductoEntrada.toLowerCase()) ||
                p.codigo.toLowerCase().includes(this.busquedaProductoEntrada.toLowerCase())
            ).slice(0, 5);
        }
    },
    methods: {
        async cargarSucursales() {
            try {
                const tokenStr = String(this.token);
                const apiUrl = window.location.origin;
                const url = `${apiUrl}/api/admin/sucursales-publico`;
                console.log('[INVENTARIO] Token:', tokenStr.substring(0, 20) + '...');
                console.log('[INVENTARIO] URL:', url);
                
                const res = await axios.get(url, {
                    headers: { Authorization: `Bearer ${tokenStr}` }
                });
                console.log('[INVENTARIO] Respuesta bruta:', res.data);
                console.log('[INVENTARIO] Status:', res.status);
                this.sucursales = Array.isArray(res.data) ? res.data.filter(s => s && s.nombre) : [];
                console.log('[INVENTARIO] Sucursales después del filtro:', this.sucursales);
                if (this.sucursales.length > 0) {
                    this.entrada.sucursal_id = this.sucursales[0].id;
                }
            } catch (err) {
                console.error('[INVENTARIO] Error - Status:', err.response?.status);
                console.error('[INVENTARIO] URL solicitada:', err.config?.url);
                this.sucursales = [];
            }
        },
        async cargarStock() {
            this.cargandoStock = true;
            try {
                const res = await axios.get(
                    `${window.location.origin}/api/inventario/stock/${this.sucursalSeleccionada}`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.stocks = res.data.stocks || [];
            } catch (err) {
                console.error(err);
            } finally {
                this.cargandoStock = false;
            }
        },
        async cargarProductos() {
            try {
                const res = await axios.get(
                    `${window.location.origin}/api/productos?per_page=2000`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.productos = res.data.productos || [];
            } catch (err) {
                console.error(err);
            }
        },
        async registrarEntrada() {
            if (!this.entrada.sucursal_id || !this.entrada.producto_id || this.entrada.cantidad <= 0) {
                this.mensajeEntrada = 'Completa todos los campos requeridos';
                this.tipoMensajeEntrada = 'danger';
                return;
            }

            try {
                // Si es edición de stock existente
                if (this.entrada.stock_id) {
                    const updateData = {};
                    if (this.entrada.cantidad) updateData.cantidad = this.entrada.cantidad;
                    if (this.entrada.cantidad_minima) updateData.cantidad_minima = this.entrada.cantidad_minima;
                    
                    const res = await axios.put(
                        `${window.location.origin}/api/inventario/stock/${this.entrada.stock_id}`,
                        updateData,
                        { headers: { Authorization: `Bearer ${this.token}` } }
                    );
                    
                    this.mensajeEntrada = `✓ Stock actualizado exitosamente`;
                } else {
                    // Si es nueva entrada
                    const postData = {
                        sucursal_id: this.entrada.sucursal_id,
                        producto_id: this.entrada.producto_id,
                        cantidad: this.entrada.cantidad,
                        observaciones: this.entrada.observaciones
                    };
                    if (this.entrada.cantidad_minima) postData.cantidad_minima = this.entrada.cantidad_minima;
                    
                    const res = await axios.post(
                        `${window.location.origin}/api/inventario/entrada`,
                        postData,
                        { headers: { Authorization: `Bearer ${this.token}` } }
                    );
                    
                    this.mensajeEntrada = `✓ Entrada registrada. Nuevo stock: ${res.data.nuevo_stock}`;
                }
                
                this.tipoMensajeEntrada = 'success';
                this.mostrarEntrada = false;
                this.cancelarEdicion();
                await this.cargarStock();
            } catch (err) {
                this.mensajeEntrada = 'Error: ' + (err.response?.data?.error || err.message);
                this.tipoMensajeEntrada = 'danger';
            }
        },
        editarStock(stock) {
            this.entrada.stock_id = stock.id;
            this.entrada.sucursal_id = stock.sucursal_id;
            this.entrada.producto_id = stock.producto_id;
            this.entrada.cantidad = stock.cantidad;
            this.entrada.cantidad_minima = stock.cantidad_minima;
            this.entrada.observaciones = '';
            this.mostrarEntrada = true;
        },
        cancelarEdicion() {
            this.entrada = { sucursal_id: '', producto_id: '', cantidad: 1, cantidad_minima: null, observaciones: '', stock_id: null };
            this.busquedaProductoEntrada = '';
            this.mostrarEntrada = false;
        },
        async eliminarStock(stockId) {
            if (!confirm('¿Eliminar este stock?')) return;
            try {
                await axios.delete(
                    `${window.location.origin}/api/inventario/${stockId}`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.mensajeEntrada = '✓ Stock eliminado exitosamente';
                this.tipoMensajeEntrada = 'success';
                await this.cargarStock();
            } catch (err) {
                this.mensajeEntrada = 'Error: ' + (err.response?.data?.error || err.message);
                this.tipoMensajeEntrada = 'danger';
            }
        }
    },
    mounted() {
        if (this.token) {
            this.cargarSucursales();
            this.cargarProductos();
        }
    },
    watch: {
        token(newToken) {
            if (newToken) {
                this.cargarSucursales();
                this.cargarProductos();
            }
        },
        sucursalSeleccionada() {
            if (this.sucursalSeleccionada) {
                this.cargarStock();
            }
        }
    }
};

// ============= COMPONENTE: REPORTES (Admin) =============
const ReportesView = {
    props: ['apiUrl', 'token', 'userRole'],
    template: `
        <div>
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Ventas Hoy</h3>
                    <div class="value">\${{ ventasHoy }}</div>
                </div>
                <div class="stat-card">
                    <h3>Transacciones</h3>
                    <div class="value">{{ transaccionesHoy }}</div>
                </div>
                <div class="stat-card">
                    <h3>Promedio</h3>
                    <div class="value">\${{ promedioVenta }}</div>
                </div>
                <div class="stat-card">
                    <h3>Impuestos</h3>
                    <div class="value">\${{ impuestosHoy }}</div>
                </div>
            </div>

            <div class="grid grid-2" style="gap: 2rem;">
                <div class="card">
                    <div class="card-header">
                        <h3>Reporte Diario</h3>
                    </div>
                    <div class="form-group">
                        <label for="fecha-reporte">Fecha</label>
                        <input v-model="fechaReporte" id="fecha-reporte" name="fecha_reporte" type="date">
                    </div>
                    <div class="form-group">
                        <label for="sucursal-reporte-diario">Sucursal</label>
                        <select v-model="sucursalReporte" id="sucursal-reporte-diario" name="sucursal_reporte_diario" required>
                            <option value="">Selecciona una sucursal</option>
                            <option v-for="suc in sucursales" :key="suc.id" :value="suc.id">{{ suc.nombre }}</option>
                        </select>
                    </div>
                    <button @click="generarReporteDiario" class="btn btn-primary" style="width: 100%;">
                        Generar Reporte
                    </button>
                </div>

                <div class="card">
                    <div class="card-header">
                        <h3>Reporte Mensual</h3>
                    </div>
                    <div class="form-group">
                        <label for="mes-reporte">Mes</label>
                        <input v-model="mesReporte" id="mes-reporte" name="mes_reporte" type="month">
                    </div>
                    <div class="form-group">
                        <label for="sucursal-reporte-mensual">Sucursal</label>
                        <select v-model="sucursalReporte" id="sucursal-reporte-mensual" name="sucursal_reporte_mensual" required>
                            <option value="">Selecciona una sucursal</option>
                            <option v-for="suc in sucursales" :key="suc.id" :value="suc.id">{{ suc.nombre }}</option>
                        </select>
                    </div>
                    <button @click="generarReporteMensual" class="btn btn-primary" style="width: 100%;">
                        Generar Reporte
                    </button>
                </div>
            </div>

            <div v-if="reporteActual" class="card" style="margin-top: 2rem;">
                <div class="card-header">
                    <h3>Resultados del Reporte</h3>
                </div>
                
                <!-- Gráfica si es reporte mensual -->
                <div v-if="tipoReporteActual === 'mensual'" style="margin-bottom: 2rem;">
                    <div style="max-height: 400px; margin-bottom: 2rem;">
                        <canvas ref="chartMensual"></canvas>
                    </div>
                </div>

                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Concepto</th>
                                <th>Valor</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Total de Ventas</td>
                                <td>\${{ reporteActual.total_ventas?.toFixed(2) }}</td>
                            </tr>
                            <tr>
                                <td>Total de Impuestos</td>
                                <td>\${{ reporteActual.total_impuestos?.toFixed(2) }}</td>
                            </tr>
                            <tr>
                                <td>Cantidad de Transacciones</td>
                                <td>{{ reporteActual.cantidad_transacciones }}</td>
                            </tr>
                            <tr>
                                <td>Promedio por Venta</td>
                                <td>\${{ reporteActual.promedio_venta?.toFixed(2) }}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            sucursales: [],
            ventasHoy: 0,
            transaccionesHoy: 0,
            promedioVenta: 0,
            impuestosHoy: 0,
            fechaReporte: new Date().toISOString().split('T')[0],
            mesReporte: new Date().toISOString().slice(0, 7),
            sucursalReporte: '',
            reporteActual: null,
            tipoReporteActual: null,
            chartMensualInstance: null
        };
    },
    methods: {
        async cargarSucursales() {
            try {
                const apiUrl = window.location.origin;
                const res = await axios.get(
                    `${apiUrl}/api/admin/sucursales-publico`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.sucursales = Array.isArray(res.data) ? res.data.filter(s => s && s.nombre) : [];
            } catch (err) {
                console.error('Error cargando sucursales:', err);
                this.sucursales = [];
            }
        },
        async cargarVentasHoy() {
            try {
                const hoy = new Date().toISOString().split('T')[0];
                const res = await axios.get(
                    `${window.location.origin}/api/reportes/ventas-diarias`,
                    {
                        params: { fecha: hoy },
                        headers: { Authorization: `Bearer ${this.token}` }
                    }
                );
                this.ventasHoy = (res.data.total_ventas || 0).toFixed(2);
                this.transaccionesHoy = res.data.cantidad_transacciones || 0;
                this.promedioVenta = (res.data.promedio_venta || 0).toFixed(2);
                this.impuestosHoy = (res.data.total_impuestos || 0).toFixed(2);
            } catch (err) {
                console.error(err);
            }
        },
        async generarReporteDiario() {
            try {
                const res = await axios.get(
                    `${window.location.origin}/api/reportes/ventas-diarias`,
                    {
                        params: {
                            fecha: this.fechaReporte,
                            sucursal_id: this.sucursalReporte || undefined
                        },
                        headers: { Authorization: `Bearer ${this.token}` }
                    }
                );
                this.reporteActual = res.data;
            } catch (err) {
                alert('Error generando reporte');
            }
        },
        async generarReporteMensual() {
            try {
                const res = await axios.get(
                    `${window.location.origin}/api/reportes/ventas-mensuales`,
                    {
                        params: {
                            mes: this.mesReporte,
                            sucursal_id: this.sucursalReporte || undefined
                        },
                        headers: { Authorization: `Bearer ${this.token}` }
                    }
                );
                this.reporteActual = res.data;
                this.tipoReporteActual = 'mensual';
                // Generar gráfica después de obtener datos
                this.$nextTick(() => {
                    this.generarGraficaMensual();
                });
            } catch (err) {
                alert('Error generando reporte');
            }
        },
        generarGraficaMensual() {
            // Generar gráfica de tendencia de ventas por mes
            if (this.chartMensualInstance) this.chartMensualInstance.destroy();
            
            const meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                          'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
            const mesActual = new Date(this.mesReporte).getMonth();
            const añoActual = new Date(this.mesReporte).getFullYear();
            
            this.chartMensualInstance = new Chart(this.$refs.chartMensual, {
                type: 'bar',
                data: {
                    labels: [meses[mesActual]],
                    datasets: [
                        {
                            label: 'Total Ventas',
                            data: [this.reporteActual.total_ventas || 0],
                            backgroundColor: '#2563eb',
                            borderColor: '#1e40af',
                            borderWidth: 1
                        },
                        {
                            label: 'Impuestos',
                            data: [this.reporteActual.total_impuestos || 0],
                            backgroundColor: '#f59e0b',
                            borderColor: '#d97706',
                            borderWidth: 1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { display: true }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toLocaleString('es-AR');
                                }
                            }
                        }
                    }
                }
            });
        },
    },
    mounted() {
        this.cargarSucursales();
        this.cargarVentasHoy();
    },
    watch: {
        token(newToken) {
            this.cargarSucursales();
            this.cargarVentasHoy();
        }
    }
};

// ============= COMPONENTE: USUARIOS (Admin) =============
const UsuariosView = {
    props: ['apiUrl', 'token', 'userRole'],
    template: `
        <div>
            <div class="card">
                <div class="card-header">
                    <h3>Gestión de Usuarios</h3>
                    <button @click="mostrarFormulario = !mostrarFormulario" class="btn btn-primary">
                        {{ mostrarFormulario ? '← Ocultar' : '+ Nuevo Usuario' }}
                    </button>
                </div>

                <!-- Formulario Nuevo Usuario -->
                <div v-if="mostrarFormulario && !usuarioEditandoId" style="background-color: var(--gray-50); padding: 1.5rem; border-radius: 0.375rem; margin-bottom: 1.5rem;">
                    <h4 style="margin-bottom: 1rem;">Nuevo Usuario</h4>
                    <div class="grid grid-3">
                        <div class="form-group">
                            <label for="user-username">Usuario</label>
                            <input v-model="nuevoUsuario.username" id="user-username" name="user_username" type="text" required>
                        </div>
                        <div class="form-group">
                            <label for="user-email">Email</label>
                            <input v-model="nuevoUsuario.email" id="user-email" name="user_email" type="email" required>
                        </div>
                        <div class="form-group">
                            <label for="user-password">Contraseña</label>
                            <input v-model="nuevoUsuario.password" id="user-password" name="user_password" type="password" required>
                        </div>
                    </div>
                    <div class="grid grid-3">
                        <div class="form-group">
                            <label for="user-role">Rol</label>
                            <select v-model="nuevoUsuario.role" id="user-role" name="user_role" required>
                                <option value="employee">Empleado</option>
                                <option value="admin">Administrador</option>
                            </select>
                        </div>
                        <div class="form-group" v-if="nuevoUsuario.role === 'employee'">
                            <label for="user-sucursal">Sucursal</label>
                            <select v-model="nuevoUsuario.sucursal_id" id="user-sucursal" name="user_sucursal" required>
                                <option value="">Selecciona sucursal</option>
                                <option v-for="suc in sucursales" :key="suc.id" :value="suc.id">
                                    {{ suc.nombre }}
                                </option>
                            </select>
                        </div>
                    </div>
                    <div v-if="error" class="alert alert-danger" style="margin-bottom: 1rem;">{{ error }}</div>
                    <div class="btn-group">
                        <button @click="guardarUsuario" class="btn btn-success" :disabled="procesando">
                            <span v-if="!procesando">✓ Guardar Usuario</span>
                            <span v-else><span class="spinner"></span> Guardando...</span>
                        </button>
                        <button @click="cancelarFormulario" class="btn btn-secondary">Cancelar</button>
                    </div>
                </div>

                <!-- Formulario Editar Usuario -->
                <div v-if="usuarioEditandoId" style="background-color: var(--gray-50); padding: 1.5rem; border-radius: 0.375rem; margin-bottom: 1.5rem;">
                    <h4 style="margin-bottom: 1rem;">Editar Usuario</h4>
                    <div class="grid grid-2">
                        <div class="form-group">
                            <label for="edit-email">Email</label>
                            <input v-model="usuarioEdicion.email" id="edit-email" name="edit_email" type="email" required>
                        </div>
                        <div class="form-group" v-if="usuarioEdicion.role === 'employee'">
                            <label for="edit-sucursal">Sucursal</label>
                            <select v-model="usuarioEdicion.sucursal_id" id="edit-sucursal" name="edit_sucursal" required>
                                <option value="">Selecciona sucursal</option>
                                <option v-for="suc in sucursales" :key="suc.id" :value="suc.id">
                                    {{ suc.nombre }}
                                </option>
                            </select>
                        </div>
                    </div>

                    <!-- Sección de cambio de contraseña -->
                    <div style="border-top: 2px solid var(--gray-200); padding-top: 1rem; margin-top: 1rem;">
                        <h5 style="margin-bottom: 1rem;">Cambiar Contraseña</h5>
                        <div class="form-group">
                            <label for="edit-password">Nueva Contraseña</label>
                            <input v-model="usuarioEdicion.new_password" id="edit-password" name="edit_password" type="password" placeholder="Dejar vacío para no cambiar">
                        </div>
                        <small style="color: var(--gray-600);">Mínimo 6 caracteres</small>
                    </div>

                    <div v-if="error" class="alert alert-danger" style="margin-top: 1rem; margin-bottom: 1rem;">{{ error }}</div>
                    <div v-if="exito" class="alert alert-success" style="margin-top: 1rem; margin-bottom: 1rem;">{{ exito }}</div>

                    <div class="btn-group">
                        <button @click="guardarEdicionUsuario" class="btn btn-success" :disabled="procesando">
                            <span v-if="!procesando">✓ Guardar Cambios</span>
                            <span v-else><span class="spinner"></span> Guardando...</span>
                        </button>
                        <button @click="cancelarEdicion" class="btn btn-secondary">Cancelar</button>
                    </div>
                </div>

                <div v-if="loading" style="text-align: center; padding: 2rem;">
                    <span class="spinner"></span>
                </div>
                <div v-else-if="usuarios.length === 0" style="padding: 2rem; text-align: center; color: var(--gray-600);">
                    No hay usuarios
                </div>
                <div v-else style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Usuario</th>
                                <th>Email</th>
                                <th>Rol</th>
                                <th>Sucursal</th>
                                <th>Estado</th>
                                <th>Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="usuario in usuarios" :key="usuario.id">
                                <td>{{ usuario.username }}</td>
                                <td>{{ usuario.email }}</td>
                                <td><strong>{{ usuario.role === 'admin' ? '🔑 Admin' : '👤 Empleado' }}</strong></td>
                                <td>{{ usuario.sucursal_nombre || '—' }}</td>
                                <td>{{ usuario.is_active ? '✓ Activo' : '✗ Inactivo' }}</td>
                                <td>
                                    <div class="btn-group">
                                        <button class="btn btn-primary btn-sm" @click="editarUsuario(usuario)">✏️ Editar</button>
                                        <button class="btn btn-danger btn-sm" @click="desactivarUsuario(usuario.id)">🗑 Desactivar</button>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            usuarios: [],
            sucursales: [],
            mostrarFormulario: false,
            usuarioEditandoId: null,
            loading: true,
            procesando: false,
            error: '',
            exito: '',
            nuevoUsuario: {
                username: '',
                email: '',
                password: '',
                role: 'employee',
                sucursal_id: ''
            },
            usuarioEdicion: {
                email: '',
                sucursal_id: '',
                new_password: '',
                role: ''
            }
        };
    },
    methods: {
        async cargarUsuarios() {
            try {
                this.loading = true;
                const res = await axios.get(
                    `${window.location.origin}/api/admin/usuarios`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.usuarios = res.data;
                this.error = '';
            } catch (err) {
                console.error('Error usuarios:', err.message);
                this.usuarios = [];
                this.error = err.response?.data?.error || 'Error cargando usuarios';
            } finally {
                this.loading = false;
            }
        },
        async cargarSucursales() {
            try {
                const apiUrl = window.location.origin;
                const res = await axios.get(
                    `${apiUrl}/api/admin/sucursales-publico`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.sucursales = Array.isArray(res.data) ? res.data.filter(s => s && s.nombre) : [];
            } catch (err) {
                console.error('Error cargando sucursales:', err);
                this.error = 'Error cargando sucursales: ' + (err.response?.data?.error || err.message);
                this.sucursales = [];
            }
        },
        async guardarUsuario() {
            this.error = '';
            if (!this.nuevoUsuario.username || !this.nuevoUsuario.email || !this.nuevoUsuario.password) {
                this.error = 'Usuario, email y contraseña son requeridos';
                return;
            }
            this.procesando = true;
            try {
                await axios.post(
                    `${window.location.origin}/api/auth/register`,
                    this.nuevoUsuario,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.cancelarFormulario();
                await this.cargarUsuarios();
            } catch (err) {
                this.error = err.response?.data?.error || 'Error guardando usuario';
            } finally {
                this.procesando = false;
            }
        },
        editarUsuario(usuario) {
            this.mostrarFormulario = false;
            this.usuarioEditandoId = usuario.id;
            this.usuarioEdicion = {
                email: usuario.email,
                sucursal_id: usuario.sucursal_id || '',
                new_password: '',
                role: usuario.role
            };
            this.error = '';
            this.exito = '';
        },
        async guardarEdicionUsuario() {
            this.error = '';
            this.exito = '';
            
            if (!this.usuarioEdicion.email) {
                this.error = 'El email es requerido';
                return;
            }

            if (this.usuarioEdicion.new_password && this.usuarioEdicion.new_password.length < 6) {
                this.error = 'La contraseña debe tener al menos 6 caracteres';
                return;
            }

            this.procesando = true;

            try {
                // Actualizar datos del usuario
                const datosActualizar = {
                    email: this.usuarioEdicion.email
                };

                if (this.usuarioEdicion.role === 'employee') {
                    datosActualizar.sucursal_id = this.usuarioEdicion.sucursal_id;
                }

                await axios.put(
                    `${window.location.origin}/api/admin/usuarios/${this.usuarioEditandoId}`,
                    datosActualizar,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );

                // Si hay contraseña nueva, cambiarla
                if (this.usuarioEdicion.new_password) {
                    await axios.post(
                        `${window.location.origin}/api/admin/usuarios/${this.usuarioEditandoId}/reset-password`,
                        { new_password: this.usuarioEdicion.new_password },
                        { headers: { Authorization: `Bearer ${this.token}` } }
                    );
                }

                this.exito = 'Usuario actualizado exitosamente';
                setTimeout(() => {
                    this.cancelarEdicion();
                    this.cargarUsuarios();
                }, 500);
            } catch (err) {
                this.error = err.response?.data?.error || 'Error actualizando usuario';
                console.error('Error:', err);
            } finally {
                this.procesando = false;
            }
        },
        cancelarFormulario() {
            this.mostrarFormulario = false;
            this.nuevoUsuario = { username: '', email: '', password: '', role: 'employee', sucursal_id: '' };
            this.error = '';
        },
        cancelarEdicion() {
            this.usuarioEditandoId = null;
            this.usuarioEdicion = { email: '', sucursal_id: '', new_password: '', role: '' };
            this.error = '';
            this.exito = '';
        },
        async desactivarUsuario(id) {
            if (!confirm('¿Estás seguro de desactivar este usuario?')) return;
            try {
                await axios.put(
                    `${window.location.origin}/api/admin/usuarios/${id}`,
                    { is_active: false },
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                await this.cargarUsuarios();
            } catch (err) {
                alert('Error: ' + (err.response?.data?.error || err.message));
            }
        }
    },
    mounted() {
        console.log('UsuariosView mounted - token:', !!this.token);
        if (this.token) {
            console.log('UsuariosView: Cargando datos...');
            this.cargarUsuarios();
            this.cargarSucursales();
        }
    },
    watch: {
        token(newToken) {
            if (newToken) {
                console.log('UsuariosView: token cambió, recargando...');
                this.cargarUsuarios();
                this.cargarSucursales();
            }
        }
    }
};

// ============= COMPONENTE: DASHBOARD (Admin) =============
const DashboardView = {
    props: ['apiUrl', 'token', 'userRole'],
    template: `
        <div>
            <div class="stats-grid">
                <div class="stat-card" style="border-left-color: #10b981;">
                    <h3>Ventas Hoy</h3>
                    <div class="value">\${{ ventasHoy }}</div>
                </div>
                <div class="stat-card" style="border-left-color: #3b82f6;">
                    <h3>Transacciones</h3>
                    <div class="value">{{ transaccionesHoy }}</div>
                </div>
                <div class="stat-card" style="border-left-color: #f59e0b;">
                    <h3>Productos</h3>
                    <div class="value">{{ totalProductos }}</div>
                </div>
                <div class="stat-card" style="border-left-color: #ef4444;">
                    <h3>Bajo Stock</h3>
                    <div class="value">{{ bajoStock }}</div>
                </div>
            </div>

            <div class="grid grid-2" style="gap: 2rem; margin-top: 2rem;">
                <div class="card">
                    <div class="card-header">
                        <h3>Ventas por Sucursal (Hoy)</h3>
                    </div>
                    <div v-if="ventasPorSucursal.length === 0" style="padding: 1rem; text-align: center; color: var(--gray-600);">
                        Sin datos
                    </div>
                    <div v-else>
                        <div style="max-height: 350px; margin-bottom: 1rem;">
                            <canvas ref="chartSucursales"></canvas>
                        </div>
                        <div style="overflow-x: auto;">
                            <table style="margin-top: 1rem;">
                                <thead>
                                    <tr>
                                        <th>Sucursal</th>
                                        <th>Total</th>
                                        <th>Transacciones</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr v-for="venta in ventasPorSucursal" :key="venta.sucursal_id">
                                        <td>{{ venta.sucursal }}</td>
                                        <td>\${{ (venta.total || 0).toFixed(2) }}</td>
                                        <td>{{ venta.cantidad }}</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <h3>Top 5 Productos Vendidos</h3>
                    </div>
                    <div v-if="productosTopVenta.length === 0" style="padding: 1rem; text-align: center; color: var(--gray-600);">
                        Sin datos
                    </div>
                    <div v-else>
                        <div v-for="prod in productosTopVenta" :key="prod.id" style="padding: 0.75rem; border-bottom: 1px solid var(--gray-200);">
                            <div style="font-weight: 600; margin-bottom: 0.25rem;">{{ prod.nombre }}</div>
                            <div style="font-size: 0.875rem; color: var(--gray-600);">
                                {{ prod.cantidad }} unidades | \${{ (prod.ingresos || 0).toFixed(2) }}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            ventasHoy: 0,
            transaccionesHoy: 0,
            totalProductos: 0,
            bajoStock: 0,
            ventasPorSucursal: [],
            productosTopVenta: [],
            chartSucursalesInstance: null
        };
    },
    methods: {
        async cargarDatos() {
            try {
                const hoy = new Date().toISOString().split('T')[0];
                
                // Ventas del día
                const resVentas = await axios.get(
                    `${window.location.origin}/api/reportes/ventas-diarias`,
                    {
                        params: { fecha: hoy },
                        headers: { Authorization: `Bearer ${this.token}` }
                    }
                );
                this.ventasHoy = (resVentas.data.total_ventas || 0).toFixed(2);
                this.transaccionesHoy = resVentas.data.cantidad_transacciones || 0;
                
                // Consolidado por sucursal
                const resConsolidado = await axios.get(
                    `${window.location.origin}/api/reportes/consolidado-sucursales`,
                    {
                        params: { fecha_inicio: hoy },
                        headers: { Authorization: `Bearer ${this.token}` }
                    }
                );
                this.ventasPorSucursal = Object.values(resConsolidado.data?.por_sucursal || {});
                
                // Generar gráfica después de obtener datos
                this.$nextTick(() => {
                    this.generarGraficaSucursales();
                });
                
                // Productos vendidos
                const resProductos = await axios.get(
                    `${window.location.origin}/api/reportes/productos-vendidos`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.productosTopVenta = (resProductos.data || []).slice(0, 5);
                
                // Productos con bajo stock
                const resBajoStock = await axios.get(
                    `${window.location.origin}/api/reportes/productos-bajo-stock`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.bajoStock = resBajoStock.data.cantidad_bajo_stock || 0;
                
                // Total de productos
                const resTotalProductos = await axios.get(
                    `${window.location.origin}/api/reportes/total-productos`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.totalProductos = resTotalProductos.data.total_productos || 0;
            } catch (err) {
                console.error('Error en DashboardView:', err);
            }
        },
        generarGraficaSucursales() {
            if (this.ventasPorSucursal.length === 0) return;

            const sucursales = this.ventasPorSucursal.map(v => v.sucursal);
            const totales = this.ventasPorSucursal.map(v => v.total || 0);
            const transacciones = this.ventasPorSucursal.map(v => v.cantidad || 0);

            if (this.chartSucursalesInstance) this.chartSucursalesInstance.destroy();

            this.chartSucursalesInstance = new Chart(this.$refs.chartSucursales, {
                type: 'bar',
                data: {
                    labels: sucursales,
                    datasets: [
                        {
                            label: 'Total Ventas',
                            data: totales,
                            backgroundColor: '#2563eb',
                            borderColor: '#1e40af',
                            borderWidth: 1,
                            yAxisID: 'y'
                        },
                        {
                            label: 'Transacciones',
                            data: transacciones,
                            backgroundColor: '#10b981',
                            borderColor: '#059669',
                            borderWidth: 1,
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'bottom'
                        }
                    },
                    scales: {
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: {
                                display: true,
                                text: 'Total Ventas ($)'
                            },
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toLocaleString('es-AR');
                                }
                            }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            title: {
                                display: true,
                                text: 'Transacciones'
                            },
                            grid: {
                                drawOnChartArea: false
                            }
                        }
                    }
                }
            });
        }
    },
    mounted() {
        this.cargarDatos();
    },
    watch: {
        token(newToken) {
            if (newToken) {
                this.cargarDatos();
            }
        }
    }
};

// ============= COMPONENTE: VENTAS SIN STOCK (Admin Only) =============
const VentasSinStockView = {
    props: ['apiUrl', 'token', 'userRole'],
    template: `
        <div class="card">
            <div class="card-header">
                <h2>📦 Ventas Sin Stock</h2>
                <p style="margin-top: 0.5rem; color: var(--gray-600); font-size: 0.875rem;">
                    Productos vendidos sin stock disponible
                </p>
            </div>

            <div style="padding: 1.5rem; border-bottom: 1px solid var(--gray-200);">
                <div class="grid" style="gap: 1rem; grid-template-columns: 1fr 1fr 1fr; align-items: end;">
                    <div>
                        <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">
                            Fecha Inicio
                        </label>
                        <input 
                            v-model="filtros.fecha_inicio" 
                            type="date"
                            style="width: 100%; padding: 0.5rem; border: 1px solid var(--gray-300); border-radius: 0.375rem;"
                            @change="cargarDatos"
                        />
                    </div>
                    <div>
                        <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">
                            Fecha Fin
                        </label>
                        <input 
                            v-model="filtros.fecha_fin" 
                            type="date"
                            style="width: 100%; padding: 0.5rem; border: 1px solid var(--gray-300); border-radius: 0.375rem;"
                            @change="cargarDatos"
                        />
                    </div>
                    <button 
                        @click="limpiarFiltros"
                        style="background: var(--gray-400); padding: 0.5rem 1rem; color: white; border: none; border-radius: 0.375rem; cursor: pointer;"
                    >
                        Limpiar
                    </button>
                </div>
            </div>

            <div v-if="cargando" style="text-align: center; padding: 2rem; color: var(--gray-600);">
                Cargando...
            </div>
            <div v-else-if="ventasSinStock.length === 0" style="padding: 2rem; text-align: center; color: var(--gray-600);">
                <p>No hay ventas sin stock en este período</p>
            </div>
            <div v-else style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: var(--gray-50); border-bottom: 2px solid var(--gray-300);">
                            <th style="padding: 0.75rem; text-align: left;">Fecha</th>
                            <th style="padding: 0.75rem; text-align: left;">Venta #</th>
                            <th style="padding: 0.75rem; text-align: left;">Producto</th>
                            <th style="padding: 0.75rem; text-align: left;">Código</th>
                            <th style="padding: 0.75rem; text-align: right;">Cantidad</th>
                            <th style="padding: 0.75rem; text-align: right;">Costo Unit.</th>
                            <th style="padding: 0.75rem; text-align: right;">Costo Total</th>
                            <th style="padding: 0.75rem; text-align: left;">Sucursal</th>
                            <th style="padding: 0.75rem; text-align: left;">Cajero</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr 
                            v-for="venta in ventasSinStock" 
                            :key="venta.detalle_id"
                            style="border-bottom: 1px solid var(--gray-200); hover: {background: var(--gray-50)}"
                        >
                            <td style="padding: 0.75rem;">
                                {{ new Date(venta.fecha_venta).toLocaleDateString('es-MX', {year: 'numeric', month: '2-digit', day: '2-digit'}) }}
                            </td>
                            <td style="padding: 0.75rem; font-weight: 600; color: #2563eb;">
                                {{ venta.numero_venta }}
                            </td>
                            <td style="padding: 0.75rem;">{{ venta.producto_nombre }}</td>
                            <td style="padding: 0.75rem; font-family: monospace; font-size: 0.875rem;">
                                {{ venta.producto_codigo }}
                            </td>
                            <td style="padding: 0.75rem; text-align: right; font-weight: 600;">
                                {{ venta.cantidad_vendida }}
                            </td>
                            <td style="padding: 0.75rem; text-align: right;">
                                \${{ venta.costo_unitario.toFixed(2) }}
                            </td>
                            <td style="padding: 0.75rem; text-align: right; font-weight: 600; color: #ef4444;">
                                \${{ venta.costo_total.toFixed(2) }}
                            </td>
                            <td style="padding: 0.75rem;">{{ venta.sucursal }}</td>
                            <td style="padding: 0.75rem;">{{ venta.cajero }}</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <div v-if="ventasSinStock.length > 0" style="padding: 1rem; border-top: 1px solid var(--gray-200); text-align: right; color: var(--gray-600);">
                <strong>Total sin stock:</strong> \${{ totalSinStock.toFixed(2) }}
            </div>

            <div v-if="pagination.pages > 1" style="padding: 1rem; display: flex; gap: 0.5rem; justify-content: center; border-top: 1px solid var(--gray-200);">
                <button 
                    v-for="page in pagination.pages" 
                    :key="page"
                    @click="irAPagina(page)"
                    :style="{
                        padding: '0.5rem 1rem',
                        background: page === paginaActual ? '#2563eb' : 'var(--gray-300)',
                        color: page === paginaActual ? 'white' : 'black',
                        border: 'none',
                        borderRadius: '0.375rem',
                        cursor: 'pointer'
                    }"
                >
                    {{ page }}
                </button>
            </div>
        </div>
    `,
    data() {
        return {
            ventasSinStock: [],
            cargando: false,
            filtros: {
                fecha_inicio: '',
                fecha_fin: ''
            },
            pagination: {
                page: 1,
                per_page: 50,
                total: 0,
                pages: 1
            },
            paginaActual: 1
        };
    },
    computed: {
        totalSinStock() {
            return this.ventasSinStock.reduce((sum, venta) => sum + venta.costo_total, 0);
        }
    },
    methods: {
        async cargarDatos(page = 1) {
            this.cargando = true;
            try {
                const params = {
                    page: page,
                    per_page: this.pagination.per_page
                };

                if (this.filtros.fecha_inicio) {
                    params.fecha_inicio = this.filtros.fecha_inicio;
                }
                if (this.filtros.fecha_fin) {
                    params.fecha_fin = this.filtros.fecha_fin;
                }

                const response = await axios.get(
                    `${window.location.origin}/api/ventas/sin-stock`,
                    {
                        params,
                        headers: { Authorization: `Bearer ${this.token}` }
                    }
                );

                this.ventasSinStock = response.data.ventas_sin_stock || [];
                this.pagination = response.data.pagination || {};
                this.paginaActual = page;
            } catch (error) {
                console.error('Error cargando ventas sin stock:', error);
                this.$emit('show-alert', 'Error al cargar datos', 'error');
            } finally {
                this.cargando = false;
            }
        },
        limpiarFiltros() {
            this.filtros.fecha_inicio = '';
            this.filtros.fecha_fin = '';
            this.cargarDatos(1);
        },
        irAPagina(page) {
            this.cargarDatos(page);
        }
    },
    mounted() {
        this.cargarDatos();
    }
};

// ============= COMPONENTE: SUCURSALES (Admin) =============
const SucursalesView = {
    props: ['apiUrl', 'token', 'userRole'],
    template: `
        <div>
            <div class="card">
                <div class="card-header">
                    <h3>Gestión de Sucursales</h3>
                    <div class="btn-group">
                        <button @click="mostrarFormulario = !mostrarFormulario" class="btn btn-primary">
                            {{ mostrarFormulario ? '← Ocultar' : '+ Nueva Sucursal' }}
                        </button>
                    </div>
                </div>

                <!-- Formulario de nueva sucursal -->
                <div v-if="mostrarFormulario" style="background-color: var(--gray-50); padding: 1.5rem; border-radius: 0.375rem; margin-bottom: 1.5rem;">
                    <h4 style="margin-bottom: 1rem;">{{ formularioEditando ? 'Editar Sucursal' : 'Nueva Sucursal' }}</h4>
                    <div class="grid grid-2">
                        <div class="form-group">
                            <label for="sucursal-nombre">Nombre *</label>
                            <input v-model="nuevoFormulario.nombre" id="sucursal-nombre" name="sucursal_nombre" type="text" placeholder="Ej: Sucursal Centro" required>
                        </div>
                        <div class="form-group">
                            <label for="sucursal-ciudad">Ciudad *</label>
                            <input v-model="nuevoFormulario.ciudad" id="sucursal-ciudad" name="sucursal_ciudad" type="text" placeholder="Ej: Buenos Aires" required>
                        </div>
                    </div>
                    <div class="grid grid-2">
                        <div class="form-group">
                            <label for="sucursal-direccion">Dirección *</label>
                            <input v-model="nuevoFormulario.direccion" id="sucursal-direccion" name="sucursal_direccion" type="text" placeholder="Ej: Av. Principal 123" required>
                        </div>
                        <div class="form-group">
                            <label for="sucursal-telefono">Teléfono</label>
                            <input v-model="nuevoFormulario.telefono" id="sucursal-telefono" name="sucursal_telefono" type="text" placeholder="Ej: 1123456789">
                        </div>
                    </div>
                    
                    <div v-if="error" class="alert alert-danger" style="margin-bottom: 1rem;">
                        {{ error }}
                    </div>

                    <div class="btn-group">
                        <button @click="guardarSucursal" class="btn btn-success" :disabled="procesando">
                            <span v-if="!procesando">✓ Guardar</span>
                            <span v-else><span class="spinner"></span> Guardando...</span>
                        </button>
                        <button @click="cancelarFormulario" class="btn btn-secondary">Cancelar</button>
                    </div>
                </div>

                <!-- Tabla de sucursales -->
                <div v-if="loading" style="text-align: center; padding: 2rem;">
                    <span class="spinner"></span>
                </div>

                <div v-else-if="sucursales.length === 0" style="padding: 2rem; text-align: center; color: var(--gray-600);">
                    No hay sucursales registradas
                </div>

                <table v-else>
                    <thead>
                        <tr>
                            <th>Nombre</th>
                            <th>Ciudad</th>
                            <th>Dirección</th>
                            <th>Teléfono</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="sucursal in sucursales" :key="sucursal.id">
                            <td><strong>{{ sucursal.nombre }}</strong></td>
                            <td>{{ sucursal.ciudad }}</td>
                            <td>{{ sucursal.direccion }}</td>
                            <td>{{ sucursal.telefono || '-' }}</td>
                            <td>
                                <div class="btn-group">
                                    <button @click="editarSucursal(sucursal)" class="btn btn-primary btn-sm">✏️ Editar</button>
                                    <button @click="eliminarSucursal(sucursal)" class="btn btn-danger btn-sm">🗑 Eliminar</button>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>

                <div v-if="exito" class="alert alert-success" style="margin-top: 1rem;">
                    {{ exito }}
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            sucursales: [],
            nuevoFormulario: {
                nombre: '',
                ciudad: '',
                direccion: '',
                telefono: ''
            },
            mostrarFormulario: false,
            formularioEditando: false,
            sucursalEditandoId: null,
            loading: true,
            procesando: false,
            error: '',
            exito: ''
        };
    },
    methods: {
        async cargarSucursales() {
            try {
                this.loading = true;
                const res = await axios.get(
                    `${window.location.origin}/api/admin/sucursales`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.sucursales = Array.isArray(res.data) ? res.data.filter(s => s && s.nombre) : [];
                this.error = '';
            } catch (err) {
                console.error('Error sucursales:', err.message);
                this.error = err.response?.data?.error || 'Error cargando sucursales';
                this.sucursales = [];
            } finally {
                this.loading = false;
            }
        },
        editarSucursal(sucursal) {
            this.formularioEditando = true;
            this.sucursalEditandoId = sucursal.id;
            this.nuevoFormulario = {
                nombre: sucursal.nombre,
                ciudad: sucursal.ciudad,
                direccion: sucursal.direccion,
                telefono: sucursal.telefono || ''
            };
            this.mostrarFormulario = true;
            this.error = '';
            this.exito = '';
        },
        cancelarFormulario() {
            this.mostrarFormulario = false;
            this.formularioEditando = false;
            this.sucursalEditandoId = null;
            this.nuevoFormulario = {
                nombre: '',
                ciudad: '',
                direccion: '',
                telefono: ''
            };
            this.error = '';
        },
        async guardarSucursal() {
            this.error = '';
            this.exito = '';
            
            if (!this.nuevoFormulario.nombre || !this.nuevoFormulario.ciudad || !this.nuevoFormulario.direccion) {
                this.error = 'Los campos Nombre, Ciudad y Dirección son requeridos';
                return;
            }

            this.procesando = true;
            
            try {
                if (this.formularioEditando) {
                    // Actualizar
                    const res = await axios.put(
                        `${window.location.origin}/api/admin/sucursales/${this.sucursalEditandoId}`,
                        this.nuevoFormulario,
                        { headers: { Authorization: `Bearer ${this.token}` } }
                    );
                    this.exito = 'Sucursal actualizada exitosamente';
                } else {
                    // Crear
                    const res = await axios.post(
                        `${window.location.origin}/api/admin/sucursales`,
                        this.nuevoFormulario,
                        { headers: { Authorization: `Bearer ${this.token}` } }
                    );
                    this.exito = 'Sucursal creada exitosamente';
                }
                
                // Recargar lista
                setTimeout(() => {
                    this.cargarSucursales();
                    this.cancelarFormulario();
                }, 500);
            } catch (err) {
                this.error = err.response?.data?.error || 'Error guardando sucursal';
                console.error('Error:', err);
            } finally {
                this.procesando = false;
            }
        },
        async eliminarSucursal(sucursal) {
            if (!confirm(`¿Estás seguro de que deseas eliminar la sucursal "${sucursal.nombre}"?`)) {
                return;
            }

            this.error = '';
            this.exito = '';
            
            try {
                await axios.delete(
                    `${window.location.origin}/api/admin/sucursales/${sucursal.id}`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.exito = 'Sucursal eliminada exitosamente';
                
                // Recargar lista
                setTimeout(() => {
                    this.cargarSucursales();
                }, 500);
            } catch (err) {
                this.error = err.response?.data?.error || 'Error eliminando sucursal';
                console.error('Error:', err);
            }
        }
    },
    mounted() {
        console.log('SucursalesView mounted - token:', !!this.token);
        if (this.token) {
            console.log('SucursalesView: Cargando datos...');
            this.cargarSucursales();
        }
    },
    watch: {
        token(newToken) {
            if (newToken) {
                console.log('SucursalesView: token cambió, recargando...');
                this.cargarSucursales();
            }
        }
    }
};

// ============= COMPONENTE: CATEGORÍAS (Admin) =============
const CategoriasView = {
    props: ['apiUrl', 'token', 'userRole'],
    template: `
        <div>
            <div class="card">
                <div class="card-header">
                    <h3>Gestión de Categorías</h3>
                    <div class="btn-group">
                        <button @click="mostrarFormulario = !mostrarFormulario" class="btn btn-primary">
                            {{ mostrarFormulario ? '← Ocultar' : '+ Nueva Categoría' }}
                        </button>
                    </div>
                </div>

                <!-- Formulario de nueva categoría -->
                <div v-if="mostrarFormulario" style="background-color: var(--gray-50); padding: 1.5rem; border-radius: 0.375rem; margin-bottom: 1.5rem;">
                    <h4 style="margin-bottom: 1rem;">{{ formularioEditando ? 'Editar Categoría' : 'Nueva Categoría' }}</h4>
                    <div class="grid grid-2">
                        <div class="form-group">
                            <label for="cat-nombre">Nombre *</label>
                            <input v-model="nuevoFormulario.nombre" id="cat-nombre" name="cat_nombre" type="text" required>
                        </div>
                        <div class="form-group">
                            <label for="cat-descripcion">Descripción</label>
                            <input v-model="nuevoFormulario.descripcion" id="cat-descripcion" name="cat_descripcion" type="text">
                        </div>
                    </div>
                    
                    <div v-if="error" class="alert alert-danger" style="margin-bottom: 1rem;">{{ error }}</div>

                    <div class="btn-group">
                        <button @click="guardarCategoria" class="btn btn-success" :disabled="procesando">
                            <span v-if="!procesando">✓ Guardar</span>
                            <span v-else><span class="spinner"></span> Guardando...</span>
                        </button>
                        <button @click="cancelarFormulario" class="btn btn-secondary">Cancelar</button>
                    </div>
                </div>

                <!-- Tabla de categorías -->
                <div v-if="loading" style="text-align: center; padding: 2rem;">
                    <span class="spinner"></span>
                </div>

                <div v-else-if="categorias.length === 0" style="padding: 2rem; text-align: center; color: var(--gray-600);">
                    No hay categorías registradas
                </div>

                <table v-else>
                    <thead>
                        <tr>
                            <th>Nombre</th>
                            <th>Descripción</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="categoria in categorias" :key="categoria.id">
                            <td><strong>{{ categoria.nombre }}</strong></td>
                            <td>{{ categoria.descripcion || '-' }}</td>
                            <td>
                                <div class="btn-group">
                                    <button @click="editarCategoria(categoria)" class="btn btn-primary btn-sm">✏️ Editar</button>
                                    <button @click="eliminarCategoria(categoria)" class="btn btn-danger btn-sm">🗑 Eliminar</button>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>

                <div v-if="exito" class="alert alert-success" style="margin-top: 1rem;">
                    {{ exito }}
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            categorias: [],
            nuevoFormulario: {
                nombre: '',
                descripcion: ''
            },
            mostrarFormulario: false,
            formularioEditando: false,
            categoriaEditandoId: null,
            loading: true,
            procesando: false,
            error: '',
            exito: ''
        };
    },
    methods: {
        async cargarCategorias() {
            try {
                this.loading = true;
                const res = await axios.get(
                    `${window.location.origin}/api/productos/categorias`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.categorias = Array.isArray(res.data) ? res.data.filter(c => c && c.nombre) : [];
                this.error = '';
            } catch (err) {
                console.error('Error categorias:', err.message);
                this.error = err.response?.data?.error || 'Error cargando categorías';
                this.categorias = [];
            } finally {
                this.loading = false;
            }
        },
        editarCategoria(categoria) {
            this.formularioEditando = true;
            this.categoriaEditandoId = categoria.id;
            this.nuevoFormulario = {
                nombre: categoria.nombre,
                descripcion: categoria.descripcion || ''
            };
            this.mostrarFormulario = true;
            this.error = '';
            this.exito = '';
        },
        cancelarFormulario() {
            this.mostrarFormulario = false;
            this.formularioEditando = false;
            this.categoriaEditandoId = null;
            this.nuevoFormulario = {
                nombre: '',
                descripcion: ''
            };
            this.error = '';
        },
        async guardarCategoria() {
            this.error = '';
            this.exito = '';
            
            if (!this.nuevoFormulario.nombre) {
                this.error = 'El nombre es requerido';
                return;
            }

            this.procesando = true;
            
            try {
                if (this.formularioEditando) {
                    await axios.put(
                        `${window.location.origin}/api/productos/categorias/${this.categoriaEditandoId}`,
                        this.nuevoFormulario,
                        { headers: { Authorization: `Bearer ${this.token}` } }
                    );
                    this.exito = 'Categoría actualizada exitosamente';
                } else {
                    await axios.post(
                        `${window.location.origin}/api/productos/categorias`,
                        this.nuevoFormulario,
                        { headers: { Authorization: `Bearer ${this.token}` } }
                    );
                    this.exito = 'Categoría creada exitosamente';
                }
                
                setTimeout(() => {
                    this.cargarCategorias();
                    this.cancelarFormulario();
                }, 500);
            } catch (err) {
                this.error = err.response?.data?.error || 'Error guardando categoría';
                console.error('Error:', err);
            } finally {
                this.procesando = false;
            }
        },
        async eliminarCategoria(categoria) {
            if (!confirm(`¿Estás seguro de que deseas eliminar la categoría "${categoria.nombre}"?`)) {
                return;
            }

            this.error = '';
            this.exito = '';
            
            try {
                await axios.delete(
                    `${window.location.origin}/api/productos/categorias/${categoria.id}`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.exito = 'Categoría eliminada exitosamente';
                
                setTimeout(() => {
                    this.cargarCategorias();
                }, 500);
            } catch (err) {
                this.error = err.response?.data?.error || 'Error eliminando categoría';
                console.error('Error:', err);
            }
        }
    },
    mounted() {
        console.log('CategoriasView mounted - token:', !!this.token);
        if (this.token) {
            console.log('CategoriasView: Cargando datos...');
            this.cargarCategorias();
        }
    },
    watch: {
        token(newToken) {
            if (newToken) {
                console.log('CategoriasView: token cambió, recargando...');
                this.cargarCategorias();
            }
        }
    }
};

// ============= COMPONENTE: SUBCATEGORÍAS (Admin) =============
const SubcategoriasView = {
    props: ['apiUrl', 'token', 'userRole'],
    template: `
        <div>
            <div class="card">
                <div class="card-header">
                    <h3>Gestión de Subcategorías</h3>
                    <div class="btn-group">
                        <button @click="mostrarFormulario = !mostrarFormulario" class="btn btn-primary">
                            {{ mostrarFormulario ? '← Ocultar' : '+ Nueva Subcategoría' }}
                        </button>
                    </div>
                </div>

                <!-- Formulario de nueva/editar subcategoría -->
                <div v-if="mostrarFormulario" style="background-color: var(--gray-50); padding: 1.5rem; border-radius: 0.375rem; margin-bottom: 1.5rem;">
                    <h4 style="margin-bottom: 1rem;">{{ nuevoFormulario.id ? 'Editar Subcategoría' : 'Nueva Subcategoría' }}</h4>
                    <div class="grid grid-3">
                        <div class="form-group">
                            <label for="subcat-categoria">Categoría *</label>
                            <select v-model="nuevoFormulario.categoria_id" id="subcat-categoria" name="subcat_categoria" required>
                                <option value="">Selecciona categoría</option>
                                <option v-for="cat in categorias" :key="cat.id" :value="cat.id">
                                    {{ cat.nombre }}
                                </option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="subcat-nombre">Nombre *</label>
                            <input v-model="nuevoFormulario.nombre" id="subcat-nombre" name="subcat_nombre" type="text" required>
                        </div>
                        <div class="form-group">
                            <label for="subcat-descripcion">Descripción</label>
                            <input v-model="nuevoFormulario.descripcion" id="subcat-descripcion" name="subcat_descripcion" type="text">
                        </div>
                    </div>
                    
                    <div v-if="error" class="alert alert-danger" style="margin-bottom: 1rem;">{{ error }}</div>

                    <div class="btn-group">
                        <button @click="guardarSubcategoria" class="btn btn-success" :disabled="procesando">
                            <span v-if="!procesando">{{ nuevoFormulario.id ? '✓ Actualizar' : '✓ Guardar' }}</span>
                            <span v-else><span class="spinner"></span> Guardando...</span>
                        </button>
                        <button @click="cancelarFormulario" class="btn btn-secondary">Cancelar</button>
                    </div>
                </div>

                <!-- Tabla de subcategorías -->
                <div v-if="loading" style="text-align: center; padding: 2rem;">
                    <span class="spinner"></span>
                </div>

                <div v-else-if="subcategorias.length === 0" style="padding: 2rem; text-align: center; color: var(--gray-600);">
                    No hay subcategorías registradas
                </div>

                <table v-else>
                    <thead>
                        <tr>
                            <th>Categoría</th>
                            <th>Subcategoría</th>
                            <th>Descripción</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="subcat in subcategorias" :key="subcat.id">
                            <td><strong>{{ obtenerNombreCategoria(subcat.categoria_id) }}</strong></td>
                            <td>{{ subcat.nombre }}</td>
                            <td>{{ subcat.descripcion || '-' }}</td>
                            <td>
                                <div class="btn-group">
                                    <button @click="editarSubcategoria(subcat)" class="btn btn-primary btn-sm">✏️ Editar</button>
                                    <button @click="eliminarSubcategoria(subcat)" class="btn btn-danger btn-sm">🗑 Eliminar</button>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>

                <div v-if="exito" class="alert alert-success" style="margin-top: 1rem;">
                    {{ exito }}
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            subcategorias: [],
            categorias: [],
            nuevoFormulario: {
                id: null,
                categoria_id: '',
                nombre: '',
                descripcion: ''
            },
            mostrarFormulario: false,
            loading: true,
            procesando: false,
            error: '',
            exito: ''
        };
    },
    methods: {
        async cargarSubcategorias() {
            try {
                this.loading = true;
                const res = await axios.get(
                    `${window.location.origin}/api/productos/subcategorias`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.subcategorias = Array.isArray(res.data) ? res.data.filter(s => s && s.nombre) : [];
                this.error = '';
            } catch (err) {
                console.error('Error subcategorias:', err.message);
                this.error = err.response?.data?.error || 'Error cargando subcategorías';
                this.subcategorias = [];
            } finally {
                this.loading = false;
            }
        },
        async cargarCategorias() {
            try {
                const res = await axios.get(
                    `${window.location.origin}/api/productos/categorias`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.categorias = Array.isArray(res.data) ? res.data.filter(c => c && c.nombre) : [];
            } catch (err) {
                console.error('Error cargando categorías:', err);
                this.categorias = [];
            }
        },
        obtenerNombreCategoria(categoriaId) {
            const cat = this.categorias.find(c => c.id === categoriaId);
            return cat ? cat.nombre : 'Desconocida';
        },
        cancelarFormulario() {
            this.mostrarFormulario = false;
            this.nuevoFormulario = {
                id: null,
                categoria_id: '',
                nombre: '',
                descripcion: ''
            };
            this.error = '';
        },
        editarSubcategoria(subcat) {
            this.nuevoFormulario = {
                id: subcat.id,
                categoria_id: subcat.categoria_id,
                nombre: subcat.nombre,
                descripcion: subcat.descripcion || ''
            };
            this.mostrarFormulario = true;
            this.error = '';
        },
        async guardarSubcategoria() {
            this.error = '';
            this.exito = '';
            
            if (!this.nuevoFormulario.nombre || !this.nuevoFormulario.categoria_id) {
                this.error = 'Nombre y categoría son requeridos';
                return;
            }

            this.procesando = true;
            const isEditing = !!this.nuevoFormulario.id;
            const payload = {
                categoria_id: this.nuevoFormulario.categoria_id,
                nombre: this.nuevoFormulario.nombre,
                descripcion: this.nuevoFormulario.descripcion
            };
            
            try {
                if (isEditing) {
                    // Actualizar subcategoría existente
                    await axios.put(
                        `${window.location.origin}/api/productos/subcategorias/${this.nuevoFormulario.id}`,
                        payload,
                        { headers: { Authorization: `Bearer ${this.token}` } }
                    );
                    this.exito = 'Subcategoría actualizada exitosamente';
                } else {
                    // Crear nueva subcategoría
                    await axios.post(
                        `${window.location.origin}/api/productos/subcategorias`,
                        payload,
                        { headers: { Authorization: `Bearer ${this.token}` } }
                    );
                    this.exito = 'Subcategoría creada exitosamente';
                }
                
                setTimeout(() => {
                    this.cargarSubcategorias();
                    this.cancelarFormulario();
                }, 500);
            } catch (err) {
                this.error = err.response?.data?.error || 'Error guardando subcategoría';
                console.error('Error:', err);
            } finally {
                this.procesando = false;
            }
        },
        async eliminarSubcategoria(subcat) {
            if (!confirm(`¿Estás seguro de que deseas eliminar la subcategoría "${subcat.nombre}"?`)) {
                return;
            }

            this.error = '';
            this.exito = '';
            
            try {
                await axios.delete(
                    `${window.location.origin}/api/productos/subcategorias/${subcat.id}`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.exito = 'Subcategoría eliminada exitosamente';
                
                setTimeout(() => {
                    this.cargarSubcategorias();
                }, 500);
            } catch (err) {
                this.error = err.response?.data?.error || 'Error eliminando subcategoría';
                console.error('Error:', err);
            }
        }
    },
    mounted() {
        console.log('SubcategoriasView mounted - token:', !!this.token);
        if (this.token) {
            console.log('SubcategoriasView: Cargando datos...');
            this.cargarSubcategorias();
            this.cargarCategorias();
        }
    },
    watch: {
        token(newToken) {
            if (newToken) {
                console.log('SubcategoriasView: token cambió, recargando...');
                this.cargarSubcategorias();
                this.cargarCategorias();
            }
        }
    }
};

// ============= COMPONENTE: VENTAS DEL DÍA (Empleado) =============
const VentasDelDiaView = {
    template: `
        <div class="card">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">Ventas del Día</h5>
            </div>
            <div class="card-body">
                <!-- Spinner -->
                <div v-if="loading" class="text-center py-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Cargando...</span>
                    </div>
                </div>

                <!-- Errores -->
                <div v-if="error && !loading" class="alert alert-danger alert-dismissible fade show" role="alert">
                    {{ error }}
                    <button type="button" class="btn-close" @click="error = ''" aria-label="Close"></button>
                </div>

                <!-- Resumen de totales -->
                <div v-if="!loading && ventas.length > 0" class="row mb-4">
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h6 class="card-title">Total General</h6>
                                <p class="h5 text-primary">{{ formatoMoneda(totales.total) }}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h6 class="card-title">Efectivo</h6>
                                <p class="h5 text-success">{{ formatoMoneda(totales.efectivo) }}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h6 class="card-title">Tarjeta</h6>
                                <p class="h5 text-info">{{ formatoMoneda(totales.tarjeta) }}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h6 class="card-title">Transferencia</h6>
                                <p class="h5 text-warning">{{ formatoMoneda(totales.transferencia) }}</p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Tabla de ventas -->
                <div v-if="!loading && ventas.length > 0" class="table-responsive">
                    <table class="table table-striped table-hover">
                        <thead class="table-dark">
                            <tr>
                                <th>Venta #</th>
                                <th>Hora</th>
                                <th>Productos</th>
                                <th>Métodos de Pago</th>
                                <th>Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="venta in ventas" :key="venta.id" class="align-middle">
                                <td>
                                    <strong>{{ venta.numero_venta }}</strong>
                                </td>
                                <td>{{ formatoHora(venta.created_at) }}</td>
                                <td>
                                    <small>
                                        <div v-for="detalle in venta.detalles" :key="detalle.id">
                                            {{ detalle.cantidad }}x {{ detalle.producto_nombre }}
                                        </div>
                                    </small>
                                </td>
                                <td>
                                    <div v-for="pago in venta.pagos" :key="pago.id" class="mb-2">
                                        <span class="badge bg-secondary">
                                            {{ capitalizarPalabra(pago.metodo_pago) }}: {{ formatoMoneda(pago.monto) }}
                                        </span>
                                    </div>
                                    <button 
                                        v-if="ventaPagosEditables(venta)" 
                                        class="btn btn-sm btn-outline-primary mt-2"
                                        @click="mostrarFormularioPago(venta)"
                                    >
                                        Editar Pagos
                                    </button>
                                </td>
                                <td><strong>{{ formatoMoneda(venta.total) }}</strong></td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <!-- Mensaje si no hay ventas -->
                <div v-if="!loading && ventas.length === 0" class="alert alert-info">
                    No hay ventas registradas en el día.
                </div>
            </div>

            <!-- Modal para editar pagos mixtos -->
            <div v-if="ventaSeleccionada" class="modal fade show d-block" style="background-color: rgba(0,0,0,0.5);">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Desglose de Pagos - {{ ventaSeleccionada.numero_venta }}</h5>
                            <button type="button" class="btn-close" @click="ventaSeleccionada = null"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label class="form-label">Total a distribuir: <strong>{{ formatoMoneda(ventaSeleccionada.total) }}</strong></label>
                            </div>
                            
                            <div v-for="(pago, index) in pagosTemporal" :key="index" class="mb-3 p-3 border rounded">
                                <div class="row">
                                    <div class="col-md-6">
                                        <label class="form-label">Método de Pago</label>
                                        <select v-model="pago.metodo_pago" class="form-select">
                                            <option value="efectivo">Efectivo</option>
                                            <option value="tarjeta">Tarjeta</option>
                                            <option value="transferencia">Transferencia</option>
                                        </select>
                                    </div>
                                    <div class="col-md-6">
                                        <label class="form-label">Monto</label>
                                        <input v-model.number="pago.monto" type="number" class="form-control" step="0.01" min="0">
                                    </div>
                                </div>
                                <button v-if="pagosTemporal.length > 1" class="btn btn-sm btn-danger mt-2" @click="pagosTemporal.splice(index, 1)">
                                    Eliminar
                                </button>
                            </div>

                            <button class="btn btn-sm btn-secondary" @click="agregarPagoMas">
                                + Agregar otro método
                            </button>

                            <div class="mt-3">
                                <small class="text-muted">
                                    Total pagos: <strong>{{ formatoMoneda(calcularTotalPagos()) }}</strong>
                                </small>
                                <div v-if="calcularTotalPagos() !== parseFloat(ventaSeleccionada.total)" class="text-danger mt-2">
                                    ⚠️ El total de pagos no coincide con el total de la venta
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" @click="ventaSeleccionada = null">Cancelar</button>
                            <button type="button" class="btn btn-primary" @click="guardarPagosMixtos" :disabled="calcularTotalPagos() !== parseFloat(ventaSeleccionada.total)">
                                Guardar Pagos
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    props: ['apiUrl', 'token', 'userRole'],
    data() {
        return {
            ventas: [],
            totales: { efectivo: 0, tarjeta: 0, transferencia: 0, total: 0 },
            loading: true,
            error: '',
            ventaSeleccionada: null,
            pagosTemporal: []
        };
    },
    methods: {
        cargarVentasDelDia() {
            this.loading = true;
            this.error = '';
            try {
                axios.get(`${window.location.origin}/api/ventas/del-dia/resumen`, {
                    headers: { 'Authorization': `Bearer ${this.token}` }
                })
                .then(response => {
                    this.ventas = response.data.ventas;
                    this.totales = response.data.totales;
                })
                .catch(err => {
                    console.error('Error cargando ventas:', err);
                    this.error = err.response?.data?.error || 'Error cargando ventas del día';
                })
                .finally(() => {
                    this.loading = false;
                });
            } catch (err) {
                this.error = 'Error al procesar la solicitud';
                this.loading = false;
            }
        },
        formatoMoneda(valor) {
            return new Intl.NumberFormat('es-AR', {
                style: 'currency',
                currency: 'ARS'
            }).format(valor || 0);
        },
        formatoHora(fecha) {
            return new Date(fecha).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });
        },
        capitalizarPalabra(palabra) {
            return palabra.charAt(0).toUpperCase() + palabra.slice(1);
        },
        ventaPagosEditables(venta) {
            // Mostrar opción si hay un solo pago o si es pago mixto sin detalles
            return venta.pagos && venta.pagos.length === 1;
        },
        mostrarFormularioPago(venta) {
            this.ventaSeleccionada = venta;
            this.pagosTemporal = [
                { metodo_pago: venta.pagos[0].metodo_pago, monto: venta.pagos[0].monto }
            ];
        },
        agregarPagoMas() {
            this.pagosTemporal.push({ metodo_pago: 'efectivo', monto: 0 });
        },
        calcularTotalPagos() {
            return this.pagosTemporal.reduce((sum, pago) => sum + (pago.monto || 0), 0);
        },
        guardarPagosMixtos() {
            if (this.calcularTotalPagos() !== parseFloat(this.ventaSeleccionada.total)) {
                alert('El total de pagos no coincide con el total de la venta');
                return;
            }
            
            // Llamar al endpoint para guardar
            axios.post(
                `${window.location.origin}/api/ventas/${this.ventaSeleccionada.id}/pagos`,
                {
                    pagos: this.pagosTemporal.map(p => ({
                        metodo_pago: p.metodo_pago,
                        monto: p.monto
                    }))
                },
                { headers: { 'Authorization': `Bearer ${this.token}` } }
            )
            .then(response => {
                alert('Pagos actualizados correctamente');
                this.ventaSeleccionada = null;
                this.cargarVentasDelDia();
            })
            .catch(err => {
                console.error('Error guardando pagos:', err);
                alert(err.response?.data?.error || 'Error al guardar los pagos');
            });
        }
    },
    mounted() {
        console.log('VentasDelDiaView mounted - token:', !!this.token);
        if (this.token) {
            console.log('VentasDelDiaView: Cargando datos...');
            this.cargarVentasDelDia();
        }
    },
    watch: {
        token(newToken) {
            if (newToken) {
                console.log('VentasDelDiaView: token cambió, recargando...');
                this.cargarVentasDelDia();
            }
        }
    }
};

// ============= COMPONENTE: CIERRE DE CAJA (Empleado) =============
const CierreCajaView = {
    template: `
        <div class="card">
            <div class="card-header bg-success text-white">
                <h5 class="mb-0">Cierre de Caja</h5>
            </div>
            <div class="card-body">
                <!-- Spinner -->
                <div v-if="loading" class="text-center py-5">
                    <div class="spinner-border text-success" role="status">
                        <span class="visually-hidden">Cargando...</span>
                    </div>
                </div>

                <!-- Errores -->
                <div v-if="error && !loading" class="alert alert-danger alert-dismissible fade show" role="alert">
                    {{ error }}
                    <button type="button" class="btn-close" @click="error = ''" aria-label="Close"></button>
                </div>

                <!-- Resumen de efectivo -->
                <div v-if="!loading && cierre" class="row mb-4">
                    <div class="col-md-6">
                        <div class="card bg-light">
                            <div class="card-body">
                                <h6 class="card-title">Total Esperado (Efectivo)</h6>
                                <p class="h4 text-success">{{ formatoMoneda(cierre.total_efectivo) }}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card bg-light">
                            <div class="card-body">
                                <h6 class="card-title">Efectivo Reportado</h6>
                                <p class="h4" :class="cierre.efectivo_reportado ? 'text-primary' : 'text-muted'">
                                    {{ cierre.efectivo_reportado ? formatoMoneda(cierre.efectivo_reportado) : 'Sin reportar' }}
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Diferencia -->
                <div v-if="!loading && cierre && cierre.estado === 'cerrado'" class="alert" :class="cierre.diferencia === 0 ? 'alert-success' : 'alert-warning'">
                    <strong>Diferencia:</strong> {{ formatoMoneda(cierre.diferencia) }}
                    <p v-if="cierre.diferencia > 0" class="mb-0 mt-2">✅ Hay dinero extra</p>
                    <p v-else-if="cierre.diferencia < 0" class="mb-0 mt-2">⚠️ Falta dinero</p>
                    <p v-else class="mb-0 mt-2">✓ Cuadra perfecto</p>
                </div>

                <!-- Resumen de otros pagos -->
                <div v-if="!loading && cierre" class="row mb-4">
                    <div class="col-md-4">
                        <div class="card text-center">
                            <div class="card-body">
                                <h6 class="card-title">Total Tarjeta</h6>
                                <p class="h5 text-info">{{ formatoMoneda(cierre.total_tarjeta) }}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card text-center">
                            <div class="card-body">
                                <h6 class="card-title">Total Transferencia</h6>
                                <p class="h5 text-warning">{{ formatoMoneda(cierre.total_transferencia) }}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card text-center">
                            <div class="card-body">
                                <h6 class="card-title">Total Ventas</h6>
                                <p class="h5 text-primary">{{ formatoMoneda(cierre.total_ventas) }}</p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Formulario de cierre -->
                <div v-if="!loading && cierre && cierre.estado === 'abierto'" class="border-top pt-4">
                    <h6 class="mb-4" style="font-weight: 700; color: var(--primary);">Registrar Cierre de Caja</h6>
                    <div class="row">
                        <div class="col-md-6 mb-4">
                            <label class="form-label" style="font-weight: 600; margin-bottom: 0.75rem; display: block;">Efectivo Reportado *</label>
                            <input 
                                v-model.number="formulario.efectivo_reportado" 
                                type="number" 
                                class="form-control" 
                                step="0.01" 
                                min="0"
                                placeholder="0.00"
                                style="padding: 0.75rem 1rem; border: 2px solid var(--gray-300); border-radius: 0.5rem; font-size: 1.1rem; transition: all 0.3s ease;"
                                @focus="$event.target.style.borderColor = '#2563EB'; $event.target.style.boxShadow = '0 0 0 3px rgba(37, 99, 235, 0.1)'"
                                @blur="$event.target.style.borderColor = 'var(--gray-300)'; $event.target.style.boxShadow = 'none'"
                            >
                        </div>
                        <div class="col-md-6 mb-4">
                            <label class="form-label" style="font-weight: 600; margin-bottom: 0.75rem; display: block;">Observaciones</label>
                            <input 
                                v-model="formulario.observaciones" 
                                type="text" 
                                class="form-control"
                                placeholder="(opcional)"
                                style="padding: 0.75rem 1rem; border: 2px solid var(--gray-300); border-radius: 0.5rem; font-size: 1rem; transition: all 0.3s ease;"
                                @focus="$event.target.style.borderColor = '#2563EB'; $event.target.style.boxShadow = '0 0 0 3px rgba(37, 99, 235, 0.1)'"
                                @blur="$event.target.style.borderColor = 'var(--gray-300)'; $event.target.style.boxShadow = 'none'"
                            >
                        </div>
                    </div>
                    <button 
                        @click="guardarCierre" 
                        class="btn btn-success"
                        style="padding: 0.75rem 2rem; font-weight: 600; border-radius: 0.5rem; transition: all 0.3s ease;"
                        :disabled="formulario.efectivo_reportado === null || formulario.efectivo_reportado === ''"
                    >
                        ✓ Cerrar Caja
                    </button>
                </div>

                <!-- Estado cerrado -->
                <div v-if="!loading && cierre && cierre.estado === 'cerrado'" class="alert alert-info">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <strong>✓ Caja Cerrada</strong> - Cierre realizado a las {{ formatoHora(cierre.created_at) }}
                            <p v-if="cierre.observaciones" class="mb-0 mt-2"><strong>Notas:</strong> {{ cierre.observaciones }}</p>
                        </div>
                        <button 
                            @click="abrirEdicionCierre" 
                            class="btn btn-sm btn-warning"
                            v-if="!editandoCierre"
                        >
                            ✏️ Editar
                        </button>
                    </div>

                    <!-- Modo edición para correcciones -->
                    <div v-if="editandoCierre" class="mt-4 border-top pt-4" style="background: var(--gray-50); padding: 1.5rem; border-radius: 0.5rem;">
                        <h6 style="font-weight: 700; margin-bottom: 1.5rem; color: var(--primary);">Corregir Efectivo Reportado</h6>
                        <div class="row mb-4">
                            <div class="col-md-6 mb-3">
                                <label class="form-label" style="font-weight: 600; margin-bottom: 0.75rem; display: block;">Efectivo Reportado (Actual: {{ formatoMoneda(cierre.efectivo_reportado) }})</label>
                                <input 
                                    v-model.number="formularioEdicion.efectivo_reportado" 
                                    type="number" 
                                    class="form-control" 
                                    step="0.01" 
                                    min="0"
                                    style="padding: 0.75rem 1rem; border: 2px solid var(--gray-300); border-radius: 0.5rem; font-size: 1.1rem; transition: all 0.3s ease;"
                                    @focus="$event.target.style.borderColor = '#2563EB'; $event.target.style.boxShadow = '0 0 0 3px rgba(37, 99, 235, 0.1)'"
                                    @blur="$event.target.style.borderColor = 'var(--gray-300)'; $event.target.style.boxShadow = 'none'"
                                >
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label" style="font-weight: 600; margin-bottom: 0.75rem; display: block;">Observaciones</label>
                                <input 
                                    v-model="formularioEdicion.observaciones" 
                                    type="text" 
                                    class="form-control"
                                    placeholder="Ej: Corrección de error anterior"
                                    style="padding: 0.75rem 1rem; border: 2px solid var(--gray-300); border-radius: 0.5rem; font-size: 1rem; transition: all 0.3s ease;"
                                    @focus="$event.target.style.borderColor = '#2563EB'; $event.target.style.boxShadow = '0 0 0 3px rgba(37, 99, 235, 0.1)'"
                                    @blur="$event.target.style.borderColor = 'var(--gray-300)'; $event.target.style.boxShadow = 'none'"
                                >
                            </div>
                        </div>
                        <button 
                            @click="guardarCorreccion" 
                            class="btn btn-primary btn-sm me-2"
                            style="padding: 0.5rem 1.5rem; font-weight: 600; border-radius: 0.375rem;"
                        >
                            💾 Guardar Corrección
                        </button>
                        <button 
                            @click="cancelarEdicion" 
                            class="btn btn-secondary btn-sm"
                            style="padding: 0.5rem 1.5rem; font-weight: 600; border-radius: 0.375rem;"
                        >
                            Cancelar
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `,
    props: ['apiUrl', 'token', 'userRole'],
    data() {
        return {
            cierre: null,
            loading: true,
            error: '',
            editandoCierre: false,
            formulario: {
                efectivo_reportado: null,
                observaciones: ''
            },
            formularioEdicion: {
                efectivo_reportado: null,
                observaciones: ''
            }
        };
    },
    methods: {
        cargarCierreCaja() {
            this.loading = true;
            this.error = '';
            try {
                axios.get(`${window.location.origin}/api/ventas/cierre-caja/hoy`, {
                    headers: { 'Authorization': `Bearer ${this.token}` }
                })
                .then(response => {
                    this.cierre = response.data;
                    this.formulario.efectivo_reportado = null;
                    this.formulario.observaciones = '';
                })
                .catch(err => {
                    console.error('Error cargando cierre:', err);
                    this.error = err.response?.data?.error || 'Error cargando cierre de caja';
                })
                .finally(() => {
                    this.loading = false;
                });
            } catch (err) {
                this.error = 'Error al procesar la solicitud';
                this.loading = false;
            }
        },
        guardarCierre() {
            if (this.formulario.efectivo_reportado === null) {
                alert('Debes reportar el efectivo');
                return;
            }
            
            axios.post(
                `${window.location.origin}/api/ventas/cierre-caja`,
                {
                    efectivo_reportado: this.formulario.efectivo_reportado,
                    observaciones: this.formulario.observaciones
                },
                { headers: { 'Authorization': `Bearer ${this.token}` } }
            )
            .then(response => {
                this.cierre = response.data.cierre;
                alert('Caja cerrada exitosamente');
            })
            .catch(err => {
                console.error('Error cerrando caja:', err);
                this.error = err.response?.data?.error || 'Error al cerrar caja';
            });
        },
        formatoMoneda(valor) {
            return new Intl.NumberFormat('es-AR', {
                style: 'currency',
                currency: 'ARS'
            }).format(valor || 0);
        },
        formatoHora(fecha) {
            return new Date(fecha).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });
        },
        abrirEdicionCierre() {
            this.editandoCierre = true;
            this.formularioEdicion.efectivo_reportado = this.cierre.efectivo_reportado;
            this.formularioEdicion.observaciones = this.cierre.observaciones || '';
        },
        cancelarEdicion() {
            this.editandoCierre = false;
            this.formularioEdicion.efectivo_reportado = null;
            this.formularioEdicion.observaciones = '';
        },
        guardarCorreccion() {
            if (this.formularioEdicion.efectivo_reportado === null) {
                alert('Debes ingresar el efectivo reportado');
                return;
            }
            
            axios.post(
                `${window.location.origin}/api/ventas/cierre-caja/corregir`,
                {
                    efectivo_reportado: this.formularioEdicion.efectivo_reportado,
                    observaciones: this.formularioEdicion.observaciones
                },
                { headers: { 'Authorization': `Bearer ${this.token}` } }
            )
            .then(response => {
                this.cierre = response.data.cierre;
                this.editandoCierre = false;
                alert('Corrección guardada exitosamente');
            })
            .catch(err => {
                console.error('Error guardando corrección:', err);
                this.error = err.response?.data?.error || 'Error al guardar la corrección';
            });
        }
    },
    mounted() {
        console.log('CierreCajaView mounted - token:', !!this.token);
        if (this.token) {
            console.log('CierreCajaView: Cargando datos...');
            this.cargarCierreCaja();
        }
    },
    watch: {
        token(newToken) {
            if (newToken) {
                console.log('CierreCajaView: token cambió, recargando...');
                this.cargarCierreCaja();
            }
        }
    }
};

// ============= COMPONENTE: REPORTES DE VENTAS (Admin) =============
const ReportesVentasView = {
    template: `
        <div class="card">
            <div class="card-header bg-info text-white">
                <h5 class="mb-0">📊 Reportes de Ventas</h5>
            </div>
            <div class="card-body">
                <!-- Filtros mejorados y responsivos -->
                <div class="filtros-container bg-light p-3 p-md-4 rounded mb-4">
                    <h6 class="mb-3 text-muted fw-bold">🔍 Filtros de Búsqueda</h6>
                    <div class="row g-2 g-md-3">
                        <!-- Fecha Inicio -->
                        <div class="col-12 col-md-6 col-lg-3">
                            <label class="form-label small fw-500 text-secondary">📅 Fecha Inicio</label>
                            <input 
                                v-model="filtros.fecha_inicio" 
                                type="date" 
                                class="form-control form-control-fecha"
                            >
                        </div>
                        <!-- Fecha Fin -->
                        <div class="col-12 col-md-6 col-lg-3">
                            <label class="form-label small fw-500 text-secondary">📅 Fecha Fin</label>
                            <input 
                                v-model="filtros.fecha_fin" 
                                type="date" 
                                class="form-control form-control-fecha"
                            >
                        </div>
                        <!-- Tipo Reporte -->
                        <div class="col-12 col-md-6 col-lg-3">
                            <label class="form-label small fw-500 text-secondary">📋 Tipo de Reporte</label>
                            <select v-model="tipoReporte" class="form-select form-control-fecha">
                                <option value="ventas">Ventas por Día</option>
                                <option value="cierres">Cierres de Caja</option>
                            </select>
                        </div>
                        <!-- Botón -->
                        <div class="col-12 col-md-6 col-lg-3 d-flex align-items-end">
                            <button 
                                @click="cargarReporte" 
                                class="btn btn-primary w-100"
                                :disabled="loading"
                            >
                                <span v-if="!loading">🔄 Generar</span>
                                <span v-else>
                                    <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                                    Cargando...
                                </span>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Errores -->
                <div v-if="error" class="alert alert-danger alert-dismissible fade show" role="alert">
                    {{ error }}
                    <button type="button" class="btn-close" @click="error = ''" aria-label="Close"></button>
                </div>

                <!-- Spinner -->
                <div v-if="loading" class="text-center py-5">
                    <div class="spinner-border text-info" role="status">
                        <span class="visually-hidden">Cargando...</span>
                    </div>
                </div>

                <!-- Reporte de Ventas -->
                <div v-if="!loading && tipoReporte === 'ventas' && totales" class="mt-4">
                    <h6 class="mb-3">Totales de Ventas</h6>
                    <div class="row mb-4">
                        <div class="col-md-3">
                            <div class="card text-center">
                                <div class="card-body">
                                    <h6 class="card-title">Total General</h6>
                                    <p class="h5 text-primary">{{ formatoMoneda(totales.total) }}</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="card text-center">
                                <div class="card-body">
                                    <h6 class="card-title">Efectivo</h6>
                                    <p class="h5 text-success">{{ formatoMoneda(totales.efectivo) }}</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="card text-center">
                                <div class="card-body">
                                    <h6 class="card-title">Tarjeta</h6>
                                    <p class="h5 text-info">{{ formatoMoneda(totales.tarjeta) }}</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="card text-center">
                                <div class="card-body">
                                    <h6 class="card-title">Transferencia</h6>
                                    <p class="h5 text-warning">{{ formatoMoneda(totales.transferencia) }}</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Gráficas -->
                    <div class="row mb-4">
                        <div class="col-lg-6 mb-3">
                            <div class="card">
                                <div class="card-body">
                                    <h6 class="card-title">📈 Ventas por Día</h6>
                                    <canvas ref="chartVentasPorDia" style="max-height: 300px;"></canvas>
                                </div>
                            </div>
                        </div>
                        <div class="col-lg-6 mb-3">
                            <div class="card">
                                <div class="card-body">
                                    <h6 class="card-title">💳 Métodos de Pago</h6>
                                    <canvas ref="chartMetodosPago" style="max-height: 300px;"></canvas>
                                </div>
                            </div>
                        </div>
                    </div>

                    <h6 class="mb-3">Detalles de Ventas ({{ ventas.length }} ventas)</h6>
                    <div class="table-responsive">
                        <table class="table table-striped">
                            <thead class="table-dark">
                                <tr>
                                    <th>Venta #</th>
                                    <th>Fecha/Hora</th>
                                    <th>Sucursal</th>
                                    <th>Cajero</th>
                                    <th>Métodos de Pago</th>
                                    <th>Total</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="venta in ventas" :key="venta.id">
                                    <td><small>{{ venta.numero_venta }}</small></td>
                                    <td><small>{{ formatoFecha(venta.created_at) }}</small></td>
                                    <td><small>{{ venta.sucursal_nombre }}</small></td>
                                    <td><small>{{ venta.cajero_nombre }}</small></td>
                                    <td>
                                        <small>
                                            <div v-for="pago in venta.pagos" :key="pago.id">
                                                <span class="badge bg-secondary">
                                                    {{ capitalizarPalabra(pago.metodo_pago) }}: {{ formatoMoneda(pago.monto) }}
                                                </span>
                                            </div>
                                        </small>
                                    </td>
                                    <td><small><strong>{{ formatoMoneda(venta.total) }}</strong></small></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Reporte de Cierres -->
                <div v-if="!loading && tipoReporte === 'cierres' && cierres" class="mt-4">
                    <h6 class="mb-3">Cierres de Caja ({{ cierres.length }} cierres)</h6>
                    <div class="table-responsive">
                        <table class="table table-striped">
                            <thead class="table-dark">
                                <tr>
                                    <th>Fecha</th>
                                    <th>Empleado</th>
                                    <th>Sucursal</th>
                                    <th>Total Ventas</th>
                                    <th>Efectivo</th>
                                    <th>Tarjeta</th>
                                    <th>Transferencia</th>
                                    <th>Diferencia</th>
                                    <th>Estado</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="cierre in cierres" :key="cierre.id">
                                    <td><small>{{ cierre.fecha }}</small></td>
                                    <td><small>{{ cierre.empleado_nombre }}</small></td>
                                    <td><small>{{ cierre.sucursal_nombre }}</small></td>
                                    <td><small>{{ formatoMoneda(cierre.total_ventas) }}</small></td>
                                    <td><small>{{ formatoMoneda(cierre.total_efectivo) }}</small></td>
                                    <td><small>{{ formatoMoneda(cierre.total_tarjeta) }}</small></td>
                                    <td><small>{{ formatoMoneda(cierre.total_transferencia) }}</small></td>
                                    <td>
                                        <small>
                                            <span v-if="cierre.diferencia !== null" :class="cierre.diferencia === 0 ? 'text-success fw-bold' : 'text-warning fw-bold'">
                                                {{ formatoMoneda(cierre.diferencia) }}
                                            </span>
                                            <span v-else class="text-muted">-</span>
                                        </small>
                                    </td>
                                    <td>
                                        <small>
                                            <span v-if="cierre.estado === 'cerrado'" class="badge bg-success">Cerrado</span>
                                            <span v-else class="badge bg-warning">Abierto</span>
                                        </small>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Mensaje si no hay datos -->
                <div v-if="!loading && ventas.length === 0 && tipoReporte === 'ventas'" class="alert alert-info">
                    No hay ventas en el rango de fechas seleccionado.
                </div>
                <div v-if="!loading && cierres.length === 0 && tipoReporte === 'cierres'" class="alert alert-info">
                    No hay cierres de caja en el rango de fechas seleccionado.
                </div>
            </div>
        </div>
    `,
    props: ['apiUrl', 'token', 'userRole'],
    data() {
        return {
            tipoReporte: 'ventas',
            filtros: {
                fecha_inicio: '',
                fecha_fin: ''
            },
            ventas: [],
            cierres: [],
            totales: null,
            loading: false,
            error: '',
            chartVentasInstance: null,
            chartPagoInstance: null
        };
    },
    methods: {
        cargarReporte() {
            if (!this.filtros.fecha_inicio || !this.filtros.fecha_fin) {
                this.error = 'Debes seleccionar ambas fechas';
                return;
            }
            
            this.loading = true;
            this.error = '';
            
            if (this.tipoReporte === 'ventas') {
                this.cargarReporteVentas();
            } else {
                this.cargarReporteCierres();
            }
        },
        cargarReporteVentas() {
            axios.get(`${window.location.origin}/api/ventas/reportes/por-fecha`, {
                params: {
                    fecha_inicio: this.filtros.fecha_inicio,
                    fecha_fin: this.filtros.fecha_fin
                },
                headers: { 'Authorization': `Bearer ${this.token}` }
            })
            .then(response => {
                this.ventas = response.data.ventas;
                this.totales = response.data.totales;
                // Generar gráficas después de obtener datos
                this.$nextTick(() => {
                    this.generarGraficasVentas();
                });
            })
            .catch(err => {
                console.error('Error:', err);
                this.error = err.response?.data?.error || 'Error cargando reporte';
            })
            .finally(() => {
                this.loading = false;
            });
        },
        generarGraficasVentas() {
            if (this.ventas.length === 0) return;

            // Agrupar ventas por fecha
            const ventasPorFecha = {};
            const totalesPorMetodo = { efectivo: 0, tarjeta: 0, transferencia: 0 };

            this.ventas.forEach(venta => {
                const fecha = new Date(venta.created_at).toLocaleDateString('es-AR');
                ventasPorFecha[fecha] = (ventasPorFecha[fecha] || 0) + venta.total;

                // Contar métodos de pago
                venta.pagos.forEach(pago => {
                    if (pago.metodo_pago === 'efectivo') totalesPorMetodo.efectivo += pago.monto;
                    else if (pago.metodo_pago === 'tarjeta') totalesPorMetodo.tarjeta += pago.monto;
                    else if (pago.metodo_pago === 'transferencia') totalesPorMetodo.transferencia += pago.monto;
                });
            });

            // Gráfica 1: Ventas por Día
            const fechas = Object.keys(ventasPorFecha).sort();
            const montos = fechas.map(f => ventasPorFecha[f]);

            if (this.chartVentasInstance) this.chartVentasInstance.destroy();
            this.chartVentasInstance = new Chart(this.$refs.chartVentasPorDia, {
                type: 'line',
                data: {
                    labels: fechas,
                    datasets: [{
                        label: 'Ventas Diarias',
                        data: montos,
                        borderColor: '#2563eb',
                        backgroundColor: 'rgba(37, 99, 235, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 5,
                        pointBackgroundColor: '#2563eb'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { display: true }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toLocaleString('es-AR');
                                }
                            }
                        }
                    }
                }
            });

            // Gráfica 2: Métodos de Pago
            if (this.chartPagoInstance) this.chartPagoInstance.destroy();
            this.chartPagoInstance = new Chart(this.$refs.chartMetodosPago, {
                type: 'doughnut',
                data: {
                    labels: ['Efectivo', 'Tarjeta', 'Transferencia'],
                    datasets: [{
                        data: [totalesPorMetodo.efectivo, totalesPorMetodo.tarjeta, totalesPorMetodo.transferencia],
                        backgroundColor: ['#10b981', '#3b82f6', '#f59e0b']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });
        },
        cargarReporteCierres() {
            axios.get(`${window.location.origin}/api/ventas/reportes/cierres-caja`, {
                params: {
                    fecha_inicio: this.filtros.fecha_inicio,
                    fecha_fin: this.filtros.fecha_fin
                },
                headers: { 'Authorization': `Bearer ${this.token}` }
            })
            .then(response => {
                this.cierres = response.data.cierres;
            })
            .catch(err => {
                console.error('Error:', err);
                this.error = err.response?.data?.error || 'Error cargando reporte';
            })
            .finally(() => {
                this.loading = false;
            });
        },
        formatoMoneda(valor) {
            return new Intl.NumberFormat('es-AR', {
                style: 'currency',
                currency: 'ARS'
            }).format(valor || 0);
        },
        formatoFecha(fecha) {
            return new Date(fecha).toLocaleString('es-AR', { 
                year: 'numeric', 
                month: '2-digit', 
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        },
        capitalizarPalabra(palabra) {
            return palabra.charAt(0).toUpperCase() + palabra.slice(1);
        }
    },
    mounted() {
        // Establecer fechas por defecto (hoy y hoy)
        const hoy = new Date().toISOString().split('T')[0];
        this.filtros.fecha_inicio = hoy;
        this.filtros.fecha_fin = hoy;
    }
};

// ==================== DEVOLUCIONES ====================

const DevolucionesView = {
    template: `
        <div class="container-fluid mt-4">
            <h2>Gestión de Devoluciones</h2>
            
            <div v-if="error" class="alert alert-danger alert-dismissible fade show">
                {{ error }}
                <button type="button" class="btn-close" @click="error = ''"></button>
            </div>
            
            <div class="row mb-3">
                <div class="col-md-4">
                    <label class="form-label">Sucursal</label>
                    <select v-model="sucursal_id" class="form-control" @change="obtenerVentasDelDia">
                        <option value="">Todas las sucursales</option>
                        <option v-for="sucursal in sucursales" :key="sucursal.id" :value="sucursal.id">
                            {{ sucursal.nombre }}
                        </option>
                    </select>
                </div>
                <div class="col-md-4">
                    <label class="form-label">&nbsp;</label>
                    <button class="btn btn-primary form-control" @click="obtenerVentasDelDia" :disabled="loading">
                        <span v-if="loading">Cargando...</span>
                        <span v-else>Cargar Ventas</span>
                    </button>
                </div>
            </div>
            
            <!-- VENTAS DEL DÍA -->
            <div class="card mb-4">
                <div class="card-header bg-dark text-white">
                    <h5 class="mb-0">Ventas del Día - {{ ventas.length }} registros</h5>
                </div>
                <div class="card-body">
                    <div v-if="ventas.length === 0" class="alert alert-info">
                        No hay ventas para este período
                    </div>
                    
                    <div v-else class="table-responsive">
                        <table class="table table-hover">
                            <thead class="table-light">
                                <tr>
                                    <th>Venta</th>
                                    <th>Hora</th>
                                    <th>Cajero</th>
                                    <th>Total</th>
                                    <th>Acciones</th>
                                </tr>
                            </thead>
                            <tbody>
                                <template v-for="venta in ventas" :key="venta.id">
                                    <tr @click="seleccionarVenta(venta)" style="cursor: pointer;" 
                                        :class="{ 'table-active': ventaSeleccionada && ventaSeleccionada.id === venta.id }">
                                        <td><strong>#{{ venta.numero_venta }}</strong></td>
                                        <td>{{ formatoFecha(venta.created_at) }}</td>
                                        <td>{{ venta.cajero_nombre }}</td>
                                        <td>{{ formatoMoneda(venta.total) }}</td>
                                        <td>
                                            <button class="btn btn-sm btn-info" @click.stop="seleccionarVenta(venta)">
                                                Ver Detalles
                                            </button>
                                        </td>
                                    </tr>
                                    
                                    <!-- DETALLES DE VENTA -->
                                    <tr v-if="ventaSeleccionada && ventaSeleccionada.id === venta.id" :class="{ 'table-active': true }">
                                        <td colspan="5">
                                            <div class="p-3 bg-light rounded">
                                                <h6 class="mb-2">Productos en esta venta:</h6>
                                                <div class="table-responsive">
                                                    <table class="table table-sm table-bordered">
                                                        <thead>
                                                            <tr>
                                                                <th>Producto</th>
                                                                <th>Cantidad</th>
                                                                <th>Precio Unit.</th>
                                                                <th>Subtotal</th>
                                                                <th>Devoluciones</th>
                                                                <th>Acción</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr v-for="detalle in venta.detalles" :key="detalle.id">
                                                                <td>{{ detalle.producto_nombre }}</td>
                                                                <td>{{ detalle.cantidad }}</td>
                                                                <td>{{ formatoMoneda(detalle.precio_unitario) }}</td>
                                                                <td>{{ formatoMoneda(detalle.subtotal) }}</td>
                                                                <td>
                                                                    <span v-if="devoluciones.filter(d => d.detalle_venta_id === detalle.id).length > 0" class="badge bg-warning">
                                                                        {{ devoluciones.filter(d => d.detalle_venta_id === detalle.id).reduce((sum, d) => sum + d.cantidad_devuelta, 0) }} devueltas
                                                                    </span>
                                                                    <span v-else class="text-muted">-</span>
                                                                </td>
                                                                <td>
                                                                    <button class="btn btn-sm btn-danger" 
                                                                            @click="mostrarModalDevolucion(venta, detalle)"
                                                                            :disabled="detalle.cantidad <= devoluciones.filter(d => d.detalle_venta_id === detalle.id).reduce((sum, d) => sum + d.cantidad_devuelta, 0)">
                                                                        Devolver
                                                                    </button>
                                                                </td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                </template>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            
            <!-- MODAL DE DEVOLUCIÓN -->
            <div v-if="modalDevolucion" class="modal d-block" style="background: rgba(0,0,0,0.5);">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header bg-danger text-white">
                            <h5 class="modal-title">Registrar Devolución</h5>
                            <button type="button" class="btn-close btn-close-white" @click="modalDevolucion = false"></button>
                        </div>
                        <div class="modal-body">
                            <div v-if="detalleSeleccionado">
                                <p><strong>Producto:</strong> {{ detalleSeleccionado.producto_nombre }}</p>
                                <p><strong>Cantidad Original:</strong> {{ detalleSeleccionado.cantidad }}</p>
                                
                                <div class="mb-3">
                                    <label class="form-label">Cantidad a Devolver</label>
                                    <input v-model.number="cantidadDevoluciones" type="number" class="form-control"
                                           min="1" :max="cantidadDisponible">
                                    <small class="text-muted">Máximo disponible: {{ cantidadDisponible }}</small>
                                </div>
                                
                                <div class="mb-3">
                                    <label class="form-label">Motivo de la Devolución</label>
                                    <select v-model="motivoDevoluciones" class="form-control">
                                        <option value="">Selecciona un motivo</option>
                                        <option value="Defectuoso">Defectuoso</option>
                                        <option value="Cambio de opinión">Cambio de opinión</option>
                                        <option value="Falta de stock">Falta de stock</option>
                                        <option value="Error de venta">Error de venta</option>
                                        <option value="Dañado en tránsito">Dañado en tránsito</option>
                                        <option value="Otro">Otro</option>
                                    </select>
                                </div>
                                
                                <div class="mb-3">
                                    <label class="form-label">Notas Adicionales (opcional)</label>
                                    <textarea v-model="notasDevoluciones" class="form-control" rows="3"></textarea>
                                </div>
                                
                                <div class="alert alert-info">
                                    <strong>Monto a Revertir:</strong> {{ formatoMoneda(detalleSeleccionado.precio_unitario * cantidadDevoluciones) }}
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" @click="modalDevolucion = false">Cancelar</button>
                            <button type="button" class="btn btn-danger" @click="registrarDevolucion" :disabled="cantidadDevoluciones <= 0">
                                Registrar Devolución
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- HISTORIAL DE DEVOLUCIONES -->
            <div class="card">
                <div class="card-header bg-dark text-white">
                    <h5 class="mb-0">Historial de Devoluciones - {{ devoluciones.length }} registros</h5>
                </div>
                <div class="card-body">
                    <div v-if="devoluciones.length === 0" class="alert alert-info">
                        No hay devoluciones registradas
                    </div>
                    
                    <div v-else class="table-responsive">
                        <table class="table table-sm">
                            <thead class="table-light">
                                <tr>
                                    <th>Venta</th>
                                    <th>Producto</th>
                                    <th>Cantidad</th>
                                    <th>Monto</th>
                                    <th>Motivo</th>
                                    <th>Administrador</th>
                                    <th>Fecha</th>
                                    <th>Acción</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="dev in devoluciones" :key="dev.id">
                                    <td>{{ dev.numero_venta }}</td>
                                    <td>{{ dev.producto_nombre }}</td>
                                    <td>{{ dev.cantidad_devuelta }}</td>
                                    <td>{{ formatoMoneda(dev.monto_devuelto) }}</td>
                                    <td><span class="badge bg-warning text-dark">{{ dev.motivo }}</span></td>
                                    <td>{{ dev.usuario_nombre }}</td>
                                    <td>{{ formatoFecha(dev.created_at) }}</td>
                                    <td>
                                        <button class="btn btn-sm btn-outline-danger" @click="cancelarDevolucion(dev.id)">
                                            Revertir
                                        </button>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            apiUrl: window.location.origin,
            token: localStorage.getItem('token'),
            userRole: localStorage.getItem('userRole'),
            sucursal_id: '',
            sucursales: [],
            ventas: [],
            devoluciones: [],
            ventaSeleccionada: null,
            modalDevolucion: false,
            detalleSeleccionado: null,
            cantidadDevoluciones: 1,
            motivoDevoluciones: '',
            notasDevoluciones: '',
            loading: false,
            error: ''
        };
    },
    computed: {
        cantidadDisponible() {
            if (!this.detalleSeleccionado) return 0;
            const yaDevueltas = this.devoluciones
                .filter(d => d.detalle_venta_id === this.detalleSeleccionado.id)
                .reduce((sum, d) => sum + d.cantidad_devuelta, 0);
            return this.detalleSeleccionado.cantidad - yaDevueltas;
        }
    },
    methods: {
        obtenerSucursales() {
            axios.get(`${this.apiUrl}/api/admin/sucursales`, {
                headers: { 'Authorization': `Bearer ${this.token}` }
            })
            .then(response => {
                this.sucursales = response.data.sucursales || [];
            })
            .catch(err => {
                console.error('Error:', err);
            });
        },
        obtenerVentasDelDia() {
            this.loading = true;
            const params = {};
            if (this.sucursal_id) params.sucursal_id = this.sucursal_id;
            
            axios.get(`${this.apiUrl}/api/devoluciones/ventas-dia`, {
                params,
                headers: { 'Authorization': `Bearer ${this.token}` }
            })
            .then(response => {
                this.ventas = response.data.ventas || [];
                this.ventaSeleccionada = null;
            })
            .catch(err => {
                console.error('Error:', err);
                this.error = err.response?.data?.error || 'Error cargando ventas';
            })
            .finally(() => {
                this.loading = false;
                this.cargarHistorialDevoluciones();
            });
        },
        seleccionarVenta(venta) {
            if (this.ventaSeleccionada && this.ventaSeleccionada.id === venta.id) {
                this.ventaSeleccionada = null;
            } else {
                this.ventaSeleccionada = venta;
            }
        },
        mostrarModalDevolucion(venta, detalle) {
            this.ventaSeleccionada = venta;
            this.detalleSeleccionado = detalle;
            this.cantidadDevoluciones = 1;
            this.motivoDevoluciones = '';
            this.notasDevoluciones = '';
            this.modalDevolucion = true;
        },
        registrarDevolucion() {
            if (!this.detalleSeleccionado || this.cantidadDevoluciones <= 0) {
                this.error = 'Por favor completa todos los campos requeridos';
                return;
            }
            
            this.loading = true;
            axios.post(`${this.apiUrl}/api/devoluciones`, {
                venta_id: this.ventaSeleccionada.id,
                detalle_venta_id: this.detalleSeleccionado.id,
                cantidad_devuelta: this.cantidadDevoluciones,
                motivo: this.motivoDevoluciones || this.notasDevoluciones
            }, {
                headers: { 'Authorization': `Bearer ${this.token}` }
            })
            .then(response => {
                this.error = '';
                alert('Devolución registrada exitosamente');
                this.modalDevolucion = false;
                this.obtenerVentasDelDia();
            })
            .catch(err => {
                this.error = err.response?.data?.error || 'Error registrando devolución';
            })
            .finally(() => {
                this.loading = false;
            });
        },
        cargarHistorialDevoluciones() {
            const params = {};
            if (this.sucursal_id) params.sucursal_id = this.sucursal_id;
            
            axios.get(`${this.apiUrl}/api/devoluciones`, {
                params,
                headers: { 'Authorization': `Bearer ${this.token}` }
            })
            .then(response => {
                this.devoluciones = response.data.devoluciones || [];
            })
            .catch(err => {
                console.error('Error:', err);
            });
        },
        cancelarDevolucion(devolucionId) {
            if (!confirm('¿Estás seguro de que deseas revertir esta devolución?')) return;
            
            this.loading = true;
            axios.delete(`${this.apiUrl}/api/devoluciones/${devolucionId}`, {
                headers: { 'Authorization': `Bearer ${this.token}` }
            })
            .then(response => {
                this.error = '';
                alert('Devolución revertida exitosamente');
                this.obtenerVentasDelDia();
            })
            .catch(err => {
                this.error = err.response?.data?.error || 'Error revirtiendo devolución';
            })
            .finally(() => {
                this.loading = false;
            });
        },
        formatoMoneda(valor) {
            return new Intl.NumberFormat('es-AR', {
                style: 'currency',
                currency: 'ARS'
            }).format(valor || 0);
        },
        formatoFecha(fecha) {
            return new Date(fecha).toLocaleString('es-AR', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    },
    mounted() {
        this.obtenerSucursales();
        this.obtenerVentasDelDia();
    }
};

// ==========================================
// COMPATIBILIDAD - Búsqueda de micas compatibles
// ==========================================
const CompatibilidadView = {
    template: `
        <div class="view-container compatibilidad-view">
            <h2>🔍 Compatibilidad de Micas</h2>
            <p style="color: var(--gray-600); margin-bottom: 2rem;">
                Busca modelos de celular compatibles con micas de cristal templado. 
                Descubre qué otras micas pueden adaptarse a tu dispositivo.
            </p>
            
            <!-- Formulario de búsqueda -->
            <div class="card" style="margin-bottom: 2rem;">
                <h3>Buscar Compatibilidad</h3>
                <div class="form-group">
                    <label for="modelo-celular">Modelo de Celular</label>
                    <input 
                        v-model="modeloCelular" 
                        id="modelo-celular" 
                        type="text" 
                        placeholder="ej: Motorola G9 Play, Samsung Galaxy A12, iPhone 13, etc."
                        @keyup.enter="buscarCompatibilidad"
                    />
                    <small style="color: var(--gray-500);">Ingresa el nombre del modelo exacto o aproximado</small>
                </div>
                
                <div class="btn-group">
                    <button 
                        @click="buscarCompatibilidad" 
                        class="btn btn-primary"
                        :disabled="!modeloCelular || cargando"
                    >
                        {{ cargando ? '🔄 Buscando...' : '🔍 Buscar Compatibilidad' }}
                    </button>
                    <button @click="limpiar" class="btn btn-secondary">Limpiar</button>
                </div>
            </div>
            
            <!-- Mensaje de error -->
            <div v-if="error" class="alert alert-danger" style="margin-bottom: 2rem;">
                <strong>❌ Error:</strong> {{ error }}
            </div>
            
            <!-- Mensaje de alerta -->
            <div v-if="alerta" class="alert alert-warning" style="margin-bottom: 2rem;">
                <strong>ℹ️ Nota:</strong> {{ alerta }}
            </div>
            
            <!-- Resultados -->
            <div v-if="resultados && resultados.modelo_solicitado" class="card">
                <h3>📱 Resultados para: <strong>{{ resultados.modelo_solicitado }}</strong></h3>
                
                <div style="margin-top: 1.5rem;">
                    <h4>Micas Compatibles:</h4>
                    <div v-if="resultados.compatibles && resultados.compatibles.length > 0">
                        <div 
                            v-for="(mica, idx) in resultados.compatibles" 
                            :key="idx"
                            class="compatibility-item"
                            :style="{'border-left': getColorBorde(mica.nivel_compatibilidad)}"
                        >
                            <div style="display: flex; justify-content: space-between; align-items: start;">
                                <div style="flex: 1;">
                                    <h5 style="margin: 0 0 0.5rem 0;">
                                        {{ getNivelIcon(mica.nivel_compatibilidad) }}
                                        {{ mica.modelo }}
                                    </h5>
                                    <p style="margin: 0.3rem 0; color: var(--gray-600);">
                                        <strong>Marca:</strong> {{ mica.marca }}
                                    </p>
                                    <p style="margin: 0.3rem 0; color: var(--gray-700);">
                                        <strong>Razón:</strong> {{ mica.razon }}
                                    </p>
                                </div>
                                <div style="text-align: right;">
                                    <span :class="getNivelClase(mica.nivel_compatibilidad)">
                                        {{ getNivelTexto(mica.nivel_compatibilidad) }}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div v-else style="color: var(--gray-500); padding: 1rem; text-align: center;">
                        No hay opciones de compatibilidad disponibles
                    </div>
                </div>
                
                <div v-if="resultados.notas" style="margin-top: 1.5rem; padding: 1rem; background-color: var(--light-gray); border-radius: 6px; border-left: 4px solid var(--warning);">
                    <p style="margin: 0;">
                        <strong>⚠️ Notas importantes:</strong>
                    </p>
                    <p style="margin: 0.5rem 0 0 0; color: var(--gray-700);">
                        {{ resultados.notas }}
                    </p>
                </div>
            </div>
            
            <!-- Estado vacío -->
            <div v-if="!cargando && !resultados.modelo_solicitado" style="text-align: center; padding: 3rem; color: var(--gray-500);">
                <p style="font-size: 1.2rem;">Ingresa un modelo de celular para buscar compatibilidades</p>
            </div>
        </div>
    `,
    props: ['apiUrl', 'token', 'userRole'],
    data() {
        return {
            modeloCelular: '',
            resultados: {
                modelo_solicitado: '',
                compatibles: [],
                notas: ''
            },
            cargando: false,
            error: '',
            alerta: ''
        };
    },
    methods: {
        async buscarCompatibilidad() {
            this.error = '';
            this.alerta = '';
            
            if (!this.modeloCelular.trim()) {
                this.error = 'Por favor ingresa un modelo de celular';
                return;
            }
            
            this.cargando = true;
            
            try {
                const response = await axios.post(
                    `${window.location.origin}/api/compatibilidad/buscar`,
                    { modelo_celular: this.modeloCelular },
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                
                if (response.data.exito) {
                    this.resultados = response.data.datos;
                    
                    // Mostrar alerta si es fallback local
                    if (this.resultados.notas && this.resultados.notas.includes('Por favor configura')) {
                        this.alerta = 'Usando base de datos local. Configura una API de IA para recomendaciones más precisas.';
                    }
                } else {
                    this.error = response.data.error || 'Error en la búsqueda';
                }
            } catch (err) {
                const errorMsg = err.response?.data?.error || err.message;
                
                if (err.response?.status === 503) {
                    this.error = 'API de IA no configurada. Usa la base de datos local o configura OpenAI/Anthropic.';
                } else {
                    this.error = `Error: ${errorMsg}`;
                }
            } finally {
                this.cargando = false;
            }
        },
        limpiar() {
            this.modeloCelular = '';
            this.resultados = {
                modelo_solicitado: '',
                compatibles: [],
                notas: ''
            };
            this.error = '';
            this.alerta = '';
        },
        getNivelIcon(nivel) {
            const icons = {
                'alta': '✅',
                'media': '⚠️',
                'baja': '❌'
            };
            return icons[nivel] || '❓';
        },
        getNivelTexto(nivel) {
            const textos = {
                'alta': 'ALTA COMPATIBILIDAD',
                'media': 'COMPATIBILIDAD MEDIA',
                'baja': 'BAJA COMPATIBILIDAD'
            };
            return textos[nivel] || 'DESCONOCIDA';
        },
        getNivelClase(nivel) {
            const clases = {
                'alta': 'compatibility-badge compatibility-alta',
                'media': 'compatibility-badge compatibility-media',
                'baja': 'compatibility-badge compatibility-baja'
            };
            return clases[nivel] || 'compatibility-badge';
        },
        getColorBorde(nivel) {
            const colores = {
                'alta': '4px solid var(--success)',
                'media': '4px solid var(--warning)',
                'baja': '4px solid var(--danger)'
            };
            return colores[nivel] || '4px solid var(--gray-400)';
        }
    }
};
