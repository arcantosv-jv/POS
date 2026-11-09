const ApartadosView = {
    props: ['token', 'userRole'],
    data() { return { registros: [], productos: [], sucursales: [], filtro: '', busqueda: '', creando: false, detalle: null, accion: '', ocupado: false, error: '', mensaje: '', seccion: 'todos',
        form: { cliente: '', telefono: '', empleado: '', observaciones: '', plazo: 30, sucursal_id: '', productos: [], anticipo: 0 },
        pago: { monto: 0, empleado: '', motivo: '', efectivo: 0, tarjeta: 0, transferencia: 0 } }; },
    computed: {
        visibles() { return this.userRole === 'admin' && this.seccion === 'sin-stock' ? this.registros.filter(r => r.sin_existencias) : this.registros; },
        encontrados() { const q = this.busqueda.trim().toLocaleLowerCase(); return q ? this.productos.filter(p => (p.nombre + ' ' + p.codigo).toLocaleLowerCase().includes(q)) : []; },
        total() { return this.form.productos.reduce((t, p) => t + Math.round(Number(p.precio || 0) * 100)/100 * p.cantidad, 0); }
    },
    methods: {
        fechaEntrega(v) { return v ? new Intl.DateTimeFormat('es-MX', { timeZone: 'America/Mexico_City', dateStyle: 'medium', timeStyle: 'short' }).format(new Date(v)) : '—'; },
        moneda(v) { return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(v); },
        headers() { return { Authorization: 'Bearer ' + this.token }; },
        async cargar() { try { const r = await axios.get('/api/apartados', { headers: this.headers(), params: { sucursal_id: this.filtro || undefined } }); this.registros = r.data.apartados; } catch (e) { this.error = e.response?.data?.error || 'No se pudieron cargar los apartados'; } },
        async nuevo() {
            this.error = ''; this.mensaje = ''; this.detalle = null;
            this.form = { cliente: '', telefono: '', empleado: '', observaciones: '', plazo: 30, sucursal_id: this.userRole === 'admin' ? this.filtro : this.$root.sucursalPrincipal, productos: [], anticipo: 0 };
            this.pago = { efectivo: 0, tarjeta: 0, transferencia: 0 };
            this.creando = true;
            try {
                let pagina = 1, paginas = 1, productos = [];
                do { const r = await axios.get('/api/productos', { headers: this.headers(), params: { page: pagina, per_page: 1000 } }); productos.push(...r.data.productos); paginas = r.data.pages; pagina++; } while (pagina <= paginas);
                this.productos = productos;
            } catch (e) { this.error = 'No se pudo cargar el catálogo'; }
        },
        agregar(p) { const existe = this.form.productos.find(l => l.producto_id === p.id); if (existe) existe.cantidad++; else this.form.productos.push({ producto_id: p.id, nombre: p.nombre, precio: '', cantidad: 1 }); this.busqueda = ''; },
        pagos() { return ['efectivo', 'tarjeta', 'transferencia'].filter(m => Number(this.pago[m]) > 0).map(m => ({ metodo: m, monto: Number(this.pago[m]) })); },
        async guardar() {
            if (this.ocupado) return;
            this.ocupado = true; this.error = '';
            try { const r = await axios.post('/api/apartados', { ...this.form, pagos: this.pagos() }, { headers: this.headers() }); this.creando = false; this.detalle = r.data; this.mensaje = 'Apartado registrado correctamente.'; await this.cargar(); }
            catch (e) { this.error = e.response?.data?.error || 'No se pudo registrar. Consulta la lista antes de reintentar.'; }
            finally { this.ocupado = false; }
        },
        abrir(r) { this.detalle = r; this.creando = false; this.accion = ''; this.error = ''; this.mensaje = ''; },
        preparar(accion) { this.accion = accion; this.pago = { monto: 0, empleado: '', motivo: '', efectivo: 0, tarjeta: 0, transferencia: 0 }; this.error = ''; this.mensaje = ''; },
        async operar() {
            if (this.ocupado) return;
            this.ocupado = true; this.error = '';
            try { const r = await axios.post('/api/apartados/' + this.detalle.id + '/' + this.accion, { empleado: this.pago.empleado, monto: this.pago.monto, devolucion: this.pago.monto, motivo: this.pago.motivo, pagos: this.pagos() }, { headers: this.headers() }); this.detalle = r.data; this.accion = ''; this.mensaje = 'Operación registrada.'; await this.cargar(); }
            catch (e) { this.error = e.response?.data?.error || 'No se pudo registrar. Revisa el historial antes de reintentar.'; }
            finally { this.ocupado = false; }
        }
    },
    async mounted() { await this.cargar(); try { const r = await axios.get('/api/admin/sucursales-publico', { headers: this.headers() }); this.sucursales = r.data; } catch (e) { this.error = 'No se pudieron cargar las sucursales'; } },
    template: `
    <section>
        <div class="reportes-intro"><div><h1>Apartados</h1><p>Los abonos se acumulan en el apartado. Al entregar, el total se registra como venta y entra al corte del día.</p></div></div>
        <div class="card">
            <div class="card-header"><h3>Apartados de clientes</h3><button v-if="$root.puede('apartados', 'crear')" class="btn btn-primary" @click="nuevo" :disabled="ocupado">+ Nuevo apartado</button></div>
            <div v-if="userRole === 'admin' && !creando" class="form-group"><label>Filtrar por sucursal</label><select v-model="filtro" @change="cargar"><option value="">Todas</option><option v-for="s in sucursales" :value="s.id" :key="s.id">{{ s.nombre }}</option></select></div>
            <div v-if="userRole === 'admin' && !creando" class="reportes-tabs" style="margin-bottom:1rem;">
                <button type="button" :class="{ activo: seccion === 'todos' }" @click="seccion='todos'; detalle=null; accion=''">Todos los apartados</button>
                <button type="button" :class="{ activo: seccion === 'sin-stock' }" @click="seccion='sin-stock'; detalle=null; accion=''">Registrados sin existencias ({{ registros.filter(r => r.sin_existencias).length }})</button>
            </div>
            <p v-if="userRole === 'admin' && seccion === 'sin-stock' && !creando">Incluye apartados que se registraron con faltantes, aunque después se hayan entregado o cancelado.</p>
            <div v-if="error" class="alert alert-danger" role="alert">{{ error }}</div><div v-if="mensaje" class="alert alert-success">{{ mensaje }}</div>
            <form v-if="creando" @submit.prevent="guardar">
                <fieldset :disabled="ocupado" style="border:0;padding:0;">
                <div class="grid grid-3">
                    <div class="form-group"><label>Cliente *</label><input v-model="form.cliente" required maxlength="150"></div>
                    <div class="form-group"><label>Teléfono *</label><input v-model="form.telefono" type="tel" inputmode="numeric" pattern="[0-9]{10}" minlength="10" maxlength="10" @input="form.telefono = $event.target.value.replace(/[^0-9]/g, '').slice(0, 10); $event.target.value = form.telefono" title="Ingresa exactamente 10 dígitos" required></div>
                    <div class="form-group"><label>Quién aparta *</label><input v-model="form.empleado" required maxlength="150"></div>
                    <div class="form-group"><label>Sucursal *</label><select v-model="form.sucursal_id" required :disabled="userRole !== 'admin'"><option v-if="userRole === 'admin'" value="" disabled>Selecciona la sucursal del apartado</option><option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option></select></div>
                    <div class="form-group"><label>Plazo</label><select v-model.number="form.plazo"><option :value="15">15 días</option><option :value="30">30 días</option><option :value="45">45 días</option></select></div>
                </div>
                <div class="form-group"><label>Buscar producto por nombre o código</label><input v-model="busqueda" placeholder="Buscar…"><div style="max-height:220px;overflow:auto;"><button v-for="p in encontrados" :key="p.id" type="button" class="btn btn-secondary" style="display:block;margin:.3rem 0;" @click="agregar(p)">{{ p.nombre }} · {{ p.codigo }}</button></div></div>
                <div v-for="(p,i) in form.productos" :key="p.producto_id" class="grid grid-3" style="align-items:end;">
                    <div class="form-group"><label>{{ p.nombre }} · Precio</label><input type="number" min="0" step=".01" v-model.number="p.precio" required></div>
                    <div class="form-group"><label>Cantidad</label><input type="number" min="1" step="1" v-model.number="p.cantidad" required></div><button type="button" class="btn btn-secondary" @click="form.productos.splice(i,1)">Quitar</button>
                </div>
                <p><strong>Total: {{ moneda(total) }}</strong></p>
                <div class="form-group"><label>Anticipo</label><input type="number" v-model.number="form.anticipo" min="0" :max="total" step=".01" required></div>
                <p>Restante: {{ moneda(total - form.anticipo) }}</p>
                <p>Desglose del anticipo (combina métodos para pago mixto):</p>
                <div class="grid grid-3"><div class="form-group" v-for="m in ['efectivo','tarjeta','transferencia']" :key="m"><label>{{ m }}</label><input type="number" min="0" step=".01" v-model.number="pago[m]"></div></div>
                <div class="form-group"><label>Observaciones</label><textarea v-model="form.observaciones" maxlength="2000"></textarea></div>
                <button class="btn btn-primary" :disabled="!form.productos.length">{{ ocupado ? 'Guardando…' : 'Registrar apartado' }}</button><button type="button" class="btn btn-secondary" @click="creando=false">Cerrar</button>
                </fieldset>
            </form>
            <div v-if="!creando" style="overflow:auto;"><table><thead><tr><th>Folio / sucursal</th><th>Cliente</th><th>Vence</th><th>Estado</th><th>Fecha de entrega (CDMX)</th><th>Total</th><th>Restante</th><th></th></tr></thead><tbody><tr v-for="r in visibles" :key="r.id"><td>{{ r.folio }}<br>{{ r.sucursal }}</td><td>{{ r.cliente }}</td><td>{{ r.vence }} <strong v-if="r.vencido" style="color:#b45309;">Vencido</strong></td><td>{{ r.estado }}</td><td>{{ fechaEntrega(r.fecha_entrega) }}</td><td>{{ moneda(r.total) }}</td><td>{{ moneda(r.restante) }}</td><td><button class="btn btn-secondary" @click="abrir(r)" :disabled="ocupado">Detalle</button></td></tr></tbody></table><p v-if="!visibles.length">No hay apartados registrados.</p></div>
        </div>
        <div v-if="detalle && !creando" class="card">
            <div class="card-header"><h3>{{ detalle.folio }} · {{ detalle.cliente }}</h3></div>
            <p>{{ detalle.telefono }} · {{ detalle.sucursal }} · Registrado: {{ detalle.fecha }} · Empleado: {{ detalle.empleado }}</p><p v-if="detalle.fecha_entrega"><strong>Entregado:</strong> {{ fechaEntrega(detalle.fecha_entrega) }} (CDMX)</p><p v-if="detalle.venta_id"><strong>Venta registrada:</strong> {{ detalle.venta_id }}</p><p>{{ detalle.observaciones }}</p>
            <ul><li v-for="p in detalle.productos" :key="p.producto_id">{{ p.cantidad }} × {{ p.nombre }} · {{ moneda(p.precio) }} c/u <strong v-if="userRole === 'admin' && p.faltantes" style="color:#b45309;"> · Sin existencias al registrar: {{ p.faltantes }} · Reservados: {{ p.reservados }}</strong></li></ul>
            <p><strong>Total: {{ moneda(detalle.total) }} · Abonado: {{ moneda(detalle.abonado) }} · Restante: {{ moneda(detalle.restante) }}</strong></p>
            <div v-if="['pendiente','liquidado'].includes(detalle.estado)" class="btn-group">
                <button v-if="$root.puede('apartados','abonar') && detalle.restante > 0" class="btn btn-primary" @click="preparar('abonar')" :disabled="ocupado">Registrar abono</button>
                <button v-if="$root.puede('apartados','entregar') && detalle.restante === 0" class="btn btn-success" @click="preparar('entregar')" :disabled="ocupado">Entregar</button>
                <button v-if="userRole === 'admin'" class="btn btn-danger" @click="preparar('cancelar')" :disabled="ocupado">Cancelar / devolución</button>
            </div>
            <form v-if="accion" @submit.prevent="operar" style="margin-top:1rem;"><fieldset :disabled="ocupado" style="border:0;padding:0;">
                <h4>{{ accion === 'cancelar' ? 'Cancelar y liberar inventario' : accion === 'entregar' ? 'Confirmar entrega' : 'Nuevo abono' }}</h4>
                <div class="form-group"><label>Nombre del empleado *</label><input v-model="pago.empleado" required maxlength="150"></div>
                <template v-if="accion !== 'entregar'"><div class="form-group"><label>{{ accion === 'cancelar' ? 'Importe devuelto al cliente' : 'Importe del abono' }}</label><input v-model.number="pago.monto" type="number" :min="accion === 'abonar' ? .01 : 0" :max="accion === 'abonar' ? detalle.restante : detalle.abonado" step=".01" required></div>
                <div class="grid grid-3"><div class="form-group" v-for="m in ['efectivo','tarjeta','transferencia']" :key="m"><label>{{ m }}</label><input type="number" min="0" step=".01" v-model.number="pago[m]"></div></div></template>
                <div v-if="accion === 'cancelar'" class="form-group"><label>Motivo *</label><textarea v-model="pago.motivo" required maxlength="2000"></textarea><small>Registra únicamente el dinero devuelto. No genera movimientos en caja.</small></div>
                <button class="btn btn-primary">{{ ocupado ? 'Guardando…' : 'Confirmar' }}</button><button type="button" class="btn btn-secondary" @click="accion=''">Cerrar</button>
            </fieldset></form>
            <h4 style="margin-top:1.5rem;">Historial</h4><ul><li v-for="(m,i) in detalle.movimientos" :key="i">{{ m.fecha }} · {{ m.tipo }} · {{ m.empleado }} <strong v-if="m.monto">{{ moneda(m.monto) }}</strong><span v-for="(p,j) in m.pagos || []" :key="j"> · {{ p.metodo }} {{ moneda(p.monto) }}</span><p v-if="m.motivo">{{ m.motivo }}</p></li></ul>
        </div>
    </section>`
};
