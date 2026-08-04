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
                        <div style="display: flex; gap: 0.5rem; margin-bottom: 0.5rem;">
                            <input 
                                v-model="searchQuery"
                                type="text"
                                placeholder="Escribe nombre, código o barras... (mín. 1 caracter)"
                                @input="buscarProductos"
                                @keyup.enter="buscarProductos"
                                style="flex: 1; padding: 0.75rem; border: 1px solid var(--gray-300); border-radius: 0.375rem;"
                            >
                            <button 
                                @click="buscarProductos" 
                                class="btn btn-primary" 
                                style="padding: 0.75rem 1rem; white-space: nowrap;"
                            >
                                🔍
                            </button>
                        </div>
                        
                        <div v-if="searchResults.length > 0" class="search-results">
                            <div 
                                v-for="producto in searchResults" 
                                :key="producto.id"
                                class="search-result-item"
                                @click="agregarAlCarrito(producto)"
                                style="cursor: pointer;"
                            >
                                <div class="search-result-name">{{ producto.nombre }}</div>
                                <div class="search-result-code">Código: {{ producto.codigo }}</div>
                                <div class="search-result-price">
                                    <span v-if="producto.precio && producto.precio > 0">💵 \${{ producto.precio }}</span>
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
                    
                    <div v-else style="max-height: auto; overflow-y: auto;">
                        <div 
                            v-for="producto in productos.slice(0, 2)" 
                            :key="producto.id"
                            style="padding: 0.75rem; border-bottom: 1px solid var(--gray-200); cursor: pointer; transition: background-color 0.2s;"
                            @click="agregarAlCarrito(producto)"
                            @mouseover="$event.target.style.backgroundColor = 'var(--gray-100)'"
                            @mouseout="$event.target.style.backgroundColor = 'transparent'"
                        >
                            <div style="font-weight: 600; margin-bottom: 0.25rem;">{{ producto.nombre }}</div>
                            <div style="font-size: 0.875rem; color: var(--gray-600);">{{ producto.codigo }}</div>
                            <div style="font-weight: 500; color: var(--primary);">
                                <span v-if="producto.precio && producto.precio > 0">💵 \${{ producto.precio }}</span>
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
                            <select v-model="formaPago" @change="manejarCambioFormaPago" id="forma-pago" name="forma_pago" style="width: 100%; padding: 0.5rem;">
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

            <!-- Modal de pago mixto -->
            <div v-if="mostrarModalPagoMixto" class="modal-overlay" style="z-index: 1001;">
                <div class="modal" style="max-width: 500px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                        <h3 style="margin: 0;">💰 Pago Mixto</h3>
                        <button @click="cerrarModalPagoMixto" class="modal-close">✕</button>
                    </div>

                    <div style="background-color: var(--gray-100); padding: 1rem; border-radius: 0.375rem; margin-bottom: 1.5rem;">
                        <div style="font-size: 0.875rem; color: var(--gray-600); margin-bottom: 0.5rem;">Total a cobrar:</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary);">\${{ total.toFixed(2) }}</div>
                    </div>

                    <div style="margin-bottom: 1.5rem;">
                        <div style="margin-bottom: 1rem;">
                            <label style="display: block; font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;">💵 Efectivo</label>
                            <input v-model.number="pagosMixtos.efectivo" type="number" step="0.01" min="0" style="width: 100%; padding: 0.5rem; border: 1px solid var(--gray-300); border-radius: 0.375rem;">
                        </div>
                        <div style="margin-bottom: 1rem;">
                            <label style="display: block; font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;">💳 Tarjeta</label>
                            <input v-model.number="pagosMixtos.tarjeta" type="number" step="0.01" min="0" style="width: 100%; padding: 0.5rem; border: 1px solid var(--gray-300); border-radius: 0.375rem;">
                        </div>
                        <div style="margin-bottom: 1rem;">
                            <label style="display: block; font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;">🏦 Transferencia</label>
                            <input v-model.number="pagosMixtos.transferencia" type="number" step="0.01" min="0" style="width: 100%; padding: 0.5rem; border: 1px solid var(--gray-300); border-radius: 0.375rem;">
                        </div>
                    </div>

                    <div style="background-color: var(--gray-100); padding: 1rem; border-radius: 0.375rem; margin-bottom: 1.5rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                            <span>Total ingresado:</span>
                            <span style="font-weight: 700;">\${{ totalPagosMixtos.toFixed(2) }}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>Diferencia:</span>
                            <span :style="{fontWeight: '700', color: Math.abs(diferenciaPagosMixtos) < 0.01 ? 'var(--success)' : 'var(--warning)'}">
                                \${{ diferenciaPagosMixtos.toFixed(2) }}
                            </span>
                        </div>
                    </div>

                    <div style="display: flex; gap: 0.5rem;">
                        <button @click="cerrarModalPagoMixto" class="btn btn-secondary" style="flex: 1;">Cancelar</button>
                        <button @click="guardarPagoMixto" class="btn btn-success" style="flex: 1;" :disabled="Math.abs(diferenciaPagosMixtos) >= 0.01">
                            ✓ Confirmar
                        </button>
                    </div>
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
            productosConStockInsuficiente: {}, // Rastrear avisos de stock por ID de producto
            mostrarModalPagoMixto: false,
            pagosMixtos: {
                efectivo: 0,
                tarjeta: 0,
                transferencia: 0
            }
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
        },
        totalPagosMixtos() {
            const efe = Number(this.pagosMixtos.efectivo) || 0;
            const tarj = Number(this.pagosMixtos.tarjeta) || 0;
            const trans = Number(this.pagosMixtos.transferencia) || 0;
            return efe + tarj + trans;
        },
        diferenciaPagosMixtos() {
            return this.totalPagosMixtos - this.total;
        }
    },
    methods: {
        async cargarProductos() {
            try {
                const response = await axios.get(
                    `${window.location.origin}/api/productos?per_page=9999`,
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
            if (producto.precio == null || producto.precio === 0) {
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
            if (this.precioFlexible < 0) {
                this.error = 'Ingresa un precio válido (mayor o igual a 0)';
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
        manejarCambioFormaPago() {
            if (this.formaPago === 'mixto') {
                // Reiniciar los pagos
                this.pagosMixtos = {
                    efectivo: 0,
                    tarjeta: 0,
                    transferencia: 0
                };
                this.mostrarModalPagoMixto = true;
            }
        },
        guardarPagoMixto() {
            if (Math.abs(this.diferenciaPagosMixtos) < 0.01) {
                this.mostrarModalPagoMixto = false;
                this.error = '';
            } else {
                this.error = `El total de pagos ($${this.totalPagosMixtos.toFixed(2)}) no coincide con el total de la venta ($${this.total.toFixed(2)})`;
            }
        },
        cerrarModalPagoMixto() {
            this.mostrarModalPagoMixto = false;
            this.formaPago = 'efectivo';
            this.pagosMixtos = { efectivo: 0, tarjeta: 0, transferencia: 0 };
        },
        async registrarVenta() {
            if (this.carrito.length === 0) return;
            
            // Validar pago mixto si es aplicable
            if (this.formaPago === 'mixto') {
                if (Math.abs(this.diferenciaPagosMixtos) >= 0.01) {
                    this.error = `El total de pagos ($${this.totalPagosMixtos.toFixed(2)}) no coincide con el total de la venta ($${this.total.toFixed(2)})`;
                    return;
                }
            }
            
            this.procesandoVenta = true;
            this.error = '';
            
            try {
                const detalles = this.carrito.map(item => ({
                    producto_id: item.id,
                    cantidad: item.cantidad,
                    precio: item.precio  // Enviar precio (puede ser personalizado)
                }));

                const ventaData = {
                    detalles,
                    forma_pago: this.formaPago
                };

                // Si es pago mixto, agregar los detalles de los pagos
                if (this.formaPago === 'mixto') {
                    ventaData.pagos_mixtos = this.pagosMixtos;
                }

                const response = await axios.post(
                    `${window.location.origin}/api/ventas`,
                    ventaData,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );

                this.ultimaVentaId = response.data.venta.id;
                this.ventaExitosa = response.data.venta.numero_venta;
                this.carrito = [];
                this.formaPago = 'efectivo';
                this.pagosMixtos = { efectivo: 0, tarjeta: 0, transferencia: 0 };
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
                    <h4 style="margin-bottom: 1rem;">Importar Productos desde CSV</h4>
                    <p style="margin-bottom: 1rem; color: var(--gray-600);">
                        📋 Carga un archivo CSV (.csv) con las siguientes columnas: 
                        <code style="background: var(--gray-100); padding: 0.25rem 0.5rem; border-radius: 0.25rem;">REF, Nombre, Categoria, Precio, En inventario</code>
                    </p>
                    <div class="form-group">
                        <label for="archivo-importacion">Archivo CSV</label>
                        <input 
                            id="archivo-importacion"
                            name="archivo_importacion"
                            type="file" 
                            accept=".csv"
                            @change="manejarCargaArchivo"
                            style="width: 100%; padding: 0.5rem; border: 2px dashed var(--primary); border-radius: 0.375rem;"
                        >
                        <small style="display: block; margin-top: 0.5rem; color: var(--gray-600);">
                            💡 Solo archivos CSV. Si tienes Excel, conviértelo así: Archivo → Exportar → CSV
                        </small>
                    </div>
                    </div>
                    <div v-if="archivoSeleccionado" style="margin-bottom: 1rem;">
                        <p>📄 {{ archivoSeleccionado.name }}</p>
                        <div class="form-group">
                            <label for="sucursal-importacion">
                                Sucursal para el stock
                                <span v-if="sucursalImportacion" style="color: green; font-weight: bold;">
                                    ✓ (Detectada automáticamente)
                                </span>
                            </label>
                            <select v-model="sucursalImportacion" id="sucursal-importacion" name="sucursal_importacion" required>
                                <option value="">Selecciona sucursal</option>
                                <option v-for="suc in sucursales" :key="suc.id" :value="suc.id">
                                    {{ suc.nombre }}
                                </option>
                            </select>
                            <small style="display: block; margin-top: 0.5rem; color: var(--gray-600);">
                                💡 Formato sugerido de archivo: <code style="background: var(--gray-100); padding: 0.25rem 0.5rem; border-radius: 0.25rem;">productos_Sucursal_Centro.csv</code>
                            </small>
                        </div>
                        <button @click="procesarImportacion" class="btn btn-success" :disabled="importandoProductos || !sucursalImportacion">
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
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
                        <div class="form-group">
                            <label for="buscar-productos-productos">Buscar Producto</label>
                            <input 
                                v-model="busquedaProducto"
                                id="buscar-productos-productos"
                                name="buscar_productos_productos"
                                type="text"
                                placeholder="Nombre o código..."
                            >
                        </div>
                        <div class="form-group">
                            <label for="categoria-selector-productos">Categoría</label>
                            <select v-model="categoriaSeleccionada" id="categoria-selector-productos" name="categoria_selector_productos">
                                <option value="">Todas</option>
                                <option v-for="cat in categorias" :key="cat.id" :value="cat.id">
                                    {{ cat.nombre }}
                                </option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="subcategoria-selector-productos">Subcategoría</label>
                            <select v-model="subcategoriaSeleccionada" id="subcategoria-selector-productos" name="subcategoria_selector_productos">
                                <option value="">Todas</option>
                                <option v-for="subcat in subcategoriasFiltradasPorCategoria" :key="subcat.id" :value="subcat.id">
                                    {{ subcat.nombre }}
                                </option>
                            </select>
                        </div>
                    </div>
                    <div style="display: flex; gap: 0.5rem;">
                        <button @click="aplicarFiltros" class="btn btn-primary" style="padding: 0.625rem 1.25rem;">
                            🔍 Buscar/Filtrar
                        </button>
                        <button @click="limpiarFiltros" class="btn" style="padding: 0.625rem 1.25rem;">
                            ✕ Limpiar Filtros
                        </button>
                    </div>
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
                                <th>Categoría</th>
                                <th>Subcategoría</th>
                                <th>Precio</th>
                                <th>Impuesto</th>
                                <th>Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="producto in productosFiltrados" :key="producto.id">
                                <td>{{ producto.codigo }}</td>
                                <td>{{ producto.nombre }}</td>
                                <td>{{ obtenerCategoria(producto) }}</td>
                                <td>{{ obtenerSubcategoria(producto) }}</td>
                                <td>
                                    <span v-if="producto.precio && producto.precio > 0">\${{ producto.precio }}</span>
                                    <button v-else @click="abrirModalPrecio(producto)" class="btn btn-warning btn-sm" style="background-color: #ffc107; color: #000;">
                                        ⚠ Sin precio
                                    </button>
                                </td>
                                <td>{{ producto.impuesto }}%</td>
                                <td>
                                    <button class="btn btn-primary btn-sm" @click="editarProducto(producto)">Editar</button>
                                    <button class="btn btn-danger btn-sm" @click="eliminarProducto(producto.id)">Eliminar</button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                
                <!-- Modal para agregar precio -->
                <div v-if="mostrarModalPrecio" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000;">
                    <div style="background-color: white; padding: 2rem; border-radius: 0.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 500px; width: 90%;">
                        <h3 style="margin-top: 0; margin-bottom: 1rem;">Agregar Precio</h3>
                        <div style="margin-bottom: 1rem;">
                            <p style="margin: 0 0 0.5rem 0; font-weight: 600;">Producto: {{ productoParaPrecio?.nombre }}</p>
                            <p style="margin: 0 0 1rem 0; color: var(--gray-600); font-size: 0.875rem;">Código: {{ productoParaPrecio?.codigo }}</p>
                        </div>
                        <div class="form-group" style="margin-bottom: 1.5rem;">
                            <label for="modal-precio-input">Precio</label>
                            <input 
                                v-model.number="precioIngresado"
                                id="modal-precio-input"
                                name="modal_precio_input"
                                type="number" 
                                step="0.01"
                                min="0"
                                placeholder="Ej: 100, 50.50, 0"
                            >
                        </div>
                        <div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
                            <button @click="cerrarModalPrecio" class="btn" style="padding: 0.625rem 1.25rem;">
                                Cancelar
                            </button>
                            <button @click="guardarPrecio" class="btn btn-primary" style="padding: 0.625rem 1.25rem;">
                                Guardar Precio
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            productos: [],
            subcategorias: [],
            categorias: [],
            sucursales: [],
            mostrarFormulario: false,
            mostrarImportacion: false,
            loading: true,
            busquedaProducto: '',
            categoriaSeleccionada: '',
            subcategoriaSeleccionada: '',
            filtrosAplicados: {
                busqueda: '',
                categoria: '',
                subcategoria: ''
            },
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
            tipoMensajeImportacion: 'success',
            mostrarModalPrecio: false,
            productoParaPrecio: null,
            precioIngresado: 0
        };
    },
    computed: {
        subcategoriasFiltradasPorCategoria() {
            if (!this.categoriaSeleccionada) return this.subcategorias;
            return this.subcategorias.filter(sub => sub.categoria_id === this.categoriaSeleccionada);
        },
        productosFiltrados() {
            return this.productos.filter(p => {
                // Filtrar por búsqueda
                const coincideBusqueda = !this.filtrosAplicados.busqueda || 
                    p.nombre.toLowerCase().includes(this.filtrosAplicados.busqueda.toLowerCase()) ||
                    p.codigo.toLowerCase().includes(this.filtrosAplicados.busqueda.toLowerCase());
                
                // Filtrar por categoría
                const coincideCategoria = !this.filtrosAplicados.categoria || 
                    p.categoria_id === this.filtrosAplicados.categoria;
                
                // Filtrar por subcategoría
                const coincideSubcategoria = !this.filtrosAplicados.subcategoria || 
                    p.subcategoria_id === this.filtrosAplicados.subcategoria;
                
                return coincideBusqueda && coincideCategoria && coincideSubcategoria;
            });
        }
    },
    methods: {
        async cargarProductos() {
            try {
                const res = await axios.get(
                    `${window.location.origin}/api/productos?per_page=9999`,
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
            
            if (this.archivoSeleccionado) {
                const nombreArchivo = this.archivoSeleccionado.name.toLowerCase();
                const esCSV = nombreArchivo.endsWith('.csv');
                
                if (!esCSV) {
                    this.mensajeImportacion = `❌ Error: El archivo debe ser CSV (.csv). Recibido: ${this.archivoSeleccionado.name}`;
                    this.tipoMensajeImportacion = 'danger';
                    this.archivoSeleccionado = null;
                    return;
                }
                // Sucursal se detecta automáticamente del CSV (nombres de columnas)
                this.mensajeImportacion = 'ℹ️ Las sucursales se detectarán del archivo CSV';
                this.tipoMensajeImportacion = 'info';
            }
        },
        extraerSucursalDelArchivo(nombreArchivo) {
            /**
             * Extrae el nombre de la sucursal del nombre del archivo
             * Formatos soportados:
             * - productos_Sucursal_Centro.csv → Sucursal Centro
             * - productos_Sucursal Centro.csv → Sucursal Centro
             * - Sucursal_Centro_productos.csv → Sucursal Centro
             * - Centro_productos.csv → Centro
             */
            
            // Remover extensión
            let nombre = nombreArchivo.replace(/\.(csv|xlsx)$/i, '');
            
            // Intentar extraer la sucursal
            let sucursalNombre = null;
            
            // Patrón 1: "productos_XXX" o "productos-XXX"
            let match = nombre.match(/(?:productos|importar)[_\-](.+)/i);
            if (match) {
                sucursalNombre = match[1];
            }
            // Patrón 2: "XXX_productos" o "XXX-productos"
            if (!sucursalNombre) {
                match = nombre.match(/(.+?)[_\-](?:productos|importar)/i);
                if (match) {
                    sucursalNombre = match[1];
                }
            }
            // Patrón 3: Si no hay patrón, usar todo el nombre
            if (!sucursalNombre) {
                sucursalNombre = nombre;
            }
            
            // Normalizar: reemplazar guiones y guiones bajos por espacios
            sucursalNombre = sucursalNombre.replace(/[_\-]+/g, ' ').trim();
            
            // Capitalizar cada palabra
            sucursalNombre = sucursalNombre
                .split(' ')
                .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
                .join(' ');
            
            console.log('Nombre extraído del archivo:', sucursalNombre);
            
            // Buscar la sucursal por nombre
            const sucursal = this.sucursales.find(s => 
                s.nombre.toLowerCase() === sucursalNombre.toLowerCase()
            );
            
            if (sucursal) {
                this.sucursalImportacion = sucursal.id;
                console.log('Sucursal encontrada:', sucursal.nombre, 'ID:', sucursal.id);
            } else {
                console.warn('Sucursal no encontrada para:', sucursalNombre);
                this.mensajeImportacion = `⚠️ No se encontró sucursal "${sucursalNombre}". Por favor, selecciona una manualmente.`;
                this.tipoMensajeImportacion = 'warning';
                this.sucursalImportacion = '';
            }
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
                        
                        // Encontrar índices de columnas - Soportar múltiples nombres
                        const idxCodigo = encabezados.findIndex(h => 
                            h.toLowerCase() === 'codigo' || 
                            h.toLowerCase() === 'ref' || 
                            h.toLowerCase() === 'sku'
                        );
                        const idxNombre = encabezados.findIndex(h => 
                            h.toLowerCase() === 'nombre' || 
                            h.toLowerCase() === 'producto'
                        );
                        const idxCategoria = encabezados.findIndex(h => 
                            h.toLowerCase() === 'categoria' || 
                            h.toLowerCase() === 'categoría'
                        );
                        const idxSubcategoria = encabezados.findIndex(h => 
                            h.toLowerCase() === 'subcategoria' || 
                            h.toLowerCase() === 'subcategoría'
                        );
                        
                        // Buscar columna de precio
                        const idxPrecio = encabezados.findIndex(h => 
                            h.toLowerCase() === 'precio' || 
                            h.toLowerCase().includes('precio')
                        );
                        
                        // Buscar columna de stock estándar
                        const idxStock = encabezados.findIndex(h => 
                            h.toLowerCase() === 'stock' || 
                            h.toLowerCase() === 'cantidad' || 
                            h.toLowerCase().includes('inventario')
                        );
                        
                        // DETECTAR DINÁMICAMENTE columnas de sucursales
                        const sucursalesMap = {}; // {nombreSucursal: id}
                        this.sucursales.forEach(s => {
                            sucursalesMap[s.nombre.toLowerCase().trim()] = s.id;
                        });
                        
                        // Encontrar columnas que coincidan con sucursales
                        const columnsSucursales = [];
                        encabezados.forEach((header, idx) => {
                            const headerLower = header.toLowerCase().trim();
                            // Búsqueda exacta y parcial
                            for (const [nombreSuc, idSuc] of Object.entries(sucursalesMap)) {
                                if (headerLower === nombreSuc || headerLower.includes(nombreSuc)) {
                                    console.log(`[DEBUG] Detectada sucursal: "${header}" (idx=${idx}) → ID=${idSuc}`);
                                    columnsSucursales.push({
                                        index: idx,
                                        nombre: header,
                                        sucursal_id: idSuc
                                    });
                                    break;
                                }
                            }
                        });
                        
                        console.log(`[DEBUG] Columnas de sucursales detectadas: ${columnsSucursales.length}`, columnsSucursales);
                        
                        const productosProcesados = [];
                        const errores = [];
                        
                        // Validar que encontró las columnas mínimas
                        if (idxCodigo === -1 || idxNombre === -1) {
                            this.mensajeImportacion = `❌ Error: No se encontraron las columnas necesarias. Se requiere al menos "Codigo" y "Nombre"`;
                            this.tipoMensajeImportacion = 'danger';
                            this.importandoProductos = false;
                            return;
                        }
                        
                        for (let i = 1; i < lineas.length; i++) {
                            const linea = lineas[i].trim();
                            if (!linea) continue;
                            
                            const valores = linea.split(',').map(v => v.trim().replace(/"/g, ''));
                            
                            const codigo = valores[idxCodigo]?.trim();
                            const nombre = valores[idxNombre]?.trim();
                            const categoria = idxCategoria !== -1 ? (valores[idxCategoria]?.trim() || '') : '';
                            const subcategoria = idxSubcategoria !== -1 ? (valores[idxSubcategoria]?.trim() || '') : '';
                            const precio = idxPrecio !== -1 ? (parseFloat(valores[idxPrecio]) || 0) : 0;
                            
                            if (codigo && nombre) {
                                // SI hay columnas de sucursales dinámicas, usarlas
                                if (columnsSucursales.length > 0) {
                                    for (const sucCol of columnsSucursales) {
                                        const stock = parseInt(valores[sucCol.index]) || 0;
                                        if (stock > 0 || stock === 0) { // Incluir aunque sea 0
                                            productosProcesados.push({
                                                codigo,
                                                nombre,
                                                categoria: categoria || 'General',
                                                subcategoria: subcategoria || categoria || '',
                                                precio,
                                                stock,
                                                sucursal_id: sucCol.sucursal_id
                                            });
                                        }
                                    }
                                } else {
                                    // Si NO hay columnas de sucursales, usar sucursal seleccionada + columna stock
                                    const stock = idxStock !== -1 ? (parseInt(valores[idxStock]) || 0) : 0;
                                    productosProcesados.push({
                                        codigo,
                                        nombre,
                                        categoria: categoria || 'General',
                                        subcategoria: subcategoria || categoria || '',
                                        precio,
                                        stock,
                                        sucursal_id: this.sucursalImportacion
                                    });
                                }
                            }
                        }
                        
                        if (productosProcesados.length === 0) {
                            this.mensajeImportacion = `❌ Error: No se encontraron productos en el archivo. Verifica que tenga datos después del encabezado.`;
                            this.tipoMensajeImportacion = 'danger';
                            this.importandoProductos = false;
                            return;
                        }
                        
                        // Enviar productos procesados al servidor
                        const response = await axios.post(
                            `${window.location.origin}/api/productos/importar`,
                            { productos: productosProcesados },
                            { headers: { Authorization: `Bearer ${this.token}` } }
                        );
                        
                        if (response.data.errores && response.data.errores.length > 0) {
                            const detalles = response.data.errores.slice(0, 3).join('\n');
                            this.mensajeImportacion = `⚠️ ${response.data.importados} de ${response.data.total} importados.\n\nErrores:\n${detalles}`;
                            this.tipoMensajeImportacion = 'warning';
                        } else {
                            this.mensajeImportacion = `✓ ${response.data.importados} productos importados exitosamente`;
                            this.tipoMensajeImportacion = 'success';
                        }
                        this.archivoSeleccionado = null;
                        await this.cargarProductos();
                    } catch (err) {
                        console.error('Error en importación:', err);
                        const errorMsg = err.response?.data?.error || err.message || 'Error desconocido';
                        this.mensajeImportacion = `❌ Error: ${errorMsg}\n\nDetalles: ${JSON.stringify(err.response?.data || {})}`;
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
        },
        async cargarCategorias() {
            try {
                const res = await axios.get(
                    `${window.location.origin}/api/productos/categorias`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.categorias = res.data || [];
            } catch (err) {
                console.error('Error cargando categorías:', err);
            }
        },
        aplicarFiltros() {
            this.filtrosAplicados.busqueda = this.busquedaProducto;
            this.filtrosAplicados.categoria = this.categoriaSeleccionada;
            this.filtrosAplicados.subcategoria = this.subcategoriaSeleccionada;
        },
        limpiarFiltros() {
            this.busquedaProducto = '';
            this.categoriaSeleccionada = '';
            this.subcategoriaSeleccionada = '';
            this.filtrosAplicados = { busqueda: '', categoria: '', subcategoria: '' };
        },
        obtenerCategoria(producto) {
            if (!producto.categoria_id) return '-';
            const categoria = this.categorias.find(c => c.id === producto.categoria_id);
            return categoria ? categoria.nombre : '-';
        },
        obtenerSubcategoria(producto) {
            if (!producto.subcategoria_id) return '-';
            const subcategoria = this.subcategorias.find(s => s.id === producto.subcategoria_id);
            return subcategoria ? subcategoria.nombre : '-';
        },
        abrirModalPrecio(producto) {
            this.productoParaPrecio = producto;
            this.precioIngresado = producto.precio || 0;
            this.mostrarModalPrecio = true;
        },
        async guardarPrecio() {
            if (!this.productoParaPrecio) return;
            
            try {
                await axios.put(
                    `${window.location.origin}/api/productos/${this.productoParaPrecio.id}`,
                    { precio: this.precioIngresado },
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.mostrarModalPrecio = false;
                await this.cargarProductos();
            } catch (err) {
                alert('Error al guardar precio: ' + (err.response?.data?.error || err.message));
            }
        },
        cerrarModalPrecio() {
            this.mostrarModalPrecio = false;
            this.productoParaPrecio = null;
            this.precioIngresado = 0;
        }
    },
    mounted() {
        if (this.token) {
            this.cargarProductos();
            this.cargarSubcategorias();
            this.cargarCategorias();
            this.cargarSucursales();
        }
    },
    watch: {
        token(newToken) {
            if (newToken) {
                this.cargarProductos();
                this.cargarSubcategorias();
                this.cargarCategorias();
                this.cargarSucursales();
            }
        },
        categoriaSeleccionada() {
            // Cuando cambia la categoría, resetear subcategoría pero no filtrar automáticamente
            this.subcategoriaSeleccionada = '';
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
                    <div style="display: flex; gap: 0.5rem;">
                        <button @click="mostrarEntrada = !mostrarEntrada" class="btn btn-primary">
                            {{ mostrarEntrada ? '← Ocultar' : '+ Registrar Entrada' }}
                        </button>
                        <button @click="exportarInventario" class="btn btn-success">
                            📥 Exportar Inventario
                        </button>
                    </div>
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
                            <div style="position: relative;">
                                <input 
                                    :value="entrada.producto_id ? '✓ ' + obtenerNombreProducto(entrada.producto_id) : busquedaProductoEntrada"
                                    @input="manejarBusquedaProducto"
                                    @focus="entrada.producto_id = ''"
                                    id="buscar-producto"
                                    name="buscar_producto"
                                    type="text"
                                    placeholder="Busca producto..."
                                    style="width: 100%; padding: 0.5rem;"
                                >
                                <!-- Dropdown de búsqueda -->
                                <div v-if="productosEncontrados.length > 0 && busquedaProductoEntrada" style="position: absolute; background: white; border: 1px solid var(--gray-300); border-radius: 0.375rem; width: 100%; max-height: 200px; overflow-y: auto; z-index: 10; top: 100%;">
                                    <div 
                                        v-for="prod in productosEncontrados" 
                                        :key="prod.id"
                                        @click="seleccionarProducto(prod)"
                                        style="padding: 0.5rem; cursor: pointer; border-bottom: 1px solid var(--gray-200);"
                                    >
                                        {{ prod.nombre }} ({{ prod.codigo }})
                                    </div>
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
                
                <!-- Sucursal (primera) -->
                <div style="margin-bottom: 1.5rem;">
                    <div class="form-group" style="max-width: 400px;">
                        <label for="sucursal-selector">Selecciona Sucursal</label>
                        <select v-model="sucursalSeleccionada" id="sucursal-selector" name="sucursal_selector">
                            <option value="">Todas</option>
                            <option v-for="suc in sucursales" :key="suc.id" :value="suc.id">
                                {{ suc.nombre }}
                            </option>
                        </select>
                    </div>
                </div>
                
                <!-- Filtros de búsqueda y categorías -->
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
                    <div class="form-group">
                        <label for="busqueda-productos">Buscar Producto</label>
                        <input 
                            v-model="busquedaProductos" 
                            id="busqueda-productos"
                            name="busqueda_productos"
                            type="text" 
                            placeholder="Nombre o código..."
                        >
                    </div>
                    <div class="form-group">
                        <label for="categoria-selector">Categoría</label>
                        <select v-model="categoriaSeleccionada" id="categoria-selector" name="categoria_selector">
                            <option value="">Todas</option>
                            <option v-for="cat in categorias" :key="cat.id" :value="cat.id">
                                {{ cat.nombre }}
                            </option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="subcategoria-selector">Subcategoría</label>
                        <select v-model="subcategoriaSeleccionada" id="subcategoria-selector" name="subcategoria_selector">
                            <option value="">Todas</option>
                            <option v-for="subcat in subcategoriasFiltradasPorCategoria" :key="subcat.id" :value="subcat.id">
                                {{ subcat.nombre }}
                            </option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="estado-selector">Estado de Stock</label>
                        <select v-model="estadoSeleccionado" id="estado-selector" name="estado_selector">
                            <option value="">Todos</option>
                            <option value="ok">✓ OK</option>
                            <option value="bajo">⚠ Bajo Stock</option>
                            <option value="sin">❌ Sin Stock</option>
                        </select>
                    </div>
                </div>
                
                <!-- Botones de filtrar y limpiar -->
                <div style="display: flex; gap: 0.5rem; margin-bottom: 1.5rem;">
                    <button @click="aplicarFiltros" class="btn btn-primary" style="padding: 0.625rem 1.25rem;">
                        🔍 Buscar/Filtrar
                    </button>
                    <button @click="limpiarFiltros" class="btn" style="padding: 0.625rem 1.25rem;">
                        ✕ Limpiar Filtros
                    </button>
                </div>
                
                <!-- Items por página -->
                <div style="margin-bottom: 1.5rem;">
                    <div class="form-group" style="max-width: 200px;">
                        <label for="items-por-pagina">Items por página</label>
                        <select v-model.number="itemsPorPagina" id="items-por-pagina" name="items_por_pagina" @change="paginaActual = 1">
                            <option :value="10">10</option>
                            <option :value="20">20</option>
                            <option :value="30">30</option>
                            <option :value="50">50</option>
                            <option :value="100">100</option>
                        </select>
                    </div>
                </div>

                <div v-if="cargandoStock" style="text-align: center; padding: 2rem;">
                    <span class="spinner"></span>
                </div>
                <div v-else-if="stocks.length === 0" style="padding: 2rem; text-align: center; color: var(--gray-600);">
                    No hay productos en stock
                </div>
                <div v-else-if="stocksFiltrados.length === 0" style="padding: 2rem; text-align: center; color: var(--gray-600);">
                    No se encontraron productos con los filtros seleccionados
                </div>
                <div v-else>
                    <div style="overflow-x: auto; margin-bottom: 1rem;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Código</th>
                                    <th>Producto</th>
                                    <th>Categoría</th>
                                    <th>Subcategoría</th>
                                    <th>Cantidad</th>
                                    <th>Mínimo</th>
                                    <th>Estado</th>
                                    <th>Precio</th>
                                    <th>Acciones</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="stock in stocksPaginadosFiltrados" :key="stock.id">
                                <td>{{ stock.producto_codigo }}</td>
                                <td>{{ stock.producto_nombre }}</td>
                                <td>{{ obtenerCategoria(stock.producto_id) }}</td>
                                <td>{{ obtenerSubcategoria(stock.producto_id) }}</td>
                                <td style="font-weight: 600;">{{ stock.cantidad }}</td>
                                <td>{{ stock.cantidad_minima }}</td>
                                <td>
                                    <span v-if="obtenerEstadoStock(stock) === 'sin'" style="color: var(--danger); font-weight: 600;">
                                        ❌ Sin Stock
                                    </span>
                                    <span v-else-if="obtenerEstadoStock(stock) === 'bajo'" style="color: var(--danger); font-weight: 600;">
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
                    
                    <!-- Información de paginación y controles -->
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; padding: 1rem; background-color: var(--gray-50); border-radius: 0.375rem;">
                        <div style="color: var(--gray-600); font-size: 0.875rem;">
                            Mostrando {{ rangoMostradoFiltrado.inicio }}-{{ rangoMostradoFiltrado.fin }} de {{ rangoMostradoFiltrado.total }} resultados
                        </div>
                        <div style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;">
                            <button @click="paginaActual = 1" :disabled="paginaActual === 1" class="btn btn-sm" style="padding: 0.5rem 0.75rem;" title="Primera página">
                                «
                            </button>
                            <button @click="paginaActual--" :disabled="paginaActual === 1" class="btn btn-sm" style="padding: 0.5rem 0.75rem;">
                                ‹ Anterior
                            </button>
                            <div style="display: flex; gap: 0.25rem;">
                                <button 
                                    v-for="n in paginasAMostrar" 
                                    :key="n"
                                    @click="paginaActual = n"
                                    :class="['btn', 'btn-sm', paginaActual === n ? 'btn-primary' : '']"
                                    style="padding: 0.5rem 0.75rem; min-width: 35px;"
                                >
                                    {{ n }}
                                </button>
                            </div>
                            <button @click="paginaActual++" :disabled="paginaActual === totalPaginasFiltradas" class="btn btn-sm" style="padding: 0.5rem 0.75rem;">
                                Siguiente ›
                            </button>
                            <button @click="paginaActual = totalPaginasFiltradas" :disabled="paginaActual === totalPaginasFiltradas" class="btn btn-sm" style="padding: 0.5rem 0.75rem;" title="Última página">
                                »
                            </button>
                        </div>
                        <div style="color: var(--gray-600); font-size: 0.875rem;">
                            Página {{ paginaActual }} de {{ totalPaginasFiltradas }}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            sucursales: [],
            stocks: [],
            productos: [],
            categorias: [],
            subcategorias: [],
            filtrosAplicados: {
                busqueda: '',
                categoria: '',
                subcategoria: '',
                estado: ''
            },
            mostrarEntrada: false,
            sucursalSeleccionada: '',
            cargandoStock: false,
            busquedaProductos: '',
            categoriaSeleccionada: '',
            subcategoriaSeleccionada: '',
            estadoSeleccionado: '',
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
            tipoMensajeEntrada: 'success',
            itemsPorPagina: 10,
            paginaActual: 1
        };
    },
    computed: {
        productosEncontrados() {
            if (!this.busquedaProductoEntrada) return [];
            return this.productos.filter(p => 
                p.nombre.toLowerCase().includes(this.busquedaProductoEntrada.toLowerCase()) ||
                p.codigo.toLowerCase().includes(this.busquedaProductoEntrada.toLowerCase())
            ).slice(0, 5);
        },
        totalPaginas() {
            return Math.ceil(this.stocks.length / this.itemsPorPagina);
        },
        stocksPaginados() {
            const inicio = (this.paginaActual - 1) * this.itemsPorPagina;
            const fin = inicio + this.itemsPorPagina;
            return this.stocks.slice(inicio, fin);
        },
        rangoMostrado() {
            const inicio = (this.paginaActual - 1) * this.itemsPorPagina + 1;
            const fin = Math.min(this.paginaActual * this.itemsPorPagina, this.stocks.length);
            return { inicio, fin, total: this.stocks.length };
        },
        paginasAMostrar() {
            const total = this.totalPaginas;
            const actual = this.paginaActual;
            const rango = 5;
            
            let inicio, fin;
            
            // Si hay 5 o menos páginas, mostrar todas
            if (total <= rango) {
                inicio = 1;
                fin = total;
            }
            // Si estamos en las primeras 3 páginas
            else if (actual <= 3) {
                inicio = 1;
                fin = rango;
            }
            // Si estamos en las últimas 3 páginas
            else if (actual > total - 3) {
                inicio = total - rango + 1;
                fin = total;
            }
            // En el medio: mostrar 2 antes y 2 después de la actual
            else {
                inicio = actual - 2;
                fin = actual + 2;
            }
            
            const paginas = [];
            for (let i = inicio; i <= fin; i++) {
                paginas.push(i);
            }
            return paginas;
        },
        subcategoriasFiltradasPorCategoria() {
            if (!this.categoriaSeleccionada) return this.subcategorias;
            return this.subcategorias.filter(sub => sub.categoria_id === this.categoriaSeleccionada);
        },
        stocksFiltrados() {
            return this.stocks.filter(stock => {
                // Usar filtrosAplicados en lugar de valores en tiempo real
                const coincideBusqueda = !this.filtrosAplicados.busqueda || 
                    stock.producto_nombre.toLowerCase().includes(this.filtrosAplicados.busqueda.toLowerCase()) ||
                    stock.producto_codigo.toLowerCase().includes(this.filtrosAplicados.busqueda.toLowerCase());
                
                const coincideCategoria = !this.filtrosAplicados.categoria || 
                    (this.productos.find(p => p.id === stock.producto_id)?.categoria_id === this.filtrosAplicados.categoria);
                
                const coincideSubcategoria = !this.filtrosAplicados.subcategoria || 
                    (this.productos.find(p => p.id === stock.producto_id)?.subcategoria_id === this.filtrosAplicados.subcategoria);
                
                const coincideEstado = !this.filtrosAplicados.estado || 
                    this.obtenerEstadoStock(stock) === this.filtrosAplicados.estado;
                
                return coincideBusqueda && coincideCategoria && coincideSubcategoria && coincideEstado;
            });
        },
        totalPaginasFiltradas() {
            return Math.ceil(this.stocksFiltrados.length / this.itemsPorPagina);
        },
        stocksPaginadosFiltrados() {
            const inicio = (this.paginaActual - 1) * this.itemsPorPagina;
            const fin = inicio + this.itemsPorPagina;
            return this.stocksFiltrados.slice(inicio, fin);
        },
        rangoMostradoFiltrado() {
            const inicio = (this.paginaActual - 1) * this.itemsPorPagina + 1;
            const fin = Math.min(this.paginaActual * this.itemsPorPagina, this.stocksFiltrados.length);
            return { inicio, fin, total: this.stocksFiltrados.length };
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
                    `${window.location.origin}/api/inventario/stock/${this.sucursalSeleccionada}?per_page=9999`,
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
                    `${window.location.origin}/api/productos?per_page=9999`,
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
            this.busquedaProductoEntrada = ''; // Limpiar búsqueda para no mostrar dropdown
            this.mostrarEntrada = true;
        },
        seleccionarProducto(producto) {
            // Establecer producto y cerrar dropdown
            this.entrada.producto_id = producto.id;
            this.busquedaProductoEntrada = ''; // Limpiar búsqueda para cerrar dropdown
        },
        manejarBusquedaProducto(evento) {
            // Limpiar producto seleccionado cuando el usuario empieza a escribir
            this.entrada.producto_id = '';
            this.busquedaProductoEntrada = evento.target.value;
        },
        obtenerNombreProducto(productoId) {
            // Buscar nombre del producto por ID
            const producto = this.productos.find(p => p.id === productoId);
            return producto ? producto.nombre : 'Producto desconocido';
        },
        obtenerCategoria(productoId) {
            const producto = this.productos.find(p => p.id === productoId);
            if (!producto) return '-';
            const categoria = this.categorias.find(c => c.id === producto.categoria_id);
            return categoria ? categoria.nombre : '-';
        },
        obtenerSubcategoria(productoId) {
            const producto = this.productos.find(p => p.id === productoId);
            if (!producto) return '-';
            const subcategoria = this.subcategorias.find(s => s.id === producto.subcategoria_id);
            return subcategoria ? subcategoria.nombre : '-';
        },
        obtenerEstadoStock(stock) {
            // Determinar el estado: OK, Bajo Stock, o Sin Stock
            if (stock.cantidad === 0) {
                return 'sin';
            } else if (stock.cantidad <= stock.cantidad_minima) {
                return 'bajo';
            } else {
                return 'ok';
            }
        },
        cancelarEdicion() {
            this.entrada = { sucursal_id: this.sucursales[0]?.id || '', producto_id: '', cantidad: 1, cantidad_minima: null, observaciones: '', stock_id: null };
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
        },
        async cargarCategorias() {
            try {
                const res = await axios.get(
                    `${window.location.origin}/api/productos/categorias`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.categorias = res.data || [];
            } catch (err) {
                console.error('Error cargando categorías:', err);
            }
        },
        async cargarSubcategorias() {
            try {
                const res = await axios.get(
                    `${window.location.origin}/api/productos/subcategorias`,
                    { headers: { Authorization: `Bearer ${this.token}` } }
                );
                this.subcategorias = res.data || [];
            } catch (err) {
                console.error('Error cargando subcategorías:', err);
            }
        },
        aplicarFiltros() {
            this.filtrosAplicados.busqueda = this.busquedaProductos;
            this.filtrosAplicados.categoria = this.categoriaSeleccionada;
            this.filtrosAplicados.subcategoria = this.subcategoriaSeleccionada;
            this.filtrosAplicados.estado = this.estadoSeleccionado;
            this.paginaActual = 1;
        },
        limpiarFiltros() {
            this.busquedaProductos = '';
            this.categoriaSeleccionada = '';
            this.subcategoriaSeleccionada = '';
            this.estadoSeleccionado = '';
            this.filtrosAplicados = { busqueda: '', categoria: '', subcategoria: '', estado: '' };
            this.paginaActual = 1;
        },
        async exportarInventario() {
            try {
                const response = await axios.get(
                    `${window.location.origin}/api/inventario/exportar`,
                    { 
                        headers: { Authorization: `Bearer ${this.token}` },
                        responseType: 'blob'
                    }
                );
                
                // Crear blob y descargar
                const url = window.URL.createObjectURL(new Blob([response.data]));
                const link = document.createElement('a');
                link.href = url;
                link.setAttribute('download', `inventario_${new Date().toISOString().split('T')[0]}.csv`);
                document.body.appendChild(link);
                link.click();
                link.parentNode.removeChild(link);
                window.URL.revokeObjectURL(url);
            } catch (err) {
                alert('Error al exportar inventario: ' + (err.response?.data?.error || err.message));
            }
        }
    },
    mounted() {
        if (this.token) {
            this.cargarSucursales();
            this.cargarProductos();
            this.cargarCategorias();
            this.cargarSubcategorias();
            // Cargar stock con la sucursal por defecto (la primera que está seleccionada)
            setTimeout(() => {
                if (this.sucursalSeleccionada) {
                    this.cargarStock();
                }
            }, 500);
        }
    },
    watch: {
        token(newToken) {
            if (newToken) {
                this.cargarSucursales();
                this.cargarProductos();
                this.cargarCategorias();
                this.cargarSubcategorias();
            }
        },
        sucursalSeleccionada() {
            if (this.sucursalSeleccionada) {
                this.cargarStock();
            }
        },
        categoriaSeleccionada() {
            // Cuando cambia la categoría, resetear subcategoría pero no filtrar automáticamente
            this.subcategoriaSeleccionada = '';
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
                    <div style="font-size: 0.85rem; color: var(--gray-600); margin-top: 0.5rem;">
                        {{ itemsBajoStock }} items en bajo stock
                    </div>
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
            itemsBajoStock: 0,
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
                this.itemsBajoStock = resBajoStock.data.items_bajo_stock || 0;
                
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
                            @change="cargarDatos(1)"
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
                            @change="cargarDatos(1)"
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

            <div v-if="pagination.total > 0" style="padding: 1rem; display: flex; gap: 1rem; justify-content: center; align-items: center; flex-wrap: wrap; border-top: 1px solid var(--gray-200);">
                <div style="display: flex; gap: 0.5rem; align-items: center;">
                    <label style="font-size: 0.875rem; white-space: nowrap;">Mostrar:</label>
                    <select v-model.number="pagination.per_page" @change="cambiarItemsPorPagina" style="padding: 0.375rem; border: 1px solid var(--gray-300); border-radius: 0.375rem;">
                        <option :value="5">5</option>
                        <option :value="10">10</option>
                        <option :value="15">15</option>
                        <option :value="20">20</option>
                    </select>
                </div>
                <div style="display: flex; gap: 0.5rem; align-items: center;">
                    <button @click="irAPagina(paginaActual - 1)" :disabled="paginaActual === 1" class="btn btn-secondary btn-sm">← Anterior</button>
                    <span style="min-width: 160px; text-align: center;">Página {{ paginaActual }} de {{ pagination.pages }} (Total: {{ pagination.total }})</span>
                    <button @click="irAPagina(paginaActual + 1)" :disabled="paginaActual === pagination.pages" class="btn btn-secondary btn-sm">Siguiente →</button>
                </div>
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
                per_page: 5,
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
            if (page >= 1 && page <= this.pagination.pages) {
                this.cargarDatos(page);
            }
        },
        cambiarItemsPorPagina() {
            this.cargarDatos(1);
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
            <!-- Modal Desglose de Pagos -->
            <div v-if="ventaSeleccionada" class="modal-overlay" style="z-index: 1001;">
                <div class="modal" style="max-width: 550px;">
                    
                    <!-- Header -->
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                        <h3 style="margin: 0;">📋 Desglose de Pagos - {{ ventaSeleccionada.numero_venta }}</h3>
                        <button @click="ventaSeleccionada = null" class="modal-close">✕</button>
                    </div>

                    <!-- Total Display -->
                    <div style="background-color: var(--gray-100); padding: 1rem; border-radius: 0.375rem; margin-bottom: 1.5rem;">
                        <div style="font-size: 0.875rem; color: var(--gray-600); margin-bottom: 0.5rem;">Total a distribuir:</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary);">{{ formatoMoneda(ventaSeleccionada.total) }}</div>
                    </div>

                    <!-- Payment Methods -->
                    <div style="margin-bottom: 1.5rem;">
                        <div v-for="(pago, index) in pagosTemporal" :key="index" style="margin-bottom: 1rem;">
                            <div style="display: grid; grid-template-columns: 1fr 1fr auto; gap: 0.75rem; align-items: end;">
                                <!-- Method Select -->
                                <div>
                                    <label style="display: block; font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;">Método</label>
                                    <select v-model="pago.metodo_pago" style="width: 100%; padding: 0.5rem; border: 1px solid var(--gray-300); border-radius: 0.375rem; font-size: 0.875rem;">
                                        <option value="efectivo">💵 Efectivo</option>
                                        <option value="tarjeta">💳 Tarjeta</option>
                                        <option value="transferencia">🏦 Transferencia</option>
                                    </select>
                                </div>
                                
                                <!-- Amount Input -->
                                <div>
                                    <label style="display: block; font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;">Monto</label>
                                    <input v-model.number="pago.monto" type="number" step="0.01" min="0" placeholder="0.00" style="width: 100%; padding: 0.5rem; border: 1px solid var(--gray-300); border-radius: 0.375rem; font-size: 0.875rem;">
                                </div>

                                <!-- Delete Button -->
                                <button v-if="pagosTemporal.length > 1" @click="pagosTemporal.splice(index, 1)" style="padding: 0.5rem 0.75rem; background-color: var(--danger); color: white; border: none; border-radius: 0.375rem; cursor: pointer; font-size: 0.875rem; font-weight: 600;">
                                    🗑️
                                </button>
                            </div>
                        </div>

                        <!-- Add Another Method Button -->
                        <button @click="agregarPagoMas" style="width: 100%; padding: 0.75rem; background-color: var(--gray-200); color: var(--gray-700); border: 1px solid var(--gray-300); border-radius: 0.375rem; cursor: pointer; font-size: 0.875rem; font-weight: 600; margin-bottom: 1rem;">
                            + Agregar otro método
                        </button>
                    </div>

                    <!-- Summary Box -->
                    <div style="background-color: var(--gray-100); padding: 1rem; border-radius: 0.375rem; margin-bottom: 1.5rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                            <span>Total registrado:</span>
                            <span style="font-weight: 700;">{{ formatoMoneda(calcularTotalPagos()) }}</span>
                        </div>
                        <div v-if="calcularTotalPagos() === parseFloat(ventaSeleccionada.total)" style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 0.375rem; color: #155724; font-size: 0.875rem; font-weight: 600;">
                            <span>✓ Los montos coinciden perfectamente</span>
                        </div>
                        <div v-else style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; background-color: #fff3cd; border: 1px solid #ffeeba; border-radius: 0.375rem; color: #856404; font-size: 0.875rem; font-weight: 600;">
                            <span>⚠️ Diferencia:</span>
                            <span>{{ formatoMoneda(Math.abs(calcularTotalPagos() - parseFloat(ventaSeleccionada.total))) }}</span>
                        </div>
                    </div>

                    <!-- Action Buttons -->
                    <div style="display: flex; gap: 0.5rem;">
                        <button @click="ventaSeleccionada = null" class="btn btn-secondary" style="flex: 1;">Cancelar</button>
                        <button @click="guardarPagosMixtos" class="btn btn-success" style="flex: 1;" :disabled="calcularTotalPagos() !== parseFloat(ventaSeleccionada.total)">
                            ✓ Guardar Pagos
                        </button>
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
                                    <th>Notas</th>
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
                                    <td>
                                        <small>
                                            <span v-if="venta.observaciones" class="badge bg-warning text-dark" :title="venta.observaciones">
                                                📝 {{ venta.observaciones.substring(0, 20) }}{{ venta.observaciones.length > 20 ? '...' : '' }}
                                            </span>
                                            <span v-else class="text-muted">-</span>
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
                                    <th>Notas</th>
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
                                            <span v-if="cierre.observaciones" class="badge bg-info text-dark" :title="cierre.observaciones">
                                                📝 {{ cierre.observaciones.substring(0, 20) }}{{ cierre.observaciones.length > 20 ? '...' : '' }}
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
                // Generar gráficas después de obtener datos con tiempo suficiente
                this.$nextTick(() => {
                    setTimeout(() => {
                        this.generarGraficasVentas();
                    }, 300);
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
            try {
                if (this.ventas.length === 0) return;

                // Verificar que los refs existen, si no reintentar
                if (!this.$refs.chartVentasPorDia || !this.$refs.chartMetodosPago) {
                    console.warn('Canvas refs aún no disponibles, reintentando...');
                    setTimeout(() => this.generarGraficasVentas(), 200);
                    return;
                }

                // Agrupar ventas por fecha
                const ventasPorFecha = {};
                const totalesPorMetodo = { efectivo: 0, tarjeta: 0, transferencia: 0 };

                this.ventas.forEach(venta => {
                    const fecha = new Date(venta.created_at).toLocaleDateString('es-AR');
                    ventasPorFecha[fecha] = (ventasPorFecha[fecha] || 0) + venta.total;

                    // Contar métodos de pago (con validación)
                    if (venta.pagos && Array.isArray(venta.pagos)) {
                        venta.pagos.forEach(pago => {
                            const metodo = (pago.metodo_pago || '').toLowerCase().trim();
                            if (metodo === 'efectivo') totalesPorMetodo.efectivo += pago.monto || 0;
                            else if (metodo === 'tarjeta') totalesPorMetodo.tarjeta += pago.monto || 0;
                            else if (metodo === 'transferencia') totalesPorMetodo.transferencia += pago.monto || 0;
                        });
                    }
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
                console.log('✓ Gráficas de ventas generadas correctamente');
            } catch (error) {
                console.error('Error generando gráficas:', error);
            }
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
            
            <!-- Modal Registrar Devolución -->
            <div v-if="modalDevolucion" class="modal-overlay" style="z-index: 1001;">
                <div class="modal" style="max-width: 550px;">
                    
                    <!-- Header -->
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                        <h3 style="margin: 0; color: var(--danger);">↩️ Registrar Devolución</h3>
                        <button @click="modalDevolucion = false" class="modal-close">✕</button>
                    </div>

                    <!-- Product Info Display -->
                    <div v-if="detalleSeleccionado" style="background-color: var(--gray-100); padding: 1rem; border-radius: 0.375rem; margin-bottom: 1.5rem;">
                        <div style="margin-bottom: 0.75rem;">
                            <div style="font-size: 0.875rem; color: var(--gray-600); margin-bottom: 0.25rem;">Producto:</div>
                            <div style="font-size: 1rem; font-weight: 700;">{{ detalleSeleccionado.producto_nombre }}</div>
                        </div>
                        <div style="margin-bottom: 0;">
                            <div style="font-size: 0.875rem; color: var(--gray-600); margin-bottom: 0.25rem;">Cantidad Original:</div>
                            <div style="font-size: 1rem; font-weight: 700;">{{ detalleSeleccionado.cantidad }} unidades</div>
                        </div>
                    </div>

                    <!-- Form Fields -->
                    <div v-if="detalleSeleccionado" style="margin-bottom: 1.5rem;">
                        <!-- Cantidad a Devolver -->
                        <div style="margin-bottom: 1rem;">
                            <label style="display: block; font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;">Cantidad a Devolver</label>
                            <input v-model.number="cantidadDevoluciones" type="number" 
                                   min="1" :max="cantidadDisponible"
                                   style="width: 100%; padding: 0.5rem; border: 1px solid var(--gray-300); border-radius: 0.375rem; font-size: 0.875rem;">
                            <small style="color: var(--gray-600); font-size: 0.75rem; margin-top: 0.25rem; display: block;">Máximo disponible: {{ cantidadDisponible }}</small>
                        </div>

                        <!-- Motivo Dropdown -->
                        <div style="margin-bottom: 1rem;">
                            <label style="display: block; font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;">Motivo de la Devolución</label>
                            <select v-model="motivoDevoluciones" style="width: 100%; padding: 0.5rem; border: 1px solid var(--gray-300); border-radius: 0.375rem; font-size: 0.875rem;">
                                <option value="">Selecciona un motivo</option>
                                <option value="Defectuoso">Defectuoso</option>
                                <option value="Cambio de opinión">Cambio de opinión</option>
                                <option value="Falta de stock">Falta de stock</option>
                                <option value="Error de venta">Error de venta</option>
                                <option value="Dañado en tránsito">Dañado en tránsito</option>
                                <option value="Otro">Otro</option>
                            </select>
                        </div>

                        <!-- Notas Adicionales -->
                        <div style="margin-bottom: 1rem;">
                            <label style="display: block; font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;">Notas Adicionales (opcional)</label>
                            <textarea v-model="notasDevoluciones" rows="3" style="width: 100%; padding: 0.5rem; border: 1px solid var(--gray-300); border-radius: 0.375rem; font-size: 0.875rem; font-family: inherit; resize: vertical;"></textarea>
                        </div>
                    </div>

                    <!-- Amount Summary -->
                    <div style="background-color: #ffe8e8; padding: 1rem; border-radius: 0.375rem; margin-bottom: 1.5rem; border: 1px solid #ffcccc;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 0.875rem; font-weight: 600; color: var(--danger);">Monto a Revertir:</span>
                            <span style="font-size: 1.25rem; font-weight: 700; color: var(--danger);">{{ formatoMoneda(detalleSeleccionado.precio_unitario * cantidadDevoluciones) }}</span>
                        </div>
                    </div>

                    <!-- Action Buttons -->
                    <div style="display: flex; gap: 0.5rem;">
                        <button @click="modalDevolucion = false" class="btn btn-secondary" style="flex: 1;">Cancelar</button>
                        <button @click="registrarDevolucion" class="btn btn-danger" style="flex: 1;" :disabled="cantidadDevoluciones <= 0">
                            ↩️ Registrar Devolución
                        </button>
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
                                    <!-- Razón desactivada para simplificar los resultados.
                                    <p style="margin: 0.3rem 0; color: var(--gray-700);">
                                        <strong>Razón:</strong> {{ mica.razon }}
                                    </p>
                                    -->
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

// ============= COMPONENTE: REPARACIONES =============
const ReparacionesView = {
    props: {
        apiUrl: String,
        token: String,
        userRole: String
    },
    template: `
        <div style="padding: 1rem;">
            <!-- Sección Admin: Catálogos -->
            <div v-if="userRoleLocal === 'admin'" style="margin-bottom: 2rem;">
                <div class="tabs" style="display: flex; gap: 0.5rem; border-bottom: 2px solid var(--gray-300); margin-bottom: 1.5rem;">
                    <button 
                        v-for="tab in tabs" 
                        :key="tab"
                        @click="tabActiva = tab"
                        :class="['btn', 'btn-sm', tabActiva === tab ? 'btn-primary' : 'btn-secondary']"
                    >
                        {{ tab }}
                    </button>
                </div>

                <!-- Marcas -->
                <div v-if="tabActiva === 'Marcas'" class="card">
                    <div class="card-header">
                        <h3>Gestión de Marcas</h3>
                        <button v-if="!editandoMarcaId" @click="mostrarFormularioMarca = !mostrarFormularioMarca" class="btn btn-primary btn-sm">
                            {{ mostrarFormularioMarca ? 'Cancelar' : '+ Nueva Marca' }}
                        </button>
                    </div>

                    <div v-if="mostrarFormularioMarca && !editandoMarcaId" class="form-group" style="background: var(--gray-100); padding: 1rem; border-radius: 0.375rem; margin-bottom: 1rem;">
                        <label>Nombre de Marca</label>
                        <input v-model="formularioMarca.nombre" type="text" placeholder="Ej: Samsung" required>
                        <div style="margin-top: 0.5rem;">
                            <button @click="guardarMarca" class="btn btn-success btn-sm">Guardar</button>
                            <button @click="mostrarFormularioMarca = false" class="btn btn-secondary btn-sm" style="margin-left: 0.5rem;">Cancelar</button>
                        </div>
                    </div>
                    
                    <div v-if="editandoMarcaId" class="form-group" style="background: var(--yellow-100); padding: 1rem; border-radius: 0.375rem; margin-bottom: 1rem; border-left: 4px solid var(--warning);">
                        <h4 style="margin-top: 0;">Editar Marca</h4>
                        <label>Nombre de Marca</label>
                        <input v-model="formularioMarca.nombre" type="text" placeholder="Ej: Samsung" required>
                        <div style="margin-top: 0.5rem;">
                            <button @click="guardarEdicionMarca" class="btn btn-success btn-sm">Guardar Cambios</button>
                            <button @click="cancelarEdicionMarca" class="btn btn-secondary btn-sm" style="margin-left: 0.5rem;">Cancelar</button>
                        </div>
                    </div>

                    <table>
                        <thead>
                            <tr>
                                <th>Nombre</th>
                                <th>Estado</th>
                                <th>Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="marca in marcas" :key="marca.id">
                                <td>{{ marca.nombre }}</td>
                                <td><span :style="{color: marca.is_active ? 'var(--success)' : 'var(--danger)'}">{{ marca.is_active ? '✓ Activa' : '✗ Inactiva' }}</span></td>
                                <td>
                                    <button @click="iniciarEdicionMarca(marca)" class="btn btn-primary btn-sm">Editar</button>
                                    <button @click="eliminarMarca(marca.id)" class="btn btn-danger btn-sm" style="margin-left: 0.25rem;">Eliminar</button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                    
                    <!-- Paginación Marcas -->
                    <div style="display: flex; justify-content: center; gap: 1rem; margin-top: 1rem; align-items: center; flex-wrap: wrap;">
                        <div style="display: flex; gap: 0.5rem; align-items: center;">
                            <label style="font-size: 0.875rem; white-space: nowrap;">Mostrar:</label>
                            <select v-model.number="itemsPerPageMarcas" @change="cambiarItemsPerPageMarcas" style="padding: 0.375rem; border: 1px solid var(--gray-300); border-radius: 0.375rem;">
                                <option :value="5">5</option>
                                <option :value="10">10</option>
                                <option :value="15">15</option>
                                <option :value="20">20</option>
                            </select>
                        </div>
                        <div style="display: flex; gap: 0.5rem; align-items: center;">
                            <button @click="irAPaginaMarcas(paginaMarcas - 1)" :disabled="paginaMarcas === 1" class="btn btn-secondary btn-sm">← Anterior</button>
                            <span style="min-width: 100px; text-align: center;">Página {{ paginaMarcas }} de {{ totalPagesMarcas }}</span>
                            <button @click="irAPaginaMarcas(paginaMarcas + 1)" :disabled="paginaMarcas === totalPagesMarcas" class="btn btn-secondary btn-sm">Siguiente →</button>
                        </div>
                    </div>
                </div>

                <!-- Modelos -->
                <div v-if="tabActiva === 'Modelos'" class="card">
                    <div class="card-header">
                        <h3>Gestión de Modelos</h3>
                        <button v-if="!editandoModeloId" @click="mostrarFormularioModelo = !mostrarFormularioModelo" class="btn btn-primary btn-sm">
                            {{ mostrarFormularioModelo ? 'Cancelar' : '+ Nuevo Modelo' }}
                        </button>
                    </div>

                    <div v-if="mostrarFormularioModelo && !editandoModeloId" class="form-group" style="background: var(--gray-100); padding: 1rem; border-radius: 0.375rem; margin-bottom: 1rem;">
                        <label>Marca</label>
                        <select v-model="formularioModelo.marca_id" required>
                            <option value="">Selecciona una marca</option>
                            <option v-for="marca in marcasDisponibles" :key="marca.id" :value="marca.id">{{ marca.nombre }}</option>
                        </select>
                        <label style="margin-top: 0.5rem;">Nombre del Modelo</label>
                        <input v-model="formularioModelo.nombre" type="text" placeholder="Ej: A32 4G" required>
                        <div style="margin-top: 0.5rem;">
                            <button @click="guardarModelo" class="btn btn-success btn-sm">Guardar</button>
                            <button @click="mostrarFormularioModelo = false" class="btn btn-secondary btn-sm" style="margin-left: 0.5rem;">Cancelar</button>
                        </div>
                    </div>
                    
                    <div v-if="editandoModeloId" class="form-group" style="background: var(--yellow-100); padding: 1rem; border-radius: 0.375rem; margin-bottom: 1rem; border-left: 4px solid var(--warning);">
                        <h4 style="margin-top: 0;">Editar Modelo</h4>
                        <label>Marca</label>
                        <select v-model="formularioModelo.marca_id" required>
                            <option value="">Selecciona una marca</option>
                            <option v-for="marca in marcasDisponibles" :key="marca.id" :value="marca.id">{{ marca.nombre }}</option>
                        </select>
                        <label style="margin-top: 0.5rem;">Nombre del Modelo</label>
                        <input v-model="formularioModelo.nombre" type="text" placeholder="Ej: A32 4G" required>
                        <div style="margin-top: 0.5rem;">
                            <button @click="guardarEdicionModelo" class="btn btn-success btn-sm">Guardar Cambios</button>
                            <button @click="cancelarEdicionModelo" class="btn btn-secondary btn-sm" style="margin-left: 0.5rem;">Cancelar</button>
                        </div>
                    </div>

                    <table>
                        <thead>
                            <tr>
                                <th>Marca</th>
                                <th>Modelo</th>
                                <th>Estado</th>
                                <th>Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="modelo in modelos" :key="modelo.id">
                                <td>{{ modelo.marca_nombre }}</td>
                                <td>{{ modelo.nombre }}</td>
                                <td><span :style="{color: modelo.is_active ? 'var(--success)' : 'var(--danger)'}">{{ modelo.is_active ? '✓' : '✗' }}</span></td>
                                <td>
                                    <button @click="iniciarEdicionModelo(modelo)" class="btn btn-primary btn-sm">Editar</button>
                                    <button @click="eliminarModelo(modelo.id)" class="btn btn-danger btn-sm" style="margin-left: 0.25rem;">Eliminar</button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                    
                    <!-- Paginación Modelos -->
                    <div style="display: flex; justify-content: center; gap: 1rem; margin-top: 1rem; align-items: center; flex-wrap: wrap;">
                        <div style="display: flex; gap: 0.5rem; align-items: center;">
                            <label style="font-size: 0.875rem; white-space: nowrap;">Mostrar:</label>
                            <select v-model.number="itemsPerPageModelos" @change="cambiarItemsPerPageModelos" style="padding: 0.375rem; border: 1px solid var(--gray-300); border-radius: 0.375rem;">
                                <option :value="5">5</option>
                                <option :value="10">10</option>
                                <option :value="15">15</option>
                                <option :value="20">20</option>
                            </select>
                        </div>
                        <div style="display: flex; gap: 0.5rem; align-items: center;">
                            <button @click="irAPaginaModelos(paginaModelos - 1)" :disabled="paginaModelos === 1" class="btn btn-secondary btn-sm">← Anterior</button>
                            <span style="min-width: 100px; text-align: center;">Página {{ paginaModelos }} de {{ totalPagesModelos }}</span>
                            <button @click="irAPaginaModelos(paginaModelos + 1)" :disabled="paginaModelos === totalPagesModelos" class="btn btn-secondary btn-sm">Siguiente →</button>
                        </div>
                    </div>
                </div>

                <!-- Tipos de Reparación -->
                <div v-if="tabActiva === 'Tipos'" class="card">
                    <div class="card-header">
                        <h3>Tipos de Reparación</h3>
                        <button v-if="!editandoTipoId" @click="mostrarFormularioTipo = !mostrarFormularioTipo" class="btn btn-primary btn-sm">
                            {{ mostrarFormularioTipo ? 'Cancelar' : '+ Nuevo Tipo' }}
                        </button>
                    </div>

                    <div v-if="mostrarFormularioTipo && !editandoTipoId" class="form-group" style="background: var(--gray-100); padding: 1rem; border-radius: 0.375rem; margin-bottom: 1rem;">
                        <label>Nombre</label>
                        <input v-model="formularioTipo.nombre" type="text" placeholder="Ej: Cambio de Pantalla" required>
                        <label style="margin-top: 0.5rem;">Descripción (opcional)</label>
                        <textarea v-model="formularioTipo.descripcion" placeholder="Descripción"></textarea>
                        <div style="margin-top: 0.5rem;">
                            <button @click="guardarTipo" class="btn btn-success btn-sm">Guardar</button>
                            <button @click="mostrarFormularioTipo = false" class="btn btn-secondary btn-sm" style="margin-left: 0.5rem;">Cancelar</button>
                        </div>
                    </div>
                    
                    <div v-if="editandoTipoId" class="form-group" style="background: var(--yellow-100); padding: 1rem; border-radius: 0.375rem; margin-bottom: 1rem; border-left: 4px solid var(--warning);">
                        <h4 style="margin-top: 0;">Editar Tipo de Reparación</h4>
                        <label>Nombre</label>
                        <input v-model="formularioTipo.nombre" type="text" placeholder="Ej: Cambio de Pantalla" required>
                        <label style="margin-top: 0.5rem;">Descripción (opcional)</label>
                        <textarea v-model="formularioTipo.descripcion" placeholder="Descripción"></textarea>
                        <div style="margin-top: 0.5rem;">
                            <button @click="guardarEdicionTipo" class="btn btn-success btn-sm">Guardar Cambios</button>
                            <button @click="cancelarEdicionTipo" class="btn btn-secondary btn-sm" style="margin-left: 0.5rem;">Cancelar</button>
                        </div>
                    </div>

                    <table>
                        <thead>
                            <tr>
                                <th>Nombre</th>
                                <th>Descripción</th>
                                <th>Estado</th>
                                <th>Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="tipo in tipos" :key="tipo.id">
                                <td>{{ tipo.nombre }}</td>
                                <td>{{ tipo.descripcion || '-' }}</td>
                                <td><span :style="{color: tipo.is_active ? 'var(--success)' : 'var(--danger)'}">{{ tipo.is_active ? '✓' : '✗' }}</span></td>
                                <td>
                                    <button @click="iniciarEdicionTipo(tipo)" class="btn btn-primary btn-sm">Editar</button>
                                    <button @click="eliminarTipo(tipo.id)" class="btn btn-danger btn-sm" style="margin-left: 0.25rem;">Eliminar</button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                    
                    <!-- Paginación Tipos -->
                    <div style="display: flex; justify-content: center; gap: 1rem; margin-top: 1rem; align-items: center; flex-wrap: wrap;">
                        <div style="display: flex; gap: 0.5rem; align-items: center;">
                            <label style="font-size: 0.875rem; white-space: nowrap;">Mostrar:</label>
                            <select v-model.number="itemsPerPageTipos" @change="cambiarItemsPerPageTipos" style="padding: 0.375rem; border: 1px solid var(--gray-300); border-radius: 0.375rem;">
                                <option :value="5">5</option>
                                <option :value="10">10</option>
                                <option :value="15">15</option>
                                <option :value="20">20</option>
                            </select>
                        </div>
                        <div style="display: flex; gap: 0.5rem; align-items: center;">
                            <button @click="irAPaginaTipos(paginaTipos - 1)" :disabled="paginaTipos === 1" class="btn btn-secondary btn-sm">← Anterior</button>
                            <span style="min-width: 100px; text-align: center;">Página {{ paginaTipos }} de {{ totalPagesTipos }}</span>
                            <button @click="irAPaginaTipos(paginaTipos + 1)" :disabled="paginaTipos === totalPagesTipos" class="btn btn-secondary btn-sm">Siguiente →</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Sección de Catálogo: Visible para todos (admin puede editar/eliminar) -->
            <div class="card" style="margin-bottom: 2rem;">
                <div class="card-header">
                    <h3>Catálogo de Reparaciones</h3>
                    <button v-if="userRoleLocal === 'admin' && !editandoCatalogoId" @click="mostrarFormularioCatalogo = !mostrarFormularioCatalogo" class="btn btn-primary btn-sm">
                        {{ mostrarFormularioCatalogo ? 'Cancelar' : '+ Agregar al Catálogo' }}
                    </button>
                </div>

                <!-- Barra de búsqueda por modelo -->
                <div class="catalog-search-bar">
                    <div class="catalog-search-input">
                        <input 
                            v-model="searchModeloCatalogo"
                            @keyup.enter="buscarEnCatalogo"
                            type="text"
                            placeholder="🔍 Buscar por modelo..."
                        >
                    </div>
                    <div class="catalog-search-actions">
                        <button 
                            @click="buscarEnCatalogo"
                            class="btn btn-primary btn-sm"
                        >
                            Buscar
                        </button>
                        <button 
                            v-if="searchModeloCatalogo"
                            @click="searchModeloCatalogo = ''; buscarEnCatalogo()"
                            class="btn btn-secondary btn-sm"
                        >
                            Limpiar búsqueda
                        </button>
                    </div>
                </div>

                <div v-if="mostrarFormularioCatalogo && !editandoCatalogoId && userRoleLocal === 'admin'" class="form-group" style="background: var(--gray-100); padding: 1rem; border-radius: 0.375rem; margin-bottom: 1rem;">
                    <label>Marca</label>
                    <select v-model="formularioCatalogo.marca_id" @change="cargarModelosDeMarca" required>
                        <option value="">Selecciona una marca</option>
                        <option v-for="marca in marcasDisponibles" :key="marca.id" :value="marca.id">{{ marca.nombre }}</option>
                    </select>
                    <label style="margin-top: 0.5rem;">Modelo</label>
                    <select v-model="formularioCatalogo.modelo_id" required>
                        <option value="">Selecciona un modelo</option>
                        <option v-for="modelo in modelosFiltrados" :key="modelo.id" :value="modelo.id">{{ modelo.nombre }}</option>
                    </select>
                    <label style="margin-top: 0.5rem;">Tipo de Reparación</label>
                    <select v-model="formularioCatalogo.tipo_reparacion_id" required>
                        <option value="">Selecciona un tipo</option>
                        <option v-for="tipo in tipos" :key="tipo.id" :value="tipo.id">{{ tipo.nombre }}</option>
                    </select>
                    <label style="margin-top: 0.5rem;">Costo</label>
                    <input v-model="formularioCatalogo.costo" type="number" placeholder="Ej: 690" required>
                    <div style="margin-top: 0.5rem;">
                        <button @click="guardarCatalogo" class="btn btn-success btn-sm">Guardar</button>
                        <button @click="mostrarFormularioCatalogo = false" class="btn btn-secondary btn-sm" style="margin-left: 0.5rem;">Cancelar</button>
                    </div>
                </div>
                
                <div v-if="editandoCatalogoId && userRoleLocal === 'admin'" class="form-group" style="background: var(--yellow-100); padding: 1rem; border-radius: 0.375rem; margin-bottom: 1rem; border-left: 4px solid var(--warning);">
                    <h4 style="margin-top: 0;">Editar Catálogo</h4>
                    <label>Marca</label>
                    <select v-model="formularioCatalogo.marca_id" @change="cargarModelosDeMarca" required>
                        <option value="">Selecciona una marca</option>
                        <option v-for="marca in marcasDisponibles" :key="marca.id" :value="marca.id">{{ marca.nombre }}</option>
                    </select>
                    <label style="margin-top: 0.5rem;">Modelo</label>
                    <select v-model="formularioCatalogo.modelo_id" required>
                        <option value="">Selecciona un modelo</option>
                        <option v-for="modelo in modelosFiltrados" :key="modelo.id" :value="modelo.id">{{ modelo.nombre }}</option>
                    </select>
                    <label style="margin-top: 0.5rem;">Tipo de Reparación</label>
                    <select v-model="formularioCatalogo.tipo_reparacion_id" required>
                        <option value="">Selecciona un tipo</option>
                        <option v-for="tipo in tipos" :key="tipo.id" :value="tipo.id">{{ tipo.nombre }}</option>
                    </select>
                    <label style="margin-top: 0.5rem;">Costo</label>
                    <input v-model="formularioCatalogo.costo" type="number" placeholder="Ej: 690" required>
                    <div style="margin-top: 0.5rem;">
                        <button @click="guardarEdicionCatalogo" class="btn btn-success btn-sm">Guardar Cambios</button>
                        <button @click="cancelarEdicionCatalogo" class="btn btn-secondary btn-sm" style="margin-left: 0.5rem;">Cancelar</button>
                    </div>
                </div>

                <table>
                    <thead>
                        <tr>
                            <th>Marca</th>
                            <th>Modelo</th>
                            <th>Tipo de Reparación</th>
                            <th>Costo</th>
                            <th v-if="userRoleLocal === 'admin'">Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="item in catalogo" :key="item.id">
                            <td>{{ item.marca_nombre }}</td>
                            <td>{{ item.modelo_nombre }}</td>
                            <td>{{ item.tipo_reparacion_nombre }}</td>
                            <td>\${{ item.costo }}</td>
                            <td v-if="userRoleLocal === 'admin'">
                                <button @click="iniciarEdicionCatalogo(item)" class="btn btn-primary btn-sm">Editar</button>
                                <button @click="eliminarCatalogo(item.id)" class="btn btn-danger btn-sm" style="margin-left: 0.25rem;">Eliminar</button>
                            </td>
                        </tr>
                    </tbody>
                </table>
                
                <!-- Paginación Catálogo -->
                <div style="display: flex; justify-content: center; gap: 1rem; margin-top: 1rem; align-items: center; flex-wrap: wrap;">
                    <div style="display: flex; gap: 0.5rem; align-items: center;">
                        <label style="font-size: 0.875rem; white-space: nowrap;">Mostrar:</label>
                        <select v-model.number="itemsPerPageCatalogo" @change="cambiarItemsPerPageCatalogo" style="padding: 0.375rem; border: 1px solid var(--gray-300); border-radius: 0.375rem;">
                            <option :value="5">5</option>
                            <option :value="10">10</option>
                            <option :value="15">15</option>
                            <option :value="20">20</option>
                        </select>
                    </div>
                    <div style="display: flex; gap: 0.5rem; align-items: center;">
                        <button @click="irAPaginaCatalogo(paginaCatalogo - 1)" :disabled="paginaCatalogo === 1" class="btn btn-secondary btn-sm">← Anterior</button>
                        <span style="min-width: 100px; text-align: center;">Página {{ paginaCatalogo }} de {{ totalPagesCatalogo }}</span>
                        <button @click="irAPaginaCatalogo(paginaCatalogo + 1)" :disabled="paginaCatalogo === totalPagesCatalogo" class="btn btn-secondary btn-sm">Siguiente →</button>
                    </div>
                </div>
            </div>

            <!-- Sección para Empleados y Admin: Registro de Reparaciones -->
            <div class="card">
                <div class="card-header">
                    <h3>{{ mostrarNuevaReparacion ? 'Nueva Reparación' : 'Listado de Reparaciones' }}</h3>
                    <button @click="mostrarNuevaReparacion = !mostrarNuevaReparacion" class="btn btn-primary btn-sm">
                        {{ mostrarNuevaReparacion ? 'Ver Listado' : '+ Nueva Reparación' }}
                    </button>
                </div>

                <!-- Formulario Nueva Reparación -->
                <div v-if="mostrarNuevaReparacion" style="background: var(--gray-100); padding: 1rem; border-radius: 0.375rem; margin-bottom: 1rem;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                        <div class="form-group">
                            <label>Nombre del Cliente</label>
                            <input v-model="formularioReparacion.nombre_cliente" type="text" placeholder="Ej: Juan Pérez" required>
                        </div>
                        <div class="form-group">
                            <label>Teléfono</label>
                            <input v-model="formularioReparacion.telefono_cliente" type="tel" placeholder="Ej: 5551234567" maxlength="10" pattern="[0-9]+" @input="validarTelefono" required>
                            <small style="color: var(--gray-600);">Máximo 10 dígitos</small>
                        </div>
                        <div class="form-group">
                            <label>Marca</label>
                            <select v-model="formularioReparacion.marca_id" @change="formularioReparacion.modelo_nombre = ''" required>
                                <option value="">Selecciona una marca</option>
                                <option v-for="marca in marcasDisponibles" :key="marca.id" :value="marca.id">{{ marca.nombre }}</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Modelo</label>
                            <input v-model.trim="formularioReparacion.modelo_nombre" type="text" placeholder="Ej: G9 Play" required>
                        </div>
                        <div class="form-group">
                            <label>Tipo de Reparación</label>
                            <select v-model="formularioReparacion.tipo_reparacion_id" required>
                                <option value="">Selecciona un tipo</option>
                                <option v-for="tipo in tipos" :key="tipo.id" :value="tipo.id">{{ tipo.nombre }}</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Costo</label>
                            <input v-model="formularioReparacion.costo" type="number" placeholder="Ej: 690" required>
                        </div>
                        <div class="form-group" v-if="userRoleLocal === 'admin'">
                            <label>Sucursal *</label>
                            <select v-model="formularioReparacion.sucursal_id" required>
                                <option value="">Selecciona una sucursal</option>
                                <option v-for="sucursal in sucursales" :key="sucursal.id" :value="sucursal.id">{{ sucursal.nombre }}</option>
                            </select>
                        </div>
                        <div class="form-group" v-else>
                            <label>Sucursal</label>
                            <input type="text" :value="sucursalEmpleado" disabled style="background-color: var(--gray-200); color: var(--gray-600);">
                            <small style="color: var(--gray-600);">(Auto-asignada)</small>
                        </div>
                        <div class="form-group">
                            <label>Fecha</label>
                            <input v-model="formularioReparacion.fecha" type="date" required>
                        </div>
                    </div>
                    <div style="margin-top: 1rem; display: flex; gap: 0.5rem;">
                        <button @click="guardarReparacion" class="btn btn-success">Guardar Reparación</button>
                        <button @click="mostrarNuevaReparacion = false" class="btn btn-secondary">Cancelar</button>
                    </div>
                </div>

                <!-- Listado de Reparaciones -->
                <div v-if="!mostrarNuevaReparacion">
                    <!-- Filtros -->
                    <div style="background: var(--gray-100); padding: 1rem; border-radius: 0.375rem; margin-bottom: 1rem;">
                        <h4>Filtros</h4>
                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr auto; gap: 1rem; margin-bottom: 0.5rem;">
                            <div class="form-group">
                                <label>Desde</label>
                                <input v-model="filtroFechaInicio" type="date">
                            </div>
                            <div class="form-group">
                                <label>Hasta</label>
                                <input v-model="filtroFechaFin" type="date">
                            </div>
                            <div class="form-group" v-if="userRoleLocal === 'admin'">
                                <label>Sucursal</label>
                                <select v-model="filtroSucursal">
                                    <option value="">Todas las sucursales</option>
                                    <option v-for="sucursal in sucursales" :key="sucursal.id" :value="sucursal.id">{{ sucursal.nombre }}</option>
                                </select>
                            </div>
                            <div style="display: flex; gap: 0.5rem; align-items: flex-end;">
                                <button @click="aplicarFiltrosReparaciones" class="btn btn-primary btn-sm" style="min-width: 80px;">Filtrar</button>
                                <button @click="limpiarFiltrosReparaciones" class="btn btn-secondary btn-sm" style="min-width: 80px;">Limpiar</button>
                            </div>
                        </div>
                    </div>
                    
                    <table>
                        <thead>
                            <tr>
                                <th>Fecha</th>
                                <th>Cliente</th>
                                <th>Teléfono</th>
                                <th>Marca</th>
                                <th>Modelo</th>
                                <th>Tipo</th>
                                <th>Costo</th>
                                <th>Estado</th>
                                <th>Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="rep in reparaciones" :key="rep.id">
                                <td>{{ rep.fecha }}</td>
                                <td>{{ rep.nombre_cliente }}</td>
                                <td>{{ rep.telefono_cliente }}</td>
                                <td>{{ rep.marca_nombre }}</td>
                                <td>{{ rep.modelo_nombre }}</td>
                                <td>{{ rep.tipo_reparacion_nombre }}</td>
                                <td>\${{ rep.costo }}</td>
                                <td><span :style="{color: rep.estado === 'entregada' ? 'var(--success)' : 'var(--warning)'}">{{ rep.estado === 'entregada' ? '✓ Entregada' : '⏳ Registrada' }}</span></td>
                                <td>
                                    <button v-if="rep.estado !== 'entregada'" @click="marcarEntregada(rep.id)" class="btn btn-success btn-sm" title="Marcar como entregada">✓</button>
                                    <button @click="editarReparacion(rep)" class="btn btn-primary btn-sm" style="margin-left: 0.25rem;">Editar</button>
                                    <button v-if="userRoleLocal === 'admin'" @click="eliminarReparacion(rep.id)" class="btn btn-danger btn-sm" style="margin-left: 0.25rem;">Eliminar</button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                    
                    <!-- Paginación Reparaciones -->
                    <div style=\"display: flex; justify-content: center; gap: 1rem; margin-top: 1rem; align-items: center; flex-wrap: wrap;\">
                        <div style=\"display: flex; gap: 0.5rem; align-items: center;\">
                            <label style=\"font-size: 0.875rem; white-space: nowrap;\">Mostrar:</label>
                            <select v-model.number=\"itemsPerPageReparaciones\" @change=\"cambiarItemsPerPageReparaciones\" style=\"padding: 0.375rem; border: 1px solid var(--gray-300); border-radius: 0.375rem;\">
                                <option :value=\"5\">5</option>
                                <option :value=\"10\">10</option>
                                <option :value=\"15\">15</option>
                                <option :value=\"20\">20</option>
                            </select>
                        </div>
                        <div style=\"display: flex; gap: 0.5rem; align-items: center;\">
                            <button @click=\"irAPaginaReparaciones(paginaReparaciones - 1)\" :disabled=\"paginaReparaciones === 1\" class=\"btn btn-secondary btn-sm\">← Anterior</button>
                            <span style=\"min-width: 150px; text-align: center;\">Página {{ paginaReparaciones }} de {{ totalPagesReparaciones }} (Total: {{ totalReparaciones }})</span>
                            <button @click=\"irAPaginaReparaciones(paginaReparaciones + 1)\" :disabled=\"paginaReparaciones === totalPagesReparaciones\" class=\"btn btn-secondary btn-sm\">Siguiente →</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Modal de error/éxito -->
            <div v-if="mensaje" :class="['alert', mensaje.tipo === 'error' ? 'alert-danger' : 'alert-success']" style="position: fixed; top: 20px; right: 20px; width: 300px; z-index: 1000;">
                {{ mensaje.texto }}
                <button @click="mensaje = null" style="float: right; background: none; border: none; cursor: pointer; font-weight: bold;">✕</button>
            </div>
        </div>
    `,
    data() {
        return {
            tabs: ['Marcas', 'Modelos', 'Tipos'],
            tabActiva: 'Marcas',
            marcas: [],
            marcasDisponibles: [],
            modelos: [],
            tipos: [],
            catalogo: [],
            reparaciones: [],
            sucursales: [],
            
            mostrarFormularioMarca: false,
            mostrarFormularioModelo: false,
            mostrarFormularioTipo: false,
            mostrarFormularioCatalogo: false,
            mostrarNuevaReparacion: false,
            
            editandoMarcaId: null,
            editandoModeloId: null,
            editandoTipoId: null,
            editandoCatalogoId: null,
            
            formularioMarca: { nombre: '' },
            formularioModelo: { marca_id: '', nombre: '' },
            formularioTipo: { nombre: '', descripcion: '' },
            formularioCatalogo: { marca_id: '', modelo_id: '', tipo_reparacion_id: '', costo: '' },
            formularioReparacion: {
                nombre_cliente: '',
                telefono_cliente: '',
                marca_id: '',
                modelo_nombre: '',
                tipo_reparacion_id: '',
                costo: '',
                sucursal_id: '',
                fecha: new Date().toISOString().split('T')[0]
            },
            
            // Paginación
            paginaMarcas: 1,
            paginaModelos: 1,
            paginaTipos: 1,
            paginaCatalogo: 1,
            paginaReparaciones: 1,
            itemsPerPageMarcas: 5,
            itemsPerPageModelos: 5,
            itemsPerPageTipos: 100,
            itemsPerPageCatalogo: 5,
            itemsPerPageReparaciones: 5,
            searchModeloCatalogo: '',
            totalPagesMarcas: 1,
            totalPagesModelos: 1,
            totalPagesTipos: 1,
            totalPagesCatalogo: 1,
            totalPagesReparaciones: 1,
            totalReparaciones: 0,
            
            // Filtros
            filtroFechaInicio: '',
            filtroFechaFin: '',
            filtroSucursal: '',
            
            modelosFiltrados: [],
            mensaje: null,
            userSucursal: null,
            userRoleLocal: null
        };
    },
    mounted() {
        console.log('ReparacionesView mounted - userRole:', this.userRole, 'token:', this.token ? 'present' : 'missing');
        
        // Si userRole está vacío, intenta leerlo del localStorage
        if (!this.userRole) {
            const user = localStorage.getItem('user');
            if (user) {
                try {
                    const userData = JSON.parse(user);
                    this.userRoleLocal = userData.role;
                    console.log('userRole cargado desde localStorage:', this.userRoleLocal);
                } catch (e) {
                    console.error('Error al parsear user del localStorage:', e);
                }
            }
        } else {
            this.userRoleLocal = this.userRole;
        }
        
        if (this.userRoleLocal === 'employee') {
            this.cargarPerfilEmpleado();
        }
        this.cargarDatos();
    },
    methods: {
        async cargarPerfilEmpleado() {
            try {
                const headers = { Authorization: `Bearer ${this.token}` };
                const res = await axios.get(`/api/auth/profile`, { headers });
                this.userSucursal = res.data.sucursal_id;
            } catch (err) {
                console.error('Error al cargar perfil:', err);
            }
        },
        async cargarMarcasDisponibles(headers) {
            const res = await axios.get(`/api/reparaciones/marcas`, {
                params: { page: 1, per_page: 100 },
                headers
            });
            const marcas = res.data.marcas || [];
            const totalPages = res.data.pages || 1;

            if (totalPages > 1) {
                const pageRequests = [];
                for (let page = 2; page <= totalPages; page++) {
                    pageRequests.push(axios.get(`/api/reparaciones/marcas`, {
                        params: { page, per_page: 100 },
                        headers
                    }));
                }

                const pages = await Promise.all(pageRequests);
                pages.forEach(pageRes => {
                    marcas.push(...(pageRes.data.marcas || []));
                });
            }

            this.marcasDisponibles = marcas;
        },
        async cargarDatos() {
            try {
                const headers = { Authorization: `Bearer ${this.token}` };
                
                const [marcasRes, modelosRes, tiposRes, catalogoRes, reparacionesRes, sucursalesRes] = await Promise.all([
                    axios.get(`/api/reparaciones/marcas`, { 
                        params: { page: this.paginaMarcas, per_page: this.itemsPerPageMarcas },
                        headers 
                    }),
                    axios.get(`/api/reparaciones/modelos`, { 
                        params: { page: this.paginaModelos, per_page: this.itemsPerPageModelos },
                        headers 
                    }),
                    axios.get(`/api/reparaciones/tipos`, { 
                        params: { page: this.paginaTipos, per_page: this.itemsPerPageTipos },
                        headers 
                    }),
                    axios.get(`/api/reparaciones/catalogo`, { 
                        params: { 
                            page: this.paginaCatalogo, 
                            per_page: this.itemsPerPageCatalogo,
                            search: this.searchModeloCatalogo || undefined
                        },
                        headers 
                    }),
                    axios.get(`/api/reparaciones`, { 
                        params: { 
                            page: this.paginaReparaciones, 
                            per_page: this.itemsPerPageReparaciones,
                            fecha_inicio: this.filtroFechaInicio || undefined,
                            fecha_fin: this.filtroFechaFin || undefined,
                            sucursal_id: this.filtroSucursal || undefined
                        },
                        headers 
                    }),
                    axios.get(`/api/admin/sucursales-publico`, { headers }),
                    this.cargarMarcasDisponibles(headers)
                ]);
                
                // Marcas
                this.marcas = marcasRes.data.marcas;
                this.totalPagesMarcas = marcasRes.data.pages;
                
                // Modelos
                this.modelos = modelosRes.data.modelos;
                this.totalPagesModelos = modelosRes.data.pages;
                
                // Tipos
                this.tipos = tiposRes.data.tipos;
                this.totalPagesTipos = tiposRes.data.pages;
                
                // Catálogo
                this.catalogo = catalogoRes.data.catalogo;
                this.totalPagesCatalogo = catalogoRes.data.pages;
                
                // Reparaciones
                this.reparaciones = reparacionesRes.data.reparaciones;
                this.totalPagesReparaciones = reparacionesRes.data.pages;
                this.totalReparaciones = reparacionesRes.data.total;
                
                // Sucursales
                this.sucursales = sucursalesRes.data;
            } catch (err) {
                this.mostrarMensaje('Error al cargar datos', 'error');
            }
        },
        irAPaginaMarcas(pagina) {
            if (pagina >= 1 && pagina <= this.totalPagesMarcas) {
                this.paginaMarcas = pagina;
                this.cargarDatos();
            }
        },
        irAPaginaModelos(pagina) {
            if (pagina >= 1 && pagina <= this.totalPagesModelos) {
                this.paginaModelos = pagina;
                this.cargarDatos();
            }
        },
        irAPaginaTipos(pagina) {
            if (pagina >= 1 && pagina <= this.totalPagesTipos) {
                this.paginaTipos = pagina;
                this.cargarDatos();
            }
        },
        irAPaginaCatalogo(pagina) {
            if (pagina >= 1 && pagina <= this.totalPagesCatalogo) {
                this.paginaCatalogo = pagina;
                this.cargarDatos();
            }
        },
        irAPaginaReparaciones(pagina) {
            if (pagina >= 1 && pagina <= this.totalPagesReparaciones) {
                this.paginaReparaciones = pagina;
                this.cargarDatos();
            }
        },
        cambiarItemsPerPageMarcas() {
            this.paginaMarcas = 1;
            this.cargarDatos();
        },
        cambiarItemsPerPageModelos() {
            this.paginaModelos = 1;
            this.cargarDatos();
        },
        cambiarItemsPerPageTipos() {
            this.paginaTipos = 1;
            this.cargarDatos();
        },
        cambiarItemsPerPageReparaciones() {
            this.paginaReparaciones = 1;
            this.cargarDatos();
        },
        aplicarFiltrosReparaciones() {
            this.paginaReparaciones = 1;
            this.cargarDatos();
        },
        limpiarFiltrosReparaciones() {
            this.filtroFechaInicio = '';
            this.filtroFechaFin = '';
            this.filtroSucursal = '';
            this.paginaReparaciones = 1;
            this.cargarDatos();
        },
        async guardarMarca() {
            if (!this.formularioMarca.nombre) return;
            try {
                const headers = { Authorization: `Bearer ${this.token}` };
                await axios.post(`/api/reparaciones/marcas`, this.formularioMarca, { headers });
                this.mostrarMensaje('Marca guardada', 'exito');
                this.formularioMarca = { nombre: '' };
                this.mostrarFormularioMarca = false;
                this.paginaMarcas = 1;
                this.cargarDatos();
            } catch (err) {
                this.mostrarMensaje(err.response?.data?.error || 'Error', 'error');
            }
        },
        iniciarEdicionMarca(marca) {
            this.editandoMarcaId = marca.id;
            this.formularioMarca = { nombre: marca.nombre };
        },
        async guardarEdicionMarca() {
            if (!this.formularioMarca.nombre) return;
            try {
                const headers = { Authorization: `Bearer ${this.token}` };
                await axios.put(`/api/reparaciones/marcas/${this.editandoMarcaId}`, this.formularioMarca, { headers });
                this.mostrarMensaje('Marca actualizada', 'exito');
                this.editandoMarcaId = null;
                this.formularioMarca = { nombre: '' };
                this.cargarDatos();
            } catch (err) {
                this.mostrarMensaje(err.response?.data?.error || 'Error', 'error');
            }
        },
        cancelarEdicionMarca() {
            this.editandoMarcaId = null;
            this.formularioMarca = { nombre: '' };
        },
        async guardarModelo() {
            if (!this.formularioModelo.marca_id || !this.formularioModelo.nombre) return;
            try {
                const headers = { Authorization: `Bearer ${this.token}` };
                await axios.post(`/api/reparaciones/modelos`, this.formularioModelo, { headers });
                this.mostrarMensaje('Modelo guardado', 'exito');
                this.formularioModelo = { marca_id: '', nombre: '' };
                this.mostrarFormularioModelo = false;
                this.paginaModelos = 1;
                this.cargarDatos();
            } catch (err) {
                this.mostrarMensaje(err.response?.data?.error || 'Error', 'error');
            }
        },
        iniciarEdicionModelo(modelo) {
            this.editandoModeloId = modelo.id;
            this.formularioModelo = { marca_id: modelo.marca_id, nombre: modelo.nombre };
        },
        async guardarEdicionModelo() {
            if (!this.formularioModelo.marca_id || !this.formularioModelo.nombre) return;
            try {
                const headers = { Authorization: `Bearer ${this.token}` };
                await axios.put(`/api/reparaciones/modelos/${this.editandoModeloId}`, this.formularioModelo, { headers });
                this.mostrarMensaje('Modelo actualizado', 'exito');
                this.editandoModeloId = null;
                this.formularioModelo = { marca_id: '', nombre: '' };
                this.cargarDatos();
            } catch (err) {
                this.mostrarMensaje(err.response?.data?.error || 'Error', 'error');
            }
        },
        cancelarEdicionModelo() {
            this.editandoModeloId = null;
            this.formularioModelo = { marca_id: '', nombre: '' };
        },
        async guardarTipo() {
            if (!this.formularioTipo.nombre) return;
            try {
                const headers = { Authorization: `Bearer ${this.token}` };
                await axios.post(`/api/reparaciones/tipos`, this.formularioTipo, { headers });
                this.mostrarMensaje('Tipo guardado', 'exito');
                this.formularioTipo = { nombre: '', descripcion: '' };
                this.mostrarFormularioTipo = false;
                this.paginaTipos = 1;
                this.cargarDatos();
            } catch (err) {
                this.mostrarMensaje(err.response?.data?.error || 'Error', 'error');
            }
        },
        iniciarEdicionTipo(tipo) {
            this.editandoTipoId = tipo.id;
            this.formularioTipo = { nombre: tipo.nombre, descripcion: tipo.descripcion || '' };
        },
        async guardarEdicionTipo() {
            if (!this.formularioTipo.nombre) return;
            try {
                const headers = { Authorization: `Bearer ${this.token}` };
                await axios.put(`/api/reparaciones/tipos/${this.editandoTipoId}`, this.formularioTipo, { headers });
                this.mostrarMensaje('Tipo actualizado', 'exito');
                this.editandoTipoId = null;
                this.formularioTipo = { nombre: '', descripcion: '' };
                this.cargarDatos();
            } catch (err) {
                this.mostrarMensaje(err.response?.data?.error || 'Error', 'error');
            }
        },
        cancelarEdicionTipo() {
            this.editandoTipoId = null;
            this.formularioTipo = { nombre: '', descripcion: '' };
        },
        async guardarCatalogo() {
            if (!this.formularioCatalogo.marca_id || !this.formularioCatalogo.modelo_id || !this.formularioCatalogo.tipo_reparacion_id || !this.formularioCatalogo.costo) return;
            try {
                const headers = { Authorization: `Bearer ${this.token}` };
                await axios.post(`/api/reparaciones/catalogo`, this.formularioCatalogo, { headers });
                this.mostrarMensaje('Catálogo guardado', 'exito');
                this.formularioCatalogo = { marca_id: '', modelo_id: '', tipo_reparacion_id: '', costo: '' };
                this.mostrarFormularioCatalogo = false;
                this.paginaCatalogo = 1;
                this.cargarDatos();
            } catch (err) {
                this.mostrarMensaje(err.response?.data?.error || 'Error', 'error');
            }
        },
        async iniciarEdicionCatalogo(item) {
            this.editandoCatalogoId = item.id;
            this.formularioCatalogo = { marca_id: item.marca_id, modelo_id: item.modelo_id, tipo_reparacion_id: item.tipo_reparacion_id, costo: item.costo };
            await this.cargarModelosDeMarca(false);
        },
        async guardarEdicionCatalogo() {
            if (!this.formularioCatalogo.marca_id || !this.formularioCatalogo.modelo_id || !this.formularioCatalogo.tipo_reparacion_id || !this.formularioCatalogo.costo) return;
            try {
                const headers = { Authorization: `Bearer ${this.token}` };
                await axios.put(`/api/reparaciones/catalogo/${this.editandoCatalogoId}`, this.formularioCatalogo, { headers });
                this.mostrarMensaje('Catálogo actualizado', 'exito');
                this.editandoCatalogoId = null;
                this.formularioCatalogo = { marca_id: '', modelo_id: '', tipo_reparacion_id: '', costo: '' };
                this.cargarDatos();
            } catch (err) {
                this.mostrarMensaje(err.response?.data?.error || 'Error', 'error');
            }
        },
        cancelarEdicionCatalogo() {
            this.editandoCatalogoId = null;
            this.formularioCatalogo = { marca_id: '', modelo_id: '', tipo_reparacion_id: '', costo: '' };
        },
        cambiarItemsPerPageCatalogo() {
            this.paginaCatalogo = 1;
            this.cargarDatos();
        },
        buscarEnCatalogo() {
            this.paginaCatalogo = 1;
            this.cargarDatos();
        },
        async guardarReparacion() {
            if (!this.formularioReparacion.nombre_cliente || !this.formularioReparacion.marca_id || !this.formularioReparacion.modelo_nombre || !this.formularioReparacion.tipo_reparacion_id) return;
            
            // Validar que admin seleccione sucursal
            if (this.userRoleLocal === 'admin' && !this.formularioReparacion.sucursal_id) {
                this.mostrarMensaje('Admin debe seleccionar una sucursal', 'error');
                return;
            }
            
            try {
                const headers = { Authorization: `Bearer ${this.token}` };
                const datos = { ...this.formularioReparacion };
                delete datos.modelo_id;
                
                // Si es empleado, usar su sucursal_id; si es admin, ya está en el formulario
                if (this.userRoleLocal === 'employee') {
                    const userRes = await axios.get(`/api/auth/profile`, { headers });
                    datos.sucursal_id = userRes.data.sucursal_id;
                }
                
                // Buscar el costo en el catálogo si no está especificado
                if (!datos.costo || datos.costo === '') {
                    const catalogoItem = this.catalogo.find(cat => 
                        cat.marca_id === this.formularioReparacion.marca_id &&
                        cat.modelo_nombre?.toLowerCase() === this.formularioReparacion.modelo_nombre.toLowerCase() &&
                        cat.tipo_reparacion_id === this.formularioReparacion.tipo_reparacion_id
                    );
                    if (catalogoItem) {
                        datos.costo = catalogoItem.costo;
                    } else {
                        this.mostrarMensaje('No se encontró el costo en el catálogo. Por favor especifique el costo.', 'error');
                        return;
                    }
                }
                
                await axios.post(`/api/reparaciones`, datos, { headers });
                this.mostrarMensaje('Reparación registrada', 'exito');
                this.formularioReparacion = {
                    nombre_cliente: '',
                    telefono_cliente: '',
                    marca_id: '',
                    modelo_nombre: '',
                    tipo_reparacion_id: '',
                    costo: '',
                    sucursal_id: '',
                    fecha: new Date().toISOString().split('T')[0]
                };
                this.mostrarNuevaReparacion = false;
                this.cargarDatos();
            } catch (err) {
                this.mostrarMensaje(err.response?.data?.error || 'Error', 'error');
            }
        },
        async marcarEntregada(id) {
            try {
                const headers = { Authorization: `Bearer ${this.token}` };
                await axios.put(`/api/reparaciones/${id}/entregar`, {}, { headers });
                this.mostrarMensaje('Marcada como entregada', 'exito');
                this.cargarDatos();
            } catch (err) {
                this.mostrarMensaje(err.response?.data?.error || 'Error', 'error');
            }
        },
        async editarReparacion(rep) {
            this.formularioReparacion = {
                nombre_cliente: rep.nombre_cliente,
                telefono_cliente: rep.telefono_cliente,
                marca_id: rep.marca_id,
                modelo_nombre: rep.modelo_nombre,
                tipo_reparacion_id: rep.tipo_reparacion_id,
                costo: rep.costo,
                sucursal_id: rep.sucursal_id,
                fecha: rep.fecha
            };
            this.mostrarNuevaReparacion = true;
        },
        async cargarModelosPorMarca(marcaId) {
            if (!marcaId) {
                this.modelosFiltrados = [];
                return;
            }

            try {
                const headers = { Authorization: `Bearer ${this.token}` };
                const res = await axios.get(`/api/reparaciones/modelos`, {
                    params: { marca_id: marcaId, page: 1, per_page: 100 },
                    headers
                });
                const modelos = res.data.modelos || [];
                const totalPages = res.data.pages || 1;

                if (totalPages > 1) {
                    const pageRequests = [];
                    for (let page = 2; page <= totalPages; page++) {
                        pageRequests.push(axios.get(`/api/reparaciones/modelos`, {
                            params: { marca_id: marcaId, page, per_page: 100 },
                            headers
                        }));
                    }

                    const pages = await Promise.all(pageRequests);
                    pages.forEach(pageRes => {
                        modelos.push(...(pageRes.data.modelos || []));
                    });
                }

                this.modelosFiltrados = modelos;
            } catch (err) {
                this.modelosFiltrados = [];
                this.mostrarMensaje('Error al cargar modelos de la marca', 'error');
            }
        },
        async cargarModelosDeMarca(resetModelo = true) {
            if (resetModelo) {
                this.formularioCatalogo.modelo_id = '';
            }
            await this.cargarModelosPorMarca(this.formularioCatalogo.marca_id);
        },
        validarTelefono() {
            // Solo permite números y limita a 10 dígitos
            this.formularioReparacion.telefono_cliente = this.formularioReparacion.telefono_cliente
                .replace(/[^0-9]/g, '') // Elimina todo lo que no sea número
                .slice(0, 10); // Limita a 10 caracteres
        },
        async eliminarMarca(id) {
            if (confirm('¿Estás seguro?')) {
                try {
                    const headers = { Authorization: `Bearer ${this.token}` };
                    await axios.delete(`/api/reparaciones/marcas/${id}`, { headers });
                    this.mostrarMensaje('Marca eliminada', 'exito');
                    this.cargarDatos();
                } catch (err) {
                    this.mostrarMensaje(err.response?.data?.error || 'Error', 'error');
                }
            }
        },
        async eliminarModelo(id) {
            if (confirm('¿Estás seguro?')) {
                try {
                    const headers = { Authorization: `Bearer ${this.token}` };
                    await axios.delete(`/api/reparaciones/modelos/${id}`, { headers });
                    this.mostrarMensaje('Modelo eliminado', 'exito');
                    this.cargarDatos();
                } catch (err) {
                    this.mostrarMensaje(err.response?.data?.error || 'Error', 'error');
                }
            }
        },
        async eliminarTipo(id) {
            if (confirm('¿Estás seguro?')) {
                try {
                    const headers = { Authorization: `Bearer ${this.token}` };
                    await axios.delete(`/api/reparaciones/tipos/${id}`, { headers });
                    this.mostrarMensaje('Tipo eliminado', 'exito');
                    this.cargarDatos();
                } catch (err) {
                    this.mostrarMensaje(err.response?.data?.error || 'Error', 'error');
                }
            }
        },
        async eliminarCatalogo(id) {
            if (confirm('¿Estás seguro?')) {
                try {
                    const headers = { Authorization: `Bearer ${this.token}` };
                    await axios.delete(`/api/reparaciones/catalogo/${id}`, { headers });
                    this.mostrarMensaje('Catálogo eliminado', 'exito');
                    this.cargarDatos();
                } catch (err) {
                    this.mostrarMensaje(err.response?.data?.error || 'Error', 'error');
                }
            }
        },
        async eliminarReparacion(id) {
            if (confirm('¿Estás seguro de que deseas eliminar esta reparación?')) {
                try {
                    const headers = { Authorization: `Bearer ${this.token}` };
                    await axios.delete(`/api/reparaciones/${id}`, { headers });
                    this.mostrarMensaje('Reparación eliminada', 'exito');
                    this.cargarDatos();
                } catch (err) {
                    this.mostrarMensaje(err.response?.data?.error || 'Error', 'error');
                }
            }
        },
        mostrarMensaje(texto, tipo) {
            this.mensaje = { texto, tipo };
            setTimeout(() => { this.mensaje = null; }, 3000);
        }
    },
    computed: {
        sucursalEmpleado() {
            if (this.userSucursal) {
                const sucursal = this.sucursales.find(s => s.id === this.userSucursal);
                return sucursal ? sucursal.nombre : 'Desconocida';
            }
            return 'Cargando...';
        }
    }
};
// ============= COMPONENTE: AYUDA =============
const AyudaView = {
    props: {
        apiUrl: String,
        token: String,
        userRole: String
    },
    template: `
        <div style="padding: 1rem;">
            <h2 style="margin-bottom: 1.5rem;">📞 Centro de Ayuda</h2>
            
            <!-- Tabs -->
            <div class="tabs" style="display: flex; gap: 0.5rem; border-bottom: 2px solid var(--gray-300); margin-bottom: 2rem;">
                
                <button 
                    @click="tabActiva = 'ayuda-general'"
                    :class="['btn', 'btn-sm', tabActiva === 'ayuda-general' ? 'btn-primary' : 'btn-secondary']"
                >
                    ⚙️ Ayuda General
                </button>
            </div>
            
            <!-- Tab: Compatibilidad -->
            <div v-if="tabActiva === 'compatibilidad'">
                <compatibilidad-view 
                    :apiUrl="apiUrl" 
                    :token="token"
                    :userRole="userRole"
                ></compatibilidad-view>
            </div>
            
            <!-- Tab: Ayuda General -->
            <div v-if="tabActiva === 'ayuda-general'">
                <div class="card">
                    <h3>¿Necesitas Ayuda?</h3>
                    <p style="color: var(--gray-600); margin-bottom: 1.5rem;">
                        Cuéntanos qué problema tienes y nuestra IA te brindará una solución personalizada.
                    </p>
                    
                    <!-- Formulario de Ayuda -->
                    <div class="form-group" style="background: var(--gray-100); padding: 1rem; border-radius: 0.375rem; margin-bottom: 1.5rem;">
                        <!-- Modelo -->
                        <label>Modelo del Dispositivo *</label>
                        <input 
                            v-model="formulario.modelo" 
                            type="text" 
                            placeholder="ej: iPhone 13, Samsung Galaxy S21, Motorola G9, etc."
                            required
                        />
                        
                        <!-- Versión del SO (Opcional) -->
                        <label style="margin-top: 1rem;">Versión del SO (Opcional)</label>
                        <input 
                            v-model="formulario.version_so" 
                            type="text" 
                            placeholder="ej: iOS 17, Android 13"
                        />
                        <small style="color: var(--gray-500);">Si no especificas, usaremos la última versión disponible</small>
                        
                        <!-- Categoría -->
                        <label style="margin-top: 1rem;">¿Cuál es tu problema? *</label>
                        <select v-model="formulario.categoria" required>
                            <option value="">-- Selecciona una opción --</option>
                            <option value="formateo">Formateo del dispositivo</option>
                            <option value="gmail">Creación de cuenta Gmail</option>
                            <option value="icloud">Creación de cuenta iCloud</option>
                            <option value="bateria">Revisión de estado de batería</option>
                            <option value="otro">Otro (especificar)</option>
                        </select>
                        
                        <!-- Campo de texto para "Otro" -->
                        <div v-if="formulario.categoria === 'otro'" style="margin-top: 1rem;">
                            <label>Describe tu problema</label>
                            <textarea 
                                v-model="formulario.requerimiento_especifico" 
                                placeholder="Describe el problema específico que tienes..."
                                style="height: 100px;"
                                required
                            ></textarea>
                        </div>
                        
                        <!-- Botones -->
                        <div style="margin-top: 1.5rem; display: flex; gap: 0.5rem;">
                            <button 
                                @click="obtenerAyuda" 
                                class="btn btn-primary"
                                :disabled="!formulario.modelo || !formulario.categoria || cargandoAyuda"
                            >
                                {{ cargandoAyuda ? '🔄 Obteniendo solución...' : '🤖 Obtener Solución' }}
                            </button>
                            <button @click="limpiarFormulario" class="btn btn-secondary">Limpiar</button>
                        </div>
                    </div>
                    
                    <!-- Mensaje de error -->
                    <div v-if="errorAyuda" class="alert alert-danger" style="margin-bottom: 1rem;">
                        <strong>❌ Error:</strong> {{ errorAyuda }}
                    </div>
                    
                    <!-- Respuesta de la IA -->
                    <div v-if="respuestaIA" class="card" style="background: var(--gray-50); border-left: 4px solid var(--success); margin-top: 1.5rem;">
                        <h4 style="margin-top: 0;">💡 Solución Sugerida</h4>
                        <div v-html="respuestaFormateada" style="line-height: 1.8; color: var(--gray-700);"></div>
                        <button @click="copiarRespuesta" class="btn btn-sm btn-secondary" style="margin-top: 1rem;">
                            📋 Copiar Respuesta
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            tabActiva: 'compatibilidad',
            formulario: {
                modelo: '',
                version_so: '',
                categoria: '',
                requerimiento_especifico: ''
            },
            respuestaIA: '',
            cargandoAyuda: false,
            errorAyuda: ''
        };
    },
    computed: {
        apiUrlFinal() {
            return this.apiUrl || window.location.origin;
        },
        respuestaFormateada() {
            if (!this.respuestaIA) return '';
            // Convertir saltos de línea a <br> y negritas
            return this.respuestaIA
                .replace(/\n/g, '<br>')
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>');
        }
    },
    methods: {
        async obtenerAyuda() {
            this.errorAyuda = '';
            this.respuestaIA = '';
            
            // Validar campos requeridos
            if (!this.formulario.modelo || !this.formulario.categoria) {
                this.errorAyuda = 'Por favor completa todos los campos requeridos';
                return;
            }
            
            // Si es "Otro", validar que haya especificación
            if (this.formulario.categoria === 'otro' && !this.formulario.requerimiento_especifico) {
                this.errorAyuda = 'Por favor describe tu problema específico';
                return;
            }
            
            this.cargandoAyuda = true;
            
            try {
                const headers = { Authorization: `Bearer ${this.token}` };
                
                const response = await axios.post(
                    `${this.apiUrlFinal}/api/ayuda/obtener-solucion`,
                    {
                        modelo: this.formulario.modelo,
                        version_so: this.formulario.version_so || '',
                        categoria: this.formulario.categoria,
                        requerimiento_especifico: this.formulario.requerimiento_especifico || ''
                    },
                    { headers }
                );
                
                this.respuestaIA = response.data.solucion;
            } catch (error) {
                console.error('Error al obtener ayuda:', error);
                this.errorAyuda = error.response?.data?.error || 'Error al conectar con IA. Intenta nuevamente.';
            } finally {
                this.cargandoAyuda = false;
            }
        },
        
        limpiarFormulario() {
            this.formulario = {
                modelo: '',
                version_so: '',
                categoria: '',
                requerimiento_especifico: ''
            };
            this.respuestaIA = '';
            this.errorAyuda = '';
        },
        
        copiarRespuesta() {
            const texto = this.respuestaIA;
            navigator.clipboard.writeText(texto).then(() => {
                alert('✓ Respuesta copiada al portapapeles');
            }).catch(() => {
                alert('No se pudo copiar. Intenta manualmente.');
            });
        }
    }
};
