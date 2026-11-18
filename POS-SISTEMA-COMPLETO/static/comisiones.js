const ComisionesView = {
    props: ['token', 'userRole', 'userId'],
    template: `
        <section class="commissions-page">
            <header class="commissions-heading"><h1>Comisiones</h1><p>{{ userRole === 'admin' ? 'Consulta y aprueba las comisiones de todas las sucursales.' : 'Registra tu comisión a partir de una venta realizada.' }}</p></header>
            <p v-if="error" class="alert alert-danger" role="alert">{{ error }}</p>
            <p v-if="mensaje" class="alert alert-success" role="status">{{ mensaje }}</p>
            <form v-if="userRole !== 'admin' && ($root.puede('comisiones', 'crear') || (editandoId && $root.puede('comisiones', 'editar')))" @submit.prevent="guardar" class="card commission-capture">
                <div class="card-header"><h2>{{ editandoId ? 'Editar registro' : 'Registrar comisión' }}</h2></div>
                <fieldset :disabled="guardando || cargando" class="commission-layout" :class="{ 'commission-editing': editandoId }">
                    <div v-if="!editandoId" class="commission-picker">
                        <h3>Selecciona una venta</h3>
                        <div class="commission-search"><div class="form-group"><label for="com-fecha">Fecha de venta</label><input id="com-fecha" type="date" v-model="fechaVenta" min="2026-11-18" @change="buscarVentas" required></div><button class="btn btn-primary" type="button" @click="buscarVentas" :disabled="buscandoVentas">{{ buscandoVentas ? 'Buscando…' : 'Buscar' }}</button></div>
                        <p v-if="errorVentas" class="alert alert-danger" role="alert">{{ errorVentas }}</p>
                        <p class="commission-caption" role="status">{{ buscandoVentas ? 'Consultando ventas…' : busquedaRealizada ? pendientes.length + ' unidades disponibles' : 'Selecciona una fecha para consultar las ventas.' }}</p>
                        <div class="commission-units" role="group" aria-label="Unidades vendidas disponibles" :aria-busy="buscandoVentas">
                            <label v-for="u in pendientes" :key="claveUnidad(u)" class="commission-unit" :class="{ selected: unidadSeleccionada === claveUnidad(u) }">
                                <input type="radio" name="com-unidad" v-model="unidadSeleccionada" :value="claveUnidad(u)" :disabled="buscandoVentas" required @change="mensaje = ''">
                                <span class="commission-device" aria-hidden="true">▯</span>
                                <span class="commission-unit-name"><strong>{{ u.producto_nombre }}</strong><small>{{ u.numero_venta }} · Unidad {{ u.unidad }}</small></span>
                                <span class="commission-unit-price"><strong>{{ moneda(u.costo) }}</strong><small>{{ pagos[u.metodo_pago] || u.metodo_pago }}</small></span>
                            </label>
                            <p v-if="busquedaRealizada && !buscandoVentas && !pendientes.length" class="commission-empty">No hay celulares o tablets pendientes para esta fecha.</p>
                        </div>
                        <p class="commission-caption commission-note">Ventas desde el 18/11/2026. Los apartados cuentan por su fecha de entrega y venta.</p>
                    </div>
                    <div class="commission-summary">
                        <h3>Datos de la comisión</h3>
                        <p class="commission-caption">{{ editandoId ? 'Puedes corregir el nombre mientras el registro no esté aprobado.' : 'Los datos de la venta se llenan automáticamente.' }}</p>
                        <dl v-if="seleccionada && !editandoId"><dt>Producto</dt><dd>{{ seleccionada.producto_nombre }}</dd><dt>Precio de venta</dt><dd>{{ moneda(seleccionada.costo) }}</dd><dt>Método de pago</dt><dd>{{ pagos[seleccionada.metodo_pago] || seleccionada.metodo_pago }}</dd></dl>
                        <p v-else-if="!editandoId" class="commission-empty">Selecciona una unidad para ver sus datos.</p>
                        <div class="commission-name form-group"><label for="com-nombre">Nombre del empleado</label><input id="com-nombre" v-model="formulario.nombre_empleado" maxlength="150" required placeholder="Ej.: Jazmín" @input="mensaje = ''"></div>
                        <button class="btn btn-primary commission-submit" type="submit" :disabled="!editandoId && (!seleccionada || buscandoVentas)">{{ guardando ? 'Guardando…' : editandoId ? 'Guardar cambios' : 'Registrar comisión' }}</button>
                        <button v-if="editandoId" class="btn btn-secondary" type="button" @click="limpiar">Cancelar</button>
                    </div>
                </fieldset>
            </form>
            <section class="card commission-history">
                <div class="card-header"><h2>{{ userRole === 'admin' ? 'Comisiones registradas' : 'Comisiones de la sucursal' }}</h2><button class="btn btn-secondary" @click="actualizar" :disabled="cargando || guardando">Actualizar</button></div>
                <div class="commission-filters" role="group" aria-label="Filtrar por aprobación"><button v-for="f in filtros" :key="f.valor" type="button" :class="{ active: filtroEstado === f.valor }" :aria-pressed="filtroEstado === f.valor" @click="filtroEstado = f.valor">{{ f.nombre }}</button></div>
                <p v-if="cargando" class="commission-empty" role="status">Cargando comisiones…</p>
                <p v-else-if="!registrosFiltrados.length" class="commission-empty">No hay comisiones{{ filtroEstado === 'todas' ? ' registradas' : ' con este estado' }}.</p>
                <div v-else class="commission-table-scroll">
                    <table class="commission-table"><thead><tr><th>Producto / venta</th><th>Empleado / sucursal</th><th>Fechas</th><th>Comisión</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>
                        <tr v-for="registro in registrosFiltrados" :key="registro.id">
                            <td><strong>{{ registro.producto_nombre || registro.dispositivo }}</strong><small v-if="registro.detalle_venta_id">{{ registro.numero_venta }} · Unidad {{ registro.unidad }}</small><small v-else>Registro histórico sin vínculo a venta</small><small>{{ moneda(registro.costo) }} · {{ pagos[registro.metodo_pago] || registro.metodo_pago }}</small></td>
                            <td><strong>{{ registro.nombre_empleado }}</strong><small>{{ registro.sucursal_nombre }}</small></td>
                            <td><small v-if="registro.fecha_venta"><strong>Venta:</strong> {{ fecha(registro.fecha_venta) }}</small><small><strong>Registro:</strong> {{ fecha(registro.created_at) }}</small></td>
                            <td><template v-if="userRole === 'admin'"><label class="commission-caption" :for="'monto-' + registro.id">Monto de comisión</label><input class="commission-amount" :id="'monto-' + registro.id" v-model="montos[registro.id]" type="number" min="0" step="0.01" placeholder="0.00" :disabled="guardando"></template><strong v-else>{{ registro.monto_comision === null ? 'Pendiente' : moneda(registro.monto_comision) }}</strong></td>
                            <td><span class="commission-badge" :class="registro.aprobada ? 'approved' : 'pending'">{{ registro.aprobada ? 'Aprobada' : 'No aprobada' }}</span></td>
                            <td><div v-if="userRole === 'admin'" class="commission-row-actions"><button class="btn btn-primary btn-sm" @click="revisar(registro, registro.aprobada)" :disabled="guardando">Guardar monto</button><button v-if="!registro.aprobada" class="btn btn-success btn-sm" @click="revisar(registro, true)" :disabled="guardando">Aprobar</button><button v-else class="btn btn-secondary btn-sm" @click="revisar(registro, false)" :disabled="guardando">Quitar aprobación</button></div><div v-else-if="!registro.aprobada && registro.creado_por_id === userId" class="commission-row-actions"><button v-if="$root.puede('comisiones', 'editar')" class="btn btn-secondary btn-sm" @click="editar(registro)" :disabled="guardando">Editar</button><button v-if="$root.puede('comisiones', 'eliminar')" class="btn btn-danger btn-sm" @click="eliminar(registro)" :disabled="guardando">Eliminar</button></div><span v-else class="commission-caption">—</span></td>
                        </tr>
                    </tbody></table>
                </div>
            </section>
        </section>
    `,
    data() { return { filtroEstado: 'todas', filtros: [{ valor: 'todas', nombre: 'Todas' }, { valor: 'pendientes', nombre: 'No aprobadas' }, { valor: 'aprobadas', nombre: 'Aprobadas' }], registros: [], montos: {}, formulario: { nombre_empleado: '' }, pendientes: [], unidadSeleccionada: '', fechaVenta: '', buscandoVentas: false, errorVentas: '', busquedaRealizada: false, solicitudVentas: 0, editandoId: null, cargando: false, guardando: false, error: '', mensaje: '', pagos: { efectivo: 'Efectivo', tarjeta: 'Tarjeta', transferencia: 'Transferencia', mixto: 'Mixto' } }; },
    watch: {
        '$root.userSucursal'() {
            this.limpiar(); this.registros = []; this.actualizar();
        }
    },
    computed: {
        registrosFiltrados() { return this.registros.filter(r => this.filtroEstado === 'todas' || (this.filtroEstado === 'aprobadas' ? r.aprobada : !r.aprobada)); },
        seleccionada() { return this.pendientes.find(u => this.claveUnidad(u) === this.unidadSeleccionada) || null; }
    },
    methods: {
        async actualizar() {
            await this.cargar();
            if (this.userRole !== 'admin' && (this.$root.puede('comisiones', 'crear') || this.$root.puede('comisiones', 'editar'))) await this.buscarVentas();
        },
        claveUnidad(u) { return u.detalle_venta_id + ':' + u.unidad; },
        async buscarVentas() {
            const solicitud = ++this.solicitudVentas;
            this.unidadSeleccionada = ''; this.pendientes = []; this.errorVentas = ''; this.busquedaRealizada = false; this.buscandoVentas = false;
            if (!this.fechaVenta || this.fechaVenta < '2026-11-18') { this.errorVentas = 'Selecciona una fecha desde el 18/11/2026.'; return; }
            this.buscandoVentas = true;
            try {
                const r = await axios.get('/api/comisiones/pendientes', { ...this.opciones(), params: { fecha: this.fechaVenta } });
                if (solicitud !== this.solicitudVentas) return;
                this.pendientes = r.data.unidades || []; this.busquedaRealizada = true;
            } catch (e) {
                if (solicitud === this.solicitudVentas) this.errorVentas = e.response?.data?.error || 'No se pudieron consultar las ventas pendientes';
            } finally { if (solicitud === this.solicitudVentas) this.buscandoVentas = false; }
        },
        opciones() { return { headers: { Authorization: `Bearer ${this.token}` } }; },
        fallo(err) {
            this.error = err.response?.data?.error || 'No se pudo completar la operación';
            if (err.response?.status === 403 && this.userRole !== 'admin') {
                this.registros = []; this.limpiar();
                window.dispatchEvent(new Event('caracteristicas-actualizadas'));
            }
        },
        async cargar() {
            this.cargando = true; this.error = '';
            try {
                const res = await axios.get('/api/comisiones', this.opciones());
                this.registros = res.data.comisiones;
                this.montos = Object.fromEntries(this.registros.map(r => [r.id, r.monto_comision ?? '']));
            } catch (err) { this.fallo(err); }
            finally { this.cargando = false; }
        },
        limpiar() { this.editandoId = null; this.formulario = { nombre_empleado: '' }; this.unidadSeleccionada = ''; },
        editar(registro) {
            if (registro.aprobada || this.userRole === 'admin') return;
            this.editandoId = registro.id;
            this.formulario = { nombre_empleado: registro.nombre_empleado };
            this.mensaje = ''; this.error = '';
            window.scrollTo({ top: 0, behavior: 'smooth' });
        },
        async guardar() {
            if (this.guardando) return;
            this.guardando = true; this.error = ''; this.mensaje = '';
            try {
                if (this.editandoId) await axios.put('/api/comisiones/' + this.editandoId, this.formulario, this.opciones());
                else {
                    if (!this.seleccionada) { this.error = 'Selecciona una unidad vendida.'; return; }
                    await axios.post('/api/comisiones', { nombre_empleado: this.formulario.nombre_empleado,
                        detalle_venta_id: this.seleccionada.detalle_venta_id, unidad: this.seleccionada.unidad }, this.opciones());
                }
                this.limpiar(); await this.cargar(); await this.buscarVentas(); this.mensaje = 'Registro guardado.';
            } catch (err) { this.fallo(err); }
            finally { this.guardando = false; }
        },
        async revisar(registro, aprobada) {
            if (this.guardando || this.userRole !== 'admin') return;
            this.guardando = true; this.error = ''; this.mensaje = '';
            try {
                await axios.put('/api/comisiones/' + registro.id, { monto_comision: this.montos[registro.id], aprobada }, this.opciones());
                await this.cargar(); this.mensaje = 'Comisión actualizada.';
            } catch (err) { this.fallo(err); }
            finally { this.guardando = false; }
        },
        async eliminar(registro) {
            if (this.guardando || registro.aprobada || !confirm('¿Eliminar este registro de comisión?')) return;
            this.guardando = true; this.error = ''; this.mensaje = '';
            try {
                await axios.delete('/api/comisiones/' + registro.id, this.opciones());
                if (this.editandoId === registro.id) this.limpiar();
                await this.cargar(); await this.buscarVentas(); this.mensaje = 'Registro eliminado.';
            } catch (err) { this.fallo(err); }
            finally { this.guardando = false; }
        },
        moneda(valor) { return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(valor); },
        fecha(valor) { return new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Mexico_City' }).format(new Date(valor)); }
    },
    mounted() {
        const partes = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Mexico_City', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date());
        const valores = Object.fromEntries(partes.map(p => [p.type, p.value]));
        this.fechaVenta = [valores.year, valores.month, valores.day].join('-');
        this.cargar();
        if (this.userRole !== 'admin' && (this.$root.puede('comisiones', 'crear') || this.$root.puede('comisiones', 'editar'))) this.buscarVentas();
    }
};
