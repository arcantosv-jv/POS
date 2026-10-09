const ComisionesView = {
    props: ['token', 'userRole', 'userId'],
    template: `
        <section class="card">
            <div class="card-header"><h2>Comisiones</h2><button class="btn btn-secondary" @click="cargar" :disabled="cargando || guardando">Actualizar</button></div>
            <p class="cash-register-help">Registro independiente de ventas y cierre de caja. Fechas y horarios de Ciudad de México.</p>
            <p v-if="error" class="alert alert-danger" role="alert">{{ error }}</p>
            <p v-if="mensaje" class="alert alert-success" role="status">{{ mensaje }}</p>
            <form v-if="userRole !== 'admin'" @submit.prevent="guardar" class="cash-register-form">
                <h3>{{ editandoId ? 'Editar registro' : 'Registrar comisión' }}</h3>
                <fieldset :disabled="guardando || cargando" class="commission-form">
                    <div class="form-group"><label for="com-dispositivo">Dispositivo *</label><select id="com-dispositivo" v-model="formulario.dispositivo" required><option value="" disabled>Selecciona una opción</option><option>Celular</option><option>Tablet</option></select></div>
                    <div class="form-group"><label for="com-costo">Costo de venta *</label><input id="com-costo" v-model="formulario.costo" type="number" min="0" step="0.01" required placeholder="0.00"></div>
                    <div class="form-group"><label for="com-pago">Método de pago *</label><select id="com-pago" v-model="formulario.metodo_pago" required><option value="" disabled>Selecciona una opción</option><option value="efectivo">Efectivo</option><option value="tarjeta">Tarjeta</option><option value="transferencia">Transferencia</option></select></div>
                    <div class="form-group"><label for="com-nombre">Usuario (nombre del empleado) *</label><input id="com-nombre" v-model="formulario.nombre_empleado" maxlength="150" required placeholder="Ej.: Jazmin"></div>
                    <div><button class="btn btn-primary" type="submit">{{ guardando ? 'Guardando…' : editandoId ? 'Guardar cambios' : 'Registrar' }}</button> <button v-if="editandoId" class="btn btn-secondary" type="button" @click="limpiar">Cancelar</button></div>
                </fieldset>
            </form>
            <p v-if="cargando" role="status">Cargando comisiones…</p>
            <p v-if="!cargando && !registros.length">No hay comisiones registradas.</p>
            <article v-for="registro in registros" :key="registro.id" class="cash-close-card commission-record">
                <header><h3>{{ registro.sucursal_nombre }}, {{ registro.nombre_empleado }}</h3><strong :class="registro.aprobada ? 'text-success' : 'text-warning'">{{ registro.aprobada ? 'Aprobada' : 'No aprobada' }}</strong></header>
                <p>{{ fecha(registro.created_at) }} · {{ registro.dispositivo }} · {{ pagos[registro.metodo_pago] }}</p>
                <p><strong>Costo de venta:</strong> {{ moneda(registro.costo) }} · <strong>Comisión:</strong> {{ registro.monto_comision === null ? 'Sin asignar' : moneda(registro.monto_comision) }}</p>
                <div v-if="userRole === 'admin'" class="commission-actions">
                    <div class="form-group"><label :for="'monto-' + registro.id">Monto de comisión</label><input :id="'monto-' + registro.id" v-model="montos[registro.id]" type="number" min="0" step="0.01" placeholder="0.00" :disabled="guardando"></div>
                    <button class="btn btn-primary" @click="revisar(registro, registro.aprobada)" :disabled="guardando">Guardar monto</button>
                    <button v-if="!registro.aprobada" class="btn btn-success" @click="revisar(registro, true)" :disabled="guardando">Aprobada</button>
                    <button v-else class="btn btn-secondary" @click="revisar(registro, false)" :disabled="guardando">Quitar aprobación</button>
                </div>
                <div v-else-if="!registro.aprobada && registro.creado_por_id === userId"><button class="btn btn-secondary btn-sm" @click="editar(registro)" :disabled="guardando">Editar</button> <button class="btn btn-danger btn-sm" @click="eliminar(registro)" :disabled="guardando">Eliminar</button></div>
            </article>
        </section>
    `,
    data() { return { registros: [], montos: {}, formulario: { dispositivo: '', costo: '', metodo_pago: '', nombre_empleado: '' }, editandoId: null, cargando: false, guardando: false, error: '', mensaje: '', pagos: { efectivo: 'Efectivo', tarjeta: 'Tarjeta', transferencia: 'Transferencia' } }; },
    methods: {
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
        limpiar() { this.editandoId = null; this.formulario = { dispositivo: '', costo: '', metodo_pago: '', nombre_empleado: '' }; },
        editar(registro) {
            if (registro.aprobada || this.userRole === 'admin') return;
            this.editandoId = registro.id;
            this.formulario = { dispositivo: registro.dispositivo, costo: registro.costo, metodo_pago: registro.metodo_pago, nombre_empleado: registro.nombre_empleado };
            this.mensaje = ''; this.error = '';
            window.scrollTo({ top: 0, behavior: 'smooth' });
        },
        async guardar() {
            if (this.guardando) return;
            this.guardando = true; this.error = ''; this.mensaje = '';
            try {
                if (this.editandoId) await axios.put('/api/comisiones/' + this.editandoId, this.formulario, this.opciones());
                else await axios.post('/api/comisiones', this.formulario, this.opciones());
                this.limpiar(); await this.cargar(); this.mensaje = 'Registro guardado.';
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
                await this.cargar(); this.mensaje = 'Registro eliminado.';
            } catch (err) { this.fallo(err); }
            finally { this.guardando = false; }
        },
        moneda(valor) { return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(valor); },
        fecha(valor) { return new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Mexico_City' }).format(new Date(valor)); }
    },
    mounted() { this.cargar(); }
};
